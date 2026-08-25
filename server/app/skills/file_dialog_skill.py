import re
import time

from pathlib import (
    Path,
)

import win32gui

from pywinauto import (
    Desktop,
)

from app.skills.base import (
    Skill,
)


class FileDialogSkill(
    Skill
):
    COMPLETION_TIMEOUT_SECONDS = 2.0
    COMPLETION_POLL_INTERVAL_SECONDS = 0.05

    FILE_NAME_AUTOMATION_IDS = frozenset(
        {
            "1001",
            "1148",
            "filenamecontrolhost",
            "filename",
        }
    )

    OPEN_PATTERN = re.compile(
        (
            r"^(?:choose|select)\s+file\s+"
            r"(.+?)"
            r"\s*[.!?]*$"
        ),
        flags=re.IGNORECASE,
    )

    SAVE_PATTERN = re.compile(
        (
            r"^save\s+file\s+as\s+"
            r"(.+?)"
            r"\s*[.!?]*$"
        ),
        flags=re.IGNORECASE,
    )

    def can_handle(
        self,
        command: str,
    ) -> bool:
        clean = command.strip()

        return (
            self.OPEN_PATTERN.match(clean)
            is not None
            or self.SAVE_PATTERN.match(clean)
            is not None
        )

    def execute(
        self,
        command: str,
    ) -> str:
        clean = command.strip()

        open_match = self.OPEN_PATTERN.match(clean)
        save_match = self.SAVE_PATTERN.match(clean)

        if open_match is not None:
            mode = "open"
            raw_path = open_match.group(1)

        elif save_match is not None:
            mode = "save"
            raw_path = save_match.group(1)

        else:
            return (
                "I couldn't understand the "
                "file dialog command."
            )

        path = self._normalize_path(raw_path)

        validation_error = self._validate_path(
            mode=mode,
            path=path,
        )

        if validation_error is not None:
            return validation_error

        hwnd = self._foreground_hwnd()

        if not hwnd:
            return (
                "I couldn't determine the active "
                "file dialog."
            )

        dialog = self._get_dialog(hwnd)

        if dialog is None:
            return (
                "I couldn't verify a Windows "
                "Open/Save file dialog."
            )

        title = self._safe_text(dialog)

        if not self._dialog_title_matches(
            title=title,
            mode=mode,
        ):
            return (
                "I couldn't verify that the active "
                f"window is the expected {mode} "
                "file dialog."
            )

        file_name_edit = self._resolve_file_name_edit(
            dialog
        )

        if file_name_edit is None:
            return (
                "I couldn't uniquely resolve the "
                "file name field."
            )

        action_button = self._resolve_action_button(
            dialog=dialog,
            mode=mode,
        )

        if action_button is None:
            return (
                f"I couldn't uniquely resolve the "
                f"{mode.title()} button."
            )

        if self._foreground_hwnd() != hwnd:
            return (
                "The active window changed before "
                "the file dialog could be used."
            )

        if not self._set_file_name(
            control=file_name_edit,
            value=str(path),
        ):
            return (
                "I couldn't safely set the file "
                "name field."
            )

        if self._foreground_hwnd() != hwnd:
            return (
                "The active window changed after "
                "the file name was entered."
            )

        if not self._invoke_button(
            action_button
        ):
            return (
                f"I couldn't safely invoke the "
                f"{mode.title()} button."
            )

        if not self._wait_for_dialog_completion(
            hwnd
        ):
            return (
                "I couldn't verify that the file "
                "dialog completed. The action was "
                "not retried."
            )

        if mode == "open":
            return f"Opened file {path}."

        return f"Saved file as {path}."

    def _normalize_path(
        self,
        raw_path: str,
    ) -> Path:
        cleaned = (
            raw_path
            .strip()
            .strip("\"'")
        )

        return Path(cleaned).expanduser()

    def _validate_path(
        self,
        *,
        mode: str,
        path: Path,
    ) -> str | None:
        if not path.is_absolute():
            return (
                "I can't use a relative path in "
                "a file dialog. Use an absolute "
                "Windows path."
            )

        if mode == "open":
            if not path.exists():
                return (
                    "I couldn't open that file "
                    "because it does not exist."
                )

            if not path.is_file():
                return (
                    "I couldn't open that path "
                    "because it is not a file."
                )

            return None

        if path.exists():
            return (
                "I can't overwrite an existing "
                "file without an explicit overwrite "
                "confirmation."
            )

        parent = path.parent

        if not (
            parent.exists()
            and parent.is_dir()
        ):
            return (
                "I couldn't save there because "
                "the destination folder does not "
                "exist."
            )

        return None

    def _foreground_hwnd(
        self,
    ) -> int:
        try:
            return int(
                win32gui.GetForegroundWindow()
            )
        except Exception:
            return 0

    def _get_dialog(
        self,
        hwnd: int,
    ):
        try:
            if not win32gui.IsWindow(hwnd):
                return None

            if not win32gui.IsWindowVisible(hwnd):
                return None

            if not win32gui.IsWindowEnabled(hwnd):
                return None

            return (
                Desktop(
                    backend="uia"
                )
                .window(
                    handle=hwnd
                )
                .wrapper_object()
            )

        except Exception:
            return None

    def _dialog_title_matches(
        self,
        *,
        title: str,
        mode: str,
    ) -> bool:
        normalized = self._normalize(title)

        if mode == "open":
            return (
                normalized == "open"
                or normalized.startswith("open ")
            )

        return (
            normalized == "save as"
            or normalized.startswith("save as ")
            or normalized == "save"
        )

    def _resolve_file_name_edit(
        self,
        dialog,
    ):
        candidates = []

        try:
            descendants = dialog.descendants()
        except Exception:
            return None

        for control in descendants:
            if not self._is_visible_enabled(
                control
            ):
                continue

            if self._control_type(
                control
            ) != "Edit":
                continue

            name = self._normalize(
                self._safe_text(
                    control
                )
            )

            automation_id = self._automation_id(
                control
            )

            if (
                "file name" in name
                or automation_id
                in self.FILE_NAME_AUTOMATION_IDS
            ):
                candidates.append(control)

        if len(candidates) != 1:
            return None

        return candidates[0]

    def _resolve_action_button(
        self,
        *,
        dialog,
        mode: str,
    ):
        expected = (
            "open"
            if mode == "open"
            else "save"
        )

        candidates = []

        try:
            descendants = dialog.descendants()
        except Exception:
            return None

        for control in descendants:
            if not self._is_visible_enabled(
                control
            ):
                continue

            if self._control_type(
                control
            ) != "Button":
                continue

            if self._normalize(
                self._safe_text(
                    control
                )
            ) != expected:
                continue

            candidates.append(control)

        # Windows common Open/Save dialogs can expose
        # multiple controls named "Open" or "Save".
        # The real native dialog action button is IDOK,
        # exposed by UI Automation with automation ID "1".
        primary_candidates = [
            control
            for control in candidates
            if self._automation_id(
                control
            ) == "1"
        ]

        if len(primary_candidates) == 1:
            return primary_candidates[0]

        # Fail closed if more than one native action
        # button somehow matches.
        if len(primary_candidates) > 1:
            return None

        # Safe fallback for dialogs that expose only
        # one matching visible/enabled action button.
        if len(candidates) == 1:
            return candidates[0]

        return None

    def _set_file_name(
        self,
        *,
        control,
        value: str,
    ) -> bool:
        try:
            setter = getattr(
                control,
                "set_edit_text",
                None,
            )

            if not callable(setter):
                return False

            setter(value)
            return True

        except Exception:
            return False

    def _invoke_button(
        self,
        control,
    ) -> bool:
        try:
            invoker = getattr(
                control,
                "invoke",
                None,
            )

            if not callable(invoker):
                return False

            invoker()
            return True

        except Exception:
            return False

    def _wait_for_dialog_completion(
        self,
        original_hwnd: int,
    ) -> bool:
        deadline = (
            time.monotonic()
            + self.COMPLETION_TIMEOUT_SECONDS
        )

        while time.monotonic() < deadline:
            try:
                if not win32gui.IsWindow(
                    original_hwnd
                ):
                    return True

                if not win32gui.IsWindowVisible(
                    original_hwnd
                ):
                    return True

            except Exception:
                return True

            if self._foreground_hwnd() != original_hwnd:
                return True

            time.sleep(
                self.COMPLETION_POLL_INTERVAL_SECONDS
            )

        return False

    def _safe_text(
        self,
        control,
    ) -> str:
        try:
            return str(
                control.window_text()
            ).strip()
        except Exception:
            return ""

    def _control_type(
        self,
        control,
    ) -> str:
        try:
            return str(
                control.element_info.control_type
            ).strip()
        except Exception:
            return ""

    def _automation_id(
        self,
        control,
    ) -> str:
        try:
            return str(
                getattr(
                    control.element_info,
                    "automation_id",
                    "",
                )
                or ""
            ).strip().lower()
        except Exception:
            return ""

    def _is_visible_enabled(
        self,
        control,
    ) -> bool:
        try:
            return (
                bool(
                    control.is_visible()
                )
                and bool(
                    control.is_enabled()
                )
            )
        except Exception:
            return False

    def _normalize(
        self,
        value: str,
    ) -> str:
        return (
            " ".join(
                value
                .strip()
                .lower()
                .replace("_", " ")
                .replace("-", " ")
                .split()
            )
        )