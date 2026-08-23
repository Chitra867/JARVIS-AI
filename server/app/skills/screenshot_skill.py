from datetime import (
    datetime,
)

from pathlib import (
    Path,
)

from PIL import (
    ImageGrab,
)

from app.skills.base import (
    Skill,
)


class ScreenshotSkill(
    Skill
):
    COMMANDS = {
        "screenshot",
        "take screenshot",
        "take a screenshot",
        "capture screenshot",
        "capture a screenshot",
        "take screen capture",
        "capture screen",
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

        return (
            normalized
            in self.COMMANDS
        )

    # ==================================================
    # EXECUTE
    # ==================================================

    def execute(
        self,
        command: str,
    ) -> str:
        del command

        try:
            screenshot_dir = (
                Path.home()
                / "Pictures"
                / "JARVIS Screenshots"
            )

            screenshot_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            timestamp = (
                datetime.now()
                .strftime(
                    "%Y-%m-%d_%H-%M-%S"
                )
            )

            path = (
                screenshot_dir
                / (
                    f"jarvis_screenshot_"
                    f"{timestamp}.png"
                )
            )

            image = (
                ImageGrab.grab(
                    all_screens=True,
                )
            )

            image.save(
                path,
                format="PNG",
            )

            return (
                "Screenshot captured and saved to "
                f"{path}."
            )

        except Exception as error:
            print(
                (
                    "Screenshot capture failed: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

            return (
                "I couldn't capture "
                "the screenshot."
            )