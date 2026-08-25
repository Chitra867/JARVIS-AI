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
