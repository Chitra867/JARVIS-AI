import unittest

from app.core.task_planner import (
    TaskPlanner,
)


class TaskPlannerTests(
    unittest.TestCase
):
    def setUp(
        self,
    ) -> None:
        self.planner = (
            TaskPlanner()
        )

    # ==================================================
    # HELPER
    # ==================================================

    def _commands(
        self,
        command: str,
    ) -> list[str]:
        plan = (
            self.planner
            .plan(
                command
            )
        )

        return [
            step.command
            for step
            in plan.steps
        ]

    # ==================================================
    # SINGLE COMMAND
    # ==================================================

    def test_single_command_creates_one_step(
        self,
    ) -> None:
        plan = (
            self.planner
            .plan(
                "open chrome"
            )
        )

        self.assertFalse(
            plan.is_multi_step
        )

        self.assertEqual(
            len(
                plan.steps
            ),
            1,
        )

        self.assertEqual(
            plan.steps[
                0
            ].command,
            "open chrome",
        )

    # ==================================================
    # AND THEN
    # ==================================================

    def test_and_then_sequence_is_split(
        self,
    ) -> None:
        plan = (
            self.planner
            .plan(
                (
                    "open chrome and then "
                    "search for Python decorators"
                )
            )
        )

        self.assertTrue(
            plan.is_multi_step
        )

        self.assertEqual(
            [
                step.command
                for step
                in plan.steps
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
        plan = (
            self.planner
            .plan(
                (
                    "open notepad "
                    "then type hello"
                )
            )
        )

        self.assertEqual(
            len(
                plan.steps
            ),
            2,
        )

        self.assertEqual(
            plan.steps[
                0
            ].command,
            "open notepad",
        )

        self.assertEqual(
            plan.steps[
                1
            ].command,
            "type hello",
        )

    # ==================================================
    # PLAIN AND
    # ==================================================

    def test_plain_and_between_actions_is_split(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                (
                    "open notepad "
                    "and type hello"
                )
            ),
            [
                "open notepad",
                "type hello",
            ],
        )

    # ==================================================
    # MULTIPLE EXPLICIT MARKERS
    # ==================================================

    def test_multiple_sequence_markers(
        self,
    ) -> None:
        plan = (
            self.planner
            .plan(
                (
                    "open chrome, "
                    "then search Python, "
                    "after that open notepad"
                )
            )
        )

        self.assertEqual(
            len(
                plan.steps
            ),
            3,
        )

        self.assertEqual(
            plan.steps[
                0
            ].index,
            1,
        )

        self.assertEqual(
            plan.steps[
                2
            ].index,
            3,
        )

        self.assertEqual(
            [
                step.command
                for step
                in plan.steps
            ],
            [
                "open chrome",
                "search Python",
                "open notepad",
            ],
        )

    # ==================================================
    # FIRST
    # ==================================================

    def test_first_marker_is_removed(
        self,
    ) -> None:
        plan = (
            self.planner
            .plan(
                (
                    "first open chrome "
                    "then search Python"
                )
            )
        )

        self.assertEqual(
            plan.steps[
                0
            ].command,
            "open chrome",
        )

    # ==================================================
    # FINALLY
    # ==================================================

    def test_finally_marker_is_split(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                (
                    "open chrome "
                    "finally open notepad"
                )
            ),
            [
                "open chrome",
                "open notepad",
            ],
        )

    # ==================================================
    # AFTER THAT
    # ==================================================

    def test_after_that_sequence_is_split(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                (
                    "open chrome "
                    "after that open notepad"
                )
            ),
            [
                "open chrome",
                "open notepad",
            ],
        )

    # ==================================================
    # AFTERWARDS
    # ==================================================

    def test_afterwards_sequence_is_split(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                (
                    "open chrome "
                    "afterwards open notepad"
                )
            ),
            [
                "open chrome",
                "open notepad",
            ],
        )

    # ==================================================
    # EMPTY COMMAND
    # ==================================================

    def test_empty_command_creates_empty_plan(
        self,
    ) -> None:
        plan = (
            self.planner
            .plan(
                "   "
            )
        )

        self.assertEqual(
            plan.steps,
            (),
        )

        self.assertFalse(
            plan.is_multi_step
        )

    # ==================================================
    # COMMA SEQUENCE
    # ==================================================

    def test_comma_separated_actions_are_split(
        self,
    ) -> None:
        plan = (
            self.planner
            .plan(
                (
                    "open chrome, "
                    "search for Python decorators"
                )
            )
        )

        self.assertEqual(
            [
                step.command
                for step
                in plan.steps
            ],
            [
                "open chrome",
                "search for Python decorators",
            ],
        )

    # ==================================================
    # SEMICOLON SEQUENCE
    # ==================================================

    def test_semicolon_separated_actions_are_split(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                (
                    "open chrome; "
                    "open notepad"
                )
            ),
            [
                "open chrome",
                "open notepad",
            ],
        )

    # ==================================================
    # YOUTUBE CONTEXT THROUGH AND
    # ==================================================

    def test_youtube_context_through_plain_and(
        self,
    ) -> None:
        plan = (
            self.planner
            .plan(
                (
                    "open YouTube and "
                    "search for Python tutorials"
                )
            )
        )

        self.assertEqual(
            [
                step.command
                for step
                in plan.steps
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
        plan = (
            self.planner
            .plan(
                (
                    "open YouTube then "
                    "search for FastAPI tutorial"
                )
            )
        )

        self.assertEqual(
            len(
                plan.steps
            ),
            2,
        )

        self.assertEqual(
            plan.steps[
                0
            ].command,
            "open YouTube",
        )

        self.assertEqual(
            plan.steps[
                1
            ].command,
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
        plan = (
            self.planner
            .plan(
                (
                    "open YouTube and "
                    "search youtube for "
                    "Python decorators"
                )
            )
        )

        self.assertEqual(
            [
                step.command
                for step
                in plan.steps
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
    # GOOGLE CONTEXT
    # ==================================================

    def test_search_after_opening_chrome_remains_generic(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                (
                    "open chrome "
                    "and search Python decorators"
                )
            ),
            [
                "open chrome",
                "search Python decorators",
            ],
        )

    # ==================================================
    # FULL NATURAL COMMAND
    # ==================================================

    def test_natural_four_step_command(
        self,
    ) -> None:
        plan = (
            self.planner
            .plan(
                (
                    "Open Chrome, "
                    "search for Python decorators, "
                    "then open YouTube and "
                    "search for a tutorial."
                )
            )
        )

        self.assertEqual(
            len(
                plan.steps
            ),
            4,
        )

        self.assertEqual(
            [
                step.command
                for step
                in plan.steps
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
    # DO NOT SPLIT SEARCH QUERY CONTENT
    # ==================================================

    def test_search_query_with_and_is_not_split(
        self,
    ) -> None:
        plan = (
            self.planner
            .plan(
                (
                    "search for "
                    "React and Vue"
                )
            )
        )

        self.assertEqual(
            len(
                plan.steps
            ),
            1,
        )

        self.assertEqual(
            plan.steps[
                0
            ].command,
            "search for React and Vue",
        )

    def test_search_query_with_comma_is_not_split(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                (
                    "search React, "
                    "Vue and Angular"
                )
            ),
            [
                (
                    "search React, "
                    "Vue and Angular"
                ),
            ],
        )

    # ==================================================
    # NEXT.JS FALSE SEPARATOR REGRESSION
    # ==================================================

    def test_next_dot_js_is_not_split(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                "search next.js documentation"
            ),
            [
                "search next.js documentation",
            ],
        )

    def test_next_word_inside_search_query_is_not_split(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                (
                    "search what comes "
                    "next in Python"
                )
            ),
            [
                (
                    "search what comes "
                    "next in Python"
                ),
            ],
        )

    # ==================================================
    # MIXED ACTION + AI
    # ==================================================

    def test_action_and_ai_request_are_split(
        self,
    ) -> None:
        plan = (
            self.planner
            .plan(
                (
                    "open chrome and "
                    "explain dependency injection"
                )
            )
        )

        self.assertEqual(
            len(
                plan.steps
            ),
            2,
        )

        self.assertEqual(
            plan.steps[
                0
            ].command,
            "open chrome",
        )

        self.assertEqual(
            plan.steps[
                1
            ].command,
            "explain dependency injection",
        )

    # ==================================================
    # UI CONFIRMATION SAFETY
    # ==================================================

    def test_ui_confirmation_after_and_is_split(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                (
                    "click delete button "
                    "and confirm click abc123"
                )
            ),
            [
                "click delete button",
                "confirm click abc123",
            ],
        )

    def test_ui_confirmation_with_ui_prefix_is_split(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                (
                    "click delete button "
                    "and confirm ui click abc123"
                )
            ),
            [
                "click delete button",
                "confirm ui click abc123",
            ],
        )

    def test_ui_confirmation_after_then_is_split(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                (
                    "click delete button "
                    "then confirm click abc123"
                )
            ),
            [
                "click delete button",
                "confirm click abc123",
            ],
        )

    # ==================================================
    # UI CANCELLATION
    # ==================================================

    def test_ui_cancel_after_click_is_split(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                (
                    "click delete button "
                    "and cancel click"
                )
            ),
            [
                "click delete button",
                "cancel click",
            ],
        )

    # ==================================================
    # POWER CONFIRMATION SAFETY
    # ==================================================

    def test_power_confirmation_after_and_is_split(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                (
                    "shutdown computer "
                    "and confirm shutdown"
                )
            ),
            [
                "shutdown computer",
                "confirm shutdown",
            ],
        )

    def test_power_confirmation_after_then_is_split(
        self,
    ) -> None:
        self.assertEqual(
            self._commands(
                (
                    "shutdown computer "
                    "then confirm shutdown"
                )
            ),
            [
                "shutdown computer",
                "confirm shutdown",
            ],
        )

    # ==================================================
    # STEP INDEXES
    # ==================================================

    def test_step_indexes_are_sequential(
        self,
    ) -> None:
        plan = (
            self.planner
            .plan(
                (
                    "open chrome, "
                    "open notepad, "
                    "take screenshot"
                )
            )
        )

        self.assertEqual(
            [
                step.index
                for step
                in plan.steps
            ],
            [
                1,
                2,
                3,
            ],
        )

    # ==================================================
    # MAXIMUM STEP LIMIT
    # ==================================================

    def test_plan_does_not_exceed_max_steps(
        self,
    ) -> None:
        commands = [
            "open chrome",
            "open notepad",
            "take screenshot",
            "open calculator",
            "open paint",
            "open settings",
            "open terminal",
            "open explorer",
            "open edge",
            "open youtube",
        ]

        plan = (
            self.planner
            .plan(
                " then ".join(
                    commands
                )
            )
        )

        self.assertEqual(
            len(
                plan.steps
            ),
            self.planner.MAX_STEPS,
        )

        self.assertEqual(
            len(
                plan.steps
            ),
            8,
        )


if __name__ == "__main__":
    unittest.main()