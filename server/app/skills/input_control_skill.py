import re

import pyautogui

from app.skills.base import (
    Skill,
)


class InputControlSkill(
    Skill
):
    MAX_TEXT_LENGTH = 500

    KEY_ALIASES = {
        "enter": "enter",
        "return": "enter",
        "escape": "esc",
        "esc": "esc",
        "tab": "tab",
        "space": "space",
        "backspace": "backspace",
        "delete": "delete",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "home": "home",
        "end": "end",
        "page up": "pageup",
        "page down": "pagedown",
    }

    HOTKEYS = {
        "copy": (
            "ctrl",
            "c",
        ),

        "paste": (
            "ctrl",
            "v",
        ),

        "select all": (
            "ctrl",
            "a",
        ),

        "undo": (
            "ctrl",
            "z",
        ),

        "redo": (
            "ctrl",
            "y",
        ),

        "save": (
            "ctrl",
            "s",
        ),

        "find": (
            "ctrl",
            "f",
        ),

        "new tab": (
            "ctrl",
            "t",
        ),

        "close tab": (
            "ctrl",
            "w",
        ),
    }

    TYPE_PATTERN = re.compile(
        r"^type\s+(.+)$",
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    PRESS_PATTERN = re.compile(
        (
            r"^press\s+"
            r"(.+?)"
            r"\s*[.!?]*$"
        ),
        flags=re.IGNORECASE,
    )

    SIMPLE_COMMANDS = {
        "click",
        "left click",
        "click here",
        "scroll up",
        "scroll down",
    }

    # ==================================================
    # INITIALIZE
    # ==================================================

    def __init__(
        self,
    ) -> None:
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05

    # ==================================================
    # ROUTING
    # ==================================================

    def can_handle(
        self,
        command: str,
    ) -> bool:
        clean_command = (
            command
            .strip()
        )

        normalized = (
            clean_command
            .lower()
            .rstrip(
                ".!?"
            )
        )

        # ==============================================
        # TYPE
        # ==============================================

        if (
            self.TYPE_PATTERN
            .match(
                clean_command
            )
            is not None
        ):
            return True

        # ==============================================
        # PRESS
        # ==============================================

        press_match = (
            self.PRESS_PATTERN
            .match(
                clean_command
            )
        )

        if (
            press_match
            is not None
        ):
            target = (
                self._normalize_press_target(
                    press_match.group(
                        1
                    )
                )
            )

            return (
                self._is_allowed_press_target(
                    target
                )
            )

        # ==============================================
        # MOUSE
        # ==============================================

        return (
            normalized
            in self.SIMPLE_COMMANDS
        )

    # ==================================================
    # EXECUTE
    # ==================================================

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
            .rstrip(
                ".!?"
            )
        )

        # ==============================================
        # TYPE TEXT
        # ==============================================

        type_match = (
            self.TYPE_PATTERN
            .match(
                clean_command
            )
        )

        if (
            type_match
            is not None
        ):
            return (
                self._type_text(
                    type_match.group(
                        1
                    )
                )
            )

        # ==============================================
        # PRESS KEY
        # ==============================================

        press_match = (
            self.PRESS_PATTERN
            .match(
                clean_command
            )
        )

        if (
            press_match
            is not None
        ):
            target = (
                self._normalize_press_target(
                    press_match.group(
                        1
                    )
                )
            )

            if not (
                self._is_allowed_press_target(
                    target
                )
            ):
                return (
                    "Unable to safely perform "
                    "that key command."
                )

            return (
                self._press(
                    target
                )
            )

        # ==============================================
        # CLICK
        # ==============================================

        if normalized in {
            "click",
            "left click",
            "click here",
        }:
            try:
                pyautogui.click()

                return (
                    "Clicked at the current "
                    "mouse position."
                )

            except (
                pyautogui.FailSafeException
            ):
                return (
                    "Mouse control was cancelled "
                    "by the safety failsafe."
                )

        # ==============================================
        # SCROLL UP
        # ==============================================

        if (
            normalized
            == "scroll up"
        ):
            try:
                pyautogui.scroll(
                    5
                )

                return (
                    "Scrolled up."
                )

            except (
                pyautogui.FailSafeException
            ):
                return (
                    "Mouse control was cancelled "
                    "by the safety failsafe."
                )

        # ==============================================
        # SCROLL DOWN
        # ==============================================

        if (
            normalized
            == "scroll down"
        ):
            try:
                pyautogui.scroll(
                    -5
                )

                return (
                    "Scrolled down."
                )

            except (
                pyautogui.FailSafeException
            ):
                return (
                    "Mouse control was cancelled "
                    "by the safety failsafe."
                )

        return (
            "Unable to safely perform "
            "that input-control command."
        )

    # ==================================================
    # TYPE
    # ==================================================

    def _type_text(
        self,
        text: str,
    ) -> str:
        clean_text = (
            text
            .strip()
        )

        if not clean_text:
            return (
                "Tell me what text "
                "you want typed."
            )

        if (
            len(
                clean_text
            )
            > self.MAX_TEXT_LENGTH
        ):
            return (
                "The text is too long "
                "to type safely in one action."
            )

        # Never automatically submit typed content.
        #
        # Enter must be an explicit separate command.
        clean_text = (
            clean_text
            .replace(
                "\r",
                " ",
            )
            .replace(
                "\n",
                " ",
            )
        )

        try:
            pyautogui.write(
                clean_text,
                interval=0.01,
            )

        except (
            pyautogui.FailSafeException
        ):
            return (
                "Keyboard control was cancelled "
                "by the safety failsafe."
            )

        return (
            f"Typed "
            f"{len(clean_text)} "
            "characters."
        )

    # ==================================================
    # PRESS
    # ==================================================

    def _press(
        self,
        target: str,
    ) -> str:
        # ==============================================
        # NAMED HOTKEY
        # ==============================================

        hotkey = (
            self.HOTKEYS
            .get(
                target
            )
        )

        if (
            hotkey
            is not None
        ):
            try:
                pyautogui.hotkey(
                    *hotkey
                )

            except (
                pyautogui.FailSafeException
            ):
                return (
                    "Keyboard control was cancelled "
                    "by the safety failsafe."
                )

            return (
                f"Pressed {target}."
            )

        # ==============================================
        # CTRL + SINGLE KEY
        # ==============================================

        if (
            target
            .startswith(
                "ctrl "
            )
        ):
            key = (
                target[
                    len(
                        "ctrl "
                    ):
                ]
                .strip()
            )

            try:
                pyautogui.hotkey(
                    "ctrl",
                    key,
                )

            except (
                pyautogui.FailSafeException
            ):
                return (
                    "Keyboard control was cancelled "
                    "by the safety failsafe."
                )

            return (
                f"Pressed Ctrl+"
                f"{key.upper()}."
            )

        # ==============================================
        # SINGLE SAFE KEY
        # ==============================================

        key = (
            self.KEY_ALIASES[
                target
            ]
        )

        try:
            pyautogui.press(
                key
            )

        except (
            pyautogui.FailSafeException
        ):
            return (
                "Keyboard control was cancelled "
                "by the safety failsafe."
            )

        return (
            f"Pressed {target}."
        )

    # ==================================================
    # SAFE PRESS VALIDATION
    # ==================================================

    def _is_allowed_press_target(
        self,
        target: str,
    ) -> bool:
        if (
            target
            in self.KEY_ALIASES
        ):
            return True

        if (
            target
            in self.HOTKEYS
        ):
            return True

        if (
            target
            .startswith(
                "ctrl "
            )
        ):
            key = (
                target[
                    len(
                        "ctrl "
                    ):
                ]
                .strip()
            )

            return (
                len(key)
                == 1
                and key.isalnum()
            )

        return False

    # ==================================================
    # NORMALIZE PRESS TARGET
    # ==================================================

    def _normalize_press_target(
        self,
        target: str,
    ) -> str:
        return (
            " ".join(
                target
                .strip()
                .lower()
                .rstrip(
                    ".!?"
                )
                .split()
            )
        )