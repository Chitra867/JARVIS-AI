import platform
import shutil

from app.skills.base import Skill


class SystemSkill(Skill):
    def can_handle(self, command: str) -> bool:
        normalized = command.strip().lower()

        return normalized in {
            "status",
            "system status",
            "show system status",
        }

    def execute(self, command: str) -> str:
        total, used, free = shutil.disk_usage("/")

        free_gb = free // (1024 ** 3)

        return (
            f"System operational. "
            f"OS: {platform.system()} {platform.release()}. "
            f"Free disk space: {free_gb} GB."
        )