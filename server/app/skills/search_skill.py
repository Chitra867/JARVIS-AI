import urllib.parse
import webbrowser

from app.core.search_provider import (
    SearchProviderError,
    search_provider_registry,
)

from app.core.task_runtime import (
    RuntimeOutputType,
    StepRuntimeOutput,
)

from app.skills.base import (
    Skill,
)


class SearchSkill(
    Skill
):
    STRUCTURED_PROVIDER = (
        "ddgs"
    )

    STRUCTURED_RESULT_LIMIT = 5

    # ==================================================
    # ROUTING
    # ==================================================

    def can_handle(
        self,
        command: str,
    ) -> bool:
        normalized = (
            command
            .strip()
            .lower()
        )

        return (
            normalized.startswith(
                "search google for "
            )
            or normalized.startswith(
                "google "
            )
            or normalized.startswith(
                "search youtube for "
            )
            or normalized.startswith(
                "youtube search "
            )
            or normalized.startswith(
                "search the web for "
            )
            or normalized.startswith(
                "search web for "
            )
            or normalized.startswith(
                "search for "
            )
            or normalized.startswith(
                "search "
            )
        )

    # ==================================================
    # EXECUTE
    # ==================================================

    def execute(
        self,
        command: str,
    ) -> str:
        provider, query = (
            self.parse_search(
                command
            )
        )

        if not query:
            return (
                "Tell me what you want "
                "me to search for."
            )

        if provider == "youtube":
            return self._youtube(
                query
            )

        return self._google(
            query
        )

    # ==================================================
    # STRUCTURED RUNTIME OUTPUT
    # ==================================================
    #
    # TaskExecutor calls this after a successful search.
    #
    # Normal SearchSkill execution still behaves exactly
    # as before and opens the user's browser.
    #
    # The structured result is additional machine-readable
    # context used by later task steps.
    # ==================================================

    def build_runtime_output(
        self,
        step_index: int,
        command: str,
        response: str,
    ) -> StepRuntimeOutput:
        provider, query = (
            self.parse_search(
                command
            )
        )

        # YouTube structured results are not implemented
        # yet. Preserve the normal textual output.
        if (
            provider == "youtube"
            or not query
        ):
            return StepRuntimeOutput(
                step_index=step_index,
                output_type=(
                    RuntimeOutputType.TEXT
                ),
                text=response,
            )

        try:
            results = (
                search_provider_registry
                .search(
                    self.STRUCTURED_PROVIDER,
                    query,
                    limit=(
                        self
                        .STRUCTURED_RESULT_LIMIT
                    ),
                )
            )

        except SearchProviderError as error:
            # Browser search has already succeeded.
            # Structured-search failure should not break
            # ordinary single-step search behavior.
            print(
                (
                    "Structured search "
                    f"unavailable: {error}"
                )
            )

            return StepRuntimeOutput(
                step_index=step_index,
                output_type=(
                    RuntimeOutputType.TEXT
                ),
                text=response,
            )

        if not results:
            return StepRuntimeOutput(
                step_index=step_index,
                output_type=(
                    RuntimeOutputType.TEXT
                ),
                text=response,
            )

        return StepRuntimeOutput(
            step_index=step_index,
            output_type=(
                RuntimeOutputType
                .SEARCH_RESULTS
            ),
            text=response,
            search_results=results,
        )

    # ==================================================
    # PARSE SEARCH
    # ==================================================

    def parse_search(
        self,
        command: str,
    ) -> tuple[
        str,
        str,
    ]:
        original = (
            command
            .strip()
        )

        lowered = (
            original
            .lower()
        )

        patterns = (
            (
                "search youtube for ",
                "youtube",
            ),
            (
                "youtube search ",
                "youtube",
            ),
            (
                "search google for ",
                "google",
            ),
            (
                "search the web for ",
                "google",
            ),
            (
                "search web for ",
                "google",
            ),
            (
                "search for ",
                "google",
            ),
            (
                "google ",
                "google",
            ),
            (
                "search ",
                "google",
            ),
        )

        for prefix, provider in (
            patterns
        ):
            if lowered.startswith(
                prefix
            ):
                query = (
                    original[
                        len(prefix):
                    ]
                    .strip()
                    .rstrip(
                        ".!?"
                    )
                    .strip()
                )

                return (
                    provider,
                    query,
                )

        return (
            "google",
            "",
        )

    # ==================================================
    # GOOGLE BROWSER SEARCH
    # ==================================================

    def _google(
        self,
        query: str,
    ) -> str:
        query = (
            query
            .strip()
            .rstrip(
                ".!?"
            )
            .strip()
        )

        if not query:
            return (
                "Tell me what you want "
                "me to search for."
            )

        encoded = (
            urllib.parse
            .quote_plus(
                query
            )
        )

        url = (
            "https://www.google.com/"
            "search"
            f"?q={encoded}"
        )

        opened = (
            webbrowser
            .open(
                url
            )
        )

        if not opened:
            return (
                "I couldn't open "
                "the Google search."
            )

        return (
            "Searching Google for "
            f"{query}."
        )

    # ==================================================
    # YOUTUBE
    # ==================================================

    def _youtube(
        self,
        query: str,
    ) -> str:
        query = (
            query
            .strip()
            .rstrip(
                ".!?"
            )
            .strip()
        )

        if not query:
            return (
                "Tell me what you want "
                "me to search for "
                "on YouTube."
            )

        encoded = (
            urllib.parse
            .quote_plus(
                query
            )
        )

        url = (
            "https://www.youtube.com/"
            "results"
            f"?search_query={encoded}"
        )

        opened = (
            webbrowser
            .open(
                url
            )
        )

        if not opened:
            return (
                "I couldn't open "
                "the YouTube search."
            )

        return (
            "Searching YouTube for "
            f"{query}."
        )