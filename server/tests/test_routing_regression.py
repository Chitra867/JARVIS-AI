import unittest

from app.skills.action_guard_skill import (
    ActionGuardSkill,
)
from app.skills.ai_skill import AISkill
from app.skills.app_launcher_skill import (
    AppLauncherSkill,
)
from app.skills.memory_control_skill import (
    MemoryControlSkill,
)
from app.skills.memory_skill import MemorySkill
from app.skills.registry import SkillRegistry
from app.skills.search_skill import SearchSkill
from app.skills.time_skill import TimeSkill


class RoutingRegressionTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.registry = SkillRegistry()

    def _assert_routes_to(
        self,
        command: str,
        expected_type: type,
    ) -> None:
        skill = self.registry.find_skill(
            command
        )

        self.assertIsNotNone(
            skill,
            msg=(
                f"No skill handled command: "
                f"{command}"
            ),
        )

        self.assertIsInstance(
            skill,
            expected_type,
            msg=(
                f"{command!r} routed to "
                f"{type(skill).__name__} "
                f"instead of "
                f"{expected_type.__name__}"
            ),
        )

    # ==================================================
    # TIME
    # ==================================================

    def test_time_routes_to_time_skill(
        self,
    ) -> None:
        self._assert_routes_to(
            "what time is it",
            TimeSkill,
        )

    # ==================================================
    # APP LAUNCHING
    # ==================================================

    def test_open_app_routes_to_launcher(
        self,
    ) -> None:
        self._assert_routes_to(
            "open chrome",
            AppLauncherSkill,
        )

    # ==================================================
    # SEARCH
    # ==================================================

    def test_search_routes_to_search_skill(
        self,
    ) -> None:
        self._assert_routes_to(
            "search python decorators",
            SearchSkill,
        )

    # ==================================================
    # EXPLICIT REMEMBER
    # ==================================================

    def test_remember_routes_to_memory_skill(
        self,
    ) -> None:
        self._assert_routes_to(
            "remember that I prefer dark mode",
            MemorySkill,
        )

    # ==================================================
    # MEMORY CONTROL
    # ==================================================

    def test_memory_control_has_priority(
        self,
    ) -> None:
        self._assert_routes_to(
            "show active memories",
            MemoryControlSkill,
        )

    # ==================================================
    # UNSUPPORTED REAL-WORLD ACTION
    # ==================================================

    def test_unsupported_action_routes_to_guard(
        self,
    ) -> None:
        self._assert_routes_to(
            "turn off wifi",
            ActionGuardSkill,
        )

    # ==================================================
    # UNSUPPORTED UI ACTION
    # ==================================================

    def test_type_action_routes_to_guard(
        self,
    ) -> None:
        self._assert_routes_to(
            "type hello",
            ActionGuardSkill,
        )

    # ==================================================
    # GENERAL AI REQUEST
    # ==================================================

    def test_general_request_routes_to_ai(
        self,
    ) -> None:
        self._assert_routes_to(
            (
                "write a python function "
                "that adds two numbers"
            ),
            AISkill,
        )


if __name__ == "__main__":
    unittest.main()