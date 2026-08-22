import tempfile
import unittest
from pathlib import Path

import app.core.conversation as conversation_module

from app.core.conversation import (
    ConversationManager,
)


class ConversationRegressionTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temp_dir = (
            tempfile.TemporaryDirectory()
        )

        self.original_database_path = (
            conversation_module.DATABASE_PATH
        )

        conversation_module.DATABASE_PATH = (
            Path(self.temp_dir.name)
            / "conversation-test.db"
        )

        self.manager = (
            ConversationManager()
        )

    def tearDown(self) -> None:
        conversation_module.DATABASE_PATH = (
            self.original_database_path
        )

        self.temp_dir.cleanup()

    # ==================================================
    # CREATE ACTIVE CONVERSATION
    # ==================================================

    def test_create_active_conversation(
        self,
    ) -> None:
        conversation_id = (
            self.manager
            .get_or_create_active_conversation()
        )

        self.assertGreater(
            conversation_id,
            0,
        )

        self.assertEqual(
            self.manager
            .get_active_conversation_id(),
            conversation_id,
        )

    # ==================================================
    # REUSE ACTIVE CONVERSATION
    # ==================================================

    def test_active_conversation_is_reused(
        self,
    ) -> None:
        first_id = (
            self.manager
            .get_or_create_active_conversation()
        )

        second_id = (
            self.manager
            .get_or_create_active_conversation()
        )

        self.assertEqual(
            first_id,
            second_id,
        )

    # ==================================================
    # ADD / READ MESSAGES
    # ==================================================

    def test_add_and_read_messages(
        self,
    ) -> None:
        conversation_id = (
            self.manager
            .get_or_create_active_conversation()
        )

        user_id = (
            self.manager
            .add_message(
                conversation_id,
                "user",
                "Hello JARVIS",
            )
        )

        assistant_id = (
            self.manager
            .add_message(
                conversation_id,
                "assistant",
                "Hello.",
            )
        )

        self.assertGreater(
            user_id,
            0,
        )

        self.assertGreater(
            assistant_id,
            user_id,
        )

        messages = (
            self.manager
            .get_recent_messages(
                conversation_id,
                limit=10,
            )
        )

        self.assertEqual(
            len(messages),
            2,
        )

        self.assertEqual(
            messages[0]["role"],
            "user",
        )

        self.assertEqual(
            messages[0]["content"],
            "Hello JARVIS",
        )

        self.assertEqual(
            messages[1]["role"],
            "assistant",
        )

        self.assertEqual(
            messages[1]["content"],
            "Hello.",
        )

    # ==================================================
    # RECENT MESSAGE ORDER / LIMIT
    # ==================================================

    def test_recent_messages_respect_limit(
        self,
    ) -> None:
        conversation_id = (
            self.manager
            .get_or_create_active_conversation()
        )

        for index in range(5):
            self.manager.add_message(
                conversation_id,
                "user",
                f"Message {index}",
            )

        messages = (
            self.manager
            .get_recent_messages(
                conversation_id,
                limit=3,
            )
        )

        self.assertEqual(
            len(messages),
            3,
        )

        self.assertEqual(
            [
                message["content"]
                for message in messages
            ],
            [
                "Message 2",
                "Message 3",
                "Message 4",
            ],
        )

    # ==================================================
    # END CONVERSATION
    # ==================================================

    def test_end_conversation_removes_active_id(
        self,
    ) -> None:
        conversation_id = (
            self.manager
            .get_or_create_active_conversation()
        )

        self.assertGreater(
            conversation_id,
            0,
        )

        self.manager.end_active_conversation()

        self.assertIsNone(
            self.manager
            .get_active_conversation_id()
        )

    # ==================================================
    # NEW CONVERSATION AFTER END
    # ==================================================

    def test_new_conversation_after_end(
        self,
    ) -> None:
        first_id = (
            self.manager
            .get_or_create_active_conversation()
        )

        self.manager.end_active_conversation()

        second_id = (
            self.manager
            .get_or_create_active_conversation()
        )

        self.assertNotEqual(
            first_id,
            second_id,
        )

        self.assertGreater(
            second_id,
            first_id,
        )

    # ==================================================
    # EMPTY MESSAGES ARE REJECTED
    # ==================================================

    def test_empty_message_is_not_saved(
        self,
    ) -> None:
        conversation_id = (
            self.manager
            .get_or_create_active_conversation()
        )

        message_id = (
            self.manager
            .add_message(
                conversation_id,
                "user",
                "   ",
            )
        )

        self.assertEqual(
            message_id,
            0,
        )

        messages = (
            self.manager
            .get_recent_messages(
                conversation_id,
                limit=10,
            )
        )

        self.assertEqual(
            messages,
            [],
        )


if __name__ == "__main__":
    unittest.main()