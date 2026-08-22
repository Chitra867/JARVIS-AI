import unittest

from app.core.task_context import (
    ReferenceType,
    TaskReference,
)

from app.core.task_runtime import (
    PageResource,
    RuntimeOutputType,
    SearchResult,
    StepRuntimeOutput,
    TaskReferenceResolver,
    TaskRuntimeContext,
)


class TaskRuntimeTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.context = (
            TaskRuntimeContext()
        )

        self.resolver = (
            TaskReferenceResolver()
        )

    # ==================================================
    # FIRST SEARCH RESULT
    # ==================================================

    def test_first_search_result_resolves(
        self,
    ) -> None:
        self.context.record(
            StepRuntimeOutput(
                step_index=1,
                output_type=(
                    RuntimeOutputType
                    .SEARCH_RESULTS
                ),
                search_results=(
                    SearchResult(
                        title="FastAPI",
                        url=(
                            "https://fastapi.tiangolo.com/"
                        ),
                    ),
                    SearchResult(
                        title="FastAPI GitHub",
                        url=(
                            "https://github.com/fastapi/fastapi"
                        ),
                    ),
                ),
            )
        )

        reference = TaskReference(
            reference_type=(
                ReferenceType
                .FIRST_SEARCH_RESULT
            ),
            raw_text="the first result",
            source_step_index=1,
        )

        result = (
            self.resolver
            .resolve(
                reference,
                self.context,
            )
        )

        self.assertTrue(
            result.resolved
        )

        self.assertIsInstance(
            result.value,
            SearchResult,
        )

        self.assertEqual(
            result.value.url,
            "https://fastapi.tiangolo.com/",
        )

    # ==================================================
    # EMPTY SEARCH RESULTS
    # ==================================================

    def test_empty_search_results_do_not_resolve(
        self,
    ) -> None:
        self.context.record(
            StepRuntimeOutput(
                step_index=1,
                output_type=(
                    RuntimeOutputType
                    .SEARCH_RESULTS
                ),
                search_results=(),
            )
        )

        reference = TaskReference(
            reference_type=(
                ReferenceType
                .FIRST_SEARCH_RESULT
            ),
            raw_text="first result",
            source_step_index=1,
        )

        result = (
            self.resolver
            .resolve(
                reference,
                self.context,
            )
        )

        self.assertFalse(
            result.resolved
        )

        self.assertIn(
            "no results",
            result.reason.lower(),
        )

    # ==================================================
    # WRONG OUTPUT TYPE
    # ==================================================

    def test_first_result_requires_search_output(
        self,
    ) -> None:
        self.context.record(
            StepRuntimeOutput(
                step_index=1,
                output_type=(
                    RuntimeOutputType.TEXT
                ),
                text="Searching Google.",
            )
        )

        reference = TaskReference(
            reference_type=(
                ReferenceType
                .FIRST_SEARCH_RESULT
            ),
            raw_text="first result",
            source_step_index=1,
        )

        result = (
            self.resolver
            .resolve(
                reference,
                self.context,
            )
        )

        self.assertFalse(
            result.resolved
        )

        self.assertIn(
            "did not produce search results",
            result.reason.lower(),
        )

    # ==================================================
    # PREVIOUS PAGE
    # ==================================================

    def test_previous_page_resolves(
        self,
    ) -> None:
        page = PageResource(
            url=(
                "https://fastapi.tiangolo.com/"
            ),
            title="FastAPI",
        )

        self.context.record(
            StepRuntimeOutput(
                step_index=2,
                output_type=(
                    RuntimeOutputType.PAGE
                ),
                page=page,
            )
        )

        reference = TaskReference(
            reference_type=(
                ReferenceType.PREVIOUS_PAGE
            ),
            raw_text="that page",
            source_step_index=2,
        )

        result = (
            self.resolver
            .resolve(
                reference,
                self.context,
            )
        )

        self.assertTrue(
            result.resolved
        )

        self.assertEqual(
            result.value,
            page,
        )

    # ==================================================
    # MISSING SOURCE OUTPUT
    # ==================================================

    def test_missing_runtime_output_does_not_resolve(
        self,
    ) -> None:
        reference = TaskReference(
            reference_type=(
                ReferenceType.PREVIOUS_PAGE
            ),
            raw_text="that page",
            source_step_index=2,
        )

        result = (
            self.resolver
            .resolve(
                reference,
                self.context,
            )
        )

        self.assertFalse(
            result.resolved
        )

        self.assertIn(
            "no runtime output",
            result.reason.lower(),
        )

    # ==================================================
    # NO SOURCE STEP
    # ==================================================

    def test_reference_without_source_step_is_rejected(
        self,
    ) -> None:
        reference = TaskReference(
            reference_type=(
                ReferenceType
                .FIRST_SEARCH_RESULT
            ),
            raw_text="first result",
            source_step_index=None,
        )

        result = (
            self.resolver
            .resolve(
                reference,
                self.context,
            )
        )

        self.assertFalse(
            result.resolved
        )

        self.assertIn(
            "no source step",
            result.reason.lower(),
        )


if __name__ == "__main__":
    unittest.main()