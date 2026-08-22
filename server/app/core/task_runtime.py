from dataclasses import dataclass
from enum import Enum

from app.core.task_context import (
    ReferenceType,
    TaskReference,
)


class RuntimeOutputType(str, Enum):
    TEXT = "text"
    SEARCH_RESULTS = "search_results"
    PAGE = "page"


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str


@dataclass(frozen=True)
class PageResource:
    url: str
    title: str | None = None
    content: str | None = None


@dataclass(frozen=True)
class StepRuntimeOutput:
    step_index: int
    output_type: RuntimeOutputType
    text: str = ""
    search_results: tuple[
        SearchResult,
        ...
    ] = ()
    page: PageResource | None = None


@dataclass(frozen=True)
class ReferenceResolution:
    reference: TaskReference
    resolved: bool
    value: object | None
    reason: str


class TaskRuntimeContext:
    def __init__(
        self,
    ) -> None:
        self._outputs: dict[
            int,
            StepRuntimeOutput,
        ] = {}

    # ==================================================
    # RECORD OUTPUT
    # ==================================================

    def record(
        self,
        output: StepRuntimeOutput,
    ) -> None:
        self._outputs[
            output.step_index
        ] = output

    # ==================================================
    # READ OUTPUT
    # ==================================================

    def get(
        self,
        step_index: int,
    ) -> StepRuntimeOutput | None:
        return self._outputs.get(
            step_index
        )

    # ==================================================
    # CLEAR
    # ==================================================

    def clear(
        self,
    ) -> None:
        self._outputs.clear()


class TaskReferenceResolver:
    # ==================================================
    # RESOLVE
    # ==================================================

    def resolve(
        self,
        reference: TaskReference,
        runtime_context: TaskRuntimeContext,
    ) -> ReferenceResolution:
        # ----------------------------------------------
        # Dependency analyzer could not identify
        # a source step.
        # ----------------------------------------------

        if (
            reference.source_step_index
            is None
        ):
            return ReferenceResolution(
                reference=reference,
                resolved=False,
                value=None,
                reason=(
                    "Reference has no source step."
                ),
            )

        source_output = (
            runtime_context
            .get(
                reference.source_step_index
            )
        )

        # ----------------------------------------------
        # Source step has not executed / produced output.
        # ----------------------------------------------

        if source_output is None:
            return ReferenceResolution(
                reference=reference,
                resolved=False,
                value=None,
                reason=(
                    "Source step has no runtime output."
                ),
            )

        # ----------------------------------------------
        # FIRST SEARCH RESULT
        # ----------------------------------------------

        if (
            reference.reference_type
            == ReferenceType.FIRST_SEARCH_RESULT
        ):
            return (
                self._resolve_first_search_result(
                    reference,
                    source_output,
                )
            )

        # ----------------------------------------------
        # PREVIOUS PAGE
        # ----------------------------------------------

        if (
            reference.reference_type
            == ReferenceType.PREVIOUS_PAGE
        ):
            return (
                self._resolve_previous_page(
                    reference,
                    source_output,
                )
            )

        return ReferenceResolution(
            reference=reference,
            resolved=False,
            value=None,
            reason=(
                "Unsupported reference type."
            ),
        )

    # ==================================================
    # FIRST SEARCH RESULT
    # ==================================================

    def _resolve_first_search_result(
        self,
        reference: TaskReference,
        source_output: StepRuntimeOutput,
    ) -> ReferenceResolution:
        if (
            source_output.output_type
            != RuntimeOutputType.SEARCH_RESULTS
        ):
            return ReferenceResolution(
                reference=reference,
                resolved=False,
                value=None,
                reason=(
                    "Source step did not produce "
                    "search results."
                ),
            )

        if not source_output.search_results:
            return ReferenceResolution(
                reference=reference,
                resolved=False,
                value=None,
                reason=(
                    "Search produced no results."
                ),
            )

        first_result = (
            source_output
            .search_results[0]
        )

        if not first_result.url.strip():
            return ReferenceResolution(
                reference=reference,
                resolved=False,
                value=None,
                reason=(
                    "First search result has no URL."
                ),
            )

        return ReferenceResolution(
            reference=reference,
            resolved=True,
            value=first_result,
            reason=(
                "Resolved from the first "
                "search result."
            ),
        )

    # ==================================================
    # PREVIOUS PAGE
    # ==================================================

    def _resolve_previous_page(
        self,
        reference: TaskReference,
        source_output: StepRuntimeOutput,
    ) -> ReferenceResolution:
        if (
            source_output.output_type
            != RuntimeOutputType.PAGE
        ):
            return ReferenceResolution(
                reference=reference,
                resolved=False,
                value=None,
                reason=(
                    "Source step did not produce "
                    "a page resource."
                ),
            )

        page = (
            source_output.page
        )

        if (
            page is None
            or not page.url.strip()
        ):
            return ReferenceResolution(
                reference=reference,
                resolved=False,
                value=None,
                reason=(
                    "Source step has no usable page."
                ),
            )

        return ReferenceResolution(
            reference=reference,
            resolved=True,
            value=page,
            reason=(
                "Resolved from the previously "
                "opened page."
            ),
        )


task_reference_resolver = (
    TaskReferenceResolver()
)