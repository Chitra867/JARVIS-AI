import re

from urllib.parse import (
    urlparse,
)

import pyautogui

from app.core.ui_automation import (
    ui_automation_service,
)

from app.skills.base import (
    Skill,
)


class BrowserNavigationSkill(
    Skill
):
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

    MAX_QUERY_LENGTH = 500
    TYPE_INTERVAL_SECONDS = 0.01

    CONTROL_SHORTCUTS = {
        "browser back": (
            "alt",
            "left",
        ),
        "browser forward": (
            "alt",
            "right",
        ),
        "refresh browser": (
            "ctrl",
            "r",
        ),
        "browser refresh": (
            "ctrl",
            "r",
        ),
        "open new tab": (
            "ctrl",
            "t",
        ),
        "new browser tab": (
            "ctrl",
            "t",
        ),
    }

    CONTROL_MESSAGES = {
        "browser back":
            "Browser moved back.",

        "browser forward":
            "Browser moved forward.",

        "refresh browser":
            "Browser refreshed.",

        "browser refresh":
            "Browser refreshed.",

        "open new tab":
            "Opened a new browser tab.",

        "new browser tab":
            "Opened a new browser tab.",
    }

    NAVIGATE_PATTERN = re.compile(
        (
            r"^(?:navigate|go)\s+to\s+"
            r"(?P<target>\S+)"
            r"\s*$"
        ),
        flags=re.IGNORECASE,
    )

    SEARCH_PATTERN = re.compile(
        (
            r"^(?:"
            r"browser\s+search"
            r"|search\s+browser"
            r")"
            r"(?:\s+for)?\s+"
            r"(?P<query>.+?)"
            r"\s*$"
        ),
        flags=re.IGNORECASE,
    )

    def can_handle(
        self,
        command: str,
    ) -> bool:
        clean = (
            command
            .strip()
        )

        if not (
            clean
        ):
            return False

        normalized = (
            " ".join(
                clean
                .lower()
                .split()
            )
        )

        return (
            normalized
            in self.CONTROL_SHORTCUTS
            or self.NAVIGATE_PATTERN
            .fullmatch(
                clean
            )
            is not None
            or self.SEARCH_PATTERN
            .fullmatch(
                clean
            )
            is not None
        )

    def execute(
        self,
        command: str,
    ) -> str:
        clean = (
            command
            .strip()
        )

        normalized = (
            " ".join(
                clean
                .lower()
                .split()
            )
        )

        if (
            normalized
            in self.CONTROL_SHORTCUTS
        ):
            return (
                self._execute_browser_control(
                    command=normalized,
                )
            )

        navigate_match = (
            self.NAVIGATE_PATTERN
            .fullmatch(
                clean
            )
        )

        if (
            navigate_match
            is not None
        ):
            target = (
                navigate_match
                .group(
                    "target"
                )
                .strip()
            )

            safe_url = (
                self._validate_web_url(
                    target
                )
            )

            if (
                safe_url
                is None
            ):
                return (
                    "I couldn't safely navigate to "
                    "that web address."
                )

            return (
                self._submit_address_bar_text(
                    text=safe_url,
                    success_message=(
                        f"Navigating to {safe_url}."
                    ),
                )
            )

        search_match = (
            self.SEARCH_PATTERN
            .fullmatch(
                clean
            )
        )

        if (
            search_match
            is not None
        ):
            query = (
                search_match
                .group(
                    "query"
                )
                .strip()
            )

            safe_query = (
                self._validate_search_query(
                    query
                )
            )

            if (
                safe_query
                is None
            ):
                return (
                    "I couldn't safely submit "
                    "that browser search."
                )

            return (
                self._submit_address_bar_text(
                    text=safe_query,
                    success_message=(
                        "Browser search submitted "
                        f"for {safe_query}."
                    ),
                )
            )

        return (
            "I couldn't understand that "
            "browser navigation command."
        )

    def _execute_browser_control(
        self,
        *,
        command: str,
    ) -> str:
        window = (
            self._get_verified_browser_window()
        )

        if (
            window
            is None
        ):
            return (
                "I couldn't safely control the "
                "browser because a supported browser "
                "is not the verified foreground window."
            )

        expected_hwnd = (
            window.hwnd
        )

        shortcut = (
            self.CONTROL_SHORTCUTS[
                command
            ]
        )

        try:
            pyautogui.hotkey(
                *shortcut
            )

        except (
            pyautogui.FailSafeException,
            OSError,
        ):
            return (
                "I couldn't safely perform that "
                "browser control."
            )

        if not (
            self._same_verified_browser_window(
                expected_hwnd
            )
        ):
            return (
                "The browser window changed during "
                "the browser control."
            )

        return (
            self.CONTROL_MESSAGES[
                command
            ]
        )

    def _submit_address_bar_text(
        self,
        *,
        text: str,
        success_message: str,
    ) -> str:
        original_window = (
            self._get_verified_browser_window()
        )

        if (
            original_window
            is None
        ):
            return (
                "I couldn't safely control the "
                "browser because a supported browser "
                "is not the verified foreground window."
            )

        expected_hwnd = (
            original_window.hwnd
        )

        try:
            pyautogui.hotkey(
                "ctrl",
                "l",
            )

        except (
            pyautogui.FailSafeException,
            OSError,
        ):
            return (
                "I couldn't safely focus the "
                "browser address bar."
            )

        if not (
            self._same_verified_browser_window(
                expected_hwnd
            )
        ):
            return (
                "The browser window changed before "
                "the address bar could be used."
            )

        try:
            pyautogui.write(
                text,
                interval=(
                    self.TYPE_INTERVAL_SECONDS
                ),
            )

        except (
            pyautogui.FailSafeException,
            OSError,
        ):
            return (
                "I couldn't safely type into the "
                "browser address bar."
            )

        if not (
            self._same_verified_browser_window(
                expected_hwnd
            )
        ):
            return (
                "The browser window changed before "
                "navigation could be submitted."
            )

        try:
            pyautogui.press(
                "enter"
            )

        except (
            pyautogui.FailSafeException,
            OSError,
        ):
            return (
                "I couldn't safely submit the "
                "browser navigation."
            )

        return (
            success_message
        )

    def _get_verified_browser_window(
        self,
    ):
        window = (
            ui_automation_service
            .get_foreground_window_info()
        )

        if (
            window
            is None
        ):
            return None

        process_name = (
            window.process_name
            .strip()
            .lower()
        )

        if (
            process_name
            not in self.BROWSER_PROCESS_NAMES
        ):
            return None

        if not (
            window.visible
            and window.enabled
        ):
            return None

        return (
            window
        )

    def _same_verified_browser_window(
        self,
        expected_hwnd: int,
    ) -> bool:
        window = (
            self._get_verified_browser_window()
        )

        if (
            window
            is None
        ):
            return False

        return (
            window.hwnd
            == expected_hwnd
        )

    def _validate_web_url(
        self,
        target: str,
    ) -> str | None:
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

        if not (
            self._is_ascii(
                candidate
            )
        ):
            return None

        if (
            "\r"
            in candidate
            or "\n"
            in candidate
            or "\t"
            in candidate
        ):
            return None

        try:
            parsed = (
                urlparse(
                    candidate
                )
            )

            if (
                parsed.scheme
                .lower()
                not in {
                    "http",
                    "https",
                }
            ):
                return None

            if not (
                parsed.hostname
            ):
                return None

            if (
                parsed.username
                is not None
                or parsed.password
                is not None
            ):
                return None

        except (
            TypeError,
            ValueError,
        ):
            return None

        return (
            candidate
        )

    def _validate_search_query(
        self,
        query: str,
    ) -> str | None:
        clean = (
            " ".join(
                query
                .strip()
                .split()
            )
        )

        if not (
            clean
        ):
            return None

        if (
            len(
                clean
            )
            > self.MAX_QUERY_LENGTH
        ):
            return None

        if not (
            self._is_ascii(
                clean
            )
        ):
            return None

        return (
            clean
        )

    def _is_ascii(
        self,
        value: str,
    ) -> bool:
        try:
            value.encode(
                "ascii"
            )

        except UnicodeEncodeError:
            return False

        return True
