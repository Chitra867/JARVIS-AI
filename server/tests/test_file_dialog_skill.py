from dataclasses import (
    dataclass,
)

from app.skills import (
    file_dialog_skill as file_dialog_module,
)

from app.skills.file_dialog_skill import (
    FileDialogSkill,
)


class ElementInfo:
    def __init__(
        self,
        *,
        control_type: str,
        automation_id: str = "",
    ):
        self.control_type = control_type
        self.automation_id = automation_id


class FakeControl:
    def __init__(
        self,
        *,
        name: str,
        control_type: str,
        automation_id: str = "",
    ):
        self._name = name

        self.element_info = ElementInfo(
            control_type=control_type,
            automation_id=automation_id,
        )

        self.value = None
        self.invoked = False

    def window_text(
        self,
    ):
        return self._name

    def is_visible(
        self,
    ):
        return True

    def is_enabled(
        self,
    ):
        return True

    def set_edit_text(
        self,
        value,
    ):
        self.value = value

    def invoke(
        self,
    ):
        self.invoked = True


class FakeDialog:
    def __init__(
        self,
        *,
        title: str,
        controls,
    ):
        self.title = title
        self.controls = list(
            controls
        )

    def window_text(
        self,
    ):
        return self.title

    def descendants(
        self,
    ):
        return self.controls



@dataclass(
    frozen=True,
)
class FakeFocusContext:
    hwnd: int = 100
    process_id: int = 200
    process_name: str = "notepad.exe"
    process_names: frozenset[str] = frozenset(
        {
            "notepad.exe",
        }
    )


def test_can_handle_open_save_and_folder_commands():
    skill = FileDialogSkill()

    assert skill.can_handle(
        r"choose file C:\Temp\a.txt"
    )
    assert skill.can_handle(
        r"save file as C:\Temp\b.txt"
    )
    assert skill.can_handle(
        r"choose folder C:\Temp"
    )
    assert not skill.can_handle(
        "open notepad"
    )


def test_open_rejects_missing_file(
    tmp_path,
):
    skill = FileDialogSkill()

    missing = (
        tmp_path
        / "missing.txt"
    )

    result = skill._validate_path(
        mode="open",
        path=missing,
    )

    assert result is not None
    assert "does not exist" in result.lower()


def test_save_rejects_existing_file(
    tmp_path,
):
    skill = FileDialogSkill()

    existing = (
        tmp_path
        / "existing.txt"
    )

    existing.write_text(
        "data"
    )

    result = skill._validate_path(
        mode="save",
        path=existing,
    )

    assert result is not None
    assert "overwrite" in result.lower()


def test_folder_rejects_missing_directory(
    tmp_path,
):
    skill = FileDialogSkill()

    missing = (
        tmp_path
        / "missing-folder"
    )

    result = skill._validate_path(
        mode="folder",
        path=missing,
    )

    assert result is not None
    assert "does not exist" in result.lower()


def test_folder_rejects_file_path(
    tmp_path,
):
    skill = FileDialogSkill()

    file_path = (
        tmp_path
        / "file.txt"
    )

    file_path.write_text(
        "data"
    )

    result = skill._validate_path(
        mode="folder",
        path=file_path,
    )

    assert result is not None
    assert "not a folder" in result.lower()


def test_resolve_file_name_edit_requires_unique_match():
    skill = FileDialogSkill()

    edit = FakeControl(
        name="File name:",
        control_type="Edit",
        automation_id="1001",
    )

    dialog = FakeDialog(
        title="Open",
        controls=[
            edit,
        ],
    )

    assert (
        skill._resolve_file_name_edit(
            dialog
        )
        is edit
    )

    dialog.controls.append(
        FakeControl(
            name="File name:",
            control_type="Edit",
            automation_id="1001",
        )
    )

    assert (
        skill._resolve_file_name_edit(
            dialog
        )
        is None
    )


def test_resolve_action_button_requires_exact_unique_name():
    skill = FileDialogSkill()

    open_button = FakeControl(
        name="Open",
        control_type="Button",
    )

    dialog = FakeDialog(
        title="Open",
        controls=[
            open_button,
        ],
    )

    assert (
        skill._resolve_action_button(
            dialog=dialog,
            mode="open",
        )
        is open_button
    )


