from app.skills.ai_skill import AISkill
from app.skills.app_launcher_skill import AppLauncherSkill
from app.skills.base import Skill
from app.skills.file_skill import FileSkill
from app.skills.memory_skill import MemorySkill
from app.skills.search_skill import SearchSkill
from app.skills.system_skill import SystemSkill
from app.skills.time_skill import TimeSkill
from app.skills.windows_control_skill import WindowsControlSkill
from app.skills.media_skill import MediaSkill
from app.skills.action_guard_skill import ActionGuardSkill


class SkillRegistry:
    def __init__(self) -> None:
        self.skills: list[Skill] = [
            TimeSkill(),
            SystemSkill(),
            SearchSkill(),
            FileSkill(),
            WindowsControlSkill(),
            MediaSkill(),
            AppLauncherSkill(),
            MemorySkill(),

            # Catch unsupported real-world actions.
            ActionGuardSkill(),

            # Keep AI last because it is the fallback.
            AISkill(),
        ]

    def find_skill(
        self,
        command: str,
    ) -> Skill | None:
        for skill in self.skills:
            if skill.can_handle(command):
                return skill

        return None


skill_registry = SkillRegistry()