import os
import shutil
import subprocess
import time
import webbrowser

from dataclasses import (
    dataclass,
)

from pathlib import (
    Path,
)

import psutil
import win32gui
import win32process

from app.core.ui_automation import (
    ui_automation_service,
)

from app.skills.base import (
    Skill,
)


# =========================================================
# LAUNCH READINESS STATE
# =========================================================


@dataclass(
    frozen=True
)
class LaunchReadiness:
    command: str
    target: str
    kind: str

    process_names: frozenset[
        str
    ]

    previous_foreground_hwnd: int

    created_at: float


# =========================================================
# LAUNCH FOCUS CONTEXT
# =========================================================


@dataclass(
    frozen=True
)
class LaunchFocusContext:
    command: str
    target: str

    hwnd: int

    process_id: int
    process_name: str

    process_names: frozenset[
        str
    ]

    title: str

    created_at: float


# =========================================================
# APP LAUNCHER
# =========================================================


class AppLauncherSkill(
    Skill
):
    # =====================================================
    # READINESS CONFIGURATION
    # =====================================================

    READINESS_TIMEOUT_SECONDS = 6.0

    READINESS_POLL_INTERVAL_SECONDS = 0.10

    # Require the same suitable foreground window to be
    # observed more than once before continuing.
    READINESS_STABLE_POLLS = 2

    # =====================================================
    # WEBSITES
    # =====================================================

    WEBSITES = {
        "youtube":
            "https://www.youtube.com",

        "google":
            "https://www.google.com",

        "github":
            "https://github.com",

        "gmail":
            "https://mail.google.com",

        "chatgpt":
            "https://chatgpt.com",

        "facebook":
            "https://www.facebook.com",

        "instagram":
            "https://www.instagram.com",

        "linkedin":
            "https://www.linkedin.com",

        "reddit":
            "https://www.reddit.com",
    }

    # =====================================================
    # APPLICATION ALIASES
    # =====================================================

    APP_ALIASES = {
        "notepad": [
            "notepad.exe",
        ],

        "calculator": [
            "calc.exe",
        ],

        "calc": [
            "calc.exe",
        ],

        "vs code": [
            "code.cmd",
            "code.exe",
        ],

        "vscode": [
            "code.cmd",
            "code.exe",
        ],

        "visual studio code": [
            "code.cmd",
            "code.exe",
        ],

        "chrome": [
            "chrome.exe",
        ],

        "powershell": [
            "powershell.exe",
            "pwsh.exe",
        ],

        "terminal": [
            "wt.exe",
            "powershell.exe",
        ],

        "command prompt": [
            "cmd.exe",
        ],

        "cmd": [
            "cmd.exe",
        ],

        "file explorer": [
            "explorer.exe",
        ],

        "explorer": [
            "explorer.exe",
        ],

        "spotify": [
            "spotify.exe",
        ],
    }

    # =====================================================
    # READINESS PROCESS NAMES
    # =====================================================
    #
    # Some launcher executables immediately hand work to a
    # different process.
    #
    # Example:
    #
    # wt.exe
    #   ↓
    # WindowsTerminal.exe
    #
    # calc.exe
    #   ↓
    # CalculatorApp.exe
    #
    # Therefore readiness checks should not depend solely
    # on the executable passed to Popen().
    # =====================================================

    READY_PROCESS_ALIASES = {
        "notepad": {
            "notepad.exe",
        },

        "calculator": {
            "calculator.exe",
            "calculatorapp.exe",
            "calc.exe",
        },

        "calc": {
            "calculator.exe",
            "calculatorapp.exe",
            "calc.exe",
        },

        "vs code": {
            "code.exe",
        },

        "vscode": {
            "code.exe",
        },

        "visual studio code": {
            "code.exe",
        },

        "chrome": {
            "chrome.exe",
        },

        "powershell": {
            "powershell.exe",
            "pwsh.exe",
        },

        "terminal": {
            "windowsterminal.exe",
            "wt.exe",
            "powershell.exe",
            "pwsh.exe",
        },

        "command prompt": {
            "cmd.exe",
        },

        "cmd": {
            "cmd.exe",
        },

        "file explorer": {
            "explorer.exe",
        },

        "explorer": {
            "explorer.exe",
        },

        "spotify": {
            "spotify.exe",
        },
    }

    # =====================================================
    # BROWSER PROCESS NAMES
    # =====================================================

    BROWSER_PROCESS_NAMES = frozenset(
        {
            "chrome.exe",
            "msedge.exe",
            "firefox.exe",
            "brave.exe",
            "opera.exe",
            "vivaldi.exe",
            "arc.exe",
        }
    )

    # =====================================================
    # CLOSE ALIASES
    # =====================================================

    CLOSE_ALIASES = {
        "notepad": {
            "notepad.exe",
        },

        "calculator": {
            "calculator.exe",
            "calculatorapp.exe",
            "calc.exe",
        },

        "calc": {
            "calculator.exe",
            "calculatorapp.exe",
            "calc.exe",
        },

        "vs code": {
            "code.exe",
        },

        "vscode": {
            "code.exe",
        },

        "visual studio code": {
            "code.exe",
        },

        "chrome": {
            "chrome.exe",
        },

        "powershell": {
            "powershell.exe",
            "pwsh.exe",
        },

        "terminal": {
            "windowsterminal.exe",
            "wt.exe",
        },

        "command prompt": {
            "cmd.exe",
        },

        "cmd": {
            "cmd.exe",
        },

        "spotify": {
            "spotify.exe",
        },
    }

    OPEN_PREFIXES = (
        "open ",
        "launch ",
        "start ",
    )

    CLOSE_PREFIXES = (
        "close ",
        "quit ",
        "exit ",
    )

    # =====================================================
    # INIT
    # =====================================================

    def __init__(
        self,
    ) -> None:
        self._last_launch: (
            LaunchReadiness
            | None
        ) = None

        self._focus_context: (
            LaunchFocusContext
            | None
        ) = None

    # =====================================================
    # ROUTING
    # =====================================================

    def can_handle(
        self,
        command: str,
    ) -> bool:
        normalized = (
            command
            .strip()
            .lower()
        )

        return normalized.startswith(
            (
                *self.OPEN_PREFIXES,
                *self.CLOSE_PREFIXES,
            )
        )

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(
        self,
        command: str,
    ) -> str:
        clean_command = (
            command
            .strip()
        )

        normalized = (
            clean_command
            .lower()
        )

        # Any new launcher command invalidates an older
        # readiness observation and its associated workflow
        # focus context.
        self._last_launch = (
            None
        )

        self._focus_context = (
            None
        )

        # =================================================
        # CLOSE APPLICATION
        # =================================================

        if normalized.startswith(
            self.CLOSE_PREFIXES
        ):
            target = (
                self._extract_target(
                    clean_command,
                    self.CLOSE_PREFIXES,
                )
            )

            return (
                self._close_app(
                    target
                )
            )

        # =================================================
        # OPEN TARGET
        # =================================================

        target = (
            self._extract_target(
                clean_command,
                self.OPEN_PREFIXES,
            )
        )

        if not target:
            return (
                "Tell me what you want "
                "me to open."
            )

        normalized_target = (
            target
            .lower()
            .rstrip(
                ".!?"
            )
            .strip()
        )

        previous_hwnd = (
            self._foreground_window_handle()
        )

        # =================================================
        # WEBSITE
        # =================================================

        if (
            normalized_target
            in self.WEBSITES
        ):
            url = (
                self.WEBSITES[
                    normalized_target
                ]
            )

            try:
                opened = (
                    webbrowser.open(
                        url
                    )
                )

            except (
                OSError,
                webbrowser.Error,
            ):
                return (
                    f"I couldn't open "
                    f"{normalized_target}."
                )

            if (
                opened
                is False
            ):
                return (
                    f"I couldn't open "
                    f"{normalized_target}."
                )

            self._record_launch(
                command=clean_command,
                target=normalized_target,
                kind="website",
                process_names=(
                    self.BROWSER_PROCESS_NAMES
                ),
                previous_foreground_hwnd=(
                    previous_hwnd
                ),
            )

            return (
                f"Opening "
                f"{normalized_target}."
            )

        # =================================================
        # EXPLICIT FILE / FOLDER PATH
        # =================================================

        path = (
            self._resolve_existing_path(
                target
            )
        )

        if (
            path
            is not None
        ):
            try:
                os.startfile(
                    str(
                        path
                    )
                )

            except OSError:
                return (
                    "I couldn't open "
                    "that path."
                )

            self._record_launch(
                command=clean_command,
                target=str(
                    path
                ),
                kind="foreground_change",
                process_names=(
                    frozenset()
                ),
                previous_foreground_hwnd=(
                    previous_hwnd
                ),
            )

            return (
                f"Opening "
                f"{path.name or path}."
            )

        # =================================================
        # COMMON WINDOWS FOLDER
        # =================================================

        folder = (
            self._get_folder(
                normalized_target
            )
        )

        if (
            folder
            is not None
        ):
            try:
                os.startfile(
                    str(
                        folder
                    )
                )

            except OSError:
                return (
                    f"I couldn't open "
                    f"{normalized_target}."
                )

            self._record_launch(
                command=clean_command,
                target=normalized_target,
                kind="application",
                process_names=(
                    frozenset(
                        {
                            "explorer.exe",
                        }
                    )
                ),
                previous_foreground_hwnd=(
                    previous_hwnd
                ),
            )

            return (
                f"Opening "
                f"{normalized_target}."
            )

        # =================================================
        # APPLICATION
        # =================================================

        executable = (
            self._resolve_app(
                normalized_target
            )
        )

        if executable:
            try:
                subprocess.Popen(
                    [
                        executable
                    ],
                    stdout=(
                        subprocess.DEVNULL
                    ),
                    stderr=(
                        subprocess.DEVNULL
                    ),
                )

            except OSError:
                return (
                    f"I couldn't open "
                    f"{normalized_target}."
                )

            process_names = (
                self._readiness_process_names(
                    app_name=(
                        normalized_target
                    ),
                    executable=(
                        executable
                    ),
                )
            )

            self._record_launch(
                command=clean_command,
                target=normalized_target,
                kind="application",
                process_names=(
                    process_names
                ),
                previous_foreground_hwnd=(
                    previous_hwnd
                ),
            )

            return (
                f"Opening "
                f"{normalized_target}."
            )

        return (
            f"I don't know how to open "
            f"{target} yet."
        )

    # =====================================================
    # WAIT UNTIL READY
    # =====================================================
    #
    # This method intentionally does NOT run automatically
    # inside execute().
    #
    # TaskExecutor will call it only when another task step
    # needs to run after this launch.
    #
    # Returns:
    #
    # (True, reason)
    #       → safe to continue to the next step
    #
    # (False, reason)
    #       → stop the multi-step workflow
    # =====================================================

    def wait_until_ready(
        self,
        command: str,
    ) -> tuple[
        bool,
        str,
    ]:
        observation = (
            self._last_launch
        )

        if (
            observation
            is None
        ):
            return (
                True,
                (
                    "No launch readiness wait "
                    "is required."
                ),
            )

        if not (
            self._same_command(
                command,
                observation.command,
            )
        ):
            return (
                True,
                (
                    "The latest launch does not "
                    "belong to this task step."
                ),
            )

        deadline = (
            time.monotonic()
            + self.READINESS_TIMEOUT_SECONDS
        )

        stable_hwnd: (
            int
            | None
        ) = None

        stable_count = 0

        while (
            time.monotonic()
            < deadline
        ):
            hwnd = (
                self._foreground_window_handle()
            )

            ready = (
                self._foreground_window_matches(
                    hwnd=hwnd,
                    observation=(
                        observation
                    ),
                )
            )

            if (
                ready
            ):
                if (
                    stable_hwnd
                    == hwnd
                ):
                    stable_count += 1

                else:
                    stable_hwnd = (
                        hwnd
                    )

                    stable_count = 1

                if (
                    stable_count
                    >= self.READINESS_STABLE_POLLS
                ):
                    self._focus_context = (
                        self._capture_focus_context(
                            observation=(
                                observation
                            ),
                            hwnd=(
                                stable_hwnd
                            ),
                        )
                    )

                    self._last_launch = (
                        None
                    )

                    return (
                        True,
                        (
                            f"{observation.target} "
                            "is ready."
                        ),
                    )

            else:
                stable_hwnd = (
                    None
                )

                stable_count = 0

            time.sleep(
                self.READINESS_POLL_INTERVAL_SECONDS
            )

        self._last_launch = (
            None
        )

        return (
            False,
            (
                f"Timed out waiting for "
                f"{observation.target} "
                "to become ready."
            ),
        )

    # =====================================================
    # GET WORKFLOW FOCUS CONTEXT
    # =====================================================

    def get_focus_context(
        self,
        command: str,
    ) -> LaunchFocusContext | None:
        context = (
            self._focus_context
        )

        if (
            context
            is None
        ):
            return None

        if not (
            self._same_command(
                command,
                context.command,
            )
        ):
            return None

        return (
            context
        )

    # =====================================================
    # RECOVER WORKFLOW FOCUS
    # =====================================================

    def recover_focus_context(
        self,
        context: LaunchFocusContext,
    ) -> tuple[
        bool,
        str,
    ]:
        if not isinstance(
            context,
            LaunchFocusContext,
        ):
            return (
                False,
                (
                    "The application focus context "
                    "is invalid."
                ),
            )

        # -------------------------------------------------
        # If the current foreground window still belongs
        # to the exact same process, do not force the main
        # window to the front.
        #
        # This preserves legitimate same-process UI states
        # such as menus, popups and tab surfaces.
        # -------------------------------------------------

        foreground = (
            ui_automation_service
            .get_foreground_window_info()
        )

        if (
            foreground
            is not None
            and foreground.process_id
            == context.process_id
            and foreground.process_name
            .strip()
            .lower()
            == context.process_name
            .strip()
            .lower()
        ):
            return (
                True,
                (
                    "The expected application "
                    "already owns the foreground."
                ),
            )

        # -------------------------------------------------
        # Otherwise recover the exact verified HWND.
        #
        # Do not search for or guess another same-process
        # window if the original HWND is gone.
        # -------------------------------------------------

        result = (
            ui_automation_service
            .focus_window(
                context.hwnd,

                expected_process_names=(
                    tuple(
                        sorted(
                            context.process_names
                        )
                    )
                ),
            )
        )

        if not (
            result.success
        ):
            return (
                False,
                (
                    result.reason
                    or
                    "The expected application "
                    "could not be safely restored."
                ),
            )

        window = (
            result.window
        )

        if (
            window
            is None
        ):
            return (
                False,
                (
                    "Focus recovery returned no "
                    "verified application window."
                ),
            )

        if (
            window.hwnd
            != context.hwnd
            or window.process_id
            != context.process_id
            or window.process_name
            .strip()
            .lower()
            != context.process_name
            .strip()
            .lower()
        ):
            return (
                False,
                (
                    "The recovered window no longer "
                    "matches the originally verified "
                    "application."
                ),
            )

        return (
            True,
            (
                "The expected application was "
                "safely restored to the foreground."
            ),
        )

    # =====================================================
    # CAPTURE WORKFLOW FOCUS CONTEXT
    # =====================================================

    def _capture_focus_context(
        self,
        *,
        observation: LaunchReadiness,
        hwnd: int | None,
    ) -> LaunchFocusContext | None:
        if not (
            hwnd
        ):
            return None

        window = (
            ui_automation_service
            .get_foreground_window_info()
        )

        if (
            window
            is None
        ):
            return None

        if (
            window.hwnd
            != hwnd
        ):
            return None

        process_name = (
            window.process_name
            .strip()
            .lower()
        )

        if not (
            process_name
        ):
            return None

        if (
            observation.process_names
            and process_name
            not in observation.process_names
        ):
            return None

        process_names = (
            observation.process_names
        )

        if not (
            process_names
        ):
            process_names = (
                frozenset(
                    {
                        process_name,
                    }
                )
            )

        return (
            LaunchFocusContext(
                command=(
                    observation.command
                ),

                target=(
                    observation.target
                ),

                hwnd=(
                    window.hwnd
                ),

                process_id=(
                    window.process_id
                ),

                process_name=(
                    window.process_name
                ),

                process_names=(
                    frozenset(
                        name
                        .strip()
                        .lower()
                        for name
                        in process_names
                        if name
                        and name.strip()
                    )
                ),

                title=(
                    window.title
                ),

                created_at=(
                    time.monotonic()
                ),
            )
        )

    # =====================================================
    # RECORD LAUNCH
    # =====================================================

    def _record_launch(
        self,
        command: str,
        target: str,
        kind: str,
        process_names: frozenset[
            str
        ],
        previous_foreground_hwnd: int,
    ) -> None:
        self._last_launch = (
            LaunchReadiness(
                command=(
                    command
                ),

                target=(
                    target
                ),

                kind=(
                    kind
                ),

                process_names=(
                    frozenset(
                        name.lower()
                        for name
                        in process_names
                        if name
                    )
                ),

                previous_foreground_hwnd=(
                    previous_foreground_hwnd
                ),

                created_at=(
                    time.monotonic()
                ),
            )
        )

    # =====================================================
    # FOREGROUND WINDOW MATCH
    # =====================================================

    def _foreground_window_matches(
        self,
        hwnd: int,
        observation: LaunchReadiness,
    ) -> bool:
        if not (
            hwnd
        ):
            return False

        try:
            if not (
                win32gui.IsWindow(
                    hwnd
                )
            ):
                return False

            if not (
                win32gui.IsWindowVisible(
                    hwnd
                )
            ):
                return False

            if not (
                win32gui.IsWindowEnabled(
                    hwnd
                )
            ):
                return False

        except Exception:
            return False

        # =================================================
        # GENERIC FILE / PATH
        # =================================================
        #
        # We do not know which associated application will
        # open a generic file, so require a foreground-window
        # transition.
        # =================================================

        if (
            observation.kind
            == "foreground_change"
        ):
            if (
                observation
                .previous_foreground_hwnd
                == 0
            ):
                return True

            return (
                hwnd
                != observation
                .previous_foreground_hwnd
            )

        # =================================================
        # APPLICATION / WEBSITE
        # =================================================

        if not (
            observation.process_names
        ):
            return False

        process_name = (
            self._window_process_name(
                hwnd
            )
        )

        if not (
            process_name
        ):
            return False

        return (
            process_name.lower()
            in observation.process_names
        )

    # =====================================================
    # WINDOW PROCESS NAME
    # =====================================================

    def _window_process_name(
        self,
        hwnd: int,
    ) -> str:
        try:
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
                return ""

            process = (
                psutil.Process(
                    process_id
                )
            )

            return (
                process.name()
                or ""
            )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
            OSError,
        ):
            return ""

        except Exception:
            return ""

    # =====================================================
    # FOREGROUND WINDOW HANDLE
    # =====================================================

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

    # =====================================================
    # READINESS PROCESS NAMES
    # =====================================================

    def _readiness_process_names(
        self,
        app_name: str,
        executable: str,
    ) -> frozenset[
        str
    ]:
        known = (
            self.READY_PROCESS_ALIASES
            .get(
                app_name
            )
        )

        if (
            known
        ):
            return (
                frozenset(
                    name.lower()
                    for name
                    in known
                )
            )

        executable_name = (
            Path(
                executable
            )
            .name
            .lower()
        )

        if not (
            executable_name
        ):
            return (
                frozenset()
            )

        return (
            frozenset(
                {
                    executable_name,
                }
            )
        )

    # =====================================================
    # SAME COMMAND
    # =====================================================

    def _same_command(
        self,
        first: str,
        second: str,
    ) -> bool:
        return (
            self._normalize_command(
                first
            )
            == self._normalize_command(
                second
            )
        )

    # =====================================================
    # NORMALIZE COMMAND
    # =====================================================

    def _normalize_command(
        self,
        command: str,
    ) -> str:
        return (
            " ".join(
                command
                .strip()
                .lower()
                .rstrip(
                    ".!?"
                )
                .split()
            )
        )

    # =====================================================
    # EXTRACT TARGET
    # =====================================================

    def _extract_target(
        self,
        command: str,
        prefixes: tuple[
            str,
            ...
        ],
    ) -> str:
        lowered = (
            command
            .lower()
        )

        for prefix in (
            prefixes
        ):
            if lowered.startswith(
                prefix
            ):
                return (
                    command[
                        len(
                            prefix
                        ):
                    ]
                    .strip()
                    .strip(
                        "\"'"
                    )
                )

        return ""

    # =====================================================
    # CLOSE APP
    # =====================================================

    def _close_app(
        self,
        target: str,
    ) -> str:
        normalized_target = (
            target
            .strip()
            .lower()
            .rstrip(
                ".!?"
            )
        )

        if not normalized_target:
            return (
                "Tell me which application "
                "you want me to close."
            )

        allowed_names = (
            self.CLOSE_ALIASES
            .get(
                normalized_target
            )
        )

        if not (
            allowed_names
        ):
            return (
                f"I don't know how to safely "
                f"close {target} yet."
            )

        matched = 0

        for process in (
            psutil.process_iter(
                [
                    "name",
                ]
            )
        ):
            try:
                process_name = (
                    process.info[
                        "name"
                    ]
                    or ""
                ).lower()

                if (
                    process_name
                    not in allowed_names
                ):
                    continue

                process.terminate()

                matched += 1

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

        if (
            matched
            == 0
        ):
            return (
                f"I don't see "
                f"{target} running."
            )

        return (
            f"Closing {target}."
        )

    # =====================================================
    # EXISTING PATH
    # =====================================================

    def _resolve_existing_path(
        self,
        target: str,
    ) -> Path | None:
        candidate = (
            target
            .strip()
            .strip(
                "\"'"
            )
        )

        if not (
            candidate
        ):
            return None

        # Avoid interpreting ordinary application names as
        # arbitrary paths.
        looks_like_path = (
            "\\"
            in candidate
            or "/"
            in candidate
            or candidate.startswith(
                "."
            )
            or (
                len(
                    candidate
                )
                >= 2
                and candidate[
                    1
                ]
                == ":"
            )
        )

        if not (
            looks_like_path
        ):
            return None

        try:
            path = (
                Path(
                    candidate
                )
                .expanduser()
            )

            if not (
                path.is_absolute()
            ):
                path = (
                    Path.cwd()
                    / path
                )

            path = (
                path.resolve(
                    strict=False
                )
            )

        except (
            OSError,
            RuntimeError,
            ValueError,
        ):
            return None

        if (
            path.exists()
        ):
            return (
                path
            )

        return None

    # =====================================================
    # RESOLVE APPLICATION
    # =====================================================

    def _resolve_app(
        self,
        app_name: str,
    ) -> str | None:
        candidates = (
            self.APP_ALIASES
            .get(
                app_name
            )
        )

        if (
            candidates
        ):
            for candidate in (
                candidates
            ):
                found = (
                    shutil.which(
                        candidate
                    )
                )

                if (
                    found
                ):
                    return (
                        found
                    )

        # =================================================
        # VS CODE FALLBACK
        # =================================================

        if app_name in {
            "vs code",
            "vscode",
            "visual studio code",
        }:
            paths = [
                (
                    Path(
                        os.getenv(
                            "LOCALAPPDATA",
                            "",
                        )
                    )
                    / "Programs"
                    / "Microsoft VS Code"
                    / "Code.exe"
                ),

                (
                    Path(
                        os.getenv(
                            "ProgramFiles",
                            "",
                        )
                    )
                    / "Microsoft VS Code"
                    / "Code.exe"
                ),
            ]

            for path in (
                paths
            ):
                if (
                    path.exists()
                ):
                    return (
                        str(
                            path
                        )
                    )

        # =================================================
        # CHROME FALLBACK
        # =================================================

        if (
            app_name
            == "chrome"
        ):
            paths = [
                (
                    Path(
                        os.getenv(
                            "ProgramFiles",
                            "",
                        )
                    )
                    / "Google"
                    / "Chrome"
                    / "Application"
                    / "chrome.exe"
                ),

                (
                    Path(
                        os.getenv(
                            "ProgramFiles(x86)",
                            "",
                        )
                    )
                    / "Google"
                    / "Chrome"
                    / "Application"
                    / "chrome.exe"
                ),

                (
                    Path(
                        os.getenv(
                            "LOCALAPPDATA",
                            "",
                        )
                    )
                    / "Google"
                    / "Chrome"
                    / "Application"
                    / "chrome.exe"
                ),
            ]

            for path in (
                paths
            ):
                if (
                    path.exists()
                ):
                    return (
                        str(
                            path
                        )
                    )

        # =================================================
        # SPOTIFY FALLBACK
        # =================================================

        if (
            app_name
            == "spotify"
        ):
            path = (
                Path(
                    os.getenv(
                        "APPDATA",
                        "",
                    )
                )
                / "Spotify"
                / "Spotify.exe"
            )

            if (
                path.exists()
            ):
                return (
                    str(
                        path
                    )
                )

        return None

    # =====================================================
    # COMMON FOLDER
    # =====================================================

    def _get_folder(
        self,
        target: str,
    ) -> Path | None:
        home = (
            Path.home()
        )

        folders = {
            "downloads":
                home
                / "Downloads",

            "download folder":
                home
                / "Downloads",

            "documents":
                home
                / "Documents",

            "documents folder":
                home
                / "Documents",

            "desktop":
                home
                / "Desktop",

            "desktop folder":
                home
                / "Desktop",

            "pictures":
                home
                / "Pictures",

            "music":
                home
                / "Music",

            "videos":
                home
                / "Videos",

            "home folder":
                home,

            "user folder":
                home,
        }

        folder = (
            folders
            .get(
                target
            )
        )

        if (
            folder
            is not None
            and folder.exists()
        ):
            return (
                folder
            )

        return None