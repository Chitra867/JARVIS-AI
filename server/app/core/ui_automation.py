from dataclasses import (
    dataclass,
)

import win32gui

from pywinauto import (
    Desktop,
)


# ======================================================
# TARGET
# ======================================================


@dataclass(
    frozen=True
)
class UIAutomationTarget:
    name: str
    control_type: str

    left: int
    top: int
    right: int
    bottom: int

    center_x: int
    center_y: int

    enabled: bool
    visible: bool

    automation_id: str = ""


# ======================================================
# LOOKUP RESULT
# ======================================================


@dataclass(
    frozen=True
)
class UIAutomationResolution:
    query: str
    status: str

    target: (
        UIAutomationTarget
        | None
    )

    candidates: tuple[
        UIAutomationTarget,
        ...,
    ]

    reason: str

    @property
    def resolved(
        self,
    ) -> bool:
        return (
            self.status
            == "resolved"
            and
            self.target
            is not None
        )

    @property
    def ambiguous(
        self,
    ) -> bool:
        return (
            self.status
            == "ambiguous"
        )


# ======================================================
# PARSED QUERY
# ======================================================


@dataclass(
    frozen=True
)
class _ParsedQuery:
    label: str

    control_types: tuple[
        str,
        ...,
    ]


# ======================================================
# SERVICE
# ======================================================


