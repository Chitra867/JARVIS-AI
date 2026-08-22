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

    TOKEN_STOP_WORDS = {
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
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "to",
        "of",
        "for",
        "in",
        "on",
        "at",
        "and",
        "or",
        "with",
        "that",
        "this",
        "it",
        "use",
        "uses",
        "using",
        "used",
        "prefer",
        "prefers",
        "preferred",
        "preference",
        "want",
        "wants",
        "wanted",
        "currently",
        "current",
        "now",
    }

    GENERIC_KEY_TOKENS = {
        "user",
        "users",
        "preference",
        "preferred",
        "fact",
        "project",
        "goal",
        "decision",
        "instruction",
        "setting",
        "settings",
        "value",
        "current",
    }

    def __init__(self) -> None:
        self.executor = (
            ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix=(
                    "jarvis-memory"
                ),
            )
        )

    # ==================================================
    # TOKEN / KEY HELPERS
    # ==================================================

    def _tokens(
        self,
        text: str,
    ) -> set[str]:
        return set(
            re.findall(
                r"[a-zA-Z0-9_+#-]+",
                text.lower(),
            )
        )

    def _meaningful_tokens(
        self,
        text: str,
    ) -> set[str]:
        return (
            self._tokens(text)
            - self.TOKEN_STOP_WORDS
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

    def _key_tokens(
        self,
        memory_key: str,
    ) -> set[str]:
        normalized = (
            self._normalize_key(
                memory_key
            )
        )

        if not normalized:
            return set()

        split_key = re.sub(
            r"[._-]+",
            " ",
            normalized,
        )

        return (
            self._tokens(
                split_key
            )
            - self.GENERIC_KEY_TOKENS
        )

        # ==================================================
    # ONE-TIME REQUEST DETECTION
    # ==================================================

    def _is_obvious_one_time_request(
        self,
        user_message: str,
    ) -> bool:
        normalized = (
            user_message
            .strip()
            .lower()
            .rstrip("?.!")
        )

        durable_markers = (
            "i prefer ",
            "i use ",
            "i usually ",
            "i always ",
            "i no longer ",
            "i don't use ",
            "i do not use ",
            "i switched ",
            "i changed ",
            "my preferred ",
            "my preference ",
            "from now on ",
            "going forward ",
        )

        if any(
            marker in normalized
            for marker in durable_markers
        ):
            return False

        request_prefixes = (
            "write ",
            "create ",
            "make ",
            "generate ",
            "explain ",
            "summarize ",
            "translate ",
            "calculate ",
            "compute ",
            "search ",
            "google ",
            "youtube ",
            "open ",
            "launch ",
            "start ",
            "close ",
            "play ",
            "pause ",
            "resume ",
            "stop ",
            "find ",
            "show ",
            "download ",
            "upload ",
            "install ",
            "uninstall ",
            "send ",
            "email ",
            "message ",
            "call ",
            "turn on ",
            "turn off ",
            "enable ",
            "disable ",
            "increase ",
            "decrease ",
            "set volume ",
            "mute ",
            "unmute ",
            "lock ",
            "shutdown ",
            "restart ",
            "reboot ",
            "sleep ",
            "take screenshot",
            "capture screenshot",
        )

        if normalized.startswith(
            request_prefixes
        ):
            return True

        question_prefixes = (
            "what ",
            "why ",
            "how ",
            "when ",
            "where ",
            "who ",
            "which ",
            "can ",
            "could ",
            "would ",
            "should ",
            "do ",
            "does ",
            "did ",
            "is ",
            "are ",
            "was ",
            "were ",
            "will ",
        )

        if normalized.startswith(
            question_prefixes
        ):
            return True

        return False

    # ==================================================
    # SKIP MEMORY-CONTROL COMMANDS
    # ==================================================

    def _should_skip_extraction(
        self,
        user_message: str,
    ) -> bool:
        normalized = (
            user_message
            .strip()
            .lower()
            .rstrip("?.!")
        )

        exact_commands = {
            "show active memories",
            "show active memory",
            "show all active memories",
            "what have you learned recently",
            "what did you learn recently",
            "show recent memories",
            "show recent memory",
        }

        if normalized in exact_commands:
            return True

        memory_query_prefixes = (
            "what do you remember",
            "what do you know about",
            "what have you learned",
            "show my memories",
            "show my memory",
            "show what you remember",
            "show what you know",
            "list my memories",
            "list what you remember",
        )

        if normalized.startswith(
            memory_query_prefixes
        ):
            return True

        if self._is_explicit_forget_request(
            user_message
        ):
            return True

        if normalized.startswith(
            (
                "remember ",
                "remember that ",
            )
        ):
            return True

        if self._is_obvious_one_time_request(
            user_message
        ):
            return True

        return False

    # ==================================================
    # EXPLICIT FORGET CHECK
    # ==================================================

    def _is_explicit_forget_request(
        self,
        user_message: str,
    ) -> bool:
        normalized = (
            user_message
            .strip()
            .lower()
        )

        forget_prefixes = (
            "forget ",
            "forget that ",
            "forget about ",
            "forget everything about ",
            "forget memory ",
            "remove from memory ",
            "delete from memory ",
            "stop remembering ",
        )

        return normalized.startswith(
            forget_prefixes
        )

    # ==================================================
    # USER-GROUNDING SAFETY
    # ==================================================

    def _content_is_grounded(
        self,
        content: str,
        user_message: str,
    ) -> bool:
        user_tokens = (
            self._meaningful_tokens(
                user_message
            )
        )

        content_tokens = (
            self._meaningful_tokens(
                content
            )
        )

        if (
            not user_tokens
            or not content_tokens
        ):
            return False

        shared = (
            user_tokens
            & content_tokens
        )

        required_overlap = min(
            2,
            len(user_tokens),
            len(content_tokens),
        )

        return (
            len(shared)
            >= required_overlap
        )

    # ==================================================
    # MEMORY KEY GROUNDING
    # ==================================================

    def _memory_key_is_grounded(
        self,
        memory_key: str,
        user_message: str,
        content: str,
        candidates: list[
            dict[str, object]
        ],
    ) -> bool:
        normalized_key = (
            self._normalize_key(
                memory_key
            )
        )

        if not normalized_key:
            return False

        # Existing known key is already trusted.
        for candidate in candidates:
            candidate_key = (
                self._normalize_key(
                    str(
                        candidate.get(
                            "memory_key",
                            "",
                        )
                    )
                )
            )

            if (
                candidate_key
                and candidate_key
                == normalized_key
            ):
                return True

        key_tokens = (
            self._key_tokens(
                normalized_key
            )
        )

        if not key_tokens:
            return False

        evidence_tokens = (
            self._meaningful_tokens(
                user_message
            )
            | self._meaningful_tokens(
                content
            )
        )

        return bool(
            key_tokens
            & evidence_tokens
        )

    # ==================================================
    # BACKGROUND SUBMIT
    # ==================================================

    def submit(
        self,
        user_message: str,
        assistant_message: str,
        conversation_id: int,
        source_message_id:
            int | None = None,
    ) -> None:
        user_message = (
            user_message
            .strip()
        )

        assistant_message = (
            assistant_message
            .strip()
        )

        if not user_message:
            return

        if self._should_skip_extraction(
            user_message
        ):
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

    # ==================================================
    # EXTRACT AND STORE
    # ==================================================

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

        candidate_ids = {
            int(memory["id"])
            for memory in candidates
        }

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

        # assistant_message is intentionally NOT included
        # in the prompt as factual evidence.
        _ = assistant_message

        prompt = f"""
You are the long-term memory manager for JARVIS.

Analyze ONLY what the USER explicitly stated.

USER MESSAGE:
{user_message}

RELEVANT ACTIVE MEMORIES:
{existing_context}

Decide whether durable user information should be:

1. REMEMBERED
2. UPDATED / SUPERSEDED
3. LEFT UNCHANGED

IMPORTANT SAFETY RULES:

- Only information explicitly stated by the USER may
  become long-term memory.

- Never use JARVIS's response as evidence.

- Never create memories from guesses or implications.

- Memory inspection commands must not become memories.

- Forget/delete commands are handled by a deterministic
  MemoryControlSkill. For any forget/delete request,
  return an empty actions list.

- supersedes_memory_ids may contain ONLY IDs shown in
  RELEVANT ACTIVE MEMORIES.

- When updating an existing conceptual property, reuse
  its existing memory_key exactly.

Example:

Existing:

ID=12
key=jarvis.desktop_interface
content=The user prefers React for the JARVIS desktop interface.

User:

"I don't use React for JARVIS anymore.
I prefer Tauri instead."

Correct:

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

MEMORY KEY RULES:

Use stable lowercase dot-separated keys.

Examples:

jarvis.desktop_interface
ai.preferred_language
campusconnect.framework
response.style
project.jarvis.voice_engine

The key must describe the same subject/property as
the user's statement.

Never guess an unrelated property.

Example:

Content:
"The user prefers Tauri for the JARVIS desktop interface."

GOOD:
jarvis.desktop_interface

BAD:
ai.preferred_language

Do not put changing values in keys.

GOOD:
jarvis.desktop_interface

BAD:
jarvis.tauri_interface

PRECISION RULES:

- Preserve exact technologies.
- Preserve names.
- Preserve programming languages.
- Preserve project names.
- Preserve frameworks.
- Preserve tools.
- Preserve important values.
- Never replace precise information with vague wording.

SAVE durable information such as:

- preferences
- project facts
- long-term goals
- decisions
- persistent instructions
- stable facts

DO NOT SAVE:

- greetings
- temporary emotions
- casual conversation
- ordinary computer commands
- one-time questions
- memory-inspection commands
- forget/delete commands
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

                    user_message=(
                        user_message
                    ),

                    conversation_id=(
                        conversation_id
                    ),

                    source_message_id=(
                        source_message_id
                    ),

                    candidates=(
                        candidates
                    ),

                    candidate_ids=(
                        candidate_ids
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
    # PROCESS MEMORY ACTION
    # ==================================================

    def _process_action(
        self,
        action: object,
        user_message: str,
        conversation_id: int,
        source_message_id:
            int | None,
        candidates: list[
            dict[str, object]
        ],
        candidate_ids: set[int],
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

        # ==================================================
        # EXTRACTOR MAY NEVER DELETE MEMORY
        # ==================================================

        if operation == "forget":
            print(
                "Rejected extractor forget action. "
                "Use MemoryControlSkill."
            )

            return

        # ==================================================
        # REMEMBER
        # ==================================================

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

        # ==================================================
        # CONTENT MUST COME FROM USER
        # ==================================================

        if not self._content_is_grounded(
            content=content,
            user_message=user_message,
        ):
            print(
                "Rejected ungrounded memory:",
                content,
            )

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

        # ==================================================
        # REJECT VAGUE MEMORY
        # ==================================================

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

        # ==================================================
        # REJECT SENSITIVE MEMORY
        # ==================================================

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

        # ==================================================
        # SUPERSEDE IDS
        # ==================================================

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
                    memory_id = int(
                        value
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                # LLM may supersede ONLY candidates
                # that were actually shown to it.
                if (
                    memory_id > 0
                    and memory_id
                    in candidate_ids
                ):
                    supersedes.append(
                        memory_id
                    )

                elif memory_id > 0:
                    print(
                        "Rejected unknown supersede ID:",
                        memory_id,
                    )

        # ==================================================
        # FORCE EXISTING STABLE KEY WHEN UPDATING
        # ==================================================

        superseded_keys: set[str] = set()

        for candidate in candidates:
            candidate_id = int(
                candidate["id"]
            )

            if candidate_id not in supersedes:
                continue

            candidate_key = (
                self._normalize_key(
                    str(
                        candidate.get(
                            "memory_key",
                            "",
                        )
                    )
                )
            )

            if candidate_key:
                superseded_keys.add(
                    candidate_key
                )

        if len(superseded_keys) == 1:
            memory_key = next(
                iter(
                    superseded_keys
                )
            )

        # ==================================================
        # VALIDATE NEW MEMORY KEY
        # ==================================================

        elif memory_key:
            if not self._memory_key_is_grounded(
                memory_key=memory_key,
                user_message=user_message,
                content=content,
                candidates=candidates,
            ):
                print(
                    "Rejected ungrounded memory key:",
                    memory_key,
                )

                # Preserve the valid memory content but
                # do not give it a dangerous stable key.
                memory_key = ""

                # Without a trusted stable key, do not
                # automatically supersede anything.
                supersedes = []

        # ==================================================
        # SAVE THROUGH MEMORY MANAGER
        # ==================================================

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