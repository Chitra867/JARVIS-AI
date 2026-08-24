import json
import re

from dataclasses import (
    dataclass,
)

import httpx

from app.core.screen_capture import (
    ScreenCapture,
    screen_capture_service,
)

from app.core.ui_automation import (
    ui_automation_service,
)

from app.skills.base import (
    Skill,
)


@dataclass(
    frozen=True
)
class VisualTarget:
    label: str

    normalized_x: int
    normalized_y: int

    screen_x: int
    screen_y: int

    confidence: float

    region_name: str


class VisualTargetSkill(
    Skill
):
    OLLAMA_URL = (
        "http://127.0.0.1:11434"
        "/api/chat"
    )

    MODEL = (
        "qwen2.5vl:3b"
    )

    MIN_CONFIDENCE = 0.55

    UI_WORDS = {
        "button",
        "icon",
        "tab",
        "menu",
        "field",
        "textbox",
        "text box",
        "input",
        "link",
        "checkbox",
        "radio",
        "dropdown",
        "search box",
        "search bar",
    }

    LOCATE_PATTERN = re.compile(
        (
            r"^(?:find|locate)\s+"
            r"(.+?)"
            r"(?:\s+on\s+(?:my|the)\s+screen)?"
            r"\s*[.!?]*$"
        ),
        flags=re.IGNORECASE,
    )

    WHERE_PATTERN = re.compile(
        (
            r"^where\s+is\s+"
            r"(.+?)"
            r"\s+on\s+(?:my|the)\s+screen"
            r"\s*[.!?]*$"
        ),
        flags=re.IGNORECASE,
    )

    # ==================================================
    # ROUTING
    # ==================================================

    def can_handle(
        self,
        command: str,
    ) -> bool:
        target = (
            self._extract_target(
                command
            )
        )

        if (
            target is None
        ):
            return False

        normalized_command = (
            command
            .strip()
            .lower()
        )

        # Explicit reference to the screen means this
        # is definitely a visual/UI target request.
        if (
            "on my screen"
            in normalized_command
            or
            "on the screen"
            in normalized_command
        ):
            return True

        # Without explicit screen wording, require
        # terminology that strongly indicates a UI
        # element.
        normalized_target = (
            target
            .strip()
            .lower()
        )

        return any(
            word
            in normalized_target

            for word
            in self.UI_WORDS
        )

    # ==================================================
    # EXECUTE
    # ==================================================

    def execute(
        self,
        command: str,
    ) -> str:
        target = (
            self._extract_target(
                command
            )
        )

        if (
            target is None
        ):
            return (
                "Tell me which visible "
                "screen element to locate."
            )

        lookup_target = (
            self._clean_target_phrase(
                target
            )
        )

        # ==================================================
        # PASS 0 — WINDOWS UI AUTOMATION
        # ==================================================
        #
        # UIA is preferred because it provides:
        #
        # - deterministic names
        # - control types
        # - visibility
        # - enabled state
        # - exact desktop rectangles
        #
        # Most importantly, resolve_target() lets us
        # distinguish:
        #
        # resolved
        # ambiguous
        # not_found
        # error
        #
        # An ambiguous result MUST NOT fall through to
        # vision because that would allow the VLM to guess.
        # ==================================================

        try:
            ui_resolution = (
                ui_automation_service
                .resolve_target(
                    lookup_target
                )
            )

        except Exception as error:
            print(
                (
                    "UI Automation target lookup failed: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

            ui_resolution = None

        # ==================================================
        # UIA — RESOLVED
        # ==================================================

        if (
            ui_resolution
            is not None
            and
            ui_resolution.resolved
            and
            ui_resolution.target
            is not None
        ):
            ui_target = (
                ui_resolution.target
            )

            status = (
                "enabled"
                if ui_target.enabled
                else "disabled"
            )

            return (
                f"I found '{ui_target.name}' "
                f"as a {ui_target.control_type} "
                f"near screen position "
                f"({ui_target.center_x}, "
                f"{ui_target.center_y}). "
                f"The control is {status}. "
                "Located using Windows UI Automation. "
                "No click was performed."
            )

        # ==================================================
        # UIA — AMBIGUOUS
        # ==================================================
        #
        # Fail closed.
        #
        # Do not use vision after UIA already established
        # that multiple plausible targets exist.
        # ==================================================

        if (
            ui_resolution
            is not None
            and
            ui_resolution.ambiguous
        ):
            candidate_descriptions: list[
                str
            ] = []

            for candidate in (
                ui_resolution
                .candidates[:5]
            ):
                candidate_descriptions.append(
                    (
                        f"{candidate.name} "
                        f"({candidate.control_type})"
                    )
                )

            candidates_text = (
                "; ".join(
                    candidate_descriptions
                )
            )

            if not (
                candidates_text
            ):
                candidates_text = (
                    "multiple visible controls"
                )

            return (
                f"I found multiple possible matches "
                f"for '{target}': "
                f"{candidates_text}. "
                "Please specify the exact control "
                "you mean. "
                "No vision fallback or click "
                "was performed."
            )

        # ==================================================
        # UIA — ERROR
        # ==================================================
        #
        # Since this skill is location-only, a UIA runtime
        # failure may continue to vision.
        #
        # Automatic clicking is still not performed.
        # ==================================================

        if (
            ui_resolution
            is not None
            and
            ui_resolution.status
            == "error"
        ):
            print(
                (
                    "UI Automation could not complete "
                    "the lookup. Continuing with "
                    "location-only vision fallback."
                )
            )

        # ==================================================
        # PASS 1 — FULL-SCREEN VISION
        # ==================================================
        #
        # Vision is used only when:
        #
        # - UIA returned not_found
        # - UIA failed internally
        # - UIA lookup unexpectedly raised
        #
        # Vision is NOT used for ambiguity.
        # ==================================================

        try:
            full_capture = (
                screen_capture_service
                .capture()
            )

            visual_target = (
                self._locate_target(
                    target=(
                        lookup_target
                    ),
                    capture=(
                        full_capture
                    ),
                )
            )

            # ==============================================
            # PASS 2 — FOCUSED VISION REGION
            # ==============================================

            if (
                visual_target
                is None
            ):
                region = (
                    self._infer_focus_region(
                        lookup_target
                    )
                )

                if (
                    region
                    is not None
                ):
                    focused_capture = (
                        screen_capture_service
                        .capture_region(
                            region
                        )
                    )

                    visual_target = (
                        self._locate_target(
                            target=(
                                lookup_target
                            ),
                            capture=(
                                focused_capture
                            ),
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
                "took too long to locate "
                "that screen element."
            )

        except (
            httpx.HTTPError,
            ValueError,
            TypeError,
            KeyError,
        ) as error:
            print(
                (
                    "Visual target lookup failed: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

            return (
                "I couldn't reliably locate "
                "that screen element."
            )

        except Exception as error:
            print(
                (
                    "Visual target failure: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

            return (
                "I couldn't capture or "
                "analyze the screen."
            )

        # ==================================================
        # NOT FOUND
        # ==================================================

        if (
            visual_target
            is None
        ):
            return (
                f"I couldn't confidently locate "
                f"'{target}' on the screen."
            )

        # ==================================================
        # VISION RESULT
        # ==================================================

        return (
            f"I found '{visual_target.label}' "
            f"near screen position "
            f"({visual_target.screen_x}, "
            f"{visual_target.screen_y}) "
            f"with "
            f"{visual_target.confidence:.0%} "
            f"confidence using the "
            f"{visual_target.region_name} "
            "screen region. "
            "No click was performed."
        )

    # ==================================================
    # LOCATE TARGET USING VISION
    # ==================================================

    def _locate_target(
        self,
        target: str,
        capture: ScreenCapture,
    ) -> VisualTarget | None:
        region_description = (
            capture
            .region_name
            .replace(
                "_",
                " ",
            )
        )

        target_json = (
            json.dumps(
                target,
                ensure_ascii=False,
            )
        )

        prompt = f"""
Look carefully at the supplied screenshot.

Find this visible target:

TARGET:
{target}

The supplied image represents the
{region_description} region of the user's screen.

Return ONLY one JSON object.

If the target is clearly visible, return:

{{
  "found": true,
  "label": {target_json},
  "x": 500,
  "y": 500,
  "confidence": 0.90
}}

Coordinate rules:

- x and y are normalized integers from 0 to 1000.
- x=0 is the left edge of THIS supplied image.
- x=1000 is the right edge of THIS supplied image.
- y=0 is the top edge of THIS supplied image.
- y=1000 is the bottom edge of THIS supplied image.
- Return the CENTER point of the requested target.
- Coordinates must be relative to this supplied image.
- If this image is a cropped region, coordinates must
  be relative to that cropped region.

If the target is not clearly visible, return:

{{
  "found": false,
  "label": "",
  "x": 0,
  "y": 0,
  "confidence": 0.0
}}

Rules:

- Inspect the supplied image carefully.
- Locate only something actually visible.
- Do not invent hidden controls.
- Do not substitute a different UI element.
- Small title-bar controls, buttons and icons count
  as visible targets.
- If multiple plausible matches exist and the intended
  target cannot be determined, return found=false.
- confidence must be between 0.0 and 1.0.
- Do not describe the screenshot.
- Do not explain your reasoning.
- Do not include Markdown.
- Return JSON only.
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
                                capture.image_data
                            ],
                        }
                    ],

                    "stream":
                        False,

                    "format":
                        "json",

                    "options": {
                        "temperature":
                            0.0,
                    },
                },
                timeout=90.0,
            )
        )

        response.raise_for_status()

        payload = (
            response.json()
        )

        message = (
            payload.get(
                "message",
                {}
            )
        )

        content = (
            str(
                message.get(
                    "content",
                    "",
                )
            )
            .strip()
        )

        if not (
            content
        ):
            raise ValueError(
                "Vision model returned "
                "an empty response."
            )

        result = (
            self._parse_json(
                content
            )
        )

        if (
            result.get(
                "found"
            )
            is not True
        ):
            return None

        label = (
            str(
                result.get(
                    "label",
                    target,
                )
            )
            .strip()
        )

        if not (
            label
        ):
            label = (
                target
            )

        x = (
            self._read_coordinate(
                result=result,
                key="x",
            )
        )

        y = (
            self._read_coordinate(
                result=result,
                key="y",
            )
        )

        confidence = (
            self._read_confidence(
                result
            )
        )

        if (
            confidence
            < self.MIN_CONFIDENCE
        ):
            return None

        screen_x, screen_y = (
            screen_capture_service
            .normalized_to_screen(
                capture=capture,
                x=x,
                y=y,
            )
        )

        return (
            VisualTarget(
                label=label,

                normalized_x=x,
                normalized_y=y,

                screen_x=screen_x,
                screen_y=screen_y,

                confidence=confidence,

                region_name=(
                    capture.region_name
                ),
            )
        )

    # ==================================================
    # PARSE JSON
    # ==================================================

    def _parse_json(
        self,
        content: str,
    ) -> dict[
        str,
        object,
    ]:
        clean = (
            content
            .strip()
        )

        # A model can occasionally ignore the JSON-only
        # instruction and wrap its result in a Markdown
        # code fence.
        if (
            clean.startswith(
                "```"
            )
        ):
            clean = re.sub(
                r"^```(?:json)?\s*",
                "",
                clean,
                flags=re.IGNORECASE,
            )

            clean = re.sub(
                r"\s*```$",
                "",
                clean,
            )

        parsed = (
            json.loads(
                clean
            )
        )

        if not isinstance(
            parsed,
            dict,
        ):
            raise ValueError(
                "Visual grounding response "
                "was not a JSON object."
            )

        return (
            parsed
        )

    # ==================================================
    # READ COORDINATE
    # ==================================================

    def _read_coordinate(
        self,
        result: dict[
            str,
            object,
        ],
        key: str,
    ) -> int:
        raw_value = (
            result.get(
                key
            )
        )

        if isinstance(
            raw_value,
            bool,
        ):
            raise ValueError(
                f"Invalid {key} coordinate."
            )

        if not isinstance(
            raw_value,
            (
                int,
                float,
            ),
        ):
            raise ValueError(
                f"Missing or invalid "
                f"{key} coordinate."
            )

        value = (
            round(
                float(
                    raw_value
                )
            )
        )

        if not (
            0
            <= value
            <= 1000
        ):
            raise ValueError(
                f"{key} coordinate "
                "is outside the allowed range."
            )

        return (
            value
        )

    # ==================================================
    # READ CONFIDENCE
    # ==================================================

    def _read_confidence(
        self,
        result: dict[
            str,
            object,
        ],
    ) -> float:
        raw_value = (
            result.get(
                "confidence"
            )
        )

        if isinstance(
            raw_value,
            bool,
        ):
            raise ValueError(
                "Invalid confidence value."
            )

        if not isinstance(
            raw_value,
            (
                int,
                float,
            ),
        ):
            raise ValueError(
                "Missing confidence value."
            )

        value = (
            float(
                raw_value
            )
        )

        if not (
            0.0
            <= value
            <= 1.0
        ):
            raise ValueError(
                "Confidence is outside "
                "the allowed range."
            )

        return (
            value
        )

    # ==================================================
    # INFER FOCUSED REGION
    # ==================================================

    def _infer_focus_region(
        self,
        target: str,
    ) -> str | None:
        normalized = (
            " ".join(
                target
                .strip()
                .lower()
                .replace(
                    "-",
                    " ",
                )
                .split()
            )
        )

        # ==============================================
        # EXPLICIT POSITION WORDING
        # ==============================================

        explicit_regions = (
            (
                (
                    "top right",
                    "upper right",
                ),
                "top_right",
            ),

            (
                (
                    "top left",
                    "upper left",
                ),
                "top_left",
            ),

            (
                (
                    "bottom right",
                    "lower right",
                ),
                "bottom_right",
            ),

            (
                (
                    "bottom left",
                    "lower left",
                ),
                "bottom_left",
            ),

            (
                (
                    "at the top",
                    "near the top",
                ),
                "top",
            ),

            (
                (
                    "at the bottom",
                    "near the bottom",
                ),
                "bottom",
            ),

            (
                (
                    "on the left",
                    "left side",
                ),
                "left",
            ),

            (
                (
                    "on the right",
                    "right side",
                ),
                "right",
            ),

            (
                (
                    "in the center",
                    "in the middle",
                    "center of",
                    "middle of",
                ),
                "center",
            ),
        )

        for (
            phrases,
            region,
        ) in explicit_regions:
            if any(
                phrase
                in normalized

                for phrase
                in phrases
            ):
                return (
                    region
                )

        # ==============================================
        # WINDOWS TITLE-BAR CONTROLS
        # ==============================================

        if any(
            phrase
            in normalized

            for phrase
            in (
                "close button",
                "close icon",
                "minimize button",
                "minimise button",
                "maximize button",
                "maximise button",
                "restore button",
                "window controls",
            )
        ):
            return (
                "top_right"
            )

        # ==============================================
        # WINDOWS START
        # ==============================================

        if any(
            phrase
            in normalized

            for phrase
            in (
                "start button",
                "windows button",
                "windows icon",
            )
        ):
            return (
                "bottom_left"
            )

        # ==============================================
        # SYSTEM TRAY
        # ==============================================

        if any(
            phrase
            in normalized

            for phrase
            in (
                "system tray",
                "notification area",
                "clock in taskbar",
            )
        ):
            return (
                "bottom_right"
            )

        # ==============================================
        # TASKBAR
        # ==============================================

        if (
            "taskbar"
            in normalized
        ):
            return (
                "bottom"
            )

        return None

    # ==================================================
    # CLEAN TARGET PHRASE
    # ==================================================

    def _clean_target_phrase(
        self,
        target: str,
    ) -> str:
        clean = (
            " ".join(
                target
                .strip()
                .split()
            )
        )

        lowered = (
            clean.lower()
        )

        for article in (
            "the ",
            "a ",
            "an ",
        ):
            if (
                lowered.startswith(
                    article
                )
            ):
                clean = (
                    clean[
                        len(
                            article
                        ):
                    ]
                    .strip()
                )

                break

        return (
            clean
        )

    # ==================================================
    # TARGET EXTRACTION
    # ==================================================

    def _extract_target(
        self,
        command: str,
    ) -> str | None:
        clean_command = (
            command
            .strip()
        )

        for pattern in (
            self.WHERE_PATTERN,
            self.LOCATE_PATTERN,
        ):
            match = (
                pattern.match(
                    clean_command
                )
            )

            if (
                match
                is None
            ):
                continue

            target = (
                match
                .group(
                    1
                )
                .strip()
                .rstrip(
                    ".!?"
                )
            )

            if (
                target
            ):
                return (
                    target
                )

        return None