def test_action_button_prefers_native_dialog_id_one():
    skill = FileDialogSkill()

    dropdown_one = FakeControl(
        name="Open",
        control_type="Button",
        automation_id="DropDown",
    )

    dropdown_two = FakeControl(
        name="Open",
        control_type="Button",
        automation_id="DropDown",
    )

    real_open_button = FakeControl(
        name="Open",
        control_type="Button",
        automation_id="1",
    )

    dialog = FakeDialog(
        title="Open",
        controls=[
            dropdown_one,
            dropdown_two,
            real_open_button,
        ],
    )

    result = skill._resolve_action_button(
        dialog=dialog,
        mode="open",
    )

    assert result is real_open_button


def test_folder_action_button_uses_native_ok_button():
    skill = FileDialogSkill()

    other_ok = FakeControl(
        name="OK",
        control_type="Button",
        automation_id="other",
    )

    real_ok = FakeControl(
        name="OK",
        control_type="Button",
        automation_id="1",
    )

    dialog = FakeDialog(
        title="Browse For Folder",
        controls=[
            other_ok,
            real_ok,
        ],
    )

    result = skill._resolve_action_button(
        dialog=dialog,
        mode="folder",
    )

    assert result is real_ok


def test_open_flow_sets_path_and_invokes_open(
    monkeypatch,
    tmp_path,
):
    skill = FileDialogSkill()

    source = (
        tmp_path
        / "sample.txt"
    )

    source.write_text(
        "hello"
    )

    edit = FakeControl(
        name="File name:",
        control_type="Edit",
        automation_id="1001",
    )

    button = FakeControl(
        name="Open",
        control_type="Button",
        automation_id="1",
    )

    dialog = FakeDialog(
        title="Open",
        controls=[
            edit,
            button,
        ],
    )

    monkeypatch.setattr(
        skill,
        "_foreground_hwnd",
        lambda: 123,
    )

    monkeypatch.setattr(
        skill,
        "_get_dialog",
        lambda hwnd: dialog,
    )

    monkeypatch.setattr(
        skill,
        "_wait_for_dialog_completion",
        lambda hwnd: True,
    )

    response = skill.execute(
        f"choose file {source}"
    )

    assert response.startswith(
        "Opened file "
    )
    assert edit.value == str(source)
    assert button.invoked is True


def test_save_flow_sets_new_path_and_invokes_save(
    monkeypatch,
    tmp_path,
):
    skill = FileDialogSkill()

    destination = (
        tmp_path
        / "new-file.txt"
    )

    edit = FakeControl(
        name="File name:",
        control_type="Edit",
        automation_id="1001",
    )

    button = FakeControl(
        name="Save",
        control_type="Button",
        automation_id="1",
    )

    dialog = FakeDialog(
        title="Save As",
        controls=[
            edit,
            button,
        ],
    )

    monkeypatch.setattr(
        skill,
        "_foreground_hwnd",
        lambda: 123,
    )

    monkeypatch.setattr(
        skill,
        "_get_dialog",
        lambda hwnd: dialog,
    )

    monkeypatch.setattr(
        skill,
        "_wait_for_dialog_completion",
        lambda hwnd: True,
    )

    response = skill.execute(
        f"save file as {destination}"
    )

    assert response.startswith(
        "Saved file as "
    )
    assert edit.value == str(destination)
    assert button.invoked is True


def test_folder_flow_selects_folder_and_invokes_ok(
    monkeypatch,
    tmp_path,
):
    skill = FileDialogSkill()

    folder = (
        tmp_path
        / "target"
    )

    folder.mkdir()

    button = FakeControl(
        name="OK",
        control_type="Button",
        automation_id="1",
    )

    dialog = FakeDialog(
        title="Browse For Folder",
        controls=[
            button,
        ],
    )

    monkeypatch.setattr(
        skill,
        "_foreground_hwnd",
        lambda: 123,
    )

    monkeypatch.setattr(
        skill,
        "_get_dialog",
        lambda hwnd: dialog,
    )

    monkeypatch.setattr(
        skill,
        "_select_folder_in_dialog",
        lambda hwnd, path: True,
    )

    monkeypatch.setattr(
        skill,
        "_wait_for_dialog_completion",
        lambda hwnd: True,
    )

    response = skill.execute(
        f"choose folder {folder}"
    )

    assert response.startswith(
        "Selected folder "
    )
    assert button.invoked is True