class UIAutomationService:
    # ==================================================
    # PUBLIC — FIND TARGET
    # ==================================================

    def find_target(
        self,
        query: str,
    ) -> UIAutomationTarget | None:
        """
        Compatibility helper.

        Returns a target only when the lookup resolves
        to exactly one safe UI Automation candidate.

        Ambiguous and missing targets both return None.

        For safety-sensitive operations, use
        resolve_target() instead so ambiguity can be
        distinguished from a genuine not-found result.
        """

        resolution = (
            self.resolve_target(
                query
            )
        )

        if not (
            resolution.resolved
        ):
            return None

        return (
            resolution.target
        )

    # ==================================================
    # PUBLIC — RESOLVE TARGET
    # ==================================================

    def resolve_target(
        self,
        query: str,
    ) -> UIAutomationResolution:
        original_query = (
            query
            .strip()
        )

        parsed_query = (
            self._parse_query(
                original_query
            )
        )

        if not (
            parsed_query.label
        ):
            return (
                UIAutomationResolution(
                    query=(
                        original_query
                    ),

                    status="not_found",

                    target=None,

                    candidates=(),

                    reason=(
                        "The target query "
                        "was empty."
                    ),
                )
            )

        try:
            window = (
                self._get_foreground_window()
            )

            if (
                window
                is None
            ):
                return (
                    UIAutomationResolution(
                        query=(
                            original_query
                        ),

                        status="not_found",

                        target=None,

                        candidates=(),

                        reason=(
                            "No foreground window "
                            "was available."
                        ),
                    )
                )

            scored_candidates: list[
                tuple[
                    int,
                    UIAutomationTarget,
                ]
            ] = []

            for control in (
                window.descendants()
            ):
                candidate = (
                    self._build_target(
                        control
                    )
                )

                if (
                    candidate
                    is None
                ):
                    continue

                # ======================================
                # OPTIONAL CONTROL-TYPE FILTER
                # ======================================

                if (
                    parsed_query
                    .control_types
                    and
                    candidate.control_type
                    not in (
                        parsed_query
                        .control_types
                    )
                ):
                    continue

                score = (
                    self._match_score(
                        query=(
                            parsed_query
                            .label
                        ),
                        name=(
                            candidate
                            .name
                        ),
                    )
                )

                if (
                    score
                    <= 0
                ):
                    continue

                scored_candidates.append(
                    (
                        score,
                        candidate,
                    )
                )

            # ==========================================
            # NOTHING MATCHED
            # ==========================================

            if not (
                scored_candidates
            ):
                return (
                    UIAutomationResolution(
                        query=(
                            original_query
                        ),

                        status="not_found",

                        target=None,

                        candidates=(),

                        reason=(
                            "No visible UI Automation "
                            "element matched the query."
                        ),
                    )
                )

            # ==========================================
            # ONLY CONSIDER BEST MATCH TIER
            # ==========================================

            highest_score = max(
                score

                for (
                    score,
                    _
                )
                in scored_candidates
            )

            best_candidates = [
                candidate

                for (
                    score,
                    candidate
                )
                in scored_candidates

                if (
                    score
                    == highest_score
                )
            ]

            # ==========================================
            # REMOVE DUPLICATE UIA REPRESENTATIONS
            # ==========================================

            best_candidates = (
                self._deduplicate_targets(
                    best_candidates
                )
            )

            # ==========================================
            # UNIQUE TARGET
            # ==========================================

            if (
                len(
                    best_candidates
                )
                == 1
            ):
                target = (
                    best_candidates[0]
                )

                return (
                    UIAutomationResolution(
                        query=(
                            original_query
                        ),

                        status="resolved",

                        target=target,

                        candidates=(
                            target,
                        ),

                        reason=(
                            "Exactly one highest-"
                            "quality visible match "
                            "was found."
                        ),
                    )
                )

            # ==========================================
            # AMBIGUOUS TARGET
            # ==========================================

            return (
                UIAutomationResolution(
                    query=(
                        original_query
                    ),

                    status="ambiguous",

                    target=None,

                    candidates=tuple(
                        best_candidates
                    ),

                    reason=(
                        "Multiple equally strong "
                        "visible matches were found."
                    ),
                )
            )

        except Exception as error:
            print(
                (
                    "UI Automation lookup failed: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

            return (
                UIAutomationResolution(
                    query=(
                        original_query
                    ),

                    status="error",

                    target=None,

                    candidates=(),

                    reason=(
                        "UI Automation lookup "
                        "failed."
                    ),
                )
            )

    # ==================================================
    # PUBLIC — FIND CANDIDATES
    # ==================================================

    def find_candidates(
        self,
        query: str,
    ) -> tuple[
        UIAutomationTarget,
        ...,
    ]:
        """
        Useful for diagnostics and future clarification
        UI. This method never chooses between ambiguous
        candidates.
        """

        resolution = (
            self.resolve_target(
                query
            )
        )

        return (
            resolution.candidates
        )

    # ==================================================
    # FOREGROUND WINDOW
    # ==================================================

    def _get_foreground_window(
        self,
    ):
        hwnd = (
            win32gui
            .GetForegroundWindow()
        )

        if not hwnd:
            return None

        return (
            Desktop(
                backend="uia"
            )
            .window(
                handle=hwnd
            )
            .wrapper_object()
        )

    # ==================================================
    # BUILD TARGET
    # ==================================================

    def _build_target(
        self,
        control,
    ) -> UIAutomationTarget | None:
        try:
            name = (
                control
                .window_text()
                .strip()
            )

            if not name:
                return None

            visible = bool(
                control
                .is_visible()
            )

            if not visible:
                return None

            enabled = bool(
                control
                .is_enabled()
            )

            rectangle = (
                control
                .rectangle()
            )

            left = int(
                rectangle.left
            )

            top = int(
                rectangle.top
            )

            right = int(
                rectangle.right
            )

            bottom = int(
                rectangle.bottom
            )

            # Invalid/empty rectangles cannot safely
            # represent an actionable screen target.
            if (
                right
                <= left
                or
                bottom
                <= top
            ):
                return None

            control_type = (
                str(
                    control
                    .element_info
                    .control_type
                )
                .strip()
            )

            automation_id = (
                str(
                    getattr(
                        control
                        .element_info,
                        "automation_id",
                        "",
                    )
                    or ""
                )
                .strip()
            )

            return (
                UIAutomationTarget(
                    name=name,

                    control_type=(
                        control_type
                    ),

                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,

                    center_x=(
                        (
                            left
                            + right
                        )
                        // 2
                    ),

                    center_y=(
                        (
                            top
                            + bottom
                        )
                        // 2
                    ),

                    enabled=enabled,
                    visible=visible,

                    automation_id=(
                        automation_id
                    ),
                )
            )

        except Exception:
            # Some UI Automation descendants may throw
            # when queried. Ignore only that individual
            # element rather than failing the whole tree.
            return None

    # ==================================================
    # MATCH SCORE
    # ==================================================

    def _match_score(
        self,
        query: str,
        name: str,
    ) -> int:
        normalized_name = (
            self._normalize_text(
                name
            )
        )

        if not (
            normalized_name
        ):
            return 0

        # ==============================================
        # TIER 3 — EXACT LABEL
        # ==============================================

        if (
            normalized_name
            == query
        ):
            return 3

        # ==============================================
        # TIER 2 — QUERY CONTAINED IN LABEL
        # ==============================================

        if (
            query
            in normalized_name
        ):
            return 2

        # ==============================================
        # TIER 1 — ALL QUERY WORDS PRESENT
        # ==============================================

        query_tokens = set(
            query.split()
        )

        name_tokens = set(
            normalized_name.split()
        )

        if (
            query_tokens
            and
            query_tokens.issubset(
                name_tokens
            )
        ):
            return 1

        return 0

    # ==================================================
    # DEDUPLICATE
    # ==================================================

    def _deduplicate_targets(
        self,
        targets: list[
            UIAutomationTarget
        ],
    ) -> list[
        UIAutomationTarget
    ]:
        unique: list[
            UIAutomationTarget
        ] = []

        seen: set[
            tuple[
                str,
                str,
                int,
                int,
                int,
                int,
            ]
        ] = set()

        for target in (
            targets
        ):
            key = (
                self._normalize_text(
                    target.name
                ),

                target.control_type,

                target.left,
                target.top,
                target.right,
                target.bottom,
            )

            if (
                key
                in seen
            ):
                continue

            seen.add(
                key
            )

            unique.append(
                target
            )

        return (
            unique
        )

    # ==================================================
    # PARSE QUERY
    # ==================================================

    def _parse_query(
        self,
        query: str,
    ) -> _ParsedQuery:
        normalized = (
            self._normalize_text(
                query
            )
        )

        # ==============================================
        # REMOVE LEADING ARTICLES
        # ==============================================

        for article in (
            "the ",
            "a ",
            "an ",
        ):
            if (
                normalized
                .startswith(
                    article
                )
            ):
                normalized = (
                    normalized[
                        len(
                            article
                        ):
                    ]
                    .strip()
                )

                break

        # ==============================================
        # OPTIONAL CONTROL-TYPE QUALIFIERS
        # ==============================================
        #
        # Longer phrases must come first.
        # ==============================================

        qualifiers: tuple[
            tuple[
                str,
                tuple[
                    str,
                    ...,
                ],
            ],
            ...,
        ] = (
            (
                "menu item",
                (
                    "MenuItem",
                ),
            ),

            (
                "search box",
                (
                    "Edit",
                    "ComboBox",
                ),
            ),

            (
                "text box",
                (
                    "Edit",
                ),
            ),

            (
                "textbox",
                (
                    "Edit",
                ),
            ),

            (
                "input field",
                (
                    "Edit",
                    "ComboBox",
                ),
            ),

            (
                "checkbox",
                (
                    "CheckBox",
                ),
            ),

            (
                "radio button",
                (
                    "RadioButton",
                ),
            ),

            (
                "dropdown",
                (
                    "ComboBox",
                ),
            ),

            (
                "button",
                (
                    "Button",
                ),
            ),

            (
                "tab",
                (
                    "TabItem",
                ),
            ),

            (
                "link",
                (
                    "Hyperlink",
                ),
            ),

            (
                "menu",
                (
                    "Menu",
                    "MenuItem",
                ),
            ),
        )

        for (
            qualifier,
            control_types,
        ) in qualifiers:
            suffix = (
                f" {qualifier}"
            )

            if (
                normalized
                .endswith(
                    suffix
                )
            ):
                label = (
                    normalized[
                        :-len(
                            suffix
                        )
                    ]
                    .strip()
                )

                if (
                    label
                ):
                    return (
                        _ParsedQuery(
                            label=label,

                            control_types=(
                                control_types
                            ),
                        )
                    )

        return (
            _ParsedQuery(
                label=normalized,
                control_types=(),
            )
        )

    # ==================================================
    # NORMALIZE TEXT
    # ==================================================

    def _normalize_text(
        self,
        text: str,
    ) -> str:
        return (
            " ".join(
                text
                .strip()
                .lower()
                .replace(
                    "-",
                    " ",
                )
                .replace(
                    "_",
                    " ",
                )
                .split()
            )
        )


ui_automation_service = (
    UIAutomationService()
)