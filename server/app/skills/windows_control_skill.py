import ctypes
import re
import subprocess

import psutil

from app.skills.base import (
    Skill,
)


class WindowsControlSkill(
    Skill
):
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF

    KEYEVENTF_KEYUP = (
        0x0002
    )

    RUNNING_PATTERN = re.compile(
        (
            r"^is\s+"
            r"(.+?)"
            r"\s+running"
            r"\s*[.!?]*$"
        ),
        flags=(
            re.IGNORECASE
        ),
    )

    # ==================================================
    # ROUTING
    # ==================================================

    def can_handle(
        self,
        command: str,
    ) -> bool:
        normalized = (
            command
            .strip()
            .lower()
        )

        return (
            "volume up"
            in normalized

            or "increase volume"
            in normalized

            or "volume down"
            in normalized

            or "decrease volume"
            in normalized

            or normalized
            in {
                "mute",
                "mute volume",
                "mute sound",
                "unmute",
                "unmute volume",
            }

            or "read clipboard"
            in normalized

            or "what is in my clipboard"
            in normalized

            or "what's in my clipboard"
            in normalized

            or "running apps"
            in normalized

            or "running processes"
            in normalized

            or self.RUNNING_PATTERN
            .match(
                normalized
            )
            is not None

            or normalized
            in {
                "lock computer",
                "lock my computer",
                "lock pc",
                "lock my pc",
            }
        )

    # ==================================================
    # EXECUTE
    # ==================================================

    def execute(
        self,
        command: str,
    ) -> str:
        normalized = (
            command
            .strip()
            .lower()
        )

        # ==============================================
        # VOLUME UP
        # ==============================================

        if (
            "volume up"
            in normalized
            or "increase volume"
            in normalized
        ):
            self._press_key(
                self.VK_VOLUME_UP,
                presses=3,
            )

            return (
                "Volume increased."
            )

        # ==============================================
        # VOLUME DOWN
        # ==============================================

        if (
            "volume down"
            in normalized
            or "decrease volume"
            in normalized
        ):
            self._press_key(
                self.VK_VOLUME_DOWN,
                presses=3,
            )

            return (
                "Volume decreased."
            )

        # ==============================================
        # MUTE
        # ==============================================

        if (
            normalized
            in {
                "mute",
                "mute volume",
                "mute sound",
                "unmute",
                "unmute volume",
            }
        ):
            self._press_key(
                self.VK_VOLUME_MUTE
            )

            return (
                "Audio mute state toggled."
            )

        # ==============================================
        # CLIPBOARD
        # ==============================================

        if (
            "read clipboard"
            in normalized
            or "clipboard"
            in normalized
        ):
            return (
                self._read_clipboard()
            )

        # ==============================================
        # RUNNING PROCESSES
        # ==============================================

        if (
            "running apps"
            in normalized
            or "running processes"
            in normalized
        ):
            return (
                self._running_apps()
            )

        # ==============================================
        # IS APP RUNNING?
        # ==============================================

        running_match = (
            self.RUNNING_PATTERN
            .match(
                normalized
            )
        )

        if (
            running_match
            is not None
        ):
            app_name = (
                running_match
                .group(
                    1
                )
                .strip()
            )

            return (
                self._is_running(
                    app_name
                )
            )

        # ==============================================
        # LOCK COMPUTER
        # ==============================================

        if (
            normalized
            in {
                "lock computer",
                "lock my computer",
                "lock pc",
                "lock my pc",
            }
        ):
            ctypes.windll.user32.LockWorkStation()

            return (
                "Locking the computer."
            )

        return (
            "I couldn't understand "
            "that Windows command."
        )

    # ==================================================
    # KEY PRESS
    # ==================================================

    def _press_key(
        self,
        key_code: int,
        presses: int = 1,
    ) -> None:
        for _ in range(
            presses
        ):
            ctypes.windll.user32.keybd_event(
                key_code,
                0,
                0,
                0,
            )

            ctypes.windll.user32.keybd_event(
                key_code,
                0,
                self.KEYEVENTF_KEYUP,
                0,
            )

    # ==================================================
    # CLIPBOARD
    # ==================================================

    def _read_clipboard(
        self,
    ) -> str:
        try:
            result = (
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        "Get-Clipboard",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
            )

            if (
                result.returncode
                != 0
            ):
                return (
                    "I couldn't read "
                    "the clipboard."
                )

            content = (
                result.stdout
                .strip()
            )

            if not content:
                return (
                    "Your clipboard "
                    "is empty."
                )

            if (
                len(content)
                > 500
            ):
                content = (
                    content[
                        :500
                    ]
                    + "..."
                )

            return (
                "Your clipboard contains: "
                + content
            )

        except (
            subprocess.SubprocessError,
            OSError,
        ):
            return (
                "I couldn't read "
                "the clipboard."
            )

    # ==================================================
    # RUNNING APPS
    # ==================================================

    def _running_apps(
        self,
    ) -> str:
        names: set[
            str
        ] = set()

        for process in (
            psutil.process_iter(
                [
                    "name",
                ]
            )
        ):
            try:
                name = (
                    process.info[
                        "name"
                    ]
                )

                if name:
                    names.add(
                        name
                    )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

        visible = (
            sorted(
                names,
                key=str.lower,
            )[
                :20
            ]
        )

        if not visible:
            return (
                "I couldn't find any "
                "running processes."
            )

        return (
            "Some currently running "
            "processes are: "
            + ", ".join(
                visible
            )
            + "."
        )

    # ==================================================
    # IS RUNNING
    # ==================================================

    def _is_running(
        self,
        app_name: str,
    ) -> str:
        clean_name = (
            app_name
            .strip()
            .rstrip(
                ".!?"
            )
        )

        if not clean_name:
            return (
                "Tell me which application "
                "to check."
            )

        target = (
            clean_name
            .lower()
            .removesuffix(
                ".exe"
            )
        )

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
                )

                process_target = (
                    process_name
                    .lower()
                    .removesuffix(
                        ".exe"
                    )
                )

                if (
                    target
                    == process_target
                    or target
                    in process_target
                ):
                    return (
                        f"Yes, {clean_name} "
                        "is running."
                    )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

        return (
            f"No, I don't see "
            f"{clean_name} running."
        )