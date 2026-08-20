import re
import sqlite3
from datetime import datetime
from pathlib import Path

from app.core.conversation import (
    DATABASE_PATH,
)


class MemoryManager:
    def __init__(self) -> None:
        self.vault_path = (
            Path(__file__).resolve().parents[3]
            / "vault"
        )

        self.daily_path = (
            self.vault_path
            / "daily"
        )

        self.daily_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        DATABASE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize_database()

    def _connect(
        self,
    ) -> sqlite3.Connection:
        connection = sqlite3.connect(
            DATABASE_PATH,
            timeout=30,
        )

        connection.row_factory = (
            sqlite3.Row
        )

        return connection

    def _initialize_database(
        self,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories
                (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    memory_type TEXT NOT NULL,

                    content TEXT NOT NULL,

                    normalized_content TEXT NOT NULL,

                    importance REAL NOT NULL
                        DEFAULT 0.5,

                    confidence REAL NOT NULL
                        DEFAULT 0.8,

                    source_conversation_id INTEGER,

                    source_message_id INTEGER,

                    created_at TEXT NOT NULL,

                    updated_at TEXT NOT NULL,

                    access_count INTEGER NOT NULL
                        DEFAULT 0,

                    last_accessed_at TEXT,

                    UNIQUE(
                        memory_type,
                        normalized_content
                    )
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_memories_type
                ON memories(memory_type)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_memories_updated
                ON memories(updated_at)
                """
            )

            connection.commit()

    def _now(
        self,
    ) -> str:
        return (
            datetime.now()
            .isoformat(
                timespec="seconds"
            )
        )

    def _normalize(
        self,
        text: str,
    ) -> str:
        return (
            " ".join(
                text
                .strip()
                .lower()
                .split()
            )
        )

    def _tokens(
        self,
        text: str,
    ) -> set[str]:
        return set(
            re.findall(
                r"[a-zA-Z0-9_+#.-]+",
                text.lower(),
            )
        )

    # ==================================================
    # SAVE STRUCTURED MEMORY
    # ==================================================

    def save_memory(
        self,
        memory_type: str,
        content: str,
        importance: float = 0.7,
        confidence: float = 0.8,
        source_conversation_id:
            int | None = None,
        source_message_id:
            int | None = None,
    ) -> None:
        content = content.strip()

        if not content:
            return

        normalized = (
            self._normalize(
                content
            )
        )

        now = self._now()

        importance = max(
            0.0,
            min(
                1.0,
                float(importance),
            ),
        )

        confidence = max(
            0.0,
            min(
                1.0,
                float(confidence),
            ),
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO memories
                (
                    memory_type,
                    content,
                    normalized_content,
                    importance,
                    confidence,
                    source_conversation_id,
                    source_message_id,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

                ON CONFLICT(
                    memory_type,
                    normalized_content
                )
                DO UPDATE SET
                    content = excluded.content,

                    importance = MAX(
                        memories.importance,
                        excluded.importance
                    ),

                    confidence = MAX(
                        memories.confidence,
                        excluded.confidence
                    ),

                    updated_at =
                        excluded.updated_at
                """,
                (
                    memory_type,
                    content,
                    normalized,
                    importance,
                    confidence,
                    source_conversation_id,
                    source_message_id,
                    now,
                    now,
                ),
            )

            connection.commit()

    # ==================================================
    # EXPLICIT "REMEMBER THIS"
    # ==================================================

    def remember(
        self,
        memory: str,
    ) -> None:
        memory = memory.strip()

        if not memory:
            return

        self.save_memory(
            memory_type="explicit",
            content=memory,
            importance=1.0,
            confidence=1.0,
        )

        # Keep your existing human-readable
        # Markdown vault too.
        today = datetime.now()

        daily_file = (
            self.daily_path
            / f"{today:%Y-%m-%d}.md"
        )

        with daily_file.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                f"\n## {today:%H:%M}\n"
            )

            file.write(
                f"- {memory}\n"
            )

    # ==================================================
    # SEMANTIC-LIKE LOCAL SEARCH
    # ==================================================

    def search(
        self,
        query: str,
        limit: int = 6,
    ) -> list[str]:
        query = query.strip()

        if not query:
            return self.get_recent_memories(
                limit=limit
            )

        query_tokens = (
            self._tokens(
                query
            )
        )

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    content,
                    importance,
                    confidence,
                    updated_at
                FROM memories
                ORDER BY updated_at DESC
                LIMIT 300
                """
            ).fetchall()

        scored: list[
            tuple[
                float,
                int,
                str,
            ]
        ] = []

        for row in rows:
            content = str(
                row["content"]
            )

            memory_tokens = (
                self._tokens(
                    content
                )
            )

            overlap = len(
                query_tokens
                & memory_tokens
            )

            if overlap <= 0:
                continue

            importance = float(
                row["importance"]
            )

            confidence = float(
                row["confidence"]
            )

            score = (
                overlap * 2.0
                + importance
                + confidence * 0.5
            )

            scored.append(
                (
                    score,
                    int(row["id"]),
                    content,
                )
            )

        scored.sort(
            key=lambda item:
                item[0],
            reverse=True,
        )

        selected = (
            scored[:limit]
        )

        if selected:
            ids = [
                item[1]
                for item in selected
            ]

            now = self._now()

            with self._connect() as connection:
                for memory_id in ids:
                    connection.execute(
                        """
                        UPDATE memories
                        SET
                            access_count =
                                access_count + 1,

                            last_accessed_at = ?
                        WHERE id = ?
                        """,
                        (
                            now,
                            memory_id,
                        ),
                    )

                connection.commit()

        results = [
            item[2]
            for item in selected
        ]

        # Also search old Markdown memories so
        # nothing you already stored is lost.
        markdown_results = (
            self._search_markdown(
                query
            )
        )

        seen = {
            value.lower()
            for value in results
        }

        for memory in markdown_results:
            if (
                memory.lower()
                not in seen
            ):
                results.append(
                    memory
                )

                seen.add(
                    memory.lower()
                )

            if len(results) >= limit:
                break

        return results[:limit]

    # ==================================================
    # RECENT MEMORY
    # ==================================================

    def get_recent_memories(
        self,
        limit: int = 20,
    ) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT content
                FROM memories
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (
                    limit,
                ),
            ).fetchall()

        memories = [
            str(
                row["content"]
            )
            for row in rows
        ]

        seen = {
            memory.lower()
            for memory in memories
        }

        # Preserve access to previous Markdown
        # memories during the migration.
        for memory in (
            self._recent_markdown(
                limit
            )
        ):
            if (
                memory.lower()
                not in seen
            ):
                memories.append(
                    memory
                )

                seen.add(
                    memory.lower()
                )

            if len(memories) >= limit:
                break

        return memories[:limit]

    # ==================================================
    # OLD MARKDOWN COMPATIBILITY
    # ==================================================

    def _search_markdown(
        self,
        query: str,
    ) -> list[str]:
        query_lower = (
            query.lower()
        )

        query_tokens = (
            self._tokens(
                query
            )
        )

        matches: list[str] = []

        for file in sorted(
            self.daily_path.glob(
                "*.md"
            ),
            reverse=True,
        ):
            try:
                lines = (
                    file.read_text(
                        encoding="utf-8"
                    )
                    .splitlines()
                )
            except OSError:
                continue

            for line in lines:
                stripped = (
                    line.strip()
                )

                if not stripped.startswith(
                    "- "
                ):
                    continue

                memory = (
                    stripped[2:]
                    .strip()
                )

                if not memory:
                    continue

                memory_lower = (
                    memory.lower()
                )

                memory_tokens = (
                    self._tokens(
                        memory
                    )
                )

                if (
                    query_lower
                    in memory_lower
                    or query_tokens
                    & memory_tokens
                ):
                    matches.append(
                        memory
                    )

        return matches

    def _recent_markdown(
        self,
        limit: int,
    ) -> list[str]:
        results: list[str] = []

        seen: set[str] = set()

        for file in sorted(
            self.daily_path.glob(
                "*.md"
            ),
            reverse=True,
        ):
            try:
                lines = (
                    file.read_text(
                        encoding="utf-8"
                    )
                    .splitlines()
                )
            except OSError:
                continue

            for line in reversed(
                lines
            ):
                stripped = (
                    line.strip()
                )

                if not stripped.startswith(
                    "- "
                ):
                    continue

                memory = (
                    stripped[2:]
                    .strip()
                )

                if (
                    not memory
                    or memory.lower()
                    in seen
                ):
                    continue

                results.append(
                    memory
                )

                seen.add(
                    memory.lower()
                )

                if len(results) >= limit:
                    return results

        return results


memory_manager = MemoryManager()