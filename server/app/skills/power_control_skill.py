import ctypes
import platform
import subprocess
import time

from dataclasses import (
    dataclass,
)

from threading import (
    RLock,
)

from app.skills.base import (
    Skill,
)


@dataclass(
    frozen=True
)
class PendingPowerAction:
    action: str
    expires_at: float


class PowerControlSkill(
    Skill
):
    CONFIRMATION_SECONDS = 30.0

    ACTION_COMMANDS = {
        "shutdown":
            "shutdown",

        "shutdown computer":
            "shutdown",

        "shutdown pc":
            "shutdown",

        "shutdown my computer":
            "shutdown",

        "shutdown my pc":
            "shutdown",

        "restart":
            "restart",

        "restart computer":
            "restart",

        "restart pc":
            "restart",

        "restart my computer":
            "restart",

        "restart my pc":
            "restart",

        "reboot":
            "restart",

        "reboot computer":
            "restart",

        "reboot pc":
            "restart",

        "sleep":
            "sleep",

        "sleep computer":
            "sleep",

        "sleep pc":
            "sleep",

        "sleep my computer":
            "sleep",

        "sleep my pc":
            "sleep",
    }

    CONFIRM_COMMANDS = {
        "confirm shutdown":
            "shutdown",

        "confirm restart":
            "restart",

        "confirm reboot":
            "restart",

        "confirm sleep":
            "sleep",
    }

    CANCEL_COMMANDS = {
        "cancel shutdown",
        "cancel restart",
        "cancel reboot",
        "cancel sleep",
        "cancel power action",
    }

    def __init__(
        self,
    ) -> None:
        self._pending: (
            PendingPowerAction
            | None
        ) = None

        self._lock = (
            RLock()
        )

    # ==================================================
    # ROUTING
    # ==================================================

    def can_handle(
        self,
        command: str,
    ) -> bool:
        normalized = (
            self._normalize(
                command
            )
        )

        return (
            normalized
            in self.ACTION_COMMANDS

            or normalized
            in self.CONFIRM_COMMANDS

            or normalized
            in self.CANCEL_COMMANDS
        )

    # ==================================================
    # EXECUTE
    # ==================================================

    def execute(
        self,
        command: str,
    ) -> str:
        normalized = (
            self._normalize(
                command
            )
        )

        # ==============================================
        # CANCEL
        # ==============================================

        if (
            normalized
            in self.CANCEL_COMMANDS
        ):
            return (
                self._cancel_pending()
            )

        # ==============================================
        # CONFIRM
        # ==============================================

        confirmed_action = (
            self.CONFIRM_COMMANDS
            .get(
                normalized
            )
        )

        if (
            confirmed_action
            is not None
        ):
            return (
                self._confirm_action(
                    confirmed_action
                )
            )

        # ==============================================
        # REQUEST ACTION
        # ==============================================

        requested_action = (
            self.ACTION_COMMANDS
            .get(
                normalized
            )
        )

        if (
            requested_action
            is not None
        ):
            return (
                self._request_confirmation(
                    requested_action
                )
            )

        return (
            "I couldn't understand "
            "that power command."
        )

    # ==================================================
    # REQUEST CONFIRMATION
    # ==================================================

    def _request_confirmation(
        self,
        action: str,
    ) -> str:
        expires_at = (
            time.monotonic()
            + self.CONFIRMATION_SECONDS
        )

        with self._lock:
            self._pending = (
                PendingPowerAction(
                    action=action,
                    expires_at=(
                        expires_at
                    ),
                )
            )

        return (
            f"{action.capitalize()} requires "
            f"confirmation. Say "
            f"'confirm {action}' within "
            f"{int(self.CONFIRMATION_SECONDS)} "
            f"seconds."
        )

    # ==================================================
    # CONFIRM
    # ==================================================

    def _confirm_action(
        self,
        action: str,
    ) -> str:
        with self._lock:
            pending = (
                self._pending
            )

            if (
                pending
                is None
            ):
                return (
                    f"There is no pending "
                    f"{action} request."
                )

            if (
                time.monotonic()
                > pending.expires_at
            ):
                self._pending = None

                return (
                    "The power confirmation "
                    "has expired."
                )

            if (
                pending.action
                != action
            ):
                return (
                    f"The pending action is "
                    f"{pending.action}, not "
                    f"{action}."
                )

            # Clear BEFORE executing.
            #
            # This prevents accidental repeated execution
            # if the command is sent twice.
            self._pending = None

        return (
            self._perform_action(
                action
            )
        )

    # ==================================================
    # CANCEL
    # ==================================================

    def _cancel_pending(
        self,
    ) -> str:
        with self._lock:
            pending = (
                self._pending
            )

            self._pending = None

        if (
            pending
            is None
        ):
            return (
                "There is no pending "
                "power action to cancel."
            )

        return (
            f"Cancelled the pending "
            f"{pending.action} request."
        )

    # ==================================================
    # PERFORM ACTION
    # ==================================================

    def _perform_action(
        self,
        action: str,
    ) -> str:
        if (
            platform.system()
            .lower()
            != "windows"
        ):
            return (
                "Power controls are currently "
                "supported only on Windows."
            )

        if (
            action
            == "shutdown"
        ):
            return (
                self._shutdown()
            )

        if (
            action
            == "restart"
        ):
            return (
                self._restart()
            )

        if (
            action
            == "sleep"
        ):
            return (
                self._sleep()
            )

        return (
            "Unsupported power action."
        )

    # ==================================================
    # SHUTDOWN
    # ==================================================

    def _shutdown(
        self,
    ) -> str:
        try:
            result = (
                subprocess.run(
                    [
                        "shutdown",
                        "/s",
                        "/t",
                        "0",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
            )

            if (
                result.returncode
                != 0
            ):
                return (
                    "I couldn't shut down "
                    "the computer."
                )

            return (
                "Shutting down the computer."
            )

        except (
            subprocess.SubprocessError,
            OSError,
        ):
            return (
                "I couldn't shut down "
                "the computer."
            )

    # ==================================================
    # RESTART
    # ==================================================

    def _restart(
        self,
    ) -> str:
        try:
            result = (
                subprocess.run(
                    [
                        "shutdown",
                        "/r",
                        "/t",
                        "0",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
            )

            if (
                result.returncode
                != 0
            ):
                return (
                    "I couldn't restart "
                    "the computer."
                )

            return (
                "Restarting the computer."
            )

        except (
            subprocess.SubprocessError,
            OSError,
        ):
            return (
                "I couldn't restart "
                "the computer."
            )

    # ==================================================
    # SLEEP
    # ==================================================

    def _sleep(
        self,
    ) -> str:
        try:
            result = (
                ctypes.windll
                .powrprof
                .SetSuspendState(
                    False,
                    False,
                    False,
                )
            )

            if not result:
                return (
                    "I couldn't put the "
                    "computer to sleep."
                )

            return (
                "Putting the computer "
                "to sleep."
            )

        except (
            AttributeError,
            OSError,
        ):
            return (
                "I couldn't put the "
                "computer to sleep."
            )

    # ==================================================
    # NORMALIZE
    # ==================================================

    def _normalize(
        self,
        command: str,
    ) -> str:
        return (
            command
            .strip()
            .lower()
            .rstrip(
                ".!?"
            )
        )