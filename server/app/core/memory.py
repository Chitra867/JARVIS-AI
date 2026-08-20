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

    # ==================================================
    # DATABASE
    # ==================================================

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
            # --------------------------------------------------
            # Fresh database schema
            # --------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories
                (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    memory_type TEXT NOT NULL,

                    memory_key TEXT,

                    content TEXT NOT NULL,

                    normalized_content TEXT NOT NULL,

                    importance REAL NOT NULL
                        DEFAULT 0.5,

                    confidence REAL NOT NULL
                        DEFAULT 0.8,

                    status TEXT NOT NULL
                        DEFAULT 'active',

                    source_conversation_id INTEGER,

                    source_message_id INTEGER,

                    created_at TEXT NOT NULL,

                    updated_at TEXT NOT NULL,

                    access_count INTEGER NOT NULL
                        DEFAULT 0,

                    last_accessed_at TEXT,

                    superseded_by INTEGER,

                    superseded_at TEXT,

                    forgotten_at TEXT,

                    UNIQUE(
                        memory_type,
                        normalized_content
                    )
                )
                """
            )

            # --------------------------------------------------
            # Existing database migration
            # --------------------------------------------------

            existing_columns = {
                str(row["name"])
                for row
                in connection.execute(
                    """
                    PRAGMA table_info(memories)
                    """
                ).fetchall()
            }

            migrations = {
                "memory_key":
                    "TEXT",

                "status":
                    "TEXT NOT NULL DEFAULT 'active'",

                "superseded_by":
                    "INTEGER",

                "superseded_at":
                    "TEXT",

                "forgotten_at":
                    "TEXT",
            }

            for (
                column_name,
                definition,
            ) in migrations.items():
                if (
                    column_name
                    not in existing_columns
                ):
                    connection.execute(
                        f"""
                        ALTER TABLE memories
                        ADD COLUMN
                        {column_name}
                        {definition}
                        """
                    )

            # --------------------------------------------------
            # Indexes
            # --------------------------------------------------

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
                idx_memories_status
                ON memories(status)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_memories_key
                ON memories(memory_key)
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

    # ==================================================
    # BASIC HELPERS
    # ==================================================

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
        return " ".join(
            text
            .strip()
            .lower()
            .split()
        )

    def _normalize_key(
        self,
        memory_key: str | None,
    ) -> str | None:
        if not memory_key:
            return None

        value = (
            memory_key
            .strip()
            .lower()
        )

        value = re.sub(
            r"[^a-z0-9_.-]+",
            ".",
            value,
        )

        value = re.sub(
            r"\.+",
            ".",
            value,
        )

        value = value.strip(".")

        return value or None

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

    def _meaningful_tokens(
        self,
        text: str,
    ) -> set[str]:
        stop_words = {
            "the",
            "a",
            "an",
            "i",
            "my",
            "me",
            "you",
            "your",
            "user",
            "users",
            "prefers",
            "prefer",
            "preferred",
            "preference",
            "uses",
            "use",
            "using",
            "used",
            "for",
            "to",
            "of",
            "in",
            "on",
            "at",
            "and",
            "or",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "instead",
            "no",
            "not",
            "longer",
            "current",
            "currently",
            "usually",
            "normally",
            "now",
            "this",
            "that",
            "it",
            "with",
        }

        return (
            self._tokens(text)
            - stop_words
        )

    # ==================================================
    # SUPERSEDE SAFETY
    # ==================================================

    def _can_supersede_memory(
        self,
        old_content: str,
        old_memory_key: str | None,
        new_content: str,
        new_memory_key: str | None,
    ) -> bool:
        """
        Deterministic safety layer.

        The LLM may propose which memories should be
        superseded, but Python decides whether that
        relationship is actually safe.
        """

        old_key = (
            self._normalize_key(
                old_memory_key
            )
        )

        new_key = (
            self._normalize_key(
                new_memory_key
            )
        )

        # --------------------------------------------------
        # Strongest case:
        # both memories have stable keys.
        #
        # They may supersede each other ONLY when
        # the keys identify exactly the same property.
        # --------------------------------------------------

        if (
            old_key
            and new_key
        ):
            return (
                old_key
                == new_key
            )

        # --------------------------------------------------
        # Legacy memories may not have memory_key.
        #
        # Require meaningful topic overlap before allowing
        # a legacy memory to be superseded.
        # --------------------------------------------------

        old_tokens = (
            self._meaningful_tokens(
                old_content
            )
        )

        new_tokens = (
            self._meaningful_tokens(
                new_content
            )
        )

        if (
            not old_tokens
            or not new_tokens
        ):
            return False

        shared_tokens = (
            old_tokens
            & new_tokens
        )

        # Require at least two meaningful shared
        # topic words for un-keyed legacy memories.
        #
        # Example:
        #
        # React JARVIS desktop interface
        # Tauri JARVIS desktop interface
        #
        # shared:
        # jarvis, desktop, interface
        #
        # -> safe
        #
        # Python
        # Tauri JARVIS desktop interface
        #
        # shared:
        # none
        #
        # -> reject
        return (
            len(shared_tokens)
            >= 2
        )

    # ==================================================
    # SAVE / UPDATE MEMORY
    # ==================================================

    def save_memory(
        self,
        memory_type: str,
        content: str,
        importance: float = 0.7,
        confidence: float = 0.8,
        memory_key: str | None = None,
        source_conversation_id:
            int | None = None,
        source_message_id:
            int | None = None,
        supersedes_memory_ids:
            list[int] | None = None,
    ) -> int | None:
        content = content.strip()

        if not content:
            return None

        memory_type = (
            memory_type
            .strip()
            .lower()
        )

        normalized = (
            self._normalize(
                content
            )
        )

        normalized_key = (
            self._normalize_key(
                memory_key
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

        supersedes: set[int] = set()

        if supersedes_memory_ids:
            for value in supersedes_memory_ids:
                try:
                    memory_id_value = int(
                        value
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                if memory_id_value > 0:
                    supersedes.add(
                        memory_id_value
                    )

        with self._connect() as connection:
            # --------------------------------------------------
            # Check whether this exact memory already exists.
            # --------------------------------------------------

            existing = connection.execute(
                """
                SELECT
                    id,
                    status
                FROM memories
                WHERE
                    memory_type = ?
                    AND normalized_content = ?
                LIMIT 1
                """,
                (
                    memory_type,
                    normalized,
                ),
            ).fetchone()

            if existing is not None:
                memory_id = int(
                    existing["id"]
                )

                # A newly repeated explicit/current statement
                # may reactivate an identical old memory.
                connection.execute(
                    """
                    UPDATE memories
                    SET
                        content = ?,

                        memory_key =
                            COALESCE(
                                ?,
                                memory_key
                            ),

                        importance =
                            MAX(
                                importance,
                                ?
                            ),

                        confidence =
                            MAX(
                                confidence,
                                ?
                            ),

                        status = 'active',

                        updated_at = ?,

                        source_conversation_id =
                            COALESCE(
                                ?,
                                source_conversation_id
                            ),

                        source_message_id =
                            COALESCE(
                                ?,
                                source_message_id
                            ),

                        superseded_by = NULL,

                        superseded_at = NULL,

                        forgotten_at = NULL

                    WHERE id = ?
                    """,
                    (
                        content,
                        normalized_key,
                        importance,
                        confidence,
                        now,
                        source_conversation_id,
                        source_message_id,
                        memory_id,
                    ),
                )

            else:
                cursor = connection.execute(
                    """
                    INSERT INTO memories
                    (
                        memory_type,
                        memory_key,
                        content,
                        normalized_content,
                        importance,
                        confidence,
                        status,
                        source_conversation_id,
                        source_message_id,
                        created_at,
                        updated_at
                    )
                    VALUES
                    (
                        ?, ?, ?, ?, ?, ?,
                        'active',
                        ?, ?, ?, ?
                    )
                    """,
                    (
                        memory_type,
                        normalized_key,
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

                memory_id = int(
                    cursor.lastrowid
                )

            # --------------------------------------------------
            # Same memory_key means same conceptual property.
            #
            # Example:
            #
            # jarvis.desktop_interface = React
            # jarvis.desktop_interface = Tauri
            #
            # Only one should stay active.
            # --------------------------------------------------

            if normalized_key:
                rows = connection.execute(
                    """
                    SELECT id
                    FROM memories
                    WHERE
                        memory_key = ?
                        AND status = 'active'
                        AND id <> ?
                    """,
                    (
                        normalized_key,
                        memory_id,
                    ),
                ).fetchall()

                for row in rows:
                    supersedes.add(
                        int(
                            row["id"]
                        )
                    )

            supersedes.discard(
                memory_id
            )

            # --------------------------------------------------
            # Validate every supersede operation locally.
            #
            # Never blindly trust LLM-generated IDs.
            # --------------------------------------------------

            for old_memory_id in supersedes:
                old_row = connection.execute(
                    """
                    SELECT
                        id,
                        memory_key,
                        content
                    FROM memories
                    WHERE
                        id = ?
                        AND status = 'active'
                    LIMIT 1
                    """,
                    (
                        old_memory_id,
                    ),
                ).fetchone()

                if old_row is None:
                    continue

                old_content = str(
                    old_row["content"]
                )

                old_memory_key = (
                    str(
                        old_row[
                            "memory_key"
                        ]
                    )
                    if old_row[
                        "memory_key"
                    ]
                    else None
                )

                allowed = (
                    self._can_supersede_memory(
                        old_content=(
                            old_content
                        ),
                        old_memory_key=(
                            old_memory_key
                        ),
                        new_content=(
                            content
                        ),
                        new_memory_key=(
                            normalized_key
                        ),
                    )
                )

                if not allowed:
                    print(
                        "Rejected unrelated supersede:",
                        old_memory_id,
                        "->",
                        memory_id,
                    )

                    continue

                connection.execute(
                    """
                    UPDATE memories
                    SET
                        status =
                            'superseded',

                        superseded_by =
                            ?,

                        superseded_at =
                            ?,

                        updated_at =
                            ?

                    WHERE
                        id = ?
                        AND status = 'active'
                        AND id <> ?
                    """,
                    (
                        memory_id,
                        now,
                        now,
                        old_memory_id,
                        memory_id,
                    ),
                )

            connection.commit()

            return memory_id

    # ==================================================
    # EXPLICIT REMEMBER
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

        # Keep a human-readable Markdown journal
        # alongside SQLite.
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
    # FORGET MEMORY IDS
    # ==================================================

    def forget_memory_ids(
        self,
        memory_ids: list[int],
    ) -> int:
        clean_ids: set[int] = set()

        for memory_id in memory_ids:
            try:
                value = int(
                    memory_id
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if value > 0:
                clean_ids.add(
                    value
                )

        sorted_ids = sorted(
            clean_ids
        )

        if not sorted_ids:
            return 0

        now = self._now()

        placeholders = ", ".join(
            "?"
            for _ in sorted_ids
        )

        with self._connect() as connection:
            cursor = connection.execute(
                f"""
                UPDATE memories
                SET
                    status = 'forgotten',

                    forgotten_at = ?,

                    updated_at = ?

                WHERE
                    id IN ({placeholders})
                    AND status = 'active'
                """,
                (
                    now,
                    now,
                    *sorted_ids,
                ),
            )

            connection.commit()

            return int(
                cursor.rowcount
            )

    # ==================================================
    # FORGET BY MEMORY KEY
    # ==================================================

    def forget_by_key(
        self,
        memory_key: str,
    ) -> int:
        normalized_key = (
            self._normalize_key(
                memory_key
            )
        )

        if not normalized_key:
            return 0

        now = self._now()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE memories
                SET
                    status = 'forgotten',

                    forgotten_at = ?,

                    updated_at = ?

                WHERE
                    memory_key = ?
                    AND status = 'active'
                """,
                (
                    now,
                    now,
                    normalized_key,
                ),
            )

            connection.commit()

            return int(
                cursor.rowcount
            )

    # ==================================================
    # GET ACTIVE MEMORY BY KEY
    # ==================================================

    def get_active_memory_by_key(
        self,
        memory_key: str,
    ) -> dict[str, object] | None:
        normalized_key = (
            self._normalize_key(
                memory_key
            )
        )

        if not normalized_key:
            return None

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    memory_type,
                    memory_key,
                    content,
                    importance,
                    confidence,
                    status,
                    created_at,
                    updated_at

                FROM memories

                WHERE
                    memory_key = ?
                    AND status = 'active'

                ORDER BY updated_at DESC

                LIMIT 1
                """,
                (
                    normalized_key,
                ),
            ).fetchone()

        if row is None:
            return None

        return {
            "id":
                int(row["id"]),

            "type":
                str(row["memory_type"]),

            "memory_key":
                str(row["memory_key"]),

            "content":
                str(row["content"]),

            "importance":
                float(row["importance"]),

            "confidence":
                float(row["confidence"]),

            "status":
                str(row["status"]),

            "created_at":
                str(row["created_at"]),

            "updated_at":
                str(row["updated_at"]),
        }

    # ==================================================
    # MEMORY CANDIDATES FOR EXTRACTOR
    # ==================================================

    def get_memory_candidates(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, object]]:
        query = query.strip()

        if not query:
            return []

        query_tokens = (
            self._meaningful_tokens(
                query
            )
        )

        # If every word was a stop-word,
        # fall back to ordinary tokens.
        if not query_tokens:
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
                    memory_type,
                    memory_key,
                    content,
                    importance,
                    confidence,
                    updated_at

                FROM memories

                WHERE status = 'active'

                ORDER BY updated_at DESC

                LIMIT 300
                """
            ).fetchall()

        scored: list[
            tuple[
                float,
                sqlite3.Row,
            ]
        ] = []

        for row in rows:
            content = str(
                row["content"]
            )

            memory_tokens = (
                self._meaningful_tokens(
                    content
                )
            )

            if not memory_tokens:
                memory_tokens = (
                    self._tokens(
                        content
                    )
                )

            overlap = len(
                query_tokens
                & memory_tokens
            )

            # --------------------------------------------------
            # Critical safety fix:
            #
            # Do not expose completely unrelated memories
            # to the LLM memory manager.
            # --------------------------------------------------

            if overlap <= 0:
                continue

            score = float(
                overlap * 3
            )

            score += float(
                row["importance"]
            )

            score += (
                float(
                    row["confidence"]
                )
                * 0.5
            )

            score += 2.0

            scored.append(
                (
                    score,
                    row,
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

        return [
            {
                "id":
                    int(row["id"]),

                "type":
                    str(
                        row["memory_type"]
                    ),

                "memory_key":
                    (
                        str(
                            row[
                                "memory_key"
                            ]
                        )
                        if row[
                            "memory_key"
                        ]
                        else None
                    ),

                "content":
                    str(
                        row["content"]
                    ),

                "importance":
                    float(
                        row["importance"]
                    ),

                "confidence":
                    float(
                        row["confidence"]
                    ),
            }
            for _, row
            in selected
        ]

    # ==================================================
    # SEARCH ACTIVE MEMORY
    # ==================================================

    def search(
        self,
        query: str,
        limit: int = 6,
    ) -> list[str]:
        query = query.strip()

        if not query:
            return (
                self.get_recent_memories(
                    limit=limit
                )
            )

        query_tokens = (
            self._meaningful_tokens(
                query
            )
        )

        if not query_tokens:
            query_tokens = (
                self._tokens(
                    query
                )
            )

        normalized_query = (
            self._normalize(
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

                WHERE status = 'active'

                ORDER BY updated_at DESC

                LIMIT 500
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

            content_normalized = (
                self._normalize(
                    content
                )
            )

            memory_tokens = (
                self._meaningful_tokens(
                    content
                )
            )

            if not memory_tokens:
                memory_tokens = (
                    self._tokens(
                        content
                    )
                )

            overlap = len(
                query_tokens
                & memory_tokens
            )

            exact_phrase = (
                normalized_query
                in content_normalized
            )

            if (
                overlap <= 0
                and not exact_phrase
            ):
                continue

            importance = float(
                row["importance"]
            )

            confidence = float(
                row["confidence"]
            )

            score = (
                overlap * 3.0
                + importance
                + confidence
            )

            if exact_phrase:
                score += 4.0

            scored.append(
                (
                    score,
                    int(
                        row["id"]
                    ),
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
            now = self._now()

            with self._connect() as connection:
                for (
                    _,
                    memory_id,
                    _,
                ) in selected:
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

        return [
            content
            for (
                _,
                _,
                content,
            )
            in selected
        ]

    # ==================================================
    # RECENT ACTIVE MEMORIES
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

                WHERE status = 'active'

                ORDER BY updated_at DESC

                LIMIT ?
                """,
                (
                    limit,
                ),
            ).fetchall()

        return [
            str(
                row["content"]
            )
            for row in rows
        ]

    # ==================================================
    # DEBUG / INSPECT MEMORIES
    # ==================================================

    def get_all_memories(
        self,
        include_inactive: bool = False,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        with self._connect() as connection:
            if include_inactive:
                rows = connection.execute(
                    """
                    SELECT
                        id,
                        memory_type,
                        memory_key,
                        content,
                        status,
                        importance,
                        confidence,
                        superseded_by,
                        created_at,
                        updated_at

                    FROM memories

                    ORDER BY id DESC

                    LIMIT ?
                    """,
                    (
                        limit,
                    ),
                ).fetchall()

            else:
                rows = connection.execute(
                    """
                    SELECT
                        id,
                        memory_type,
                        memory_key,
                        content,
                        status,
                        importance,
                        confidence,
                        superseded_by,
                        created_at,
                        updated_at

                    FROM memories

                    WHERE status = 'active'

                    ORDER BY id DESC

                    LIMIT ?
                    """,
                    (
                        limit,
                    ),
                ).fetchall()

        return [
            {
                "id":
                    int(row["id"]),

                "type":
                    str(
                        row["memory_type"]
                    ),

                "memory_key":
                    (
                        str(
                            row[
                                "memory_key"
                            ]
                        )
                        if row[
                            "memory_key"
                        ]
                        else None
                    ),

                "content":
                    str(
                        row["content"]
                    ),

                "status":
                    str(
                        row["status"]
                    ),

                "importance":
                    float(
                        row["importance"]
                    ),

                "confidence":
                    float(
                        row["confidence"]
                    ),

                "superseded_by":
                    (
                        int(
                            row[
                                "superseded_by"
                            ]
                        )
                        if row[
                            "superseded_by"
                        ]
                        is not None
                        else None
                    ),

                "created_at":
                    str(
                        row["created_at"]
                    ),

                "updated_at":
                    str(
                        row["updated_at"]
                    ),
            }
            for row in rows
        ]


memory_manager = MemoryManager()