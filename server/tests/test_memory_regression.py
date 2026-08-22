import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app.core.memory as memory_module

from app.core.memory import MemoryManager
from app.core.memory_extractor import MemoryExtractor
from app.skills.memory_control_skill import (
    MemoryControlSkill,
)


class MemoryRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()

        self.original_database_path = (
            memory_module.DATABASE_PATH
        )

        memory_module.DATABASE_PATH = (
            Path(self.temp_dir.name)
            / "jarvis-test.db"
        )

        self.memory = MemoryManager()

    def tearDown(self) -> None:
        memory_module.DATABASE_PATH = (
            self.original_database_path
        )

        self.temp_dir.cleanup()

    # ==================================================
    # BASIC SAVE / SEARCH
    # ==================================================

    def test_save_and_search_record(
        self,
    ) -> None:
        memory_id = self.memory.save_memory(
            memory_type="preference",
            content=(
                "The user prefers Tauri "
                "for the JARVIS desktop interface."
            ),
            memory_key="jarvis.desktop_interface",
            importance=1.0,
            confidence=1.0,
        )

        self.assertIsNotNone(
            memory_id
        )

        results = self.memory.search_records(
            "JARVIS desktop",
            limit=10,
        )

        self.assertEqual(
            len(results),
            1,
        )

        self.assertEqual(
            results[0]["memory_key"],
            "jarvis.desktop_interface",
        )

    # ==================================================
    # SAME KEY SUPERSEDING
    # ==================================================

    def test_same_key_supersedes_old_memory(
        self,
    ) -> None:
        old_id = self.memory.save_memory(
            memory_type="preference",
            content=(
                "JARVIS desktop interface uses React."
            ),
            memory_key="jarvis.desktop_interface",
        )

        new_id = self.memory.save_memory(
            memory_type="preference",
            content=(
                "JARVIS desktop interface uses Tauri."
            ),
            memory_key="jarvis.desktop_interface",
        )

        self.assertIsNotNone(
            old_id
        )

        self.assertIsNotNone(
            new_id
        )

        records = (
            self.memory
            .get_all_memories(
                include_inactive=True,
                limit=20,
            )
        )

        by_id = {
            int(record["id"]): record
            for record in records
        }

        self.assertEqual(
            by_id[int(old_id)]["status"],
            "superseded",
        )

        self.assertEqual(
            by_id[int(old_id)]["superseded_by"],
            int(new_id),
        )

        self.assertEqual(
            by_id[int(new_id)]["status"],
            "active",
        )

    # ==================================================
    # STABLE KEY PROTECTION
    # ==================================================

    def test_existing_stable_key_is_not_overwritten(
        self,
    ) -> None:
        content = (
            "UNIQUE stable key regression test."
        )

        first_id = self.memory.save_memory(
            memory_type="preference",
            content=content,
            memory_key="test.stable.correct",
        )

        second_id = self.memory.save_memory(
            memory_type="preference",
            content=content,
            memory_key="test.stable.wrong",
        )

        self.assertEqual(
            first_id,
            second_id,
        )

        correct = (
            self.memory
            .get_active_memory_by_key(
                "test.stable.correct"
            )
        )

        wrong = (
            self.memory
            .get_active_memory_by_key(
                "test.stable.wrong"
            )
        )

        self.assertIsNotNone(
            correct
        )

        self.assertIsNone(
            wrong
        )

    # ==================================================
    # FORGET BY KEY
    # ==================================================

    def test_forget_by_key(
        self,
    ) -> None:
        self.memory.save_memory(
            memory_type="fact",
            content=(
                "Temporary regression memory."
            ),
            memory_key="test.forget",
        )

        count = (
            self.memory
            .forget_by_key(
                "test.forget"
            )
        )

        self.assertEqual(
            count,
            1,
        )

        active = (
            self.memory
            .get_active_memory_by_key(
                "test.forget"
            )
        )

        self.assertIsNone(
            active
        )

    # ==================================================
    # EXACT FORGET MUST NOT DELETE WEAK MATCH
    # ==================================================

    def test_forget_that_requires_exact_match(
        self,
    ) -> None:
        self.memory.save_memory(
            memory_type="preference",
            content=(
                "The user prefers Tauri "
                "for the JARVIS desktop interface."
            ),
            memory_key="jarvis.desktop_interface",
        )

        skill = MemoryControlSkill()

        with patch(
            "app.skills.memory_control_skill.memory_manager",
            self.memory,
        ):
            response = skill.execute(
                "forget that TEMP JARVIS "
                "memory that does not exist"
            )

        self.assertIn(
            "couldn't find an exact active memory",
            response.lower(),
        )

        real_memory = (
            self.memory
            .get_active_memory_by_key(
                "jarvis.desktop_interface"
            )
        )

        self.assertIsNotNone(
            real_memory
        )

    # ==================================================
    # EXACT FORGET WORKS
    # ==================================================

    def test_forget_that_exact_match_works(
        self,
    ) -> None:
        content = (
            "TEMP FINAL MEMORY TEST 991177"
        )

        self.memory.save_memory(
            memory_type="fact",
            content=content,
            memory_key="test.final.memory",
        )

        skill = MemoryControlSkill()

        with patch(
            "app.skills.memory_control_skill.memory_manager",
            self.memory,
        ):
            response = skill.execute(
                f"forget that {content}"
            )

        self.assertEqual(
            response,
            f"I've forgotten: {content}",
        )

        active = (
            self.memory
            .get_active_memory_by_key(
                "test.final.memory"
            )
        )

        self.assertIsNone(
            active
        )


class MemoryExtractorSafetyTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.extractor = MemoryExtractor()

    def tearDown(self) -> None:
        self.extractor.executor.shutdown(
            wait=True,
            cancel_futures=True,
        )

    # ==================================================
    # COMPARISON REQUEST FILTERING
    # ==================================================

    def test_compare_request_is_skipped(
        self,
    ) -> None:
        result = (
            self.extractor
            ._should_skip_extraction(
                "Compare React and Vue "
                "for building a dashboard."
            )
        )

        self.assertTrue(
            result
        )

    # ==================================================
    # ONE-TIME REQUEST FILTERING
    # ==================================================

    def test_one_time_coding_request_is_skipped(
        self,
    ) -> None:
        result = (
            self.extractor
            ._should_skip_extraction(
                "write a python function "
                "that adds two numbers"
            )
        )

        self.assertTrue(
            result
        )

    def test_search_request_is_skipped(
        self,
    ) -> None:
        result = (
            self.extractor
            ._should_skip_extraction(
                "search python decorators"
            )
        )

        self.assertTrue(
            result
        )

    # ==================================================
    # SINGLE-WORD FOLLOW-UP QUESTIONS
    # ==================================================

    def test_single_word_why_is_skipped(
        self,
    ) -> None:
        result = (
            self.extractor
            ._should_skip_extraction(
                "Why?"
            )
        )

        self.assertTrue(
            result
        )

    def test_single_word_how_is_skipped(
        self,
    ) -> None:
        result = (
            self.extractor
            ._should_skip_extraction(
                "How?"
            )
        )

        self.assertTrue(
            result
        )

    # ==================================================
    # DURABLE PREFERENCE SHOULD BE EXTRACTED
    # ==================================================

    def test_durable_preference_is_not_skipped(
        self,
    ) -> None:
        result = (
            self.extractor
            ._should_skip_extraction(
                "I prefer Tauri for the "
                "JARVIS desktop interface."
            )
        )

        self.assertFalse(
            result
        )

    # ==================================================
    # FORGET COMMANDS NEVER ENTER EXTRACTOR
    # ==================================================

    def test_forget_command_is_skipped(
        self,
    ) -> None:
        result = (
            self.extractor
            ._should_skip_extraction(
                "forget that TEMP memory"
            )
        )

        self.assertTrue(
            result
        )

    # ==================================================
    # MEMORY INSPECTION NEVER ENTERS EXTRACTOR
    # ==================================================

    def test_memory_query_is_skipped(
        self,
    ) -> None:
        result = (
            self.extractor
            ._should_skip_extraction(
                "show active memories"
            )
        )

        self.assertTrue(
            result
        )

    # ==================================================
    # CONTENT GROUNDING
    # ==================================================

    def test_ungrounded_content_is_rejected(
        self,
    ) -> None:
        result = (
            self.extractor
            ._content_is_grounded(
                content="Tauri",
                user_message=(
                    "forget that TEMP JARVIS "
                    "memory test"
                ),
            )
        )

        self.assertFalse(
            result
        )

    def test_grounded_content_is_allowed(
        self,
    ) -> None:
        result = (
            self.extractor
            ._content_is_grounded(
                content=(
                    "The user prefers Tauri "
                    "for the JARVIS desktop interface."
                ),
                user_message=(
                    "I prefer Tauri for the "
                    "JARVIS desktop interface."
                ),
            )
        )

        self.assertTrue(
            result
        )

    # ==================================================
    # MEMORY KEY GROUNDING
    # ==================================================

    def test_unrelated_memory_key_is_rejected(
        self,
    ) -> None:
        result = (
            self.extractor
            ._memory_key_is_grounded(
                memory_key=(
                    "ai.preferred_language"
                ),
                user_message=(
                    "I prefer Tauri for the "
                    "JARVIS desktop interface."
                ),
                content=(
                    "The user prefers Tauri "
                    "for the JARVIS desktop interface."
                ),
                candidates=[],
            )
        )

        self.assertFalse(
            result
        )

    def test_correct_memory_key_is_allowed(
        self,
    ) -> None:
        result = (
            self.extractor
            ._memory_key_is_grounded(
                memory_key=(
                    "jarvis.desktop_interface"
                ),
                user_message=(
                    "I prefer Tauri for the "
                    "JARVIS desktop interface."
                ),
                content=(
                    "The user prefers Tauri "
                    "for the JARVIS desktop interface."
                ),
                candidates=[],
            )
        )

        self.assertTrue(
            result
        )


if __name__ == "__main__":
    unittest.main()