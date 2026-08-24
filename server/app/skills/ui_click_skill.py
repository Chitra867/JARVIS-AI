import re
import secrets
import time

from dataclasses import (
    dataclass,
)

import pyautogui
import win32gui

from app.core.ui_automation import (
    UIAutomationResolution,
    UIAutomationTarget,
    ui_automation_service,
)

from app.skills.base import (
    Skill,
)


# ======================================================
# PENDING SENSITIVE CLICK
# ======================================================


@dataclass(
    frozen=True
)
class PendingUIClick:
    query: str

    original_target: UIAutomationTarget

    confirmation_token: str

    created_at: float

    foreground_hwnd: int


# ======================================================
# UI AUTOMATION CLICK SKILL
# ======================================================


class UIAutomationClickSkill(
    Skill
):
    # Small delay between the first resolution and the
    # final pre-click verification.
    REVALIDATION_DELAY_SECONDS = 0.05

    # Bounded retry is intentionally conservative.
    #
    # Only a temporary "not_found" result is retried.
    # Ambiguous/error results still fail closed
    # immediately.
    RESOLUTION_RETRY_ATTEMPTS = 3
    RESOLUTION_RETRY_DELAY_SECONDS = 0.10

    # Maximum allowed movement of a target between two
    # immediate UIA resolutions.
    MAX_POSITION_DRIFT = 8

    # Sensitive confirmations automatically expire.
    CONFIRMATION_TTL_SECONDS = 30.0

    # ==================================================
    # SENSITIVE / CONSEQUENTIAL ACTION TERMS
    # ==================================================

    SENSITIVE_TERMS = (
        # Destructive data actions
        "delete",
        "remove",
        "erase",
        "format",
        "reset",
        "factory reset",
        "overwrite",
        "replace",

        # Software / system changes
        "install",
        "uninstall",
        "disable",
        "shutdown",
        "restart",
        "terminate",
        "kill",

        # Financial actions
        "purchase",
        "buy",
        "pay",
        "checkout",
        "place order",

        # External communication
        "send",
        "submit",
        "publish",
        "post",
        "upload",
        "share",

        # Authorization
        "confirm",
        "approve",
        "authorize",
        "allow",
        "grant",
        "accept",
        "yes",

        # Session/window termination
        "close",
        "exit",
        "quit",
        "sign out",
        "log out",
    )

    # ==================================================
    # COMMAND PATTERNS
    # ==================================================

    CLICK_PATTERN = re.compile(
        (
            r"^(?:click|left\s+click)\s+"
            r"(.+?)"
            r"(?:\s+on\s+(?:my|the)\s+screen)?"
            r"\s*[.!?]*$"
        ),
        flags=re.IGNORECASE,
    )

    CONFIRM_PATTERN = re.compile(
        (
            r"^confirm\s+"
            r"(?:ui\s+)?"
            r"click\s+"
            r"([a-f0-9]{6})"
            r"\s*[.!?]*$"
        ),
        flags=re.IGNORECASE,
    )

    CANCEL_PATTERN = re.compile(
        (
            r"^cancel\s+"
            r"(?:ui\s+)?"
            r"click"
            r"\s*[.!?]*$"
        ),
        flags=re.IGNORECASE,
    )

    # ==================================================
    # INIT
    # ==================================================

    def __init__(
        self,
    ) -> None:
        self._pending_confirmation: (
            PendingUIClick
            | None
        ) = None

    # ==================================================
    # ROUTING
    # ==================================================

    def can_handle(
        self,
        command: str,
    ) -> bool:
        clean_command = (
            command
            .strip()
        )

        if (
            self.CONFIRM_PATTERN
            .match(
                clean_command
            )
            is not None
        ):
            return True

        if (
            self.CANCEL_PATTERN
            .match(
                clean_command
            )
            is not None
        ):
            return True

        return (
            self._extract_target(
                clean_command
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
        clean_command = (
            command
            .strip()
        )

        # ==============================================
        # CONFIRM PENDING SENSITIVE CLICK
        # ==============================================

        confirmation_match = (
            self.CONFIRM_PATTERN
            .match(
                clean_command
            )
        )

        if (
            confirmation_match
            is not None
        ):
            return (
                self._handle_confirmation(
                    confirmation_match
                    .group(
                        1
                    )
                )
            )

        # ==============================================
        # CANCEL PENDING CLICK
        # ==============================================

        if (
            self.CANCEL_PATTERN
            .match(
                clean_command
            )
            is not None
        ):
            return (
                self._handle_cancel()
            )

        # ==============================================
        # NORMAL TARGETED CLICK
        # ==============================================

        target_query = (
            self._extract_target(
                clean_command
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

        return (
            self._handle_click_request(
                target_query
            )
        )

    # ==================================================
    # HANDLE CLICK REQUEST
    # ==================================================

    def _handle_click_request(
        self,
        target_query: str,
    ) -> str:
        target_query = (
            self._clean_target_phrase(
                target_query
            )
        )

        # A new targeted click invalidates any previous
        # pending sensitive confirmation.
        self._pending_confirmation = (
            None
        )

        # ==============================================
        # FOREGROUND WINDOW SNAPSHOT
        # ==============================================

        foreground_hwnd = (
            self._foreground_window_handle()
        )

        if not (
            foreground_hwnd
        ):
            return (
                "I couldn't determine the active "
                "window. "
                "No click was performed."
            )

        # ==============================================
        # INITIAL TARGET RESOLUTION
        # ==============================================

        (
            resolution,
            retry_failure,
        ) = (
            self._resolve_with_bounded_retry(
                query=target_query,
                expected_hwnd=(
                    foreground_hwnd
                ),
            )
        )

        if (
            retry_failure
            is not None
        ):
            return (
                retry_failure
            )

        blocked_response = (
            self._resolution_failure_message(
                query=target_query,
                resolution=resolution,
            )
        )

        if (
            blocked_response
            is not None
        ):
            return (
                blocked_response
            )

        target = (
            resolution.target
        )

        if (
            target
            is None
        ):
            return (
                "I couldn't safely resolve "
                f"'{target_query}'. "
                "No click was performed."
            )

        if not (
            self._target_is_actionable(
                target
            )
        ):
            return (
                f"I found '{target.name}', "
                "but the control is not currently "
                "safe to click. "
                "No click was performed."
            )

        # ==============================================
        # SENSITIVE TARGET
        # ==============================================

        if (
            self._requires_confirmation(
                query=target_query,
                target=target,
            )
        ):
            confirmation_token = (
                secrets.token_hex(
                    3
                )
            )

            self._pending_confirmation = (
                PendingUIClick(
                    query=(
                        target_query
                    ),

                    original_target=(
                        target
                    ),

                    confirmation_token=(
                        confirmation_token
                    ),

                    created_at=(
                        time.monotonic()
                    ),

                    foreground_hwnd=(
                        foreground_hwnd
                    ),
                )
            )

            return (
                f"'{target.name}' may perform a "
                "sensitive or destructive action. "
                "No click was performed. "
                "To proceed, send exactly: "
                f"confirm click "
                f"{confirmation_token}"
            )

        # ==============================================
        # ORDINARY GUARDED CLICK
        # ==============================================

        return (
            self._revalidate_and_click(
                query=target_query,
                first_target=target,
                expected_hwnd=(
                    foreground_hwnd
                ),
            )
        )

    # ==================================================
    # HANDLE CONFIRMATION
    # ==================================================

    def _handle_confirmation(
        self,
        supplied_token: str,
    ) -> str:
        pending = (
            self._pending_confirmation
        )

        if (
            pending
            is None
        ):
            return (
                "There is no pending sensitive "
                "UI click to confirm."
            )

        # ==============================================
        # EXPIRATION
        # ==============================================

        age = (
            time.monotonic()
            - pending.created_at
        )

        if (
            age
            > self.CONFIRMATION_TTL_SECONDS
        ):
            self._pending_confirmation = (
                None
            )

            return (
                "The UI click confirmation "
                "expired. "
                "Please request the action again."
            )

        # ==============================================
        # TOKEN CHECK
        # ==============================================

        if not (
            secrets.compare_digest(
                supplied_token.lower(),
                pending
                .confirmation_token
                .lower(),
            )
        ):
            # Invalid confirmation destroys the pending
            # token so repeated guessing cannot occur.
            self._pending_confirmation = (
                None
            )

            return (
                "That confirmation token does "
                "not match the pending UI action. "
                "The pending confirmation was "
                "cleared. "
                "No click was performed."
            )

        # ==============================================
        # FOREGROUND WINDOW CHECK
        # ==============================================

        if (
            self._foreground_window_handle()
            != pending.foreground_hwnd
        ):
            self._pending_confirmation = (
                None
            )

            return (
                "The active window changed after "
                "the sensitive action was requested. "
                "Please request the action again. "
                "No click was performed."
            )

        # Consume the valid token BEFORE attempting the
        # action. The token can therefore never be
        # replayed.
        self._pending_confirmation = (
            None
        )

        # ==============================================
        # RE-RESOLVE AFTER CONFIRMATION
        # ==============================================

        try:
            current_resolution = (
                self._resolve(
                    pending.query
                )
            )

        except Exception as error:
            print(
                (
                    "Confirmed UI target resolution "
                    "failed: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

            return (
                "The target could not be safely "
                "resolved again. "
                "No click was performed."
            )

        if (
            self._foreground_window_handle()
            != pending.foreground_hwnd
        ):
            return (
                "The active window changed while "
                "the confirmed target was being "
                "verified. "
                "No click was performed."
            )

        blocked_response = (
            self._resolution_failure_message(
                query=pending.query,
                resolution=(
                    current_resolution
                ),
            )
        )

        if (
            blocked_response
            is not None
        ):
            return (
                "The confirmed target could not "
                "be safely resolved again. "
                f"{blocked_response}"
            )

        current_target = (
            current_resolution.target
        )

        if (
            current_target
            is None
        ):
            return (
                "The target disappeared before "
                "the confirmed action could run. "
                "No click was performed."
            )

        if not (
            self._target_is_actionable(
                current_target
            )
        ):
            return (
                f"'{current_target.name}' is no "
                "longer visible or enabled. "
                "No click was performed."
            )

        # For sensitive actions, even after explicit
        # confirmation, require the control to remain the
        # same target at essentially the same position.
        #
        # If it moved significantly, fail closed and ask
        # the user to request the action again.
        if not (
            self._same_target(
                pending.original_target,
                current_target,
            )
        ):
            return (
                "The confirmed control changed "
                "identity or position after the "
                "request. "
                "Please request the action again. "
                "No click was performed."
            )

        # ==============================================
        # FINAL IMMEDIATE REVALIDATION
        # ==============================================

        return (
            self._revalidate_and_click(
                query=pending.query,
                first_target=(
                    current_target
                ),
                expected_hwnd=(
                    pending
                    .foreground_hwnd
                ),
            )
        )

    # ==================================================
    # CANCEL
    # ==================================================

    def _handle_cancel(
        self,
    ) -> str:
        if (
            self._pending_confirmation
            is None
        ):
            return (
                "There is no pending UI click "
                "to cancel."
            )

        self._pending_confirmation = (
            None
        )

        return (
            "Pending UI click cancelled."
        )

    # ==================================================
    # REVALIDATE AND CLICK
    # ==================================================

    def _revalidate_and_click(
        self,
        query: str,
        first_target: UIAutomationTarget,
        expected_hwnd: int,
    ) -> str:
        # ==============================================
        # WINDOW CHECK BEFORE DELAY
        # ==============================================

        if (
            self._foreground_window_handle()
            != expected_hwnd
        ):
            return (
                "The active window changed before "
                "the target could be clicked. "
                "No click was performed."
            )

        time.sleep(
            self.REVALIDATION_DELAY_SECONDS
        )

        # ==============================================
        # WINDOW CHECK BEFORE SECOND RESOLUTION
        # ==============================================

        if (
            self._foreground_window_handle()
            != expected_hwnd
        ):
            return (
                "The active window changed before "
                "the target could be revalidated. "
                "No click was performed."
            )

        (
            second_resolution,
            retry_failure,
        ) = (
            self._resolve_with_bounded_retry(
                query=query,
                expected_hwnd=(
                    expected_hwnd
                ),
            )
        )

        if (
            retry_failure
            is not None
        ):
            return (
                retry_failure
            )

        blocked_response = (
            self._resolution_failure_message(
                query=query,
                resolution=(
                    second_resolution
                ),
            )
        )

        if (
            blocked_response
            is not None
        ):
            return (
                "The screen changed before I "
                "could safely click the target. "
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
                f"'{second_target.name}' is no "
                "longer visible or enabled. "
                "No click was performed."
            )

        # ==============================================
        # TARGET IDENTITY + POSITION STABILITY
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
        # RECTANGLE VALIDATION
        # ==============================================

        if not (
            self._valid_target_rectangle(
                second_target
            )
        ):
            return (
                "The resolved control has an "
                "invalid screen rectangle. "
                "No click was performed."
            )

        click_x = (
            second_target.center_x
        )

        click_y = (
            second_target.center_y
        )

        # ==============================================
        # FINAL WINDOW CHECK
        # ==============================================

        if (
            self._foreground_window_handle()
            != expected_hwnd
        ):
            return (
                "The active window changed at the "
                "final safety check. "
                "No click was performed."
            )

        # ==============================================
        # GUARDED CLICK
        # ==============================================

        try:
            pyautogui.FAILSAFE = (
                True
            )

            pyautogui.PAUSE = (
                0.05
            )

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
    # BOUNDED SAFE RESOLUTION RETRY
    # ==================================================

    def _resolve_with_bounded_retry(
        self,
        *,
        query: str,
        expected_hwnd: int,
    ) -> tuple[
        UIAutomationResolution,
        str | None,
    ]:
        """
        Resolve a target with a small bounded retry window.

        Safety rules:
        - retry only when UIA reports ``not_found``;
        - ambiguity is never retried or auto-selected;
        - UIA errors fail closed immediately;
        - the foreground HWND must remain unchanged;
        - no coordinates are used for recovery or guessing.
        """

        attempts = max(
            1,
            int(
                self.RESOLUTION_RETRY_ATTEMPTS
            ),
        )

        last_resolution: (
            UIAutomationResolution
            | None
        ) = None

        for attempt in range(
            attempts
        ):
            if (
                self._foreground_window_handle()
                != expected_hwnd
            ):
                return (
                    self._not_found_resolution(
                        query
                    ),
                    (
                        "The active window changed "
                        "while I was locating the "
                        "target. "
                        "No click was performed."
                    ),
                )

            try:
                resolution = (
                    self._resolve(
                        query
                    )
                )

            except Exception as error:
                print(
                    (
                        "UI click target resolution "
                        "failed: "
                        f"{type(error).__name__}: "
                        f"{error}"
                    )
                )

                return (
                    self._not_found_resolution(
                        query
                    ),
                    (
                        "Windows UI Automation could "
                        "not safely resolve that "
                        "target. "
                        "No click was performed."
                    ),
                )

            if (
                self._foreground_window_handle()
                != expected_hwnd
            ):
                return (
                    resolution,
                    (
                        "The active window changed "
                        "while I was locating the "
                        "target. "
                        "No click was performed."
                    ),
                )

            last_resolution = (
                resolution
            )

            # Resolved, ambiguous, and error results are
            # final. Only a transient not_found state is
            # eligible for another attempt.
            if (
                resolution.status
                != "not_found"
            ):
                return (
                    resolution,
                    None,
                )

            if (
                attempt
                >= (
                    attempts
                    - 1
                )
            ):
                break

            time.sleep(
                self.RESOLUTION_RETRY_DELAY_SECONDS
            )

        if (
            last_resolution
            is None
        ):
            last_resolution = (
                self._not_found_resolution(
                    query
                )
            )

        return (
            last_resolution,
            None,
        )

    # ==================================================
    # SYNTHETIC NOT-FOUND RESULT
    # ==================================================

    def _not_found_resolution(
        self,
        query: str,
    ) -> UIAutomationResolution:
        return (
            UIAutomationResolution(
                query=query,
                status="not_found",
                target=None,
                candidates=(),
                reason=(
                    "The target could not be "
                    "safely resolved."
                ),
            )
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
    # RESOLUTION FAILURE MESSAGE
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
                "I couldn't find a unique visible "
                "UI Automation target for "
                f"'{query}'. "
                "No click was performed."
            )

        # ==============================================
        # ERROR
        # ==============================================

        return (
            "Windows UI Automation could not "
            "safely resolve that target. "
            "No click was performed."
        )

    # ==================================================
    # RISK CLASSIFICATION
    # ==================================================

    def _requires_confirmation(
        self,
        query: str,
        target: UIAutomationTarget,
    ) -> bool:
        combined = (
            self._normalize(
                (
                    f"{query} "
                    f"{target.name}"
                )
            )
        )

        for term in (
            self.SENSITIVE_TERMS
        ):
            if (
                self._contains_phrase(
                    text=combined,
                    phrase=term,
                )
            ):
                return True

        return False

    # ==================================================
    # PHRASE MATCHING
    # ==================================================

    def _contains_phrase(
        self,
        text: str,
        phrase: str,
    ) -> bool:
        normalized_phrase = (
            self._normalize(
                phrase
            )
        )

        if not (
            normalized_phrase
        ):
            return False

        escaped = (
            re.escape(
                normalized_phrase
            )
        )

        pattern = (
            rf"(?<!\w)"
            rf"{escaped}"
            rf"(?!\w)"
        )

        return (
            re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
            is not None
        )

    # ==================================================
    # ACTIONABLE TARGET
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
    # SAME IDENTITY
    # ==================================================

    def _same_identity(
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

        # If both UIA elements expose automation IDs,
        # require those IDs to remain identical.
        if (
            first.automation_id
            and
            second.automation_id
            and
            first.automation_id
            != second.automation_id
        ):
            return False

        return True

    # ==================================================
    # SAME TARGET + POSITION
    # ==================================================

    def _same_target(
        self,
        first: UIAutomationTarget,
        second: UIAutomationTarget,
    ) -> bool:
        if not (
            self._same_identity(
                first,
                second,
            )
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
    # FOREGROUND WINDOW
    # ==================================================

    def _foreground_window_handle(
        self,
    ) -> int:
        try:
            return int(
                win32gui
                .GetForegroundWindow()
            )

        except Exception:
            return 0

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
            match
            .group(
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