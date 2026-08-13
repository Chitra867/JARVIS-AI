from datetime import datetime


class Jarvis:
    def execute(self, command: str) -> str:
        normalized_command = command.strip().lower()

        if not normalized_command:
            return "I didn't receive a command."

        if normalized_command in {"hello", "hi", "hey"}:
            return "Hello. JARVIS is online."

        if normalized_command in {"status", "system status"}:
            return "All core systems operational."

        if normalized_command in {"time", "what time is it"}:
            current_time = datetime.now().strftime("%I:%M %p")
            return f"The current time is {current_time}."

        if normalized_command in {"date", "what is today's date"}:
            current_date = datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {current_date}."

        return f"I don't have a skill for '{command}' yet."


jarvis = Jarvis()