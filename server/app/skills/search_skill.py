import urllib.parse
import webbrowser

from app.skills.base import Skill


class SearchSkill(Skill):
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

    def execute(
        self,
        command: str,
    ) -> str:
        original = (
            command
            .strip()
        )

        lowered = (
            original
            .lower()
        )

        if lowered.startswith(
            "search google for "
        ):
            query = original[
                len("search google for "):
            ].strip()

            return self._google(
                query
            )

        if lowered.startswith(
            "google "
        ):
            query = original[
                len("google "):
            ].strip()

            return self._google(
                query
            )

        if lowered.startswith(
            "search youtube for "
        ):
            query = original[
                len("search youtube for "):
            ].strip()

            return self._youtube(
                query
            )

        if lowered.startswith(
            "youtube search "
        ):
            query = original[
                len("youtube search "):
            ].strip()

            return self._youtube(
                query
            )

        if lowered.startswith(
            "search the web for "
        ):
            query = original[
                len("search the web for "):
            ].strip()

            return self._google(
                query
            )

        if lowered.startswith(
            "search web for "
        ):
            query = original[
                len("search web for "):
            ].strip()

            return self._google(
                query
            )

        if lowered.startswith(
            "search for "
        ):
            query = original[
                len("search for "):
            ].strip()

            return self._google(
                query
            )

        if lowered.startswith(
            "search "
        ):
            query = original[
                len("search "):
            ].strip()

            return self._google(
                query
            )

        return (
            "Tell me what you want "
            "me to search for."
        )

    def _google(
        self,
        query: str,
    ) -> str:
        query = (
            query
            .strip()
        )

        if not query:
            return (
                "Tell me what you want "
                "me to search for."
            )

        encoded = (
            urllib.parse.quote_plus(
                query
            )
        )

        url = (
            "https://www.google.com/search"
            f"?q={encoded}"
        )

        opened = (
            webbrowser.open(
                url
            )
        )

        if not opened:
            return (
                "I couldn't open "
                "the Google search."
            )

        return (
            f"Searching Google for {query}."
        )

    def _youtube(
        self,
        query: str,
    ) -> str:
        query = (
            query
            .strip()
        )

        if not query:
            return (
                "Tell me what you want me "
                "to search for on YouTube."
            )

        encoded = (
            urllib.parse.quote_plus(
                query
            )
        )

        url = (
            "https://www.youtube.com/results"
            f"?search_query={encoded}"
        )

        opened = (
            webbrowser.open(
                url
            )
        )

        if not opened:
            return (
                "I couldn't open "
                "the YouTube search."
            )

        return (
            f"Searching YouTube for {query}."
        )