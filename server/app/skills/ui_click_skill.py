import re
import time

import pyautogui

from app.core.ui_automation import (
    UIAutomationResolution,
    UIAutomationTarget,
    ui_automation_service,
)

from app.skills.base import (
    Skill,
)


class UIAutomationClickSkill(
    Skill
):
    # Small delay between the initial resolution and
    # final pre-click verification.
    REVALIDATION_DELAY_SECONDS = 0.05

    # Small movement tolerance is allowed in case the
    # application shifts a control by a few pixels.
    MAX_POSITION_DRIFT = 8

    CLICK_PATTERN = re.compile(
        (
            r"^(?:click|left\s+click)\s+"
            r"(.+?)"
            r"(?:\s+on\s+(?:my|the)\s+screen)?"
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
        return (
            self._extract_target(
                command
            )
            is not None
        )

    # ==================================================
    # EXECUTE
    # ==================================================

    def execute(
        self,
        command: str,
    ) -> str:
        target_query = (
            self._extract_target(
                command
            )
        )

        if (
            target_query
            is None
        ):
            return (
                "Tell me which visible "
                "screen control to click."
            )

        target_query = (
            self._clean_target_phrase(
                target_query
            )
        )

        # ==============================================
        # RESOLUTION 1
        # ==============================================

        first_resolution = (
            self._resolve(
                target_query
            )
        )

        blocked_response = (
            self._resolution_failure_message(
                target_query,
                first_resolution,
            )
        )

        if (
            blocked_response
            is not None
        ):
            return (
                blocked_response
            )

        first_target = (
            first_resolution.target
        )

        if (
            first_target
            is None
        ):
            return (
                "I couldn't safely resolve "
                f"'{target_query}'. "
                "No click was performed."
            )

        if not (
            self._target_is_actionable(
                first_target
            )
        ):
            return (
                f"I found '{first_target.name}', "
                "but the control is not currently "
                "safe to click. "
                "No click was performed."
            )

        # ==============================================
        # REVALIDATION
        # ==============================================
        #
        # The UI may change between detection and action.
        # Resolve the target again immediately before
        # clicking.
        # ==============================================

        time.sleep(
            self.REVALIDATION_DELAY_SECONDS
        )

        second_resolution = (
            self._resolve(
                target_query
            )
        )

        blocked_response = (
            self._resolution_failure_message(
                target_query,
                second_resolution,
            )
        )

        if (
            blocked_response
            is not None
        ):
            return (
                "The screen changed before I could "
                "safely click the target. "
                f"{blocked_response}"
            )

        second_target = (
            second_resolution.target
        )

        if (
            second_target
            is None
        ):
            return (
                "The target disappeared before "
                "the click could be verified. "
                "No click was performed."
            )

        if not (
            self._target_is_actionable(
                second_target
            )
        ):
            return (
                f"'{second_target.name}' is no longer "
                "visible or enabled. "
                "No click was performed."
            )

        # ==============================================
        # TARGET STABILITY
        # ==============================================

        if not (
            self._same_target(
                first_target,
                second_target,
            )
        ):
            return (
                "The target changed position or "
                "identity before the action could "
                "be verified. "
                "No click was performed."
            )

        # ==============================================
        # FINAL COORDINATE VALIDATION
        # ==============================================

        if not (
            self._valid_target_rectangle(
                second_target
            )
        ):
            return (
                "The resolved control has an invalid "
                "screen rectangle. "
                "No click was performed."
            )

        click_x = (
            second_target.center_x
        )

        click_y = (
            second_target.center_y
        )

        # ==============================================
        # GUARDED CLICK
        # ==============================================

        try:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.05

            pyautogui.click(
                x=click_x,
                y=click_y,
                button="left",
            )

        except (
            pyautogui.FailSafeException
        ):
            return (
                "Mouse fail-safe was triggered. "
                "The click was cancelled."
            )

        except Exception as error:
            print(
                (
                    "Guarded UI click failed: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

            return (
                "I couldn't safely complete "
                "the click."
            )

        return (
            f"Clicked '{second_target.name}' "
            f"({second_target.control_type}) "
            f"at screen position "
            f"({click_x}, {click_y}) "
            "after UI Automation verification."
        )

    # ==================================================
    # RESOLVE
    # ==================================================

    def _resolve(
        self,
        query: str,
    ) -> UIAutomationResolution:
        return (
            ui_automation_service
            .resolve_target(
                query
            )
        )

    # ==================================================
    # FAILURE MESSAGE
    # ==================================================

    def _resolution_failure_message(
        self,
        query: str,
        resolution: UIAutomationResolution,
    ) -> str | None:
        if (
            resolution.resolved
        ):
            return None

        # ==============================================
        # AMBIGUOUS
        # ==============================================

        if (
            resolution.ambiguous
        ):
            descriptions: list[
                str
            ] = []

            for candidate in (
                resolution
                .candidates[:5]
            ):
                descriptions.append(
                    (
                        f"{candidate.name} "
                        f"({candidate.control_type})"
                    )
                )

            if (
                descriptions
            ):
                candidates_text = (
                    "; ".join(
                        descriptions
                    )
                )

                return (
                    f"I found multiple possible "
                    f"matches for '{query}': "
                    f"{candidates_text}. "
                    "Please specify the exact "
                    "control. "
                    "No click was performed."
                )

            return (
                f"'{query}' is ambiguous. "
                "Please specify the exact control. "
                "No click was performed."
            )

        # ==============================================
        # NOT FOUND
        # ==============================================

        if (
            resolution.status
            == "not_found"
        ):
            return (
                f"I couldn't find a unique visible "
                f"UI Automation target for "
                f"'{query}'. "
                "No click was performed."
            )

        # ==============================================
        # ERROR
        # ==============================================

        return (
            "Windows UI Automation could not safely "
            "resolve that target. "
            "No click was performed."
        )

    # ==================================================
    # ACTIONABLE
    # ==================================================

    def _target_is_actionable(
        self,
        target: UIAutomationTarget,
    ) -> bool:
        if not (
            target.visible
        ):
            return False

        if not (
            target.enabled
        ):
            return False

        return (
            self._valid_target_rectangle(
                target
            )
        )

    # ==================================================
    # RECTANGLE VALIDATION
    # ==================================================

    def _valid_target_rectangle(
        self,
        target: UIAutomationTarget,
    ) -> bool:
        if (
            target.right
            <= target.left
        ):
            return False

        if (
            target.bottom
            <= target.top
        ):
            return False

        if not (
            target.left
            <= target.center_x
            < target.right
        ):
            return False

        if not (
            target.top
            <= target.center_y
            < target.bottom
        ):
            return False

        return True

    # ==================================================
    # SAME TARGET
    # ==================================================

    def _same_target(
        self,
        first: UIAutomationTarget,
        second: UIAutomationTarget,
    ) -> bool:
        if (
            self._normalize(
                first.name
            )
            !=
            self._normalize(
                second.name
            )
        ):
            return False

        if (
            first.control_type
            != second.control_type
        ):
            return False

        # If both controls provide automation IDs,
        # they must agree.
        if (
            first.automation_id
            and
            second.automation_id
            and
            first.automation_id
            != second.automation_id
        ):
            return False

        x_drift = abs(
            first.center_x
            - second.center_x
        )

        y_drift = abs(
            first.center_y
            - second.center_y
        )

        if (
            x_drift
            > self.MAX_POSITION_DRIFT
        ):
            return False

        if (
            y_drift
            > self.MAX_POSITION_DRIFT
        ):
            return False

        return True

    # ==================================================
    # TARGET EXTRACTION
    # ==================================================

    def _extract_target(
        self,
        command: str,
    ) -> str | None:
        match = (
            self.CLICK_PATTERN
            .match(
                command.strip()
            )
        )

        if (
            match
            is None
        ):
            return None

        target = (
            match.group(
                1
            )
            .strip()
            .rstrip(
                ".!?"
            )
        )

        if not (
            target
        ):
            return None

        return (
            target
        )

    # ==================================================
    # CLEAN TARGET
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
    # NORMALIZE
    # ==================================================

    def _normalize(
        self,
        text: str,
    ) -> str:
        return (
            " ".join(
                text
                .strip()
                .lower()
                .replace(
                    "-",
                    " ",
                )
                .replace(
                    "_",
                    " ",
                )
                .split()
            )
        )