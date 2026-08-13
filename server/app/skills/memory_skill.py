from app.core.memory import memory_manager
from app.skills.base import Skill


class MemorySkill(Skill):
    def can_handle(self, command: str) -> bool:
        normalized = command.strip().lower()

        return (
            normalized.startswith("remember ")
            or normalized.startswith("recall ")
            or normalized.startswith("search memory ")
            or normalized.startswith("what do you remember about ")
        )

    def execute(self, command: str) -> str:
        normalized = command.strip()
        lowered = normalized.lower()

        if lowered.startswith("remember "):
            text = normalized[9:].strip()

            return memory_manager.remember(text)

        prefixes = [
            "recall ",
            "search memory ",
            "what do you remember about ",
        ]

        query = normalized

        for prefix in prefixes:
            if lowered.startswith(prefix):
                query = normalized[len(prefix):].strip()
                break

        matches = memory_manager.search(query)

        if not matches:
            return f"I couldn't find anything in memory about {query}."

        return "I found:\n" + "\n".join(
            f"- {match}"
            for match in matches
        )