import re

from dataclasses import (
    dataclass,
)

from enum import (
    Enum,
)

from app.core.task_planner import (
    TaskPlan,
)


# =========================================================
# REFERENCE TYPES
# =========================================================


class ReferenceType(
    str,
    Enum,
):
    FIRST_SEARCH_RESULT = (
        "first_search_result"
    )

    PREVIOUS_PAGE = (
        "previous_page"
    )


# =========================================================
# TASK REFERENCE
# =========================================================


@dataclass(
    frozen=True
)
class TaskReference:
    reference_type: ReferenceType
    raw_text: str
    source_step_index: int | None

    @property
    def is_resolved(
        self,
    ) -> bool:
        """
        This means the dependency source step is known.

        It does NOT mean the runtime value itself has
        already been produced.
        """

        return (
            self.source_step_index
            is not None
        )


# =========================================================
# CONTEXTUAL STEP
# =========================================================


@dataclass(
    frozen=True
)
class ContextualTaskStep:
    index: int
    command: str

    references: tuple[
        TaskReference,
        ...
    ]

    @property
    def has_references(
        self,
    ) -> bool:
        return bool(
            self.references
        )


# =========================================================
# CONTEXTUAL PLAN
# =========================================================


@dataclass(
    frozen=True
)
class ContextualTaskPlan:
    original_command: str

    steps: tuple[
        ContextualTaskStep,
        ...
    ]

    @property
    def has_contextual_references(
        self,
    ) -> bool:
        return any(
            step.has_references
            for step in self.steps
        )

    @property
    def unresolved_references(
        self,
    ) -> tuple[
        TaskReference,
        ...
    ]:
        return tuple(
            reference
            for step in self.steps
            for reference in step.references
            if not reference.is_resolved
        )


# =========================================================
# CONTEXT ANALYZER
# =========================================================


class TaskContextAnalyzer:
    # -----------------------------------------------------
    # "the first result"
    # "first search result"
    # "top result"
    # -----------------------------------------------------

    FIRST_RESULT_PATTERN = re.compile(
        (
            r"\b"
            r"(?:the\s+)?"
            r"(?:first|top)\s+"
            r"(?:search\s+)?"
            r"result"
            r"\b"
        ),
        flags=re.IGNORECASE,
    )

    # -----------------------------------------------------
    # "that page"
    # "this page"
    # "the page"
    # -----------------------------------------------------

    PAGE_REFERENCE_PATTERN = re.compile(
        (
            r"\b"
            r"(?:that|this|the)\s+"
            r"page"
            r"\b"
        ),
        flags=re.IGNORECASE,
    )

    SEARCH_PREFIXES = (
        "search ",
        "google ",
        "youtube search ",
    )

    DIRECT_PAGE_PREFIXES = (
        "open http://",
        "open https://",
    )

    # =====================================================
    # ANALYZE
    # =====================================================

    def analyze(
        self,
        plan: TaskPlan,
    ) -> ContextualTaskPlan:
        contextual_steps: list[
            ContextualTaskStep
        ] = []

        last_search_step: (
            int | None
        ) = None

        last_page_step: (
            int | None
        ) = None

        for step in plan.steps:
            references: list[
                TaskReference
            ] = []

            command = (
                step.command
                .strip()
            )

            normalized = (
                command
                .lower()
                .strip()
            )

            # =================================================
            # FIRST SEARCH RESULT REFERENCE
            # =================================================

            first_result_match = (
                self
                .FIRST_RESULT_PATTERN
                .search(
                    command
                )
            )

            if (
                first_result_match
                is not None
            ):
                references.append(
                    TaskReference(
                        reference_type=(
                            ReferenceType
                            .FIRST_SEARCH_RESULT
                        ),
                        raw_text=(
                            first_result_match
                            .group(0)
                        ),
                        source_step_index=(
                            last_search_step
                        ),
                    )
                )

            # =================================================
            # PREVIOUS PAGE REFERENCE
            # =================================================

            page_match = (
                self
                .PAGE_REFERENCE_PATTERN
                .search(
                    command
                )
            )

            if (
                page_match
                is not None
            ):
                references.append(
                    TaskReference(
                        reference_type=(
                            ReferenceType
                            .PREVIOUS_PAGE
                        ),
                        raw_text=(
                            page_match
                            .group(0)
                        ),
                        source_step_index=(
                            last_page_step
                        ),
                    )
                )

            contextual_steps.append(
                ContextualTaskStep(
                    index=step.index,
                    command=command,
                    references=tuple(
                        references
                    ),
                )
            )

            # =================================================
            # UPDATE SEARCH CONTEXT
            # =================================================

            if normalized.startswith(
                self.SEARCH_PREFIXES
            ):
                last_search_step = (
                    step.index
                )

            # =================================================
            # UPDATE PAGE CONTEXT
            # =================================================
            #
            # Do NOT treat any random mention of
            # "first result" as a page.
            #
            # It becomes a page source only when the command
            # actually opens that result.
            # =================================================

            opens_first_result = (
                normalized.startswith(
                    "open "
                )
                and first_result_match
                is not None
            )

            opens_direct_url = (
                normalized.startswith(
                    self.DIRECT_PAGE_PREFIXES
                )
            )

            if (
                opens_first_result
                or opens_direct_url
            ):
                last_page_step = (
                    step.index
                )

        return ContextualTaskPlan(
            original_command=(
                plan.original_command
            ),
            steps=tuple(
                contextual_steps
            ),
        )


task_context_analyzer = (
    TaskContextAnalyzer()
)