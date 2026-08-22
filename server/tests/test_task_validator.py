import unittest

from app.core.task_validator import (
    StepType,
    TaskValidator,
)


class TaskValidatorTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.validator = TaskValidator()

    # ==================================================
    # SUPPORTED MULTI-STEP PLAN
    # ==================================================

    def test_supported_two_step_plan_is_safe(
        self,
    ) -> None:
        result = (
            self.validator
            .validate(
                (
                    "open chrome and then "
                    "search Python decorators"
                )
            )
        )

        self.assertTrue(
            result.is_multi_step
        )

        self.assertTrue(
            result.is_safe_to_execute
        )

        self.assertEqual(
            len(result.steps),
            2,
        )

        self.assertEqual(
            result.steps[0].handler,
            "AppLauncherSkill",
        )

        self.assertEqual(
            result.steps[1].handler,
            "SearchSkill",
        )

    # ==================================================
    # UNSUPPORTED ACTION
    # ==================================================

    def test_unsupported_action_blocks_plan(
        self,
    ) -> None:
        result = (
            self.validator
            .validate(
                (
                    "open chrome and then "
                    "turn off wifi"
                )
            )
        )

        self.assertFalse(
            result.is_safe_to_execute
        )

        self.assertEqual(
            len(result.blocked_steps),
            1,
        )

        self.assertEqual(
            result.blocked_steps[0].command,
            "turn off wifi",
        )

    # ==================================================
    # UI ACTION
    # ==================================================

    def test_type_action_is_blocked(
        self,
    ) -> None:
        result = (
            self.validator
            .validate(
                (
                    "open notepad then "
                    "type hello"
                )
            )
        )

        self.assertFalse(
            result.is_safe_to_execute
        )

        self.assertEqual(
            result.steps[1].step_type,
            StepType.BLOCKED,
        )

    # ==================================================
    # SINGLE AI STEP
    # ==================================================

    def test_ai_reasoning_step_is_allowed(
        self,
    ) -> None:
        result = (
            self.validator
            .validate(
                "explain dependency injection"
            )
        )

        self.assertTrue(
            result.is_safe_to_execute
        )

        self.assertEqual(
            result.steps[0].step_type,
            StepType.AI,
        )

        self.assertEqual(
            result.steps[0].handler,
            "AISkill",
        )

    # ==================================================
    # AI INSIDE MULTI-STEP PLAN
    # ==================================================

    def test_ai_step_inside_multi_step_plan_is_blocked(
        self,
    ) -> None:
        result = (
            self.validator
            .validate(
                (
                    "open chrome then "
                    "explain dependency injection"
                )
            )
        )

        self.assertTrue(
            result.is_multi_step
        )

        self.assertFalse(
            result.is_safe_to_execute
        )

        self.assertEqual(
            result.steps[0].step_type,
            StepType.SKILL,
        )

        self.assertEqual(
            result.steps[0].handler,
            "AppLauncherSkill",
        )

        self.assertTrue(
            result.steps[0].allowed
        )

        self.assertEqual(
            result.steps[1].step_type,
            StepType.BLOCKED,
        )

        self.assertEqual(
            result.steps[1].handler,
            "AISkill",
        )

        self.assertFalse(
            result.steps[1].allowed
        )

        self.assertIn(
            "AI reasoning cannot yet",
            result.steps[1].reason,
        )

    # ==================================================
    # EMPTY PLAN
    # ==================================================

    def test_empty_plan_is_not_safe(
        self,
    ) -> None:
        result = (
            self.validator
            .validate(
                "   "
            )
        )

        self.assertFalse(
            result.is_safe_to_execute
        )

        self.assertEqual(
            result.steps,
            (),
        )


if __name__ == "__main__":
    unittest.main()