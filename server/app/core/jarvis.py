import re

from app.core.conversation import (
    conversation_manager,
)

from app.core.intent_classifier import (
    IntentType,
    intent_classifier,
)

from app.core.memory_extractor import (
    memory_extractor,
)

from app.core.task_executor import (
    TaskExecutionResult,
    task_executor,
)

from app.skills.registry import (
    skill_registry,
)


class Jarvis:
    # ==================================================
    # EXECUTE
    # ==================================================

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

        # ==================================================
        # PERSISTENT CONVERSATION
        # ==================================================

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

        # ==================================================
        # NORMAL GREETING
        # ==================================================

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
            response = (
                self._route_command(
                    normalized_command
                )
            )

        # ==================================================
        # SAVE JARVIS RESPONSE
        # ==================================================

        conversation_manager.add_message(
            conversation_id,
            "assistant",
            response,
        )

        # ==================================================
        # BACKGROUND MEMORY EXTRACTION
        # ==================================================

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
    # COMMAND ROUTING
    # ==================================================

    def _route_command(
        self,
        command: str,
    ) -> str:
        classification = (
            intent_classifier
            .classify(
                command,
                has_matching_skill=False,
            )
        )

        # ==================================================
        # MULTI-STEP REQUEST
        # ==================================================

        if (
            classification.intent
            == IntentType.MULTI_STEP
        ):
            result = (
                task_executor
                .execute(
                    command
                )
            )

            return (
                self._format_task_result(
                    result
                )
            )

        # ==================================================
        # NORMAL DETERMINISTIC ROUTING
        # ==================================================

        skill = (
            skill_registry
            .find_skill(
                command
            )
        )

        if skill is not None:
            return skill.execute(
                command
            )

        return (
            "I don't have a skill "
            f"for '{command}' yet."
        )

    # ==================================================
    # FORMAT MULTI-STEP RESULT
    # ==================================================

    def _format_task_result(
        self,
        result: TaskExecutionResult,
    ) -> str:
        # Entire plan rejected before execution.
        if result.blocked:
            return (
                "I didn't execute that multi-step "
                "request because at least one step "
                "is unsupported or unsafe."
            )

        # Execution started but failed.
        if not result.success:
            if result.steps:
                failed_step = (
                    result.steps[-1]
                )

                return (
                    f"I stopped at step "
                    f"{failed_step.index} "
                    f"('{failed_step.command}'): "
                    f"{failed_step.response}"
                )

            return (
                "I couldn't complete that "
                "multi-step request."
            )

        if not result.steps:
            return (
                "The multi-step request "
                "completed."
            )

        summaries = [
            (
                f"{step.index}. "
                f"{step.response}"
            )
            for step
            in result.steps
            if step.response.strip()
        ]

        if not summaries:
            return (
                "The multi-step request "
                "completed."
            )

        return (
            "Completed the requested steps: "
            + " ".join(
                summaries
            )
        )

    # ==================================================
    # COMMAND CLEANUP
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

        return text.strip()


jarvis = Jarvis()