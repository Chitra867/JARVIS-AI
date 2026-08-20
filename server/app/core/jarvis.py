import re

from app.core.conversation import (
    conversation_manager,
)

from app.core.memory_extractor import (
    memory_extractor,
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


        # ---------------------------------------------
        # Persistent conversation
        # ---------------------------------------------

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


        # ---------------------------------------------
        # Normal greeting
        # ---------------------------------------------

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
            # -----------------------------------------
            # Route to a REAL skill first.
            # AISkill remains fallback.
            # -----------------------------------------

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


        # ---------------------------------------------
        # Save JARVIS response
        # ---------------------------------------------

        conversation_manager.add_message(
            conversation_id,
            "assistant",
            response,
        )


        # ---------------------------------------------
        # Learn useful facts in background.
        # Does NOT delay spoken response.
        # ---------------------------------------------

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


    def _clean_command(
        self,
        command: str,
    ) -> str:
        text = command.strip()

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

        return text.strip()


jarvis = Jarvis()