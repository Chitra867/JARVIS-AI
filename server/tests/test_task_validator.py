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

    def test_supported_two_step_plan_is_safe(
        self,
    ) -> None:
        result = self.validator.validate(
            (
                "open chrome and then "
                "search Python decorators"
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

    def test_unsupported_action_blocks_plan(
        self,
    ) -> None:
        result = self.validator.validate(
            (
                "open chrome and then "
                "turn off wifi"
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

    def test_type_action_is_blocked(
        self,
    ) -> None:
        result = self.validator.validate(
            (
                "open notepad then "
                "type hello"
            )
        )

        self.assertFalse(
            result.is_safe_to_execute
        )

        self.assertEqual(
            result.steps[1].step_type,
            StepType.BLOCKED,
        )

    def test_ai_reasoning_step_is_allowed(
        self,
    ) -> None:
        result = self.validator.validate(
            "explain dependency injection"
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

    def test_empty_plan_is_not_safe(
        self,
    ) -> None:
        result = self.validator.validate(
            "   "
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