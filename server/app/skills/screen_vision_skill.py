import httpx

from app.core.screen_capture import (
    screen_capture_service,
)

from app.skills.base import (
    Skill,
)


class ScreenVisionSkill(
    Skill
):
    OLLAMA_URL = (
        "http://127.0.0.1:11434"
        "/api/chat"
    )

    MODEL = (
        "qwen2.5vl:3b"
    )

    COMMANDS = {
        "what is on my screen",
        "what's on my screen",
        "what is on the screen",
        "what's on the screen",
        "describe my screen",
        "describe the screen",
        "analyze my screen",
        "analyse my screen",
        "analyze the screen",
        "analyse the screen",
        "look at my screen",
        "look at the screen",
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
            capture = (
                screen_capture_service
                .capture()
            )

        except Exception as error:
            print(
                (
                    "Screen capture failed: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

            return (
                "I couldn't capture "
                "the screen."
            )

        try:
            return (
                self._analyze_screen(
                    capture.image_data
                )
            )

        except (
            httpx.ConnectError
        ):
            return (
                "I can't connect to "
                "the local vision model."
            )

        except (
            httpx.TimeoutException
        ):
            return (
                "The local vision model "
                "took too long to respond."
            )

        except (
            httpx.HTTPError,
            ValueError,
            TypeError,
            KeyError,
        ) as error:
            print(
                (
                    "Screen vision failed: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

            return (
                "I couldn't analyze "
                "the screen."
            )

    # ==================================================
    # ANALYZE
    # ==================================================

    def _analyze_screen(
        self,
        image_data: str,
    ) -> str:
        prompt = """
You are the screen-vision component of JARVIS.

Analyze the screenshot supplied by the user.

Rules:

- Describe only what is visibly present.
- Do not invent hidden information.
- Identify the main application or window if possible.
- Mention important visible text, controls, errors,
  warnings, code, terminal output, or browser content.
- Focus on information useful to the user.
- Do not expose or repeat passwords, API keys, tokens,
  private credentials, or other obvious secrets.
- If sensitive information appears, describe it only as
  sensitive information being visible.
- Do not claim that you clicked, typed, changed, or
  executed anything.
- Keep the answer concise but useful.
- If the screenshot is unclear, say what you can
  confidently determine.

Describe what is currently on the screen.
""".strip()

        response = (
            httpx.post(
                self.OLLAMA_URL,
                json={
                    "model":
                        self.MODEL,

                    "messages": [
                        {
                            "role":
                                "user",

                            "content":
                                prompt,

                            "images": [
                                image_data
                            ],
                        }
                    ],

                    "stream":
                        False,

                    "options": {
                        "temperature":
                            0.1,
                    },
                },
                timeout=90.0,
            )
        )

        response.raise_for_status()

        data = (
            response.json()
        )

        message = (
            data.get(
                "message",
                {}
            )
        )

        answer = (
            str(
                message.get(
                    "content",
                    "",
                )
            )
            .strip()
        )

        if not answer:
            return (
                "I couldn't determine "
                "what is on the screen."
            )

        return answer