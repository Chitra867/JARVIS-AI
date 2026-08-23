import ctypes
import re

import pywhatkit

from app.skills.base import (
    Skill,
)


class MediaSkill(
    Skill
):
    VK_MEDIA_NEXT_TRACK = 0xB0
    VK_MEDIA_PREV_TRACK = 0xB1
    VK_MEDIA_STOP = 0xB2
    VK_MEDIA_PLAY_PAUSE = 0xB3

    KEYEVENTF_KEYUP = (
        0x0002
    )

    CONTROL_COMMANDS = {
        "pause":
            VK_MEDIA_PLAY_PAUSE,

        "pause music":
            VK_MEDIA_PLAY_PAUSE,

        "pause song":
            VK_MEDIA_PLAY_PAUSE,

        "pause media":
            VK_MEDIA_PLAY_PAUSE,

        "resume":
            VK_MEDIA_PLAY_PAUSE,

        "resume music":
            VK_MEDIA_PLAY_PAUSE,

        "resume song":
            VK_MEDIA_PLAY_PAUSE,

        "resume media":
            VK_MEDIA_PLAY_PAUSE,

        "play pause":
            VK_MEDIA_PLAY_PAUSE,

        "next":
            VK_MEDIA_NEXT_TRACK,

        "next song":
            VK_MEDIA_NEXT_TRACK,

        "next track":
            VK_MEDIA_NEXT_TRACK,

        "previous":
            VK_MEDIA_PREV_TRACK,

        "previous song":
            VK_MEDIA_PREV_TRACK,

        "previous track":
            VK_MEDIA_PREV_TRACK,

        "stop music":
            VK_MEDIA_STOP,

        "stop song":
            VK_MEDIA_STOP,

        "stop media":
            VK_MEDIA_STOP,
    }

    # ==================================================
    # ROUTING
    # ==================================================

    def can_handle(
        self,
        command: str,
    ) -> bool:
        normalized = (
            command
            .strip()
            .lower()
            .rstrip(
                ".!?"
            )
        )

        if (
            normalized
            in self.CONTROL_COMMANDS
        ):
            return True

        return normalized.startswith(
            (
                "play ",
                "play music",
                "play song",
                "play youtube",
            )
        )

    # ==================================================
    # EXECUTE
    # ==================================================

    def execute(
        self,
        command: str,
    ) -> str:
        normalized = (
            command
            .strip()
            .lower()
            .rstrip(
                ".!?"
            )
        )

        # ==============================================
        # MEDIA CONTROL
        # ==============================================

        key_code = (
            self.CONTROL_COMMANDS
            .get(
                normalized
            )
        )

        if (
            key_code
            is not None
        ):
            self._press_media_key(
                key_code
            )

            if (
                key_code
                == self.VK_MEDIA_NEXT_TRACK
            ):
                return (
                    "Skipping to the next track."
                )

            if (
                key_code
                == self.VK_MEDIA_PREV_TRACK
            ):
                return (
                    "Going to the previous track."
                )

            if (
                key_code
                == self.VK_MEDIA_STOP
            ):
                return (
                    "Stopping media playback."
                )

            return (
                "Toggling media playback."
            )

        # ==============================================
        # PLAY YOUTUBE
        # ==============================================

        query = (
            self._extract_query(
                command
            )
        )

        if not query:
            query = (
                "music"
            )

        try:
            pywhatkit.playonyt(
                query,
                open_video=True,
            )

            return (
                f"Playing {query} "
                f"on YouTube."
            )

        except Exception as error:
            print(
                (
                    "YouTube playback "
                    f"error: {error}"
                )
            )

            return (
                f"I couldn't play "
                f"{query} on YouTube."
            )

    # ==================================================
    # MEDIA KEY
    # ==================================================

    def _press_media_key(
        self,
        key_code: int,
    ) -> None:
        ctypes.windll.user32.keybd_event(
            key_code,
            0,
            0,
            0,
        )

        ctypes.windll.user32.keybd_event(
            key_code,
            0,
            self.KEYEVENTF_KEYUP,
            0,
        )

    # ==================================================
    # QUERY
    # ==================================================

    def _extract_query(
        self,
        command: str,
    ) -> str:
        text = (
            command
            .strip()
        )

        text = re.sub(
            r"^play\s+",
            "",
            text,
            flags=(
                re.IGNORECASE
            ),
        )

        text = re.sub(
            (
                r"\s+"
                r"(?:on|in|using)"
                r"\s+youtube\s*$"
            ),
            "",
            text,
            flags=(
                re.IGNORECASE
            ),
        )

        text = (
            text
            .strip()
        )

        if (
            text.lower()
            in {
                "",
                "youtube",
                "music",
                "some music",
                "a song",
                "song",
            }
        ):
            return (
                "music"
            )

        return text