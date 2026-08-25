from app.skills.file_dialog_skill import (
    FileDialogSkill,
)


# ======================================================
# HELPERS
# ======================================================


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


# ======================================================
# ROUTING
# ======================================================


def test_can_handle_open_and_save_commands():
    skill = FileDialogSkill()

    assert (
        skill.can_handle(
            r"choose file C:\Temp\a.txt"
        )
        is True
    )

    assert (
        skill.can_handle(
            r"save file as C:\Temp\b.txt"
        )
        is True
    )

    assert (
        skill.can_handle(
            "open notepad"
        )
        is False
    )


# ======================================================
# OPEN VALIDATION
# ======================================================


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
    assert (
        "does not exist"
        in result.lower()
    )


# ======================================================
# SAVE OVERWRITE PROTECTION
# ======================================================


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
    assert (
        "overwrite"
        in result.lower()
    )


# ======================================================
# UNIQUE FILE NAME FIELD
# ======================================================


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


# ======================================================
# UNIQUE ACTION BUTTON
# ======================================================


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


# ======================================================
# WINDOWS NATIVE ACTION BUTTON
# ======================================================


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

    assert (
        result
        is real_open_button
    )


# ======================================================
# FULL OPEN FLOW
# ======================================================


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

    assert (
        response.startswith(
            "Opened file "
        )
    )

    assert (
        edit.value
        == str(
            source
        )
    )

    assert (
        button.invoked
        is True
    )


# ======================================================
# FULL SAVE FLOW
# ======================================================


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

    assert (
        response.startswith(
            "Saved file as "
        )
    )

    assert (
        edit.value
        == str(
            destination
        )
    )

    assert (
        button.invoked
        is True
    )