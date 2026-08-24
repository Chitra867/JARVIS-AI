import unittest

from app.skills.action_guard_skill import (
    ActionGuardSkill,
)

from app.skills.ai_skill import (
    AISkill,
)

from app.skills.app_launcher_skill import (
    AppLauncherSkill,
)

from app.skills.input_control_skill import (
    InputControlSkill,
)

from app.skills.memory_control_skill import (
    MemoryControlSkill,
)

from app.skills.memory_skill import (
    MemorySkill,
)

from app.skills.registry import (
    SkillRegistry,
)

from app.skills.search_skill import (
    SearchSkill,
)

from app.skills.time_skill import (
    TimeSkill,
)

from app.skills.ui_click_skill import (
    UIAutomationClickSkill,
)


class RoutingRegressionTests(
    unittest.TestCase
):
    def setUp(
        self,
    ) -> None:
        self.registry = (
            SkillRegistry()
        )

    # ==================================================
    # ROUTING ASSERTION HELPER
    # ==================================================

    def _assert_routes_to(
        self,
        command: str,
        expected_type: type,
    ) -> None:
        skill = (
            self.registry
            .find_skill(
                command
            )
        )

        self.assertIsNotNone(
            skill,
            msg=(
                "No skill handled command: "
                f"{command}"
            ),
        )

        self.assertIsInstance(
            skill,
            expected_type,
            msg=(
                f"{command!r} routed to "
                f"{type(skill).__name__} "
                "instead of "
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
    # SUPPORTED TEXT INPUT
    # ==================================================

    def test_type_action_routes_to_input_control(
        self,
    ) -> None:
        self._assert_routes_to(
            "type hello",
            InputControlSkill,
        )

    # ==================================================
    # SUPPORTED KEYBOARD ACTIONS
    # ==================================================

    def test_press_enter_routes_to_input_control(
        self,
    ) -> None:
        self._assert_routes_to(
            "press enter",
            InputControlSkill,
        )

    def test_press_copy_routes_to_input_control(
        self,
    ) -> None:
        self._assert_routes_to(
            "press copy",
            InputControlSkill,
        )

    # ==================================================
    # GUARDED UI TARGET CLICKS
    # ==================================================

    def test_targeted_click_routes_to_ui_automation(
        self,
    ) -> None:
        commands = (
            (
                "click the close button "
                "on my screen"
            ),

            "click terminal menu item",

            "click search",
        )

        for command in (
            commands
        ):
            with self.subTest(
                command=command
            ):
                self._assert_routes_to(
                    command,
                    UIAutomationClickSkill,
                )

    # ==================================================
    # UI CLICK CONFIRMATION
    # ==================================================

    def test_ui_click_confirmation_routes_to_ui_automation(
        self,
    ) -> None:
        commands = (
            "confirm click abc123",
            "confirm ui click abc123",
        )

        for command in (
            commands
        ):
            with self.subTest(
                command=command
            ):
                self._assert_routes_to(
                    command,
                    UIAutomationClickSkill,
                )

    # ==================================================
    # UI CLICK CANCELLATION
    # ==================================================

    def test_ui_click_cancel_routes_to_ui_automation(
        self,
    ) -> None:
        commands = (
            "cancel click",
            "cancel ui click",
        )

        for command in (
            commands
        ):
            with self.subTest(
                command=command
            ):
                self._assert_routes_to(
                    command,
                    UIAutomationClickSkill,
                )

    # ==================================================
    # BASIC MOUSE ACTION
    # ==================================================

    def test_bare_click_routes_to_input_control(
        self,
    ) -> None:
        self._assert_routes_to(
            "click",
            InputControlSkill,
        )

    def test_scroll_routes_to_input_control(
        self,
    ) -> None:
        self._assert_routes_to(
            "scroll down",
            InputControlSkill,
        )

    # ==================================================
    # UNSUPPORTED INPUT ACTIONS
    # ==================================================

    def test_unsupported_key_action_routes_to_guard(
        self,
    ) -> None:
        self._assert_routes_to(
            "press alt f4",
            ActionGuardSkill,
        )

    def test_unsupported_drag_routes_to_guard(
        self,
    ) -> None:
        self._assert_routes_to(
            "drag this",
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