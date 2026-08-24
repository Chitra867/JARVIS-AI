import time

from dataclasses import (
    dataclass,
)

import psutil
import win32con
import win32gui
import win32process

from pywinauto import (
    Desktop,
)


# ======================================================
# TOP-LEVEL WINDOW
# ======================================================


@dataclass(
    frozen=True
)
class UIAutomationWindow:
    hwnd: int

    title: str

    process_id: int
    process_name: str

    left: int
    top: int
    right: int
    bottom: int

    visible: bool
    enabled: bool
    minimized: bool


# ======================================================
# WINDOW RESOLUTION
# ======================================================


@dataclass(
    frozen=True
)
class UIAutomationWindowResolution:
    query: str
    status: str

    window: (
        UIAutomationWindow
        | None
    )

    candidates: tuple[
        UIAutomationWindow,
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
            self.window
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
# FOCUS RESULT
# ======================================================


@dataclass(
    frozen=True
)
class UIAutomationFocusResult:
    status: str

    window: (
        UIAutomationWindow
        | None
    )

    candidates: tuple[
        UIAutomationWindow,
        ...,
    ]

    reason: str

    @property
    def success(
        self,
    ) -> bool:
        return (
            self.status
            in {
                "already_focused",
                "focused",
            }
            and
            self.window
            is not None
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
    FOCUS_TIMEOUT_SECONDS = 1.5

    FOCUS_POLL_INTERVAL_SECONDS = 0.05

    # ==================================================
    # PUBLIC — FOREGROUND WINDOW INFO
    # ==================================================

    def get_foreground_window_info(
        self,
    ) -> UIAutomationWindow | None:
        hwnd = (
            self._foreground_window_handle()
        )

        if not (
            hwnd
        ):
            return None

        return (
            self._build_window_info(
                hwnd
            )
        )

    # ==================================================
    # PUBLIC — RESOLVE TOP-LEVEL WINDOW
    # ==================================================

    def resolve_window(
        self,
        *,
        process_names: tuple[
            str,
            ...,
        ] = (),
        title: str | None = None,
        preferred_hwnd: int | None = None,
    ) -> UIAutomationWindowResolution:
        normalized_process_names = (
            frozenset(
                name
                .strip()
                .lower()
                for name
                in process_names
                if name
                and name.strip()
            )
        )

        normalized_title = (
            self._normalize_text(
                title
                or ""
            )
        )

        query = (
            self._window_query_text(
                process_names=(
                    normalized_process_names
                ),
                title=(
                    normalized_title
                ),
                preferred_hwnd=(
                    preferred_hwnd
                ),
            )
        )

        if (
            not normalized_process_names
            and not normalized_title
            and not preferred_hwnd
        ):
            return (
                UIAutomationWindowResolution(
                    query=query,

                    status="not_found",

                    window=None,

                    candidates=(),

                    reason=(
                        "No window identity "
                        "constraints were provided."
                    ),
                )
            )

        try:
            # ------------------------------------------
            # STRONGEST IDENTITY — PREFERRED HWND
            # ------------------------------------------
            #
            # A previously verified window handle is the
            # safest recovery target. It is accepted only
            # when it still matches the supplied process /
            # title constraints.
            # ------------------------------------------

            if (
                preferred_hwnd
            ):
                preferred = (
                    self._build_window_info(
                        int(
                            preferred_hwnd
                        )
                    )
                )

                if (
                    preferred
                    is not None
                    and self._window_matches_constraints(
                        window=preferred,
                        process_names=(
                            normalized_process_names
                        ),
                        title=(
                            normalized_title
                        ),
                    )
                ):
                    return (
                        UIAutomationWindowResolution(
                            query=query,

                            status="resolved",

                            window=(
                                preferred
                            ),

                            candidates=(
                                preferred,
                            ),

                            reason=(
                                "The previously verified "
                                "window handle still "
                                "matches the expected "
                                "application."
                            ),
                        )
                    )

            # ------------------------------------------
            # ENUMERATE SAFE TOP-LEVEL WINDOWS
            # ------------------------------------------

            windows = (
                self._enumerate_top_level_windows()
            )

            scored: list[
                tuple[
                    int,
                    UIAutomationWindow,
                ]
            ] = []

            for window in (
                windows
            ):
                if not (
                    self._window_matches_constraints(
                        window=window,
                        process_names=(
                            normalized_process_names
                        ),
                        title=(
                            normalized_title
                        ),
                    )
                ):
                    continue

                score = (
                    self._window_match_score(
                        window=window,
                        title=(
                            normalized_title
                        ),
                    )
                )

                scored.append(
                    (
                        score,
                        window,
                    )
                )

            if not (
                scored
            ):
                return (
                    UIAutomationWindowResolution(
                        query=query,

                        status="not_found",

                        window=None,

                        candidates=(),

                        reason=(
                            "No visible top-level "
                            "window matched the "
                            "expected application."
                        ),
                    )
                )

            highest_score = max(
                score
                for (
                    score,
                    _
                )
                in scored
            )

            candidates = [
                window
                for (
                    score,
                    window
                )
                in scored
                if (
                    score
                    == highest_score
                )
            ]

            candidates = (
                self._deduplicate_windows(
                    candidates
                )
            )

            if (
                len(
                    candidates
                )
                == 1
            ):
                window = (
                    candidates[
                        0
                    ]
                )

                return (
                    UIAutomationWindowResolution(
                        query=query,

                        status="resolved",

                        window=window,

                        candidates=(
                            window,
                        ),

                        reason=(
                            "Exactly one safe "
                            "top-level window matched "
                            "the expected application."
                        ),
                    )
                )

            return (
                UIAutomationWindowResolution(
                    query=query,

                    status="ambiguous",

                    window=None,

                    candidates=tuple(
                        candidates
                    ),

                    reason=(
                        "Multiple equally strong "
                        "top-level windows matched "
                        "the expected application. "
                        "No window was chosen."
                    ),
                )
            )

        except Exception as error:
            print(
                (
                    "UI Automation window "
                    "resolution failed: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

            return (
                UIAutomationWindowResolution(
                    query=query,

                    status="error",

                    window=None,

                    candidates=(),

                    reason=(
                        "Window resolution failed."
                    ),
                )
            )

    # ==================================================
    # PUBLIC — FOCUS EXACT WINDOW
    # ==================================================

    def focus_window(
        self,
        hwnd: int,
        *,
        expected_process_names: tuple[
            str,
            ...,
        ] = (),
        expected_title: str | None = None,
        timeout_seconds: float | None = None,
    ) -> UIAutomationFocusResult:
        normalized_process_names = (
            frozenset(
                name
                .strip()
                .lower()
                for name
                in expected_process_names
                if name
                and name.strip()
            )
        )

        normalized_title = (
            self._normalize_text(
                expected_title
                or ""
            )
        )

        target = (
            self._build_window_info(
                int(
                    hwnd
                )
            )
        )

        if (
            target
            is None
        ):
            return (
                UIAutomationFocusResult(
                    status="not_found",

                    window=None,

                    candidates=(),

                    reason=(
                        "The expected application "
                        "window no longer exists or "
                        "is not safely accessible."
                    ),
                )
            )

        if not (
            self._window_matches_constraints(
                window=target,
                process_names=(
                    normalized_process_names
                ),
                title=(
                    normalized_title
                ),
            )
        ):
            return (
                UIAutomationFocusResult(
                    status="mismatch",

                    window=None,

                    candidates=(
                        target,
                    ),

                    reason=(
                        "The window handle no longer "
                        "matches the expected "
                        "application identity."
                    ),
                )
            )

        current_hwnd = (
            self._foreground_window_handle()
        )

        if (
            current_hwnd
            == target.hwnd
        ):
            return (
                UIAutomationFocusResult(
                    status="already_focused",

                    window=target,

                    candidates=(
                        target,
                    ),

                    reason=(
                        "The expected application "
                        "is already in the "
                        "foreground."
                    ),
                )
            )

        try:
            if (
                target.minimized
            ):
                win32gui.ShowWindow(
                    target.hwnd,
                    win32con.SW_RESTORE,
                )

            wrapper = (
                Desktop(
                    backend="uia"
                )
                .window(
                    handle=(
                        target.hwnd
                    )
                )
                .wrapper_object()
            )

            # pywinauto's set_focus() is preferable to
            # blind coordinate interaction. If Windows
            # rejects it, SetForegroundWindow is tried as
            # a second OS-level request. No keyboard or
            # mouse workaround is used.
            try:
                wrapper.set_focus()

            except Exception:
                win32gui.SetForegroundWindow(
                    target.hwnd
                )

        except Exception as error:
            print(
                (
                    "UI Automation focus request "
                    "failed: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

            return (
                UIAutomationFocusResult(
                    status="error",

                    window=None,

                    candidates=(
                        target,
                    ),

                    reason=(
                        "Windows could not safely "
                        "focus the expected "
                        "application."
                    ),
                )
            )

        timeout = (
            self.FOCUS_TIMEOUT_SECONDS
            if timeout_seconds is None
            else max(
                0.0,
                float(
                    timeout_seconds
                ),
            )
        )

        deadline = (
            time.monotonic()
            + timeout
        )

        while (
            True
        ):
            foreground_hwnd = (
                self._foreground_window_handle()
            )

            if (
                foreground_hwnd
                == target.hwnd
            ):
                verified = (
                    self._build_window_info(
                        target.hwnd
                    )
                )

                if (
                    verified
                    is None
                ):
                    return (
                        UIAutomationFocusResult(
                            status="error",

                            window=None,

                            candidates=(),

                            reason=(
                                "The application "
                                "window disappeared "
                                "during focus recovery."
                            ),
                        )
                    )

                if not (
                    self._same_window_identity(
                        target,
                        verified,
                    )
                ):
                    return (
                        UIAutomationFocusResult(
                            status="mismatch",

                            window=None,

                            candidates=(
                                verified,
                            ),

                            reason=(
                                "The focused window "
                                "identity changed during "
                                "focus recovery."
                            ),
                        )
                    )

                if not (
                    self._window_matches_constraints(
                        window=verified,
                        process_names=(
                            normalized_process_names
                        ),
                        title=(
                            normalized_title
                        ),
                    )
                ):
                    return (
                        UIAutomationFocusResult(
                            status="mismatch",

                            window=None,

                            candidates=(
                                verified,
                            ),

                            reason=(
                                "The focused window no "
                                "longer matches the "
                                "expected application."
                            ),
                        )
                    )

                return (
                    UIAutomationFocusResult(
                        status="focused",

                        window=verified,

                        candidates=(
                            verified,
                        ),

                        reason=(
                            "The expected application "
                            "was safely restored to "
                            "the foreground."
                        ),
                    )
                )

            if (
                time.monotonic()
                >= deadline
            ):
                break

            time.sleep(
                self.FOCUS_POLL_INTERVAL_SECONDS
            )

        return (
            UIAutomationFocusResult(
                status="timeout",

                window=None,

                candidates=(
                    target,
                ),

                reason=(
                    "Timed out waiting for the "
                    "expected application to "
                    "become the foreground window."
                ),
            )
        )

    # ==================================================
    # PUBLIC — RESOLVE + RECOVER FOCUS
    # ==================================================

    def recover_focus(
        self,
        *,
        process_names: tuple[
            str,
            ...,
        ] = (),
        title: str | None = None,
        preferred_hwnd: int | None = None,
        timeout_seconds: float | None = None,
    ) -> UIAutomationFocusResult:
        resolution = (
            self.resolve_window(
                process_names=(
                    process_names
                ),
                title=(
                    title
                ),
                preferred_hwnd=(
                    preferred_hwnd
                ),
            )
        )

        if not (
            resolution.resolved
        ):
            return (
                UIAutomationFocusResult(
                    status=(
                        resolution.status
                    ),

                    window=None,

                    candidates=(
                        resolution
                        .candidates
                    ),

                    reason=(
                        resolution.reason
                    ),
                )
            )

        window = (
            resolution.window
        )

        if (
            window
            is None
        ):
            return (
                UIAutomationFocusResult(
                    status="error",

                    window=None,

                    candidates=(),

                    reason=(
                        "Window resolution returned "
                        "no usable window."
                    ),
                )
            )

        return (
            self.focus_window(
                window.hwnd,

                expected_process_names=(
                    process_names
                ),

                expected_title=(
                    title
                ),

                timeout_seconds=(
                    timeout_seconds
                ),
            )
        )

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
    # FOREGROUND WINDOW HANDLE
    # ==================================================

    def _foreground_window_handle(
        self,
    ) -> int:
        try:
            return int(
                win32gui
                .GetForegroundWindow()
            )

        except Exception:
            return 0

    # ==================================================
    # ENUMERATE TOP-LEVEL WINDOWS
    # ==================================================

    def _enumerate_top_level_windows(
        self,
    ) -> list[
        UIAutomationWindow
    ]:
        handles: list[
            int
        ] = []

        def collect(
            hwnd: int,
            _,
        ) -> bool:
            handles.append(
                int(
                    hwnd
                )
            )

            return True

        win32gui.EnumWindows(
            collect,
            None,
        )

        windows: list[
            UIAutomationWindow
        ] = []

        for hwnd in (
            handles
        ):
            window = (
                self._build_window_info(
                    hwnd
                )
            )

            if (
                window
                is not None
            ):
                windows.append(
                    window
                )

        return (
            windows
        )

    # ==================================================
    # BUILD TOP-LEVEL WINDOW INFO
    # ==================================================

    def _build_window_info(
        self,
        hwnd: int,
    ) -> UIAutomationWindow | None:
        try:
            if not (
                hwnd
            ):
                return None

            if not (
                win32gui.IsWindow(
                    hwnd
                )
            ):
                return None

            visible = bool(
                win32gui.IsWindowVisible(
                    hwnd
                )
            )

            if not (
                visible
            ):
                return None

            enabled = bool(
                win32gui.IsWindowEnabled(
                    hwnd
                )
            )

            if not (
                enabled
            ):
                return None

            title = (
                win32gui
                .GetWindowText(
                    hwnd
                )
                .strip()
            )

            (
                _,
                process_id,
            ) = (
                win32process
                .GetWindowThreadProcessId(
                    hwnd
                )
            )

            if not (
                process_id
            ):
                return None

            process = (
                psutil.Process(
                    process_id
                )
            )

            process_name = (
                process.name()
                or ""
            ).strip()

            if not (
                process_name
            ):
                return None

            (
                left,
                top,
                right,
                bottom,
            ) = (
                win32gui.GetWindowRect(
                    hwnd
                )
            )

            left = int(
                left
            )

            top = int(
                top
            )

            right = int(
                right
            )

            bottom = int(
                bottom
            )

            if (
                right
                <= left
                or
                bottom
                <= top
            ):
                return None

            minimized = bool(
                win32gui.IsIconic(
                    hwnd
                )
            )

            return (
                UIAutomationWindow(
                    hwnd=(
                        int(
                            hwnd
                        )
                    ),

                    title=title,

                    process_id=(
                        int(
                            process_id
                        )
                    ),

                    process_name=(
                        process_name
                    ),

                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,

                    visible=visible,
                    enabled=enabled,
                    minimized=(
                        minimized
                    ),
                )
            )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
            OSError,
        ):
            return None

        except Exception:
            return None

    # ==================================================
    # WINDOW CONSTRAINT MATCH
    # ==================================================

    def _window_matches_constraints(
        self,
        *,
        window: UIAutomationWindow,
        process_names: frozenset[
            str
        ],
        title: str,
    ) -> bool:
        if not (
            window.visible
            and window.enabled
        ):
            return False

        if (
            process_names
            and window.process_name
            .strip()
            .lower()
            not in process_names
        ):
            return False

        if (
            title
        ):
            normalized_window_title = (
                self._normalize_text(
                    window.title
                )
            )

            if not (
                normalized_window_title
            ):
                return False

            if (
                normalized_window_title
                != title
                and title
                not in normalized_window_title
            ):
                return False

        return True

    # ==================================================
    # WINDOW MATCH SCORE
    # ==================================================

    def _window_match_score(
        self,
        *,
        window: UIAutomationWindow,
        title: str,
    ) -> int:
        if not (
            title
        ):
            return 1

        normalized_window_title = (
            self._normalize_text(
                window.title
            )
        )

        if (
            normalized_window_title
            == title
        ):
            return 3

        if (
            title
            in normalized_window_title
        ):
            return 2

        return 0

    # ==================================================
    # DEDUPLICATE WINDOWS
    # ==================================================

    def _deduplicate_windows(
        self,
        windows: list[
            UIAutomationWindow
        ],
    ) -> list[
        UIAutomationWindow
    ]:
        unique: list[
            UIAutomationWindow
        ] = []

        seen: set[
            int
        ] = set()

        for window in (
            windows
        ):
            if (
                window.hwnd
                in seen
            ):
                continue

            seen.add(
                window.hwnd
            )

            unique.append(
                window
            )

        return (
            unique
        )

    # ==================================================
    # SAME WINDOW IDENTITY
    # ==================================================

    def _same_window_identity(
        self,
        first: UIAutomationWindow,
        second: UIAutomationWindow,
    ) -> bool:
        return (
            first.hwnd
            == second.hwnd
            and
            first.process_id
            == second.process_id
            and
            first.process_name
            .strip()
            .lower()
            ==
            second.process_name
            .strip()
            .lower()
        )

    # ==================================================
    # WINDOW QUERY TEXT
    # ==================================================

    def _window_query_text(
        self,
        *,
        process_names: frozenset[
            str
        ],
        title: str,
        preferred_hwnd: int | None,
    ) -> str:
        parts: list[
            str
        ] = []

        if (
            process_names
        ):
            parts.append(
                (
                    "process="
                    + ",".join(
                        sorted(
                            process_names
                        )
                    )
                )
            )

        if (
            title
        ):
            parts.append(
                (
                    "title="
                    f"{title}"
                )
            )

        if (
            preferred_hwnd
        ):
            parts.append(
                (
                    "hwnd="
                    f"{preferred_hwnd}"
                )
            )

        return (
            "; ".join(
                parts
            )
            or "unspecified"
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