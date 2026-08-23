import re

from app.core.conversation import (
    conversation_manager,
)

from app.core.page_reader import (
    PageReadError,
    page_reader,
)

from app.core.task_context import (
    ReferenceType,
)

from app.core.task_runtime import (
    PageResource,
    ReferenceResolution,
    RuntimeOutputType,
    StepRuntimeOutput,
    page_context_store,
)

from app.skills.ai_skill import (
    AISkill,
)

from app.skills.base import (
    Skill,
)


class PageSummarySkill(
    Skill
):
    SUMMARY_PATTERN = re.compile(
        (
            r"^"
            r"(?:summarize|summarise)"
            r"\s+"
            r"(?:that|this|the)"
            r"\s+page"
            r"\s*[.!?]*"
            r"$"
        ),
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
    ) -> None:
        self._ai = (
            AISkill()
        )

    # ==================================================
    # ROUTING
    # ==================================================

    def can_handle(
        self,
        command: str,
    ) -> bool:
        return bool(
            self.SUMMARY_PATTERN
            .match(
                command.strip()
            )
        )

    # ==================================================
    # NORMAL EXECUTION
    # ==================================================

    def execute(
        self,
        command: str,
    ) -> str:
        del command

        return (
            "Unable to determine which "
            "webpage to summarize."
        )

    # ==================================================
    # CONTEXTUAL EXECUTION
    # ==================================================

    def execute_with_references(
        self,
        step_index: int,
        command: str,
        resolutions: tuple[
            ReferenceResolution,
            ...
        ],
    ) -> tuple[
        str,
        StepRuntimeOutput | None,
    ]:
        del command

        page: (
            PageResource | None
        ) = None

        # --------------------------------------------------
        # RESOLVE PAGE
        # --------------------------------------------------

        for resolution in (
            resolutions
        ):
            if not (
                resolution.resolved
            ):
                continue

            if (
                resolution
                .reference
                .reference_type
                != ReferenceType
                .PREVIOUS_PAGE
            ):
                continue

            if isinstance(
                resolution.value,
                PageResource,
            ):
                page = (
                    resolution.value
                )

                break

        if page is None:
            return (
                (
                    "Unable to determine "
                    "which webpage to summarize."
                ),
                None,
            )

        # --------------------------------------------------
        # READ PAGE CONTENT
        # --------------------------------------------------

        readable_page = (
            page
        )

        if not (
            readable_page.content
            and readable_page
            .content
            .strip()
        ):
            try:
                readable_page = (
                    page_reader.read(
                        page.url
                    )
                )

            except PageReadError as error:
                print(
                    (
                        "Page reading failed: "
                        f"{error}"
                    )
                )

                return (
                    (
                        "I couldn't read enough "
                        "content from that page "
                        "to summarize it."
                    ),
                    None,
                )

        content = (
            readable_page.content
            or ""
        ).strip()

        if not content:
            return (
                (
                    "I couldn't find readable "
                    "content on that page."
                ),
                None,
            )

        # --------------------------------------------------
        # IMPORTANT:
        # Replace URL-only cached page with the fully
        # downloaded readable page.
        # --------------------------------------------------

        conversation_id = (
            conversation_manager
            .get_active_conversation_id()
        )

        page_context_store.record(
            page=(
                readable_page
            ),
            conversation_id=(
                conversation_id
            ),
        )

        # --------------------------------------------------
        # SUMMARIZE
        # --------------------------------------------------

        summary = (
            self._ai
            .summarize_page(
                title=(
                    readable_page.title
                ),
                url=(
                    readable_page.url
                ),
                content=(
                    content
                ),
            )
            .strip()
        )

        if not summary:
            return (
                (
                    "I couldn't generate "
                    "a summary of that page."
                ),
                None,
            )

        runtime_output = (
            StepRuntimeOutput(
                step_index=(
                    step_index
                ),
                output_type=(
                    RuntimeOutputType.TEXT
                ),
                text=(
                    summary
                ),
            )
        )

        return (
            summary,
            runtime_output,
        )