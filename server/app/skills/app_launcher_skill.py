import os
import shutil
import subprocess
import webbrowser

from pathlib import (
    Path,
)

import psutil

from app.skills.base import (
    Skill,
)


class AppLauncherSkill(
    Skill
):
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

    # Exact executable names that may be terminated.
    CLOSE_ALIASES = {
        "notepad": {
            "notepad.exe",
        },

        "calculator": {
            "calculatorapp.exe",
            "calc.exe",
        },

        "calc": {
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

        return normalized.startswith(
            (
                *self.OPEN_PREFIXES,
                *self.CLOSE_PREFIXES,
            )
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
        )

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
        )

        # ==============================================
        # WEBSITE
        # ==============================================

        if (
            normalized_target
            in self.WEBSITES
        ):
            url = (
                self.WEBSITES[
                    normalized_target
                ]
            )

            webbrowser.open(
                url
            )

            return (
                f"Opening "
                f"{normalized_target}."
            )

        # ==============================================
        # EXPLICIT FILE / FOLDER PATH
        # ==============================================

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

                return (
                    f"Opening "
                    f"{path.name or path}."
                )

            except OSError:
                return (
                    "I couldn't open "
                    "that path."
                )

        # ==============================================
        # COMMON WINDOWS FOLDER
        # ==============================================

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

                return (
                    f"Opening "
                    f"{normalized_target}."
                )

            except OSError:
                return (
                    f"I couldn't open "
                    f"{normalized_target}."
                )

        # ==============================================
        # APPLICATION
        # ==============================================

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

                return (
                    f"Opening "
                    f"{normalized_target}."
                )

            except OSError:
                return (
                    f"I couldn't open "
                    f"{normalized_target}."
                )

        return (
            f"I don't know how to open "
            f"{target} yet."
        )

    # ==================================================
    # EXTRACT TARGET
    # ==================================================

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
                        len(prefix):
                    ]
                    .strip()
                    .strip(
                        "\"'"
                    )
                )

        return ""

    # ==================================================
    # CLOSE APP
    # ==================================================

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

        if not allowed_names:
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

    # ==================================================
    # EXISTING PATH
    # ==================================================

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

        if not candidate:
            return None

        # Avoid interpreting normal app names such as
        # "chrome" as arbitrary paths.
        looks_like_path = (
            "\\" in candidate
            or "/" in candidate
            or candidate.startswith(
                "."
            )
            or (
                len(candidate)
                >= 2
                and candidate[1]
                == ":"
            )
        )

        if not looks_like_path:
            return None

        try:
            path = (
                Path(
                    candidate
                )
                .expanduser()
            )

            if (
                not path.is_absolute()
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
            return path

        return None

    # ==================================================
    # RESOLVE APPLICATION
    # ==================================================

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

        if candidates:
            for candidate in (
                candidates
            ):
                found = (
                    shutil.which(
                        candidate
                    )
                )

                if found:
                    return found

        # ==============================================
        # VS CODE FALLBACK
        # ==============================================

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

            for path in paths:
                if (
                    path.exists()
                ):
                    return str(
                        path
                    )

        # ==============================================
        # CHROME FALLBACK
        # ==============================================

        if app_name == "chrome":
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

            for path in paths:
                if (
                    path.exists()
                ):
                    return str(
                        path
                    )

        # ==============================================
        # SPOTIFY FALLBACK
        # ==============================================

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

            if (
                path.exists()
            ):
                return str(
                    path
                )

        return None

    # ==================================================
    # COMMON FOLDER
    # ==================================================

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
            folder is not None
            and folder.exists()
        ):
            return folder

        return None