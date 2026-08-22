import unittest
from unittest.mock import patch

from app.skills.search_skill import (
    SearchSkill,
)


class SearchSkillRegressionTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.skill = SearchSkill()

    # ==================================================
    # GOOGLE PARSING
    # ==================================================

    def test_google_search_is_parsed(
        self,
    ) -> None:
        provider, query = (
            self.skill
            .parse_search(
                "search google for FastAPI"
            )
        )

        self.assertEqual(
            provider,
            "google",
        )

        self.assertEqual(
            query,
            "FastAPI",
        )

    # ==================================================
    # GENERIC SEARCH
    # ==================================================

    def test_generic_search_defaults_to_google(
        self,
    ) -> None:
        provider, query = (
            self.skill
            .parse_search(
                "search for Python decorators"
            )
        )

        self.assertEqual(
            provider,
            "google",
        )

        self.assertEqual(
            query,
            "Python decorators",
        )

    # ==================================================
    # YOUTUBE PARSING
    # ==================================================

    def test_youtube_search_is_parsed(
        self,
    ) -> None:
        provider, query = (
            self.skill
            .parse_search(
                (
                    "search youtube for "
                    "FastAPI tutorial"
                )
            )
        )

        self.assertEqual(
            provider,
            "youtube",
        )

        self.assertEqual(
            query,
            "FastAPI tutorial",
        )

    # ==================================================
    # TRAILING PUNCTUATION
    # ==================================================

    def test_query_punctuation_is_removed(
        self,
    ) -> None:
        provider, query = (
            self.skill
            .parse_search(
                "search for FastAPI."
            )
        )

        self.assertEqual(
            provider,
            "google",
        )

        self.assertEqual(
            query,
            "FastAPI",
        )

    # ==================================================
    # GOOGLE EXECUTION
    # ==================================================

    @patch(
        "app.skills.search_skill.webbrowser.open"
    )
    def test_google_execution_opens_google(
        self,
        mock_open,
    ) -> None:
        mock_open.return_value = True

        result = (
            self.skill
            .execute(
                "search google for FastAPI"
            )
        )

        mock_open.assert_called_once()

        opened_url = (
            mock_open
            .call_args
            .args[0]
        )

        self.assertIn(
            "google.com/search",
            opened_url,
        )

        self.assertIn(
            "q=FastAPI",
            opened_url,
        )

        self.assertEqual(
            result,
            "Searching Google for FastAPI.",
        )

    # ==================================================
    # YOUTUBE EXECUTION
    # ==================================================

    @patch(
        "app.skills.search_skill.webbrowser.open"
    )
    def test_youtube_execution_opens_youtube(
        self,
        mock_open,
    ) -> None:
        mock_open.return_value = True

        result = (
            self.skill
            .execute(
                (
                    "search youtube for "
                    "FastAPI tutorial"
                )
            )
        )

        mock_open.assert_called_once()

        opened_url = (
            mock_open
            .call_args
            .args[0]
        )

        self.assertIn(
            "youtube.com/results",
            opened_url,
        )

        self.assertIn(
            "search_query=FastAPI+tutorial",
            opened_url,
        )

        self.assertEqual(
            result,
            (
                "Searching YouTube for "
                "FastAPI tutorial."
            ),
        )


if __name__ == "__main__":
    unittest.main()