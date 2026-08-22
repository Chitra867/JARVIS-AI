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
    # DIRECT RESPONSE BEHAVIOR
    # ==================================================

    def test_prompt_requires_direct_user_response(
        self,
    ) -> None:
        prompt = (
            self.skill
            ._build_prompt(
                command="Why?",
                memory_context=(
                    "- No relevant long-term memory."
                ),
                conversation_context=(
                    "USER: Compare React and Vue.\n"
                    "ASSISTANT: I would choose Vue."
                ),
            )
        )

        self.assertIn(
            "never describe the user's intent",
            prompt.lower(),
        )

        self.assertIn(
            "answer as jarvis directly",
            prompt.lower(),
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
    # PROMPT CONTEXT
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
    # SHORT FOLLOW-UP DETECTION
    # ==================================================

    def test_short_follow_up_detection(
        self,
    ) -> None:
        self.assertTrue(
            self.skill
            ._is_short_follow_up(
                "Why?"
            )
        )

        self.assertTrue(
            self.skill
            ._is_short_follow_up(
                "Which one?"
            )
        )

        self.assertTrue(
            self.skill
            ._is_short_follow_up(
                "Give me an example"
            )
        )

        self.assertFalse(
            self.skill
            ._is_short_follow_up(
                (
                    "Explain the differences between "
                    "React and Vue in detail"
                )
            )
        )

    # ==================================================
    # SHORT FOLLOW-UP PROMPT RULES
    # ==================================================

    def test_prompt_contains_follow_up_rules(
        self,
    ) -> None:
        prompt = (
            self.skill
            ._build_prompt(
                command="Why?",
                memory_context=(
                    "- No relevant long-term memory."
                ),
                conversation_context=(
                    "USER: Compare React and Vue.\n"
                    "ASSISTANT: I would choose Vue."
                ),
            )
        )

        self.assertIn(
            "short follow-up",
            prompt.lower(),
        )

        self.assertIn(
            (
                "previous assistant response "
                "made a recommendation"
            ),
            prompt.lower(),
        )

        self.assertIn(
            "Why?",
            prompt,
        )

        self.assertIn(
            "I would choose Vue.",
            prompt,
        )

    # ==================================================
    # RESPONSE CLEANUP
    # ==================================================

    def test_meta_narration_is_removed(
        self,
    ) -> None:
        answer = (
            "You're asking why I chose Vue. "
            "I chose Vue because it is simpler "
            "for this dashboard."
        )

        cleaned = (
            self.skill
            ._clean_response(
                answer
            )
        )

        self.assertEqual(
            cleaned,
            (
                "I chose Vue because it is simpler "
                "for this dashboard."
            ),
        )

    def test_third_person_meta_narration_is_removed(
        self,
    ) -> None:
        answer = (
            "The user is asking why Vue was chosen. "
            "Vue was chosen because it provides "
            "a simpler development experience."
        )

        cleaned = (
            self.skill
            ._clean_response(
                answer
            )
        )

        self.assertEqual(
            cleaned,
            (
                "Vue was chosen because it provides "
                "a simpler development experience."
            ),
        )

    def test_normal_answer_is_preserved(
        self,
    ) -> None:
        answer = (
            "I chose Vue because it is simpler "
            "for this dashboard."
        )

        cleaned = (
            self.skill
            ._clean_response(
                answer
            )
        )

        self.assertEqual(
            cleaned,
            answer,
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

        mock_post.assert_called_once()

    # ==================================================
    # RESPONSE CLEANUP THROUGH GENERATOR
    # ==================================================

    @patch(
        "app.skills.ai_skill.httpx.post"
    )
    def test_generate_response_cleans_meta_narration(
        self,
        mock_post,
    ) -> None:
        response = MagicMock()

        response.raise_for_status.return_value = None

        response.json.return_value = {
            "response": (
                "You're asking why I chose Vue. "
                "I chose Vue because it is simpler."
            )
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
            "I chose Vue because it is simpler.",
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