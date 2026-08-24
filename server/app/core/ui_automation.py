from dataclasses import (
    dataclass,
)

import win32gui

from pywinauto import (
    Desktop,
)


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


class UIAutomationService:
    # ==================================================
    # FIND TARGET
    # ==================================================

    def find_target(
        self,
        query: str,
    ) -> UIAutomationTarget | None:
        normalized_query = (
            self._normalize(
                query
            )
        )

        if not normalized_query:
            return None

        try:
            hwnd = (
                win32gui
                .GetForegroundWindow()
            )

            if not hwnd:
                return None

            window = (
                Desktop(
                    backend="uia"
                )
                .window(
                    handle=hwnd
                )
                .wrapper_object()
            )

            matches: list[
                UIAutomationTarget
            ] = []

            for control in (
                window.descendants()
            ):
                try:
                    name = (
                        control
                        .window_text()
                        .strip()
                    )

                    if not name:
                        continue

                    normalized_name = (
                        self._normalize(
                            name
                        )
                    )

                    if not (
                        self._matches(
                            query=(
                                normalized_query
                            ),
                            name=(
                                normalized_name
                            ),
                        )
                    ):
                        continue

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

                    if (
                        right <= left
                        or bottom <= top
                    ):
                        continue

                    visible = bool(
                        control
                        .is_visible()
                    )

                    enabled = bool(
                        control
                        .is_enabled()
                    )

                    if not visible:
                        continue

                    control_type = (
                        str(
                            control
                            .element_info
                            .control_type
                        )
                        .strip()
                    )

                    matches.append(
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
                        )
                    )

                except Exception:
                    # One inaccessible UIA child should
                    # not break the entire tree search.
                    continue

            return (
                self._choose_unique_match(
                    query=(
                        normalized_query
                    ),
                    matches=matches,
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

            return None

    # ==================================================
    # CHOOSE UNIQUE MATCH
    # ==================================================

    def _choose_unique_match(
        self,
        query: str,
        matches: list[
            UIAutomationTarget
        ],
    ) -> UIAutomationTarget | None:
        if not matches:
            return None

        # ==============================================
        # EXACT NAME MATCH
        # ==============================================

        exact_matches = [
            target
            for target
            in matches
            if (
                self._normalize(
                    target.name
                )
                == query
            )
        ]

        if (
            len(
                exact_matches
            )
            == 1
        ):
            return (
                exact_matches[0]
            )

        if (
            len(
                exact_matches
            )
            > 1
        ):
            return None

        # ==============================================
        # ONE PARTIAL MATCH ONLY
        # ==============================================

        if (
            len(
                matches
            )
            == 1
        ):
            return (
                matches[0]
            )

        # Ambiguous matches fail closed.
        return None

    # ==================================================
    # MATCH QUERY
    # ==================================================

    def _matches(
        self,
        query: str,
        name: str,
    ) -> bool:
        if (
            query
            == name
        ):
            return True

        if (
            query
            in name
        ):
            return True

        if (
            name
            in query
        ):
            return True

        return False

    # ==================================================
    # NORMALIZE
    # ==================================================

    def _normalize(
        self,
        text: str,
    ) -> str:
        normalized = (
            " ".join(
                text
                .strip()
                .lower()
                .replace(
                    "-",
                    " ",
                )
                .split()
            )
        )

        # Remove common UI nouns that users may include
        # even when UI Automation exposes only the label.
        removable_suffixes = (
            " button",
            " icon",
            " control",
        )

        for suffix in (
            removable_suffixes
        ):
            if (
                normalized
                .endswith(
                    suffix
                )
            ):
                normalized = (
                    normalized[
                        :-len(
                            suffix
                        )
                    ]
                    .strip()
                )

                break

        return normalized


ui_automation_service = (
    UIAutomationService()
)