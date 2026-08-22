import re

from app.core.conversation import (
    conversation_manager,
)

from app.core.memory_extractor import (
    memory_extractor,
)

from app.skills.memory_control_skill import (
    MemoryControlSkill,
)

from app.skills.registry import (
    skill_registry,
)


class Jarvis:
    def execute(
        self,
        command: str,
    ) -> str:
        normalized_command = (
            self._clean_command(
                command
            )
        )

        if not normalized_command:
            return "Yes?"

        # ==============================================
        # PERSISTENT CONVERSATION
        # ==============================================

        conversation_id = (
            conversation_manager
            .get_or_create_active_conversation()
        )

        user_message_id = (
            conversation_manager
            .add_message(
                conversation_id,
                "user",
                normalized_command,
            )
        )

        skill = None

        # ==============================================
        # GREETING
        # ==============================================

        if (
            normalized_command.lower()
            in {
                "hello",
                "hi",
                "hey",
            }
        ):
            response = (
                "Hello. JARVIS is online."
            )

        else:
            # ==========================================
            # SKILL ROUTING
            # ==========================================

            skill = (
                skill_registry
                .find_skill(
                    normalized_command
                )
            )

            if skill:
                response = (
                    skill.execute(
                        normalized_command
                    )
                )

            else:
                response = (
                    "I don't have a skill "
                    f"for '{normalized_command}' "
                    "yet."
                )

        # ==============================================
        # SAVE ASSISTANT RESPONSE
        # ==============================================

        conversation_manager.add_message(
            conversation_id,
            "assistant",
            response,
        )

        # ==============================================
        # MEMORY EXTRACTION
        # ==============================================
        #
        # Memory-control commands must NEVER be sent
        # back into automatic learning.
        #
        # Otherwise:
        #
        # forget X
        #     ↓
        # extractor sees X again
        #     ↓
        # may recreate/supersede memory ❌
        #
        # ==============================================

        if not isinstance(
            skill,
            MemoryControlSkill,
        ):
            memory_extractor.submit(
                user_message=(
                    normalized_command
                ),

                assistant_message=(
                    response
                ),

                conversation_id=(
                    conversation_id
                ),

                source_message_id=(
                    user_message_id
                ),
            )

        return response

    # ==================================================
    # CLEAN COMMAND
    # ==================================================

    def _clean_command(
        self,
        command: str,
    ) -> str:
        text = (
            command
            .strip()
        )

        text = re.sub(
            r"^(?:"
            r"hey\s+jarvis"
            r"|hello\s+jarvis"
            r"|hi\s+jarvis"
            r"|jarvis"
            r")"
            r"[\s,.:;!?-]*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        return (
            text
            .strip()
        )


jarvis = Jarvis()