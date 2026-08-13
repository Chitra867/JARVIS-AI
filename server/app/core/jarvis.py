from app.skills.registry import skill_registry


class Jarvis:
    def execute(self, command: str) -> str:
        normalized_command = command.strip()

        if not normalized_command:
            return "I didn't receive a command."

        if normalized_command.lower() in {"hello", "hi", "hey"}:
            return "Hello. JARVIS is online."

        skill = skill_registry.find_skill(normalized_command)

        if skill:
            return skill.execute(normalized_command)

        return f"I don't have a skill for '{command}' yet."


jarvis = Jarvis()