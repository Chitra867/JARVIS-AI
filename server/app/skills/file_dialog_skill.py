import re
import time

from pathlib import (
    Path,
)

import pyautogui
import win32gui
import win32process

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

    PREPARATION_TIMEOUT_SECONDS = 3.0
    PREPARATION_POLL_INTERVAL_SECONDS = 0.05

    SUPPORTED_PREPARATION_PROCESS_NAMES = frozenset(
        {
            "notepad",
            "notepad.exe",
        }
    )

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

    FOLDER_PATTERN = re.compile(
        (
            r"^(?:choose|select)\s+folder\s+"
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
            or self.FOLDER_PATTERN.match(clean)
            is not None
        )

    # ==================================================
    # MULTI-STEP PREPARATION
    # ==================================================

    def prepare_for_execution(
        self,
        command: str,
        focus_context: object,
    ) -> tuple[
        bool,
        str,
    ]:
        parsed = self._parse_command(
            command
        )

        if parsed is None:
            return (
                False,
                (
                    "I couldn't understand the "
                    "file dialog command."
                ),
            )

        (
            mode,
            raw_path,
        ) = parsed

        path = self._normalize_path(
            raw_path
        )

        validation_error = self._validate_path(
            mode=mode,
            path=path,
        )

        # Validate before opening any dialog so an invalid
        # path cannot cause an unnecessary desktop action.
        if validation_error is not None:
            return (
                False,
                validation_error,
            )

        # If the expected dialog is already open and is
        # owned by the exact verified application window,
        # preparation is already complete.
        if self._current_prepared_dialog_matches(
            mode=mode,
            focus_context=focus_context,
        ):
            return (
                True,
                "",
            )

        # Folder-picker invocation is application-specific.
        # We can safely operate an already-open Browse For
        # Folder dialog, but we do not guess a shortcut for
        # opening one from an arbitrary application.
        if mode == "folder":
            return (
                False,
                (
                    "Automatic folder-dialog opening "
                    "is unavailable for this "
                    "application. Open the Browse "
                    "For Folder dialog first."
                ),
            )

        if not self._focus_context_is_supported_notepad(
            focus_context
        ):
            return (
                False,
                (
                    "Automatic Open/Save dialog "
                    "preparation is currently "
                    "supported only for a verified "
                    "Notepad window."
                ),
            )

        owner_hwnd = self._focus_context_hwnd(
            focus_context
        )

        if not owner_hwnd:
            return (
                False,
                (
                    "The verified application "
                    "window is unavailable."
                ),
            )

        if not self._focus_context_window_matches(
            focus_context
        ):
            return (
                False,
                (
                    "The verified application "
                    "window changed before the "
                    "file dialog could be opened."
                ),
            )

        # The executor has already recovered application
        # focus. Require the exact verified main window
        # before sending an application shortcut.
        if self._foreground_hwnd() != owner_hwnd:
            return (
                False,
                (
                    "The verified Notepad window "
                    "is not currently in the "
                    "foreground."
                ),
            )

        try:
            if mode == "open":
                pyautogui.hotkey(
                    "ctrl",
                    "o",
                )

            else:
                pyautogui.hotkey(
                    "ctrl",
                    "shift",
                    "s",
                )

        except Exception:
            return (
                False,
                (
                    "I couldn't safely send the "
                    "file-dialog shortcut."
                ),
            )

        if not self._wait_for_prepared_dialog(
            mode=mode,
            focus_context=focus_context,
        ):
            return (
                False,
                (
                    "The expected file dialog did "
                    "not appear from the verified "
                    "Notepad window."
                ),
            )

        return (
            True,
            "",
        )

    def _parse_command(
        self,
        command: str,
    ) -> tuple[
        str,
        str,
    ] | None:
        clean = command.strip()

        open_match = self.OPEN_PATTERN.match(
            clean
        )

        if open_match is not None:
            return (
                "open",
                open_match.group(1),
            )

        save_match = self.SAVE_PATTERN.match(
            clean
        )

        if save_match is not None:
            return (
                "save",
                save_match.group(1),
            )

        folder_match = self.FOLDER_PATTERN.match(
            clean
        )

        if folder_match is not None:
            return (
                "folder",
                folder_match.group(1),
            )

        return None

    def _focus_context_hwnd(
        self,
        focus_context: object,
    ) -> int:
        try:
            hwnd = int(
                getattr(
                    focus_context,
                    "hwnd",
                    0,
                )
                or 0
            )

            return (
                hwnd
                if hwnd > 0
                else 0
            )

        except Exception:
            return 0

    def _focus_context_process_id(
        self,
        focus_context: object,
    ) -> int:
        try:
            process_id = int(
                getattr(
                    focus_context,
                    "process_id",
                    0,
                )
                or 0
            )

            return (
                process_id
                if process_id > 0
                else 0
            )

        except Exception:
            return 0

    def _focus_context_process_names(
        self,
        focus_context: object,
    ) -> frozenset[
        str
    ]:
        names: set[
            str
        ] = set()

        try:
            single_name = getattr(
                focus_context,
                "process_name",
                "",
            )

            if single_name:
                names.add(
                    Path(
                        str(
                            single_name
                        )
                    )
                    .name
                    .casefold()
                )

        except Exception:
            pass

        try:
            multiple_names = getattr(
                focus_context,
                "process_names",
                (),
            )

            if isinstance(
                multiple_names,
                (
                    tuple,
                    list,
                    set,
                    frozenset,
                ),
            ):
                for value in multiple_names:
                    if not value:
                        continue

                    names.add(
                        Path(
                            str(
                                value
                            )
                        )
                        .name
                        .casefold()
                    )

        except Exception:
            pass

        return frozenset(
            names
        )

    def _focus_context_is_supported_notepad(
        self,
        focus_context: object,
    ) -> bool:
        names = self._focus_context_process_names(
            focus_context
        )

        return bool(
            names
            & self.SUPPORTED_PREPARATION_PROCESS_NAMES
        )

    def _focus_context_window_matches(
        self,
        focus_context: object,
    ) -> bool:
        hwnd = self._focus_context_hwnd(
            focus_context
        )

        if not hwnd:
            return False

        try:
            if not win32gui.IsWindow(
                hwnd
            ):
                return False

            if not win32gui.IsWindowVisible(
                hwnd
            ):
                return False

            if not win32gui.IsWindowEnabled(
                hwnd
            ):
                return False

            (
                _,
                actual_process_id,
            ) = (
                win32process
                .GetWindowThreadProcessId(
                    hwnd
                )
            )

        except Exception:
            return False

        expected_process_id = (
            self._focus_context_process_id(
                focus_context
            )
        )

        if (
            expected_process_id
            and actual_process_id
            != expected_process_id
        ):
            return False

        return True

    def _current_prepared_dialog_matches(
        self,
        *,
        mode: str,
        focus_context: object,
    ) -> bool:
        dialog_hwnd = self._foreground_hwnd()

        if not dialog_hwnd:
            return False

        owner_hwnd = self._focus_context_hwnd(
            focus_context
        )

        if not owner_hwnd:
            return False

        try:
            if not win32gui.IsWindow(
                dialog_hwnd
            ):
                return False

            if not win32gui.IsWindowVisible(
                dialog_hwnd
            ):
                return False

            if not win32gui.IsWindowEnabled(
                dialog_hwnd
            ):
                return False

            if (
                win32gui.GetClassName(
                    dialog_hwnd
                )
                != "#32770"
            ):
                return False

            if (
                int(
                    win32gui.GetWindow(
                        dialog_hwnd,
                        4,
                    )
                    or 0
                )
                != owner_hwnd
            ):
                return False

            (
                _,
                dialog_process_id,
            ) = (
                win32process
                .GetWindowThreadProcessId(
                    dialog_hwnd
                )
            )

        except Exception:
            return False

        expected_process_id = (
            self._focus_context_process_id(
                focus_context
            )
        )

        if (
            expected_process_id
            and dialog_process_id
            != expected_process_id
        ):
            return False

        dialog = self._get_dialog(
            dialog_hwnd
        )

        if dialog is None:
            return False

        title = self._safe_text(
            dialog
        )

        return self._dialog_title_matches(
            title=title,
            mode=mode,
        )

    def _wait_for_prepared_dialog(
        self,
        *,
        mode: str,
        focus_context: object,
    ) -> bool:
        deadline = (
            time.monotonic()
            + self.PREPARATION_TIMEOUT_SECONDS
        )

        while (
            time.monotonic()
            < deadline
        ):
            if self._current_prepared_dialog_matches(
                mode=mode,
                focus_context=focus_context,
            ):
                return True

            time.sleep(
                self.PREPARATION_POLL_INTERVAL_SECONDS
            )

        return False

    def execute(
        self,
        command: str,
    ) -> str:
        clean = command.strip()

        open_match = self.OPEN_PATTERN.match(clean)
        save_match = self.SAVE_PATTERN.match(clean)
        folder_match = self.FOLDER_PATTERN.match(clean)

        if open_match is not None:
            mode = "open"
            raw_path = open_match.group(1)

        elif save_match is not None:
            mode = "save"
            raw_path = save_match.group(1)

        elif folder_match is not None:
            mode = "folder"
            raw_path = folder_match.group(1)

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
                "file dialog."
            )

        title = self._safe_text(dialog)

        if not self._dialog_title_matches(
            title=title,
            mode=mode,
        ):
            return (
                "I couldn't verify that the active "
                "window is the expected file dialog."
            )

        if mode == "folder":
            return self._execute_folder_selection(
                hwnd=hwnd,
                dialog=dialog,
                path=path,
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

    def _execute_folder_selection(
        self,
        *,
        hwnd: int,
        dialog,
        path: Path,
    ) -> str:
        if self._foreground_hwnd() != hwnd:
            return (
                "The active window changed before "
                "the folder dialog could be used."
            )

        if not self._select_folder_in_dialog(
            hwnd=hwnd,
            path=path,
        ):
            return (
                "I couldn't safely select that "
                "folder in the folder dialog."
            )

        # Win32 TreeView selection can temporarily move
        # keyboard focus even though the same folder
        # dialog remains active and valid. Do not depend
        # on foreground equality after programmatic tree
        # selection. Revalidate the exact original dialog
        # HWND and resolve the OK button again instead.
        revalidated_dialog = self._get_dialog(
            hwnd
        )

        if revalidated_dialog is None:
            return (
                "I couldn't revalidate the folder "
                "dialog after selecting the folder."
            )

        title = self._safe_text(
            revalidated_dialog
        )

        if not self._dialog_title_matches(
            title=title,
            mode="folder",
        ):
            return (
                "The folder dialog changed before "
                "the selection could be confirmed."
            )

        action_button = self._resolve_action_button(
            dialog=revalidated_dialog,
            mode="folder",
        )

        if action_button is None:
            return (
                "I couldn't uniquely resolve the "
                "folder dialog OK button."
            )

        if not self._invoke_button(
            action_button
        ):
            return (
                "I couldn't safely invoke the "
                "folder dialog OK button."
            )

        if not self._wait_for_dialog_completion(
            hwnd
        ):
            return (
                "I couldn't verify that the folder "
                "dialog completed. The action was "
                "not retried."
            )

        return f"Selected folder {path}."

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

        if mode == "folder":
            if not path.exists():
                return (
                    "I couldn't select that folder "
                    "because it does not exist."
                )

            if not path.is_dir():
                return (
                    "I couldn't select that path "
                    "because it is not a folder."
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

        if mode == "folder":
            return (
                normalized == "browse for folder"
                or normalized.startswith(
                    "browse for folder "
                )
            )

        return (
            normalized == "save as"
            or normalized.startswith("save as ")
            or normalized == "save"
        )

    def _select_folder_in_dialog(
        self,
        *,
        hwnd: int,
        path: Path,
    ) -> bool:
        try:
            drive = path.drive

            if not drive:
                return False

            drive_letter = (
                drive.rstrip("\\/")
                .upper()
            )

            relative_parts = list(
                path.parts[1:]
            )

            dialog = (
                Desktop(
                    backend="win32"
                )
                .window(
                    handle=hwnd
                )
            )

            tree = (
                dialog
                .child_window(
                    control_id=100
                )
                .wrapper_object()
            )

            this_pc = tree.get_item(
                r"\Desktop\This PC"
            )

            try:
                this_pc.expand()
            except Exception:
                pass

            time.sleep(
                self.COMPLETION_POLL_INTERVAL_SECONDS
            )

            drive_item = None

            for child in this_pc.children():
                text = (
                    str(
                        child.text()
                    )
                    .strip()
                )

                if (
                    f"({drive_letter})"
                    in text.upper()
                ):
                    if drive_item is not None:
                        return False

                    drive_item = child

            if drive_item is None:
                return False

            current = drive_item

            if relative_parts:
                try:
                    current.expand()
                except Exception:
                    pass

                time.sleep(
                    self.COMPLETION_POLL_INTERVAL_SECONDS
                )

            for index, part in enumerate(
                relative_parts
            ):
                matches = []

                for child in current.children():
                    text = (
                        str(
                            child.text()
                        )
                        .strip()
                    )

                    if (
                        text.casefold()
                        == str(part).casefold()
                    ):
                        matches.append(
                            child
                        )

                if len(matches) != 1:
                    return False

                current = matches[0]

                if index < len(
                    relative_parts
                ) - 1:
                    try:
                        current.expand()
                    except Exception:
                        pass

                    time.sleep(
                        self.COMPLETION_POLL_INTERVAL_SECONDS
                    )

            current.select()

            return True

        except Exception:
            return False

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
        if mode == "open":
            expected = "open"
        elif mode == "folder":
            expected = "ok"
        else:
            expected = "save"

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

        primary_candidates = [
            control
            for control in candidates
            if self._automation_id(
                control
            ) == "1"
        ]

        if len(primary_candidates) == 1:
            return primary_candidates[0]

        if len(primary_candidates) > 1:
            return None

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