import urllib.parse
import webbrowser

from app.skills.base import Skill


class SearchSkill(Skill):
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

        for prefix, provider in patterns:
            if lowered.startswith(
                prefix
            ):
                query = (
                    original[
                        len(prefix):
                    ]
                    .strip()
                    .rstrip(".!?")
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
    # GOOGLE
    # ==================================================

    def _google(
        self,
        query: str,
    ) -> str:
        query = (
            query
            .strip()
            .rstrip(".!?")
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
            "https://www.google.com/search"
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
            f"Searching Google for "
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
            .rstrip(".!?")
            .strip()
        )

        if not query:
            return (
                "Tell me what you want "
                "me to search for on YouTube."
            )

        encoded = (
            urllib.parse
            .quote_plus(
                query
            )
        )

        url = (
            "https://www.youtube.com/results"
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
            f"Searching YouTube for "
            f"{query}."
        )