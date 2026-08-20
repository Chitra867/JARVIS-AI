import json
import re
from concurrent.futures import (
    ThreadPoolExecutor,
)

import httpx

from app.core.memory import (
    memory_manager,
)


class MemoryExtractor:
    OLLAMA_URL = (
        "http://127.0.0.1:11434"
        "/api/generate"
    )

    MODEL = "llama3.2:3b"

    ALLOWED_TYPES = {
        "preference",
        "fact",
        "project",
        "goal",
        "decision",
        "instruction",
    }

    VAGUE_PHRASES = (
        "specific programming language",
        "specific language",
        "specific framework",
        "specific tool",
        "specific project",
        "some programming language",
        "some framework",
        "some tool",
        "certain programming language",
        "certain framework",
    )

    SENSITIVE_PATTERNS = (
        r"\bpassword\b",
        r"\bpasswd\b",
        r"\bapi[\s_-]?key\b",
        r"\baccess[\s_-]?token\b",
        r"\brefresh[\s_-]?token\b",
        r"\bsecret[\s_-]?key\b",
        r"\bauthentication[\s_-]?token\b",
        r"\bbearer[\s_-]?token\b",
        r"\bprivate[\s_-]?key\b",
    )

    def __init__(self) -> None:
        self.executor = (
            ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix=(
                    "jarvis-memory"
                ),
            )
        )

    def submit(
        self,
        user_message: str,
        assistant_message: str,
        conversation_id: int,
        source_message_id:
            int | None = None,
    ) -> None:
        if not user_message.strip():
            return

        try:
            self.executor.submit(
                self._extract_and_store,
                user_message,
                assistant_message,
                conversation_id,
                source_message_id,
            )

        except RuntimeError as error:
            print(
                "Memory worker unavailable:",
                error,
            )

    def _extract_and_store(
        self,
        user_message: str,
        assistant_message: str,
        conversation_id: int,
        source_message_id:
            int | None,
    ) -> None:
        candidates = (
            memory_manager
            .get_memory_candidates(
                user_message,
                limit=20,
            )
        )

        existing_context = "\n".join(
            (
                f"ID={memory['id']} | "
                f"type={memory['type']} | "
                f"key={memory['memory_key']} | "
                f"content={memory['content']}"
            )
            for memory
            in candidates
        )

        if not existing_context:
            existing_context = (
                "No relevant active memories."
            )

        prompt = f"""
You are the long-term memory manager for JARVIS.

Analyze what the USER said.

USER MESSAGE:
{user_message}

JARVIS RESPONSE:
{assistant_message}

RELEVANT ACTIVE MEMORIES:
{existing_context}

Your job is to determine whether memory should be:

1. REMEMBERED
2. UPDATED / SUPERSEDED
3. FORGOTTEN
4. LEFT UNCHANGED

IMPORTANT:
The user's newest explicit statement has priority over
older memories.

If a new statement changes an older preference, decision,
project configuration, instruction, goal, or fact:

- create the NEW memory
- reuse the old memory_key when available
- include the IDs of the old memories in
  supersedes_memory_ids

Example:

Existing:
ID=12
key=jarvis.desktop_interface
content=The user prefers React for the JARVIS desktop interface.

User:
"I don't use React for JARVIS anymore.
I prefer Tauri instead."

Correct action:

{{
  "actions": [
    {{
      "operation": "remember",
      "type": "preference",
      "memory_key": "jarvis.desktop_interface",
      "content": "The user prefers Tauri for the JARVIS desktop interface.",
      "importance": 0.9,
      "confidence": 0.99,
      "supersedes_memory_ids": [12]
    }}
  ]
}}

If the existing memory does not yet have a memory_key,
you may create a sensible stable key and still include its
ID in supersedes_memory_ids.

MEMORY KEY RULES:

Use a stable lowercase dot-separated key describing the
subject and property.

Examples:

jarvis.desktop_interface
ai.preferred_language
campusconnect.framework
response.style
project.jarvis.voice_engine

Do NOT put the actual changing value in the key.

GOOD:
jarvis.desktop_interface

BAD:
jarvis.react_interface

This lets future values replace older values.

FORGETTING:

If the user explicitly asks JARVIS to forget stored
information, return:

{{
  "actions": [
    {{
      "operation": "forget",
      "memory_ids": [12]
    }}
  ]
}}

Only forget information when the USER explicitly asks
to forget/remove it.

PRECISION RULES:

- Preserve exact technologies and names.
- Preserve programming languages.
- Preserve project names.
- Preserve frameworks.
- Preserve tools.
- Preserve important values.
- Never replace precise information with vague wording.
- Save only information originating from the USER.
- Never treat the JARVIS response as proof of a user fact.
- Never invent information.

SAVE durable information such as:

- preferences
- project facts
- long-term goals
- decisions
- persistent instructions
- important stable facts

DO NOT SAVE:

- greetings
- temporary emotions
- casual conversation
- ordinary computer commands
- one-time questions
- JARVIS-generated advice
- guesses
- passwords
- API keys
- tokens
- credentials
- secrets

Allowed types:

preference
fact
project
goal
decision
instruction

Return JSON only.

Schema:

{{
  "actions": [
    {{
      "operation": "remember",
      "type": "preference",
      "memory_key": "subject.property",
      "content": "Precise standalone memory.",
      "importance": 0.8,
      "confidence": 0.9,
      "supersedes_memory_ids": []
    }}
  ]
}}

If nothing should change:

{{
  "actions": []
}}
""".strip()

        try:
            response = httpx.post(
                self.OLLAMA_URL,
                json={
                    "model":
                        self.MODEL,

                    "prompt":
                        prompt,

                    "stream":
                        False,

                    "format":
                        "json",

                    "options": {
                        "temperature":
                            0.1,
                    },
                },
                timeout=60.0,
            )

            response.raise_for_status()

            raw_answer = (
                response
                .json()
                .get(
                    "response",
                    "",
                )
                .strip()
            )

            if not raw_answer:
                return

            data = json.loads(
                raw_answer
            )

            actions = data.get(
                "actions",
                [],
            )

            if not isinstance(
                actions,
                list,
            ):
                return

            for action in actions:
                self._process_action(
                    action=action,
                    conversation_id=(
                        conversation_id
                    ),
                    source_message_id=(
                        source_message_id
                    ),
                )

        except (
            httpx.HTTPError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            print(
                "Memory extraction error:",
                error,
            )

    # ==================================================
    # PROCESS ACTION
    # ==================================================

    def _process_action(
        self,
        action: object,
        conversation_id: int,
        source_message_id:
            int | None,
    ) -> None:
        if not isinstance(
            action,
            dict,
        ):
            return

        operation = str(
            action.get(
                "operation",
                "",
            )
        ).strip().lower()

        if operation == "forget":
            memory_ids = (
                action.get(
                    "memory_ids",
                    [],
                )
            )

            if not isinstance(
                memory_ids,
                list,
            ):
                return

            clean_ids: list[int] = []

            for value in memory_ids:
                try:
                    clean_ids.append(
                        int(value)
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

            if clean_ids:
                memory_manager.forget_memory_ids(
                    clean_ids
                )

            return

        if operation != "remember":
            return

        memory_type = str(
            action.get(
                "type",
                "",
            )
        ).strip().lower()

        memory_key = str(
            action.get(
                "memory_key",
                "",
            )
        ).strip()

        content = str(
            action.get(
                "content",
                "",
            )
        ).strip()

        if (
            memory_type
            not in self.ALLOWED_TYPES
        ):
            return

        if (
            len(content) < 5
            or len(content) > 400
        ):
            return

        try:
            importance = float(
                action.get(
                    "importance",
                    0.5,
                )
            )

            confidence = float(
                action.get(
                    "confidence",
                    0.7,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return

        importance = max(
            0.0,
            min(
                1.0,
                importance,
            ),
        )

        confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        if importance < 0.6:
            return

        if confidence < 0.65:
            return

        content_lower = (
            content.lower()
        )

        if any(
            phrase in content_lower
            for phrase
            in self.VAGUE_PHRASES
        ):
            print(
                "Rejected vague memory:",
                content,
            )

            return

        if any(
            re.search(
                pattern,
                content_lower,
            )
            is not None
            for pattern
            in self.SENSITIVE_PATTERNS
        ):
            print(
                "Rejected sensitive memory."
            )

            return

        raw_supersedes = (
            action.get(
                "supersedes_memory_ids",
                [],
            )
        )

        supersedes: list[int] = []

        if isinstance(
            raw_supersedes,
            list,
        ):
            for value in raw_supersedes:
                try:
                    supersedes.append(
                        int(value)
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

        memory_manager.save_memory(
            memory_type=(
                memory_type
            ),

            memory_key=(
                memory_key
                or None
            ),

            content=content,

            importance=importance,

            confidence=confidence,

            source_conversation_id=(
                conversation_id
            ),

            source_message_id=(
                source_message_id
            ),

            supersedes_memory_ids=(
                supersedes
            ),
        )


memory_extractor = MemoryExtractor()