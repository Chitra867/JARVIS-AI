import unittest
from unittest.mock import (
    MagicMock,
    patch,
)

import httpx

from app.skills.ai_skill import AISkill


class AISkillRegressionTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.skill = AISkill()

    # ==================================================
    # ROUTING
    # ==================================================

    def test_non_empty_command_is_supported(
        self,
    ) -> None:
        self.assertTrue(
            self.skill.can_handle(
                "explain decorators"
            )
        )

        self.assertFalse(
            self.skill.can_handle(
                "   "
            )
        )

    # ==================================================
    # MEMORY CONTEXT
    # ==================================================

    @patch(
        "app.skills.ai_skill.memory_manager"
    )
    def test_memory_context_uses_relevant_memories(
        self,
        mock_memory_manager,
    ) -> None:
        mock_memory_manager.search.return_value = [
            "The user prefers Tauri for JARVIS."
        ]

        context = (
            self.skill
            ._get_memory_context(
                "What desktop framework do I prefer?"
            )
        )

        self.assertIn(
            "Tauri",
            context,
        )

        mock_memory_manager.search.assert_called_once_with(
            "What desktop framework do I prefer?",
            limit=6,
        )

    # ==================================================
    # EMPTY MEMORY CONTEXT
    # ==================================================

    @patch(
        "app.skills.ai_skill.memory_manager"
    )
    def test_empty_memory_context_is_handled(
        self,
        mock_memory_manager,
    ) -> None:
        mock_memory_manager.search.return_value = []

        context = (
            self.skill
            ._get_memory_context(
                "Explain decorators"
            )
        )

        self.assertEqual(
            context,
            "- No relevant long-term memory.",
        )

    # ==================================================
    # CONVERSATION CONTEXT
    # ==================================================

    @patch(
        "app.skills.ai_skill.conversation_manager"
    )
    def test_current_user_message_is_not_duplicated(
        self,
        mock_conversation_manager,
    ) -> None:
        (
            mock_conversation_manager
            .get_active_conversation_id
            .return_value
        ) = 1

        (
            mock_conversation_manager
            .get_recent_messages
            .return_value
        ) = [
            {
                "role": "user",
                "content": "Explain Python",
                "created_at": "test",
            },
            {
                "role": "assistant",
                "content": "Python is a language.",
                "created_at": "test",
            },
            {
                "role": "user",
                "content": "Give me an example",
                "created_at": "test",
            },
        ]

        context = (
            self.skill
            ._get_conversation_context(
                "Give me an example"
            )
        )

        self.assertIn(
            "USER: Explain Python",
            context,
        )

        self.assertIn(
            "ASSISTANT: Python is a language.",
            context,
        )

        self.assertNotIn(
            "USER: Give me an example",
            context,
        )

    # ==================================================
    # NO ACTIVE CONVERSATION
    # ==================================================

    @patch(
        "app.skills.ai_skill.conversation_manager"
    )
    def test_no_active_conversation_is_handled(
        self,
        mock_conversation_manager,
    ) -> None:
        (
            mock_conversation_manager
            .get_active_conversation_id
            .return_value
        ) = None

        context = (
            self.skill
            ._get_conversation_context(
                "Explain Python"
            )
        )

        self.assertEqual(
            context,
            "- No previous conversation context.",
        )

    # ==================================================
    # PROMPT
    # ==================================================

    def test_prompt_contains_all_context(
        self,
    ) -> None:
        prompt = (
            self.skill
            ._build_prompt(
                command=(
                    "What framework do I prefer?"
                ),
                memory_context=(
                    "- The user prefers Tauri."
                ),
                conversation_context=(
                    "USER: We were discussing JARVIS."
                ),
            )
        )

        self.assertIn(
            "The user prefers Tauri.",
            prompt,
        )

        self.assertIn(
            "We were discussing JARVIS.",
            prompt,
        )

        self.assertIn(
            "What framework do I prefer?",
            prompt,
        )

    # ==================================================
    # SUCCESSFUL OLLAMA RESPONSE
    # ==================================================

    @patch(
        "app.skills.ai_skill.httpx.post"
    )
    def test_generate_response_success(
        self,
        mock_post,
    ) -> None:
        response = MagicMock()

        response.raise_for_status.return_value = None

        response.json.return_value = {
            "response":
                "Tauri is your preferred framework."
        }

        mock_post.return_value = response

        result = (
            self.skill
            ._generate_response(
                "test prompt"
            )
        )

        self.assertEqual(
            result,
            "Tauri is your preferred framework.",
        )

    # ==================================================
    # EMPTY AI RESPONSE
    # ==================================================

    @patch(
        "app.skills.ai_skill.httpx.post"
    )
    def test_empty_response_is_handled(
        self,
        mock_post,
    ) -> None:
        response = MagicMock()

        response.raise_for_status.return_value = None

        response.json.return_value = {
            "response": ""
        }

        mock_post.return_value = response

        result = (
            self.skill
            ._generate_response(
                "test prompt"
            )
        )

        self.assertEqual(
            result,
            "I couldn't generate a response.",
        )

    # ==================================================
    # CONNECTION FAILURE
    # ==================================================

    @patch(
        "app.skills.ai_skill.httpx.post"
    )
    def test_connection_failure_is_handled(
        self,
        mock_post,
    ) -> None:
        mock_post.side_effect = (
            httpx.ConnectError(
                "connection failed"
            )
        )

        result = (
            self.skill
            ._generate_response(
                "test prompt"
            )
        )

        self.assertEqual(
            result,
            (
                "I can't connect to "
                "the local AI engine."
            ),
        )

    # ==================================================
    # GENERIC HTTP FAILURE
    # ==================================================

    @patch(
        "app.skills.ai_skill.httpx.post"
    )
    def test_http_failure_is_handled(
        self,
        mock_post,
    ) -> None:
        mock_post.side_effect = (
            httpx.HTTPError(
                "request failed"
            )
        )

        result = (
            self.skill
            ._generate_response(
                "test prompt"
            )
        )

        self.assertEqual(
            result,
            (
                "The local AI engine "
                "returned an error."
            ),
        )


if __name__ == "__main__":
    unittest.main()