from app.skills.app_launcher_skill import AppLauncherSkill
from app.skills.base import Skill
from app.skills.system_skill import SystemSkill
from app.skills.time_skill import TimeSkill


class SkillRegistry:
    def __init__(self) -> None:
        self.skills: list[Skill] = [
            TimeSkill(),
            SystemSkill(),
            AppLauncherSkill(),
        ]

    def find_skill(self, command: str) -> Skill | None:
        for skill in self.skills:
            if skill.can_handle(command):
                return skill

        return None


skill_registry = SkillRegistry()