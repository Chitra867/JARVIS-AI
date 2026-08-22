import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


DATABASE_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "jarvis.db"
)


class ConversationManager:
    def __init__(self) -> None:
        DATABASE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = threading.Lock()

        self._initialize_database()

    @contextmanager
    def _connect(
        self,
    ) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            DATABASE_PATH,
            timeout=30,
        )

        connection.row_factory = (
            sqlite3.Row
        )

        connection.execute(
            "PRAGMA busy_timeout = 30000"
        )

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        try:
            yield connection

        except Exception:
            connection.rollback()
            raise

        else:
            connection.commit()

        finally:
            connection.close()

    def _initialize_database(
        self,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations
                (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    title TEXT
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages
                (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,

                    FOREIGN KEY(conversation_id)
                        REFERENCES conversations(id)
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_messages_conversation
                ON messages(
                    conversation_id,
                    id
                )
                """
            )

            connection.commit()

    def _now(
        self,
    ) -> str:
        return (
            datetime.now(
                timezone.utc
            )
            .isoformat()
        )

    def get_active_conversation_id(
        self,
    ) -> int | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id
                FROM conversations
                WHERE status = 'active'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

        if row is None:
            return None

        return int(
            row["id"]
        )

    def start_conversation(
        self,
    ) -> int:
        with self._lock:
            existing = (
                self
                .get_active_conversation_id()
            )

            if existing is not None:
                return existing

            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO conversations
                    (
                        started_at,
                        status
                    )
                    VALUES (?, 'active')
                    """,
                    (
                        self._now(),
                    ),
                )

                connection.commit()

                return int(
                    cursor.lastrowid
                )

    def get_or_create_active_conversation(
        self,
    ) -> int:
        conversation_id = (
            self
            .get_active_conversation_id()
        )

        if conversation_id is not None:
            return conversation_id

        return self.start_conversation()

    def end_active_conversation(
        self,
    ) -> None:
        conversation_id = (
            self
            .get_active_conversation_id()
        )

        if conversation_id is None:
            return

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE conversations
                SET
                    status = 'ended',
                    ended_at = ?
                WHERE id = ?
                """,
                (
                    self._now(),
                    conversation_id,
                ),
            )

            connection.commit()

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
    ) -> int:
        content = content.strip()

        if not content:
            return 0

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO messages
                (
                    conversation_id,
                    role,
                    content,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    role,
                    content,
                    self._now(),
                ),
            )

            connection.commit()

            return int(
                cursor.lastrowid
            )

    def get_recent_messages(
        self,
        conversation_id: int,
        limit: int = 12,
    ) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    role,
                    content,
                    created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    conversation_id,
                    limit,
                ),
            ).fetchall()

        rows = list(
            reversed(rows)
        )

        return [
            {
                "role": str(
                    row["role"]
                ),
                "content": str(
                    row["content"]
                ),
                "created_at": str(
                    row["created_at"]
                ),
            }
            for row in rows
        ]


conversation_manager = (
    ConversationManager()
)