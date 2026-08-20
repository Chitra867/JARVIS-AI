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

    # Memories containing these phrases are
    # usually too vague to be useful.
    VAGUE_PHRASES = (
        "specific programming language",
        "specific language",
        "specific framework",
        "specific tool",
        "specific project",
        "specific technology",
        "some programming language",
        "some framework",
        "some tool",
        "some project",
        "certain programming language",
        "certain framework",
        "certain tool",
        "certain project",
        "a programming language",
        "a framework",
        "a certain tool",
    )

    # Extra local protection.
    # The LLM is instructed not to store secrets,
    # but we also reject obvious credential-like
    # memories in code.
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
        # Memory extraction runs independently
        # from the main JARVIS response.
        #
        # Therefore JARVIS can answer/speak while
        # learning happens in the background.
        self.executor = (
            ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix=(
                    "jarvis-memory"
                ),
            )
        )

    # ==================================================
    # PUBLIC BACKGROUND SUBMIT
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
            user_message.strip()
        )

        assistant_message = (
            assistant_message.strip()
        )

        if not user_message:
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
            # Can occur during interpreter shutdown.
            print(
                "Memory worker unavailable:",
                error,
            )

    # ==================================================
    # EXTRACT MEMORY WITH OLLAMA
    # ==================================================

    def _extract_and_store(
        self,
        user_message: str,
        assistant_message: str,
        conversation_id: int,
        source_message_id:
            int | None,
    ) -> None:
        prompt = f"""
You are the long-term memory extraction system for JARVIS.

Your job is NOT to answer the user.
Your job is to identify durable information that the USER
explicitly revealed and that may be useful in future conversations.

USER MESSAGE:
{user_message}

JARVIS RESPONSE:
{assistant_message}

Only learn information that originates from the USER.

Good things to remember:
- stable user preferences
- important facts deliberately provided by the user
- ongoing project information
- technologies used in projects
- long-term goals
- important decisions
- persistent instructions
- stable working preferences
- recurring workflows

CRITICAL PRECISION RULES:
- Preserve exact important details from the user's statement.
- Preserve concrete names.
- Preserve project names.
- Preserve programming languages.
- Preserve technologies.
- Preserve frameworks.
- Preserve applications and tools.
- Preserve meaningful numbers and values.
- Preserve explicit choices and preferences.
- A saved memory must make sense without the original conversation.
- Do not remove the most important noun or value.
- Do not generalize precise information into vague information.
- Do not infer information the user did not state.
- Do not transform uncertainty into certainty.
- Store only what the USER revealed.
- The JARVIS response is context only and is not evidence of a user fact.

NEVER create vague memories such as:
- "The user prefers a specific programming language."
- "The user uses a certain framework."
- "The user is working on some project."
- "The user prefers a particular tool."

Instead preserve the concrete information.

EXAMPLE 1

User:
"For my AI projects I usually prefer Python."

GOOD MEMORY:
{{
  "type": "preference",
  "content": "The user usually prefers Python for AI projects.",
  "importance": 0.85,
  "confidence": 0.98
}}

BAD MEMORY:
{{
  "type": "preference",
  "content": "The user prefers a specific programming language.",
  "importance": 0.8,
  "confidence": 0.9
}}

EXAMPLE 2

User:
"My CampusConnect project uses React Native and Expo."

GOOD MEMORY:
{{
  "type": "project",
  "content": "CampusConnect uses React Native and Expo.",
  "importance": 0.85,
  "confidence": 0.98
}}

BAD MEMORY:
{{
  "type": "project",
  "content": "The user has a mobile application project.",
  "importance": 0.7,
  "confidence": 0.8
}}

EXAMPLE 3

User:
"For the JARVIS desktop interface I prefer React."

GOOD MEMORY:
{{
  "type": "preference",
  "content": "The user prefers React for the JARVIS desktop interface.",
  "importance": 0.85,
  "confidence": 0.98
}}

DO NOT SAVE:
- greetings
- temporary emotions
- casual small talk
- one-time questions
- ordinary commands such as opening an application
- search requests
- generated JARVIS advice
- assumptions
- guesses
- information invented by JARVIS
- information mentioned only by JARVIS
- trivial conversation
- passwords
- API keys
- access tokens
- authentication tokens
- private keys
- credentials
- secrets

Allowed memory types:
- preference
- fact
- project
- goal
- decision
- instruction

Return valid JSON only.

Required schema:

{{
  "memories": [
    {{
      "type": "preference",
      "content": "A precise standalone memory.",
      "importance": 0.8,
      "confidence": 0.9
    }}
  ]
}}

If nothing useful should be learned, return:

{{
  "memories": []
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

            memories = data.get(
                "memories",
                [],
            )

            if not isinstance(
                memories,
                list,
            ):
                return

            for memory in memories:
                self._validate_and_store(
                    memory=memory,
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
            # Learning must never break the
            # normal JARVIS conversation.
            print(
                "Memory extraction error:",
                error,
            )

    # ==================================================
    # VALIDATE EXTRACTED MEMORY
    # ==================================================

    def _validate_and_store(
        self,
        memory: object,
        conversation_id: int,
        source_message_id:
            int | None,
    ) -> None:
        if not isinstance(
            memory,
            dict,
        ):
            return

        memory_type = str(
            memory.get(
                "type",
                "",
            )
        ).strip().lower()

        content = str(
            memory.get(
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
                memory.get(
                    "importance",
                    0.5,
                )
            )

            confidence = float(
                memory.get(
                    "confidence",
                    0.7,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return

        # Clamp values.
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

        # Reject weak memories.
        if importance < 0.6:
            return

        if confidence < 0.65:
            return

        content_lower = (
            content.lower()
        )

        # ----------------------------------------------
        # Reject vague memories
        # ----------------------------------------------

        if any(
            phrase in content_lower
            for phrase in self.VAGUE_PHRASES
        ):
            print(
                "Rejected vague memory:",
                content,
            )

            return

        # ----------------------------------------------
        # Reject obvious secrets/credentials
        # ----------------------------------------------

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

        # ----------------------------------------------
        # Store
        # ----------------------------------------------

        memory_manager.save_memory(
            memory_type=(
                memory_type
            ),

            content=content,

            importance=(
                importance
            ),

            confidence=(
                confidence
            ),

            source_conversation_id=(
                conversation_id
            ),

            source_message_id=(
                source_message_id
            ),
        )


memory_extractor = MemoryExtractor()