def test_folder_flow_revalidates_original_dialog_after_selection(
    monkeypatch,
    tmp_path,
):
    skill = FileDialogSkill()

    folder = (
        tmp_path
        / "target"
    )

    folder.mkdir()

    button = FakeControl(
        name="OK",
        control_type="Button",
        automation_id="1",
    )

    initial_dialog = FakeDialog(
        title="Browse For Folder",
        controls=[
            button,
        ],
    )

    revalidated_dialog = FakeDialog(
        title="Browse For Folder",
        controls=[
            button,
        ],
    )

    dialogs = iter(
        [
            initial_dialog,
            revalidated_dialog,
        ]
    )

    monkeypatch.setattr(
        skill,
        "_foreground_hwnd",
        lambda: 123,
    )

    monkeypatch.setattr(
        skill,
        "_get_dialog",
        lambda hwnd: next(dialogs),
    )

    monkeypatch.setattr(
        skill,
        "_select_folder_in_dialog",
        lambda hwnd, path: True,
    )

    monkeypatch.setattr(
        skill,
        "_wait_for_dialog_completion",
        lambda hwnd: True,
    )

    response = skill.execute(
        f"choose folder {folder}"
    )

    assert response.startswith(
        "Selected folder "
    )
    assert button.invoked is True


# ======================================================
# MULTI-STEP PREPARATION - OPEN
# ======================================================


def test_prepare_open_sends_notepad_open_shortcut(
    monkeypatch,
    tmp_path,
):
    skill = FileDialogSkill()
    context = FakeFocusContext()

    source = (
        tmp_path
        / "sample.txt"
    )

    source.write_text(
        "hello"
    )

    calls = []

    monkeypatch.setattr(
        skill,
        "_current_prepared_dialog_matches",
        lambda mode, focus_context: False,
    )

    monkeypatch.setattr(
        skill,
        "_focus_context_window_matches",
        lambda focus_context: True,
    )

    monkeypatch.setattr(
        skill,
        "_foreground_hwnd",
        lambda: context.hwnd,
    )

    monkeypatch.setattr(
        skill,
        "_wait_for_prepared_dialog",
        lambda mode, focus_context: True,
    )

    monkeypatch.setattr(
        file_dialog_module.pyautogui,
        "hotkey",
        lambda *keys: calls.append(
            keys
        ),
    )

    result = skill.prepare_for_execution(
        f"choose file {source}",
        context,
    )

    assert result == (
        True,
        "",
    )

    assert calls == [
        (
            "ctrl",
            "o",
        ),
    ]


# ======================================================
# MULTI-STEP PREPARATION - SAVE AS
# ======================================================


def test_prepare_save_sends_notepad_save_as_shortcut(
    monkeypatch,
    tmp_path,
):
    skill = FileDialogSkill()
    context = FakeFocusContext()

    destination = (
        tmp_path
        / "new-file.txt"
    )

    calls = []

    monkeypatch.setattr(
        skill,
        "_current_prepared_dialog_matches",
        lambda mode, focus_context: False,
    )

    monkeypatch.setattr(
        skill,
        "_focus_context_window_matches",
        lambda focus_context: True,
    )

    monkeypatch.setattr(
        skill,
        "_foreground_hwnd",
        lambda: context.hwnd,
    )

    monkeypatch.setattr(
        skill,
        "_wait_for_prepared_dialog",
        lambda mode, focus_context: True,
    )

    monkeypatch.setattr(
        file_dialog_module.pyautogui,
        "hotkey",
        lambda *keys: calls.append(
            keys
        ),
    )

    result = skill.prepare_for_execution(
        f"save file as {destination}",
        context,
    )

    assert result == (
        True,
        "",
    )

    assert calls == [
        (
            "ctrl",
            "shift",
            "s",
        ),
    ]


# ======================================================
# MULTI-STEP PREPARATION - UNSUPPORTED APP
# ======================================================


def test_prepare_rejects_unsupported_application(
    monkeypatch,
    tmp_path,
):
    skill = FileDialogSkill()

    source = (
        tmp_path
        / "sample.txt"
    )

    source.write_text(
        "hello"
    )

    context = FakeFocusContext(
        process_name="chrome.exe",
        process_names=frozenset(
            {
                "chrome.exe",
            }
        ),
    )

    monkeypatch.setattr(
        skill,
        "_current_prepared_dialog_matches",
        lambda mode, focus_context: False,
    )

    prepared, reason = (
        skill.prepare_for_execution(
            f"choose file {source}",
            context,
        )
    )

    assert prepared is False
    assert "notepad" in reason.lower()


# ======================================================
# MULTI-STEP PREPARATION - WRONG FOREGROUND
# ======================================================


def test_prepare_rejects_wrong_foreground_window(
    monkeypatch,
    tmp_path,
):
    skill = FileDialogSkill()
    context = FakeFocusContext()

    source = (
        tmp_path
        / "sample.txt"
    )

    source.write_text(
        "hello"
    )

    monkeypatch.setattr(
        skill,
        "_current_prepared_dialog_matches",
        lambda mode, focus_context: False,
    )

    monkeypatch.setattr(
        skill,
        "_focus_context_window_matches",
        lambda focus_context: True,
    )

    monkeypatch.setattr(
        skill,
        "_foreground_hwnd",
        lambda: 999,
    )

    prepared, reason = (
        skill.prepare_for_execution(
            f"choose file {source}",
            context,
        )
    )

    assert prepared is False
    assert "foreground" in reason.lower()


# ======================================================
# MULTI-STEP PREPARATION - INVALID PATH
# ======================================================


def test_prepare_rejects_invalid_path_before_shortcut(
    monkeypatch,
    tmp_path,
):
    skill = FileDialogSkill()
    context = FakeFocusContext()

    missing = (
        tmp_path
        / "missing.txt"
    )

    calls = []

    monkeypatch.setattr(
        file_dialog_module.pyautogui,
        "hotkey",
        lambda *keys: calls.append(
            keys
        ),
    )

    prepared, reason = (
        skill.prepare_for_execution(
            f"choose file {missing}",
            context,
        )
    )

    assert prepared is False
    assert "does not exist" in reason.lower()
    assert calls == []


# ======================================================
# MULTI-STEP PREPARATION - FOLDER DIALOG
# ======================================================


def test_prepare_folder_does_not_guess_application_shortcut(
    monkeypatch,
    tmp_path,
):
    skill = FileDialogSkill()
    context = FakeFocusContext()

    monkeypatch.setattr(
        skill,
        "_current_prepared_dialog_matches",
        lambda mode, focus_context: False,
    )

    prepared, reason = (
        skill.prepare_for_execution(
            f"choose folder {tmp_path}",
            context,
        )
    )

    assert prepared is False
    assert "folder-dialog" in reason.lower()


# ======================================================
# MULTI-STEP PREPARATION - ALREADY OPEN DIALOG
# ======================================================


def test_prepare_accepts_already_open_verified_dialog(
    monkeypatch,
    tmp_path,
):
    skill = FileDialogSkill()
    context = FakeFocusContext()

    source = (
        tmp_path
        / "sample.txt"
    )

    source.write_text(
        "hello"
    )

    calls = []

    monkeypatch.setattr(
        skill,
        "_current_prepared_dialog_matches",
        lambda mode, focus_context: True,
    )

    monkeypatch.setattr(
        file_dialog_module.pyautogui,
        "hotkey",
        lambda *keys: calls.append(
            keys
        ),
    )

    result = skill.prepare_for_execution(
        f"choose file {source}",
        context,
    )

    assert result == (
        True,
        "",
    )

    assert calls == []
