import os
import shutil
import subprocess
import webbrowser
from pathlib import Path

from app.skills.base import Skill


class AppLauncherSkill(Skill):
    WEBSITES = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://github.com",
        "gmail": "https://mail.google.com",
        "chatgpt": "https://chatgpt.com",
        "facebook": "https://www.facebook.com",
        "instagram": "https://www.instagram.com",
        "linkedin": "https://www.linkedin.com",
        "reddit": "https://www.reddit.com",
    }

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
                "open ",
                "launch ",
                "start ",
            )
        )

    def execute(
        self,
        command: str,
    ) -> str:
        normalized = (
            command
            .strip()
            .lower()
        )

        target = normalized

        for prefix in (
            "open ",
            "launch ",
            "start ",
        ):
            if target.startswith(prefix):
                target = target[
                    len(prefix):
                ].strip()

                break

        if not target:
            return "Tell me what you want me to open."

        # ---------------------------------------------
        # Websites
        # ---------------------------------------------

        if target in self.WEBSITES:
            url = self.WEBSITES[
                target
            ]

            webbrowser.open(url)

            return (
                f"Opening {target}."
            )

        # ---------------------------------------------
        # Common Windows folders
        # ---------------------------------------------

        folder = self._get_folder(
            target
        )

        if folder is not None:
            try:
                os.startfile(
                    str(folder)
                )

                return (
                    f"Opening {target}."
                )

            except OSError:
                return (
                    f"I couldn't open {target}."
                )

        # ---------------------------------------------
        # Desktop applications
        # ---------------------------------------------

        executable = self._resolve_app(
            target
        )

        if executable:
            try:
                subprocess.Popen(
                    [executable],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                return (
                    f"Opening {target}."
                )

            except OSError:
                return (
                    f"I couldn't open {target}."
                )

        return (
            f"I don't know how to open {target} yet."
        )

    def _resolve_app(
        self,
        app_name: str,
    ) -> str | None:
        candidates = (
            self.APP_ALIASES.get(
                app_name
            )
        )

        if candidates:
            for candidate in candidates:
                found = shutil.which(
                    candidate
                )

                if found:
                    return found

        # ---------------------------------------------
        # VS Code fallback paths
        # ---------------------------------------------

        if app_name in {
            "vs code",
            "vscode",
            "visual studio code",
        }:
            paths = [
                Path(
                    os.getenv(
                        "LOCALAPPDATA",
                        "",
                    )
                )
                / "Programs"
                / "Microsoft VS Code"
                / "Code.exe",

                Path(
                    os.getenv(
                        "ProgramFiles",
                        "",
                    )
                )
                / "Microsoft VS Code"
                / "Code.exe",
            ]

            for path in paths:
                if path.exists():
                    return str(path)

        # ---------------------------------------------
        # Chrome fallback paths
        # ---------------------------------------------

        if app_name == "chrome":
            paths = [
                Path(
                    os.getenv(
                        "ProgramFiles",
                        "",
                    )
                )
                / "Google"
                / "Chrome"
                / "Application"
                / "chrome.exe",

                Path(
                    os.getenv(
                        "ProgramFiles(x86)",
                        "",
                    )
                )
                / "Google"
                / "Chrome"
                / "Application"
                / "chrome.exe",

                Path(
                    os.getenv(
                        "LOCALAPPDATA",
                        "",
                    )
                )
                / "Google"
                / "Chrome"
                / "Application"
                / "chrome.exe",
            ]

            for path in paths:
                if path.exists():
                    return str(path)

        # ---------------------------------------------
        # Spotify fallback
        # ---------------------------------------------

        if app_name == "spotify":
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

            if path.exists():
                return str(path)

        return None

    def _get_folder(
        self,
        target: str,
    ) -> Path | None:
        home = Path.home()

        folders = {
            "downloads":
                home / "Downloads",

            "download folder":
                home / "Downloads",

            "documents":
                home / "Documents",

            "documents folder":
                home / "Documents",

            "desktop":
                home / "Desktop",

            "desktop folder":
                home / "Desktop",

            "pictures":
                home / "Pictures",

            "music":
                home / "Music",

            "videos":
                home / "Videos",

            "home folder":
                home,

            "user folder":
                home,
        }

        folder = folders.get(
            target
        )

        if (
            folder is not None
            and folder.exists()
        ):
            return folder

        return None