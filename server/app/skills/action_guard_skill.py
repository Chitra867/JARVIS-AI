from app.skills.base import Skill


class ActionGuardSkill(Skill):
    """
    Catches action commands that no real skill handled.

    This prevents the AI fallback from pretending that
    it performed an action which JARVIS cannot actually do.
    """

    ACTION_PREFIXES = (
        "open ",
        "launch ",
        "start ",
        "close ",
        "play ",
        "pause ",
        "resume ",
        "stop ",
        "search ",
        "find ",
        "show ",
        "create ",
        "make ",
        "delete ",
        "remove ",
        "rename ",
        "move ",
        "copy ",
        "paste ",
        "download ",
        "upload ",
        "install ",
        "uninstall ",
        "send ",
        "email ",
        "message ",
        "call ",
        "turn on ",
        "turn off ",
        "enable ",
        "disable ",
        "increase ",
        "decrease ",
        "set volume ",
        "mute ",
        "unmute ",
        "lock ",
        "shutdown ",
        "restart ",
        "reboot ",
        "sleep ",
        "take screenshot",
        "capture screenshot",
    )

    def can_handle(
        self,
        command: str,
    ) -> bool:
        normalized = (
            command
            .strip()
            .lower()
        )

        return normalized.startswith(
            self.ACTION_PREFIXES
        )

    def execute(
        self,
        command: str,
    ) -> str:
        clean_command = (
            command
            .strip()
            .rstrip(".!?")
        )

        return (
            f"I can't perform '{clean_command}' yet. "
            "I don't have a real skill for that action."
        )