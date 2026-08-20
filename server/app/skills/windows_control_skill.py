import ctypes
import subprocess

import psutil

from app.skills.base import Skill


class WindowsControlSkill(Skill):
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF
    KEYEVENTF_KEYUP = 0x0002

    def can_handle(self, command: str) -> bool:
        normalized = command.strip().lower()

        return (
            "volume up" in normalized
            or "increase volume" in normalized
            or "volume down" in normalized
            or "decrease volume" in normalized
            or normalized in {
                "mute",
                "mute volume",
                "mute sound",
                "unmute",
                "unmute volume",
            }
            or "read clipboard" in normalized
            or "what is in my clipboard" in normalized
            or "what's in my clipboard" in normalized
            or "running apps" in normalized
            or "running processes" in normalized
            or "is running" in normalized
            or normalized in {
                "lock computer",
                "lock my computer",
                "lock pc",
                "lock my pc",
            }
        )

    def execute(self, command: str) -> str:
        normalized = command.strip().lower()

        if (
            "volume up" in normalized
            or "increase volume" in normalized
        ):
            self._press_key(
                self.VK_VOLUME_UP,
                presses=3,
            )

            return "Volume increased."

        if (
            "volume down" in normalized
            or "decrease volume" in normalized
        ):
            self._press_key(
                self.VK_VOLUME_DOWN,
                presses=3,
            )

            return "Volume decreased."

        if normalized in {
            "mute",
            "mute volume",
            "mute sound",
            "unmute",
            "unmute volume",
        }:
            self._press_key(
                self.VK_VOLUME_MUTE
            )

            return "Audio mute state toggled."

        if (
            "read clipboard" in normalized
            or "clipboard" in normalized
        ):
            return self._read_clipboard()

        if (
            "running apps" in normalized
            or "running processes" in normalized
        ):
            return self._running_apps()

        if "is running" in normalized:
            app_name = (
                normalized
                .replace("is", "", 1)
                .replace("running", "", 1)
                .strip()
            )

            return self._is_running(
                app_name
            )

        if normalized in {
            "lock computer",
            "lock my computer",
            "lock pc",
            "lock my pc",
        }:
            ctypes.windll.user32.LockWorkStation()

            return "Locking the computer."

        return "I couldn't understand that Windows command."

    def _press_key(
        self,
        key_code: int,
        presses: int = 1,
    ) -> None:
        for _ in range(presses):
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

    def _read_clipboard(self) -> str:
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-Clipboard",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            content = result.stdout.strip()

            if not content:
                return "Your clipboard is empty."

            if len(content) > 500:
                content = (
                    content[:500]
                    + "..."
                )

            return (
                "Your clipboard contains: "
                + content
            )

        except Exception:
            return "I couldn't read the clipboard."

    def _running_apps(self) -> str:
        names: set[str] = set()

        for process in psutil.process_iter(
            ["name"]
        ):
            try:
                name = process.info["name"]

                if name:
                    names.add(name)
            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
            ):
                continue

        visible = sorted(names)[:20]

        return (
            "Some currently running processes are: "
            + ", ".join(visible)
            + "."
        )

    def _is_running(
        self,
        app_name: str,
    ) -> str:
        if not app_name:
            return "Tell me which application to check."

        target = (
            app_name
            .lower()
            .replace(".exe", "")
        )

        for process in psutil.process_iter(
            ["name"]
        ):
            try:
                process_name = (
                    process.info["name"]
                    or ""
                ).lower()

                if (
                    target
                    in process_name.replace(
                        ".exe",
                        "",
                    )
                ):
                    return (
                        f"Yes, {app_name} is running."
                    )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
            ):
                continue

        return (
            f"No, I don't see {app_name} running."
        )