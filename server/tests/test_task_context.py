import unittest

from app.core.task_context import (
    ReferenceType,
    TaskContextAnalyzer,
)

from app.core.task_planner import (
    TaskPlanner,
)


class TaskContextAnalyzerTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.planner = TaskPlanner()

        self.analyzer = (
            TaskContextAnalyzer()
        )

    def _analyze(
        self,
        command: str,
    ):
        plan = (
            self.planner
            .plan(
                command
            )
        )

        return (
            self.analyzer
            .analyze(
                plan
            )
        )

    # ==================================================
    # ORDINARY COMMAND
    # ==================================================

    def test_normal_steps_have_no_references(
        self,
    ) -> None:
        result = self._analyze(
            (
                "open chrome then "
                "search for FastAPI"
            )
        )

        self.assertFalse(
            result.has_contextual_references
        )

    # ==================================================
    # FIRST SEARCH RESULT
    # ==================================================

    def test_first_result_references_search_step(
        self,
    ) -> None:
        result = self._analyze(
            (
                "search google for FastAPI "
                "then open the first result"
            )
        )

        reference = (
            result
            .steps[1]
            .references[0]
        )

        self.assertEqual(
            reference.reference_type,
            ReferenceType.FIRST_SEARCH_RESULT,
        )

        self.assertEqual(
            reference.source_step_index,
            1,
        )

    # ==================================================
    # THAT PAGE
    # ==================================================

    def test_that_page_references_opened_result(
        self,
    ) -> None:
        result = self._analyze(
            (
                "search google for FastAPI, "
                "open the first result, "
                "then summarize that page"
            )
        )

        reference = (
            result
            .steps[2]
            .references[0]
        )

        self.assertEqual(
            reference.reference_type,
            ReferenceType.PREVIOUS_PAGE,
        )

        self.assertEqual(
            reference.source_step_index,
            2,
        )

    # ==================================================
    # ORPHAN REFERENCE
    # ==================================================

    def test_first_result_without_search_is_unresolved(
        self,
    ) -> None:
        result = self._analyze(
            "open the first result"
        )

        reference = (
            result
            .steps[0]
            .references[0]
        )

        self.assertFalse(
            reference.is_resolved
        )

        self.assertEqual(
            reference.source_step_index,
            None,
        )

    # ==================================================
    # COMPLETE DEPENDENCY CHAIN
    # ==================================================

    def test_three_step_dependency_chain(
        self,
    ) -> None:
        result = self._analyze(
            (
                "search google for Django, "
                "open the first result, "
                "then summarize that page"
            )
        )

        self.assertEqual(
            len(result.steps),
            3,
        )

        self.assertEqual(
            (
                result.steps[1]
                .references[0]
                .source_step_index
            ),
            1,
        )

        self.assertEqual(
            (
                result.steps[2]
                .references[0]
                .source_step_index
            ),
            2,
        )


if __name__ == "__main__":
    unittest.main()