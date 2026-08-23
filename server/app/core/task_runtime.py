from dataclasses import (
    dataclass,
)

from enum import (
    Enum,
)

from threading import (
    RLock,
)

from app.core.task_context import (
    ReferenceType,
    TaskReference,
)


# =========================================================
# RUNTIME OUTPUT TYPES
# =========================================================


class RuntimeOutputType(
    str,
    Enum,
):
    TEXT = "text"
    SEARCH_RESULTS = "search_results"
    PAGE = "page"


# =========================================================
# SEARCH RESULT
# =========================================================


@dataclass(
    frozen=True
)
class SearchResult:
    title: str
    url: str


# =========================================================
# PAGE RESOURCE
# =========================================================


@dataclass(
    frozen=True
)
class PageResource:
    url: str
    title: str | None = None
    content: str | None = None


# =========================================================
# STEP RUNTIME OUTPUT
# =========================================================


@dataclass(
    frozen=True
)
class StepRuntimeOutput:
    step_index: int
    output_type: RuntimeOutputType

    text: str = ""

    search_results: tuple[
        SearchResult,
        ...
    ] = ()

    page: PageResource | None = None


# =========================================================
# REFERENCE RESOLUTION
# =========================================================


@dataclass(
    frozen=True
)
class ReferenceResolution:
    reference: TaskReference
    resolved: bool
    value: object | None
    reason: str


# =========================================================
# PER-TASK RUNTIME CONTEXT
# =========================================================


class TaskRuntimeContext:
    def __init__(
        self,
    ) -> None:
        self._outputs: dict[
            int,
            StepRuntimeOutput,
        ] = {}

    # =====================================================
    # RECORD
    # =====================================================

    def record(
        self,
        output: StepRuntimeOutput,
    ) -> None:
        self._outputs[
            output.step_index
        ] = output

    # =====================================================
    # GET
    # =====================================================

    def get(
        self,
        step_index: int,
    ) -> StepRuntimeOutput | None:
        return (
            self._outputs
            .get(
                step_index
            )
        )

    # =====================================================
    # CLEAR
    # =====================================================

    def clear(
        self,
    ) -> None:
        self._outputs.clear()


# =========================================================
# PERSISTENT ACTIVE PAGE CONTEXT
# =========================================================


class PageContextStore:
    LOCAL_CONTEXT_KEY = (
        "__local__"
    )

    def __init__(
        self,
    ) -> None:
        self._pages: dict[
            str,
            PageResource,
        ] = {}

        self._lock = (
            RLock()
        )

    # =====================================================
    # RECORD PAGE
    # =====================================================

    def record(
        self,
        page: PageResource,
        conversation_id: object | None = None,
    ) -> None:
        if not (
            page.url
            .strip()
        ):
            return

        key = (
            self._context_key(
                conversation_id
            )
        )

        with self._lock:
            self._pages[
                key
            ] = page

    # =====================================================
    # GET PAGE
    # =====================================================

    def get(
        self,
        conversation_id: object | None = None,
    ) -> PageResource | None:
        key = (
            self._context_key(
                conversation_id
            )
        )

        with self._lock:
            return (
                self._pages
                .get(
                    key
                )
            )

    # =====================================================
    # CLEAR PAGE
    # =====================================================

    def clear(
        self,
        conversation_id: object | None = None,
    ) -> None:
        key = (
            self._context_key(
                conversation_id
            )
        )

        with self._lock:
            self._pages.pop(
                key,
                None,
            )

    # =====================================================
    # CONTEXT KEY
    # =====================================================

    def _context_key(
        self,
        conversation_id: object | None,
    ) -> str:
        if (
            conversation_id
            is None
        ):
            return (
                self.LOCAL_CONTEXT_KEY
            )

        return (
            f"conversation:"
            f"{conversation_id}"
        )


page_context_store = (
    PageContextStore()
)


# =========================================================
# TASK REFERENCE RESOLVER
# =========================================================


class TaskReferenceResolver:
    # =====================================================
    # RESOLVE
    # =====================================================

    def resolve(
        self,
        reference: TaskReference,
        runtime_context: TaskRuntimeContext,
    ) -> ReferenceResolution:
        # -------------------------------------------------
        # NO SOURCE STEP
        # -------------------------------------------------

        if (
            reference.source_step_index
            is None
        ):
            return ReferenceResolution(
                reference=reference,
                resolved=False,
                value=None,
                reason=(
                    "Reference has no "
                    "source step."
                ),
            )

        source_output = (
            runtime_context
            .get(
                reference
                .source_step_index
            )
        )

        # -------------------------------------------------
        # SOURCE STEP HAS NO OUTPUT
        # -------------------------------------------------

        if (
            source_output
            is None
        ):
            return ReferenceResolution(
                reference=reference,
                resolved=False,
                value=None,
                reason=(
                    "Source step has no "
                    "runtime output."
                ),
            )

        # -------------------------------------------------
        # FIRST SEARCH RESULT
        # -------------------------------------------------

        if (
            reference.reference_type
            == ReferenceType
            .FIRST_SEARCH_RESULT
        ):
            return (
                self
                ._resolve_first_search_result(
                    reference=reference,
                    source_output=(
                        source_output
                    ),
                )
            )

        # -------------------------------------------------
        # PREVIOUS PAGE
        # -------------------------------------------------

        if (
            reference.reference_type
            == ReferenceType
            .PREVIOUS_PAGE
        ):
            return (
                self
                ._resolve_previous_page(
                    reference=reference,
                    source_output=(
                        source_output
                    ),
                )
            )

        # -------------------------------------------------
        # UNKNOWN REFERENCE TYPE
        # -------------------------------------------------

        return ReferenceResolution(
            reference=reference,
            resolved=False,
            value=None,
            reason=(
                "Unsupported reference type."
            ),
        )

    # =====================================================
    # FIRST SEARCH RESULT
    # =====================================================

    def _resolve_first_search_result(
        self,
        reference: TaskReference,
        source_output: StepRuntimeOutput,
    ) -> ReferenceResolution:
        if (
            source_output.output_type
            != RuntimeOutputType
            .SEARCH_RESULTS
        ):
            return ReferenceResolution(
                reference=reference,
                resolved=False,
                value=None,
                reason=(
                    "Source step did not "
                    "produce search results."
                ),
            )

        if not (
            source_output
            .search_results
        ):
            return ReferenceResolution(
                reference=reference,
                resolved=False,
                value=None,
                reason=(
                    "Search produced "
                    "no results."
                ),
            )

        first_result = (
            source_output
            .search_results[0]
        )

        if not (
            first_result.url
            .strip()
        ):
            return ReferenceResolution(
                reference=reference,
                resolved=False,
                value=None,
                reason=(
                    "First search result "
                    "has no URL."
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

    # =====================================================
    # PREVIOUS PAGE
    # =====================================================

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
                    "Source step did not "
                    "produce a page resource."
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
                    "Source step has "
                    "no usable page."
                ),
            )

        return ReferenceResolution(
            reference=reference,
            resolved=True,
            value=page,
            reason=(
                "Resolved from the "
                "previously opened page."
            ),
        )


task_reference_resolver = (
    TaskReferenceResolver()
)