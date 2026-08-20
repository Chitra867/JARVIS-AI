import re

import pywhatkit

from app.skills.base import Skill


class MediaSkill(Skill):
    def can_handle(
        self,
        command: str,
    ) -> bool:
        normalized = (
            command
            .strip()
            .lower()
        )

        patterns = (
            "play ",
            "play music",
            "play song",
            "play youtube",
        )

        return normalized.startswith(
            patterns
        )

    def execute(
        self,
        command: str,
    ) -> str:
        normalized = (
            command
            .strip()
        )

        query = self._extract_query(
            normalized
        )

        if not query:
            query = "music"

        try:
            pywhatkit.playonyt(
                query,
                open_video=True,
            )

            return (
                f"Playing {query} on YouTube."
            )

        except Exception as error:
            print(
                "YouTube playback error:",
                error,
            )

            return (
                f"I couldn't play {query} on YouTube."
            )

    def _extract_query(
        self,
        command: str,
    ) -> str:
        text = command.strip()

        # Remove initial "play"
        text = re.sub(
            r"^play\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Remove phrases such as:
        # "on youtube"
        # "in youtube"
        # "using youtube"
        text = re.sub(
            r"\s+(on|in|using)\s+youtube\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = text.strip()

        if text.lower() in {
            "",
            "youtube",
            "music",
            "some music",
            "a song",
            "song",
        }:
            return "music"

        return text