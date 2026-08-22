import re

from app.core.memory import (
    memory_manager,
)

from app.skills.base import Skill


class MemoryControlSkill(Skill):
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
            normalized in {
                "show active memories",
                "show active memory",
                "show all active memories",
                "what have you learned recently",
                "what did you learn recently",
                "show recent memories",
                "show recent memory",
            }
            or normalized.startswith(
                "forget that "
            )
            or normalized.startswith(
                "forget about "
            )
            or normalized.startswith(
                "forget everything about "
            )
            or normalized.startswith(
                "forget memory "
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

        normalized = (
            original.lower()
        )

        # ==================================================
        # SHOW ACTIVE MEMORIES
        # ==================================================

        if normalized in {
            "show active memories",
            "show active memory",
            "show all active memories",
        }:
            memories = (
                memory_manager
                .get_all_memories(
                    include_inactive=False,
                    limit=20,
                )
            )

            if not memories:
                return (
                    "I don't currently have "
                    "any active long-term memories."
                )

            return self._format_records(
                memories
            )

        # ==================================================
        # RECENT MEMORIES
        # ==================================================

        if normalized in {
            "what have you learned recently",
            "what did you learn recently",
            "show recent memories",
            "show recent memory",
        }:
            memories = (
                memory_manager
                .get_all_memories(
                    include_inactive=False,
                    limit=5,
                )
            )

            if not memories:
                return (
                    "I haven't learned anything "
                    "persistent yet."
                )

            return self._format_records(
                memories,
                intro=(
                    "Recently, I learned that"
                ),
            )

        # ==================================================
        # FORGET BY ID
        # ==================================================

        if normalized.startswith(
            "forget memory "
        ):
            value = original[
                len("forget memory "):
            ].strip()

            match = re.fullmatch(
                r"(?:id\s*)?(\d+)",
                value,
                flags=re.IGNORECASE,
            )

            if not match:
                return (
                    "Tell me the numeric memory ID "
                    "you want me to forget."
                )

            memory_id = int(
                match.group(1)
            )

            count = (
                memory_manager
                .forget_memory_ids(
                    [memory_id]
                )
            )

            if count == 0:
                return (
                    f"I couldn't find active memory "
                    f"{memory_id}."
                )

            return (
                f"Memory {memory_id} "
                f"has been forgotten."
            )

        # ==================================================
        # FORGET EVERYTHING ABOUT TOPIC
        # ==================================================

        if normalized.startswith(
            "forget everything about "
        ):
            topic = original[
                len(
                    "forget everything about "
                ):
            ].strip()

            topic = self._clean_topic(
                topic
            )

            if not topic:
                return (
                    "Tell me what topic "
                    "you want me to forget."
                )

            matches = (
                memory_manager
                .search_records(
                    topic,
                    limit=50,
                )
            )

            if not matches:
                return (
                    f"I don't have any active "
                    f"memory about {topic}."
                )

            ids = [
                int(
                    memory["id"]
                )
                for memory in matches
            ]

            count = (
                memory_manager
                .forget_memory_ids(
                    ids
                )
            )

            return (
                f"I forgot {count} active "
                f"{'memory' if count == 1 else 'memories'} "
                f"about {topic}."
            )

        # ==================================================
        # FORGET THAT — EXACT MEMORY ONLY
        # ==================================================

        if normalized.startswith(
            "forget that "
        ):
            topic = original[
                len("forget that "):
            ].strip()

            topic = self._clean_topic(
                topic
            )

            if not topic:
                return (
                    "Tell me exactly what "
                    "you want me to forget."
                )

            matches = (
                memory_manager
                .search_records(
                    topic,
                    limit=20,
                )
            )

            normalized_topic = (
                self._normalize_match_text(
                    topic
                )
            )

            exact_matches = [
                memory
                for memory in matches
                if (
                    self._normalize_match_text(
                        str(
                            memory["content"]
                        )
                    )
                    == normalized_topic
                )
            ]

            if len(exact_matches) == 1:
                return (
                    self._forget_memory(
                        exact_matches[0]
                    )
                )

            if len(exact_matches) > 1:
                return (
                    self._multiple_matches_response(
                        exact_matches
                    )
                )

            return (
                "I couldn't find an exact active "
                f"memory matching: {topic}"
            )

        # ==================================================
        # FORGET ABOUT — TOPIC MATCH
        # ==================================================

        if normalized.startswith(
            "forget about "
        ):
            topic = original[
                len("forget about "):
            ].strip()

            topic = self._clean_topic(
                topic
            )

            if not topic:
                return (
                    "Tell me what topic "
                    "you want me to forget."
                )

            matches = (
                memory_manager
                .search_records(
                    topic,
                    limit=10,
                )
            )

            if not matches:
                return (
                    f"I couldn't find an active "
                    f"memory about {topic}."
                )

            if len(matches) > 1:
                return (
                    self._multiple_matches_response(
                        matches
                    )
                )

            return (
                self._forget_memory(
                    matches[0]
                )
            )
    # ==================================================
    # FORGET RECORD
    # ==================================================

    def _forget_memory(
        self,
        memory: dict[str, object],
    ) -> str:
        memory_id = int(
            memory["id"]
        )

        memory_content = str(
            memory["content"]
        )

        count = (
            memory_manager
            .forget_memory_ids(
                [memory_id]
            )
        )

        if count == 0:
            return (
                "That memory is already inactive."
            )

        return (
            "I've forgotten: "
            f"{memory_content}"
        )

    # ==================================================
    # MATCH NORMALIZATION
    # ==================================================

    def _clean_topic(
        self,
        topic: str,
    ) -> str:
        return (
            topic
            .strip()
            .rstrip("?.!")
            .strip()
        )

    def _normalize_match_text(
        self,
        text: str,
    ) -> str:
        text = (
            text
            .strip()
            .lower()
        )

        text = re.sub(
            r"[?.!]+$",
            "",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return (
            text
            .strip()
        )

    # ==================================================
    # MULTIPLE MATCHES
    # ==================================================

    def _multiple_matches_response(
        self,
        memories: list[
            dict[str, object]
        ],
    ) -> str:
        descriptions = "; ".join(
            (
                f"ID {memory['id']}: "
                f"{memory['content']}"
            )
            for memory
            in memories[:5]
        )

        return (
            "I found multiple possible "
            "memories. Specify the memory ID: "
            + descriptions
        )

    # ==================================================
    # FORMAT RECORDS
    # ==================================================

    def _format_records(
        self,
        memories: list[
            dict[str, object]
        ],
        intro: str = (
            "My active memories are"
        ),
    ) -> str:
        if not memories:
            return (
                "I don't currently have "
                "any active memories."
            )

        visible = (
            memories[:10]
        )

        items = [
            (
                f"ID {memory['id']}: "
                f"{memory['content']}"
            )
            for memory
            in visible
        ]

        body = "; ".join(
            items
        )

        if (
            len(memories)
            > len(visible)
        ):
            remaining = (
                len(memories)
                - len(visible)
            )

            return (
                f"{intro}: {body}. "
                f"I have {remaining} more."
            )

        return (
            f"{intro}: {body}."
        )