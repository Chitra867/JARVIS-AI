import os
from pathlib import Path

from app.skills.base import Skill


class FileSkill(Skill):
    def __init__(self) -> None:
        self.home = Path.home()

        self.jarvis_project = Path(
            r"D:\AI\JARVIS"
        )

        self.named_folders = {
            "downloads": self.home / "Downloads",
            "documents": self.home / "Documents",
            "desktop": self.home / "Desktop",
            "pictures": self.home / "Pictures",
            "videos": self.home / "Videos",
            "music": self.home / "Music",
        }

    def can_handle(self, command: str) -> bool:
        normalized = command.strip().lower()

        return (
            normalized.startswith("show files in ")
            or normalized.startswith("list files in ")
            or normalized.startswith("find file ")
            or normalized.startswith("find ")
            or normalized in {
                "open my jarvis project",
                "open jarvis project",
                "open the jarvis project",
            }
        )

    def execute(self, command: str) -> str:
        normalized = command.strip()
        lowered = normalized.lower()

        if lowered in {
            "open my jarvis project",
            "open jarvis project",
            "open the jarvis project",
        }:
            return self._open_jarvis_project()

        if lowered.startswith("show files in "):
            folder_name = normalized[
                len("show files in "):
            ].strip()

            return self._list_folder(folder_name)

        if lowered.startswith("list files in "):
            folder_name = normalized[
                len("list files in "):
            ].strip()

            return self._list_folder(folder_name)

        if lowered.startswith("find file "):
            filename = normalized[
                len("find file "):
            ].strip()

            return self._find_file(filename)

        if lowered.startswith("find "):
            filename = normalized[
                len("find "):
            ].strip()

            return self._find_file(filename)

        return "I couldn't understand that file command."

    def _open_jarvis_project(self) -> str:
        if not self.jarvis_project.exists():
            return (
                "I couldn't find the JARVIS project folder."
            )

        try:
            os.startfile(
                str(self.jarvis_project)
            )

            return "Opening your JARVIS project."

        except OSError:
            return (
                "I couldn't open the JARVIS project."
            )

    def _list_folder(
        self,
        folder_name: str,
    ) -> str:
        folder_key = (
            folder_name
            .strip()
            .lower()
            .replace(" folder", "")
        )

        folder = self.named_folders.get(
            folder_key
        )

        if folder is None:
            return (
                f"I don't know the folder {folder_name} yet."
            )

        if not folder.exists():
            return (
                f"The {folder_key} folder does not exist."
            )

        try:
            items = sorted(
                folder.iterdir(),
                key=lambda item: (
                    not item.is_dir(),
                    item.name.lower(),
                ),
            )

        except OSError:
            return (
                f"I couldn't read the {folder_key} folder."
            )

        if not items:
            return (
                f"Your {folder_key} folder is empty."
            )

        visible = items[:10]

        names = [
            (
                f"{item.name} folder"
                if item.is_dir()
                else item.name
            )
            for item in visible
        ]

        result = ", ".join(names)

        if len(items) > len(visible):
            remaining = (
                len(items) -
                len(visible)
            )

            return (
                f"I found {len(items)} items in your "
                f"{folder_key} folder. "
                f"The first items are: {result}. "
                f"There are {remaining} more."
            )

        return (
            f"I found {len(items)} items in your "
            f"{folder_key} folder: {result}."
        )

    def _find_file(
        self,
        filename: str,
    ) -> str:
        filename = filename.strip()

        if not filename:
            return (
                "Tell me the name of the file you want to find."
            )

        search_term = filename.lower()

        search_locations = [
            self.home / "Desktop",
            self.home / "Downloads",
            self.home / "Documents",
            self.jarvis_project,
        ]

        ignored_directories = {
            "node_modules",
            ".git",
            ".venv",
            "__pycache__",
            "dist",
            "build",
        }

        matches: list[Path] = []

        for root in search_locations:
            if not root.exists():
                continue

            for current_root, dirs, files in os.walk(root):
                dirs[:] = [
                    directory
                    for directory in dirs
                    if directory not in ignored_directories
                ]

                for file_name in files:
                    if search_term in file_name.lower():
                        matches.append(
                            Path(current_root)
                            / file_name
                        )

                        if len(matches) >= 5:
                            break

                if len(matches) >= 5:
                    break

            if len(matches) >= 5:
                break

        if not matches:
            return (
                f"I couldn't find a file matching {filename}."
            )

        if len(matches) == 1:
            return (
                f"I found {matches[0].name} in "
                f"{matches[0].parent}."
            )

        result = "; ".join(
            f"{match.name} in {match.parent}"
            for match in matches
        )

        return (
            f"I found {len(matches)} matching files. "
            f"{result}"
        )