from app.skills.action_guard_skill import (
    ActionGuardSkill,
)

from app.skills.ai_skill import (
    AISkill,
)

from app.skills.app_launcher_skill import (
    AppLauncherSkill,
)

from app.skills.base import (
    Skill,
)

from app.skills.file_skill import (
    FileSkill,
)

from app.skills.input_control_skill import (
    InputControlSkill,
)

from app.skills.media_skill import (
    MediaSkill,
)

from app.skills.memory_control_skill import (
    MemoryControlSkill,
)

from app.skills.memory_skill import (
    MemorySkill,
)

from app.skills.page_open_skill import (
    PageOpenSkill,
)

from app.skills.page_summary_skill import (
    PageSummarySkill,
)

from app.skills.power_control_skill import (
    PowerControlSkill,
)

from app.skills.screen_vision_skill import (
    ScreenVisionSkill,
)

from app.skills.screenshot_skill import (
    ScreenshotSkill,
)

from app.skills.search_skill import (
    SearchSkill,
)

from app.skills.system_skill import (
    SystemSkill,
)

from app.skills.time_skill import (
    TimeSkill,
)

from app.skills.visual_target_skill import (
    VisualTargetSkill,
)

from app.skills.windows_control_skill import (
    WindowsControlSkill,
)


class SkillRegistry:
    def __init__(
        self,
    ) -> None:
        self.skills: list[
            Skill
        ] = [
            TimeSkill(),

            SystemSkill(),

            # Visual target detection must appear
            # before SearchSkill because commands
            # can begin with "find".
            VisualTargetSkill(),

            SearchSkill(),

            PageOpenSkill(),

            PageSummarySkill(),

            FileSkill(),

            WindowsControlSkill(),

            MediaSkill(),

            PowerControlSkill(),

            ScreenshotSkill(),

            ScreenVisionSkill(),

            AppLauncherSkill(),

            InputControlSkill(),

            MemoryControlSkill(),

            MemorySkill(),

            # Unsupported actions stop here.
            ActionGuardSkill(),

            # AI fallback always stays last.
            AISkill(),
        ]

    def find_skill(
        self,
        command: str,
    ) -> Skill | None:
        for skill in (
            self.skills
        ):
            if (
                skill.can_handle(
                    command
                )
            ):
                return skill

        return None


skill_registry = (
    SkillRegistry()
)