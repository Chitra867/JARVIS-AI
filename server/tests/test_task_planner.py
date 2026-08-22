import unittest

from app.core.task_planner import (
    TaskPlanner,
)


class TaskPlannerTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.planner = TaskPlanner()

    # ==================================================
    # SINGLE COMMAND
    # ==================================================

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

    # ==================================================
    # AND THEN
    # ==================================================

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

    # ==================================================
    # THEN
    # ==================================================

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

    # ==================================================
    # MULTIPLE EXPLICIT MARKERS
    # ==================================================

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

    # ==================================================
    # FIRST
    # ==================================================

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

    # ==================================================
    # EMPTY COMMAND
    # ==================================================

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

    # ==================================================
    # NATURAL COMMA SEQUENCE
    # ==================================================

    def test_comma_separated_actions_are_split(
        self,
    ) -> None:
        plan = self.planner.plan(
            (
                "open chrome, "
                "search for Python decorators"
            )
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

    # ==================================================
    # YOUTUBE CONTEXT THROUGH "AND"
    # ==================================================

    def test_plain_and_between_actions_is_split(
        self,
    ) -> None:
        plan = self.planner.plan(
            (
                "open YouTube and "
                "search for Python tutorials"
            )
        )

        self.assertEqual(
            [
                step.command
                for step in plan.steps
            ],
            [
                "open YouTube",
                (
                    "search youtube for "
                    "Python tutorials"
                ),
            ],
        )

    # ==================================================
    # YOUTUBE PROVIDER INHERITANCE
    # ==================================================

    def test_search_after_opening_youtube_uses_youtube(
        self,
    ) -> None:
        plan = self.planner.plan(
            (
                "open YouTube then "
                "search for FastAPI tutorial"
            )
        )

        self.assertEqual(
            len(plan.steps),
            2,
        )

        self.assertEqual(
            plan.steps[0].command,
            "open YouTube",
        )

        self.assertEqual(
            plan.steps[1].command,
            (
                "search youtube for "
                "FastAPI tutorial"
            ),
        )

    # ==================================================
    # EXPLICIT YOUTUBE SEARCH
    # ==================================================

    def test_explicit_youtube_search_is_preserved(
        self,
    ) -> None:
        plan = self.planner.plan(
            (
                "open YouTube and "
                "search youtube for Python decorators"
            )
        )

        self.assertEqual(
            [
                step.command
                for step in plan.steps
            ],
            [
                "open YouTube",
                (
                    "search youtube for "
                    "Python decorators"
                ),
            ],
        )

    # ==================================================
    # FULL NATURAL COMMAND
    # ==================================================

    def test_natural_four_step_command(
        self,
    ) -> None:
        plan = self.planner.plan(
            (
                "Open Chrome, "
                "search for Python decorators, "
                "then open YouTube and "
                "search for a tutorial."
            )
        )

        self.assertEqual(
            len(plan.steps),
            4,
        )

        self.assertEqual(
            [
                step.command
                for step in plan.steps
            ],
            [
                "Open Chrome",
                "search for Python decorators",
                "open YouTube",
                (
                    "search youtube for "
                    "a tutorial"
                ),
            ],
        )

    # ==================================================
    # DO NOT SPLIT QUERY CONTENT
    # ==================================================

    def test_search_query_with_and_is_not_split(
        self,
    ) -> None:
        plan = self.planner.plan(
            "search for React and Vue"
        )

        self.assertEqual(
            len(plan.steps),
            1,
        )

        self.assertEqual(
            plan.steps[0].command,
            "search for React and Vue",
        )

    # ==================================================
    # MIXED ACTION + AI
    # ==================================================

    def test_action_and_ai_request_are_split(
        self,
    ) -> None:
        plan = self.planner.plan(
            (
                "open chrome and "
                "explain dependency injection"
            )
        )

        self.assertEqual(
            len(plan.steps),
            2,
        )

        self.assertEqual(
            plan.steps[0].command,
            "open chrome",
        )

        self.assertEqual(
            plan.steps[1].command,
            "explain dependency injection",
        )


if __name__ == "__main__":
    unittest.main()