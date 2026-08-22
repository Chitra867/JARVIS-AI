import unittest

from app.core.task_planner import (
    TaskPlanner,
)


class TaskPlannerTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.planner = TaskPlanner()

    def test_single_command_creates_one_step(
        self,
    ) -> None:
        plan = self.planner.plan(
            "open chrome"
        )

        self.assertFalse(
            plan.is_multi_step
        )

        self.assertEqual(
            len(plan.steps),
            1,
        )

        self.assertEqual(
            plan.steps[0].command,
            "open chrome",
        )

    def test_and_then_sequence_is_split(
        self,
    ) -> None:
        plan = self.planner.plan(
            (
                "open chrome and then "
                "search for Python decorators"
            )
        )

        self.assertTrue(
            plan.is_multi_step
        )

        self.assertEqual(
            [
                step.command
                for step in plan.steps
            ],
            [
                "open chrome",
                "search for Python decorators",
            ],
        )

    def test_then_sequence_is_split(
        self,
    ) -> None:
        plan = self.planner.plan(
            "open notepad then type hello"
        )

        self.assertEqual(
            len(plan.steps),
            2,
        )

        self.assertEqual(
            plan.steps[0].command,
            "open notepad",
        )

        self.assertEqual(
            plan.steps[1].command,
            "type hello",
        )

    def test_multiple_sequence_markers(
        self,
    ) -> None:
        plan = self.planner.plan(
            (
                "open chrome, then search Python, "
                "after that open notepad"
            )
        )

        self.assertEqual(
            len(plan.steps),
            3,
        )

        self.assertEqual(
            plan.steps[0].index,
            1,
        )

        self.assertEqual(
            plan.steps[2].index,
            3,
        )

    def test_first_marker_is_removed(
        self,
    ) -> None:
        plan = self.planner.plan(
            (
                "first open chrome "
                "then search Python"
            )
        )

        self.assertEqual(
            plan.steps[0].command,
            "open chrome",
        )

    def test_empty_command_creates_empty_plan(
        self,
    ) -> None:
        plan = self.planner.plan(
            "   "
        )

        self.assertEqual(
            plan.steps,
            (),
        )

        self.assertFalse(
            plan.is_multi_step
        )


if __name__ == "__main__":
    unittest.main()