from datetime import datetime

from app.skills.base import Skill


class TimeSkill(Skill):
    def can_handle(self, command: str) -> bool:
        normalized = command.strip().lower()

        return normalized in {
            "time",
            "what time is it",
            "date",
            "what is today's date",
        }

    def execute(self, command: str) -> str:
        normalized = command.strip().lower()

        if normalized in {"time", "what time is it"}:
            current_time = datetime.now().strftime("%I:%M %p")
            return f"The current time is {current_time}."

        current_date = datetime.now().strftime("%A, %B %d, %Y")
        return f"Today is {current_date}."