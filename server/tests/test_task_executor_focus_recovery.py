from types import (
    SimpleNamespace,
)

import pytest

from app.core.task_executor import (
    ExecutionStatus,
    TaskExecutor,
)

from app.skills.registry import (
    skill_registry,
)


# ======================================================
# HELPERS
# ======================================================


def _step(
    index: int,
    command: str,
    handler: str,
):
    return (
        SimpleNamespace(
            index=index,
            command=command,
            handler=handler,
            references=(),
        )
    )


def _plan(
    *steps,
):
    return (
        SimpleNamespace(
            original_command=" then ".join(
                step.command
                for step
                in steps
            ),
            is_safe_to_execute=True,
            steps=tuple(
                steps
            ),
        )
    )


class AppLauncherSkill:
    def __init__(
        self,
        *,
        context=object(),
        recovery_result=(
            True,
            "focus recovered",
        ),
    ):
        self.context = (
            context
        )

        self.recovery_result = (
            recovery_result
        )

        self.recovery_calls = []

        self.executed = []

    def execute(
        self,
        command: str,
    ) -> str:
        self.executed.append(
            command
        )

        return (
            "Opening notepad."
        )

    def wait_until_ready(
        self,
        command: str,
    ):
        return (
            True,
            "notepad is ready",
        )

    def get_focus_context(
        self,
        command: str,
    ):
        return (
            self.context
        )

    def recover_focus_context(
        self,
        context,
    ):
        self.recovery_calls.append(
            context
        )

        return (
            self.recovery_result
        )


class InputControlSkill:
    def __init__(
        self,
    ):
        self.executed = []

    def execute(
        self,
        command: str,
    ) -> str:
        self.executed.append(
            command
        )

        return (
            "Typed 5 characters."
        )


class UIAutomationClickSkill:
    def __init__(
        self,
    ):
        self.executed = []

    def execute(
        self,
        command: str,
    ) -> str:
        self.executed.append(
            command
        )

        return (
            "Clicked 'File' (MenuItem) "
            "at screen position (10, 10)."
        )


class DummySkill:
    def __init__(
        self,
    ):
        self.executed = []

    def execute(
        self,
        command: str,
    ) -> str:
        self.executed.append(
            command
        )

        return (
            "Done."
        )


def _install_registry(
    monkeypatch,
    mapping,
):
    monkeypatch.setattr(
        skill_registry,
        "find_skill",
        lambda command: (
            mapping.get(
                command
            )
        ),
    )


# ======================================================
# INPUT CONTROL RECOVERY
# ======================================================


def test_executor_recovers_focus_before_input_control(
    monkeypatch,
):
    context = (
        object()
    )

    launcher = (
        AppLauncherSkill(
            context=context,
        )
    )

    input_skill = (
        InputControlSkill()
    )

    _install_registry(
        monkeypatch,
        {
            "open notepad":
                launcher,

            "type hello":
                input_skill,
        },
    )

    plan = (
        _plan(
            _step(
                1,
                "open notepad",
                "AppLauncherSkill",
            ),
            _step(
                2,
                "type hello",
                "InputControlSkill",
            ),
        )
    )

    result = (
        TaskExecutor()
        .execute_plan(
            plan
        )
    )

    assert (
        result.success
        is True
    )

    assert (
        launcher.recovery_calls
        == [
            context,
        ]
    )

    assert (
        input_skill.executed
        == [
            "type hello",
        ]
    )


# ======================================================
# UI CLICK RECOVERY
# ======================================================


def test_executor_recovers_focus_before_uia_click(
    monkeypatch,
):
    context = (
        object()
    )

    launcher = (
        AppLauncherSkill(
            context=context,
        )
    )

    click_skill = (
        UIAutomationClickSkill()
    )

    _install_registry(
        monkeypatch,
        {
            "open notepad":
                launcher,

            "click file menu item":
                click_skill,
        },
    )

    result = (
        TaskExecutor()
        .execute_plan(
            _plan(
                _step(
                    1,
                    "open notepad",
                    "AppLauncherSkill",
                ),
                _step(
                    2,
                    "click file menu item",
                    "UIAutomationClickSkill",
                ),
            )
        )
    )

    assert (
        result.success
        is True
    )

    assert (
        launcher.recovery_calls
        == [
            context,
        ]
    )

    assert (
        click_skill.executed
        == [
            "click file menu item",
        ]
    )


# ======================================================
# RECOVERY FAILURE
# ======================================================


def test_executor_blocks_sensitive_step_when_focus_recovery_fails(
    monkeypatch,
):
    context = (
        object()
    )

    launcher = (
        AppLauncherSkill(
            context=context,
            recovery_result=(
                False,
                (
                    "The expected application "
                    "window no longer exists."
                ),
            ),
        )
    )

    input_skill = (
        InputControlSkill()
    )

    _install_registry(
        monkeypatch,
        {
            "open notepad":
                launcher,

            "type hello":
                input_skill,
        },
    )

    result = (
        TaskExecutor()
        .execute_plan(
            _plan(
                _step(
                    1,
                    "open notepad",
                    "AppLauncherSkill",
                ),
                _step(
                    2,
                    "type hello",
                    "InputControlSkill",
                ),
            )
        )
    )

    assert (
        result.success
        is False
    )

    assert (
        result.blocked
        is True
    )

    assert (
        result.stopped_at
        == 2
    )

    assert (
        input_skill.executed
        == []
    )

    assert (
        result.steps[
            -1
        ].status
        == ExecutionStatus.BLOCKED
    )


# ======================================================
# NON-FOREGROUND-SENSITIVE STEP
# ======================================================


def test_executor_does_not_recover_focus_for_unrelated_skill(
    monkeypatch,
):
    context = (
        object()
    )

    launcher = (
        AppLauncherSkill(
            context=context,
        )
    )

    dummy = (
        DummySkill()
    )

    _install_registry(
        monkeypatch,
        {
            "open notepad":
                launcher,

            "do something":
                dummy,
        },
    )

    result = (
        TaskExecutor()
        .execute_plan(
            _plan(
                _step(
                    1,
                    "open notepad",
                    "AppLauncherSkill",
                ),
                _step(
                    2,
                    "do something",
                    "DummySkill",
                ),
            )
        )
    )

    assert (
        result.success
        is True
    )

    assert (
        launcher.recovery_calls
        == []
    )

    assert (
        dummy.executed
        == [
            "do something",
        ]
    )


# ======================================================
# NO CAPTURED CONTEXT
# ======================================================


def test_executor_blocks_focus_sensitive_step_when_launcher_has_no_context(
    monkeypatch,
):
    launcher = (
        AppLauncherSkill(
            context=None,
        )
    )

    input_skill = (
        InputControlSkill()
    )

    _install_registry(
        monkeypatch,
        {
            "open notepad":
                launcher,

            "type hello":
                input_skill,
        },
    )

    result = (
        TaskExecutor()
        .execute_plan(
            _plan(
                _step(
                    1,
                    "open notepad",
                    "AppLauncherSkill",
                ),
                _step(
                    2,
                    "type hello",
                    "InputControlSkill",
                ),
            )
        )
    )

    assert (
        result.success
        is False
    )

    assert (
        result.blocked
        is True
    )

    assert (
        result.stopped_at
        == 1
    )

    assert (
        launcher.recovery_calls
        == []
    )

    assert (
        input_skill.executed
        == []
    )

    assert (
        len(
            result.steps
        )
        == 1
    )

    assert (
        result.steps[
            0
        ].status
        == ExecutionStatus.BLOCKED
    )

    assert (
        "focus context"
        in result.steps[
            0
        ].response.lower()
    )


# ======================================================
# NEW LAUNCH REPLACES OLD CONTEXT
# ======================================================


def test_new_launcher_step_replaces_previous_focus_context(
    monkeypatch,
):
    first_context = (
        object()
    )

    second_context = (
        object()
    )

    first_launcher = (
        AppLauncherSkill(
            context=(
                first_context
            ),
        )
    )

    second_launcher = (
        AppLauncherSkill(
            context=(
                second_context
            ),
        )
    )

    input_skill = (
        InputControlSkill()
    )

    _install_registry(
        monkeypatch,
        {
            "open notepad":
                first_launcher,

            "open calculator":
                second_launcher,

            "type hello":
                input_skill,
        },
    )

    result = (
        TaskExecutor()
        .execute_plan(
            _plan(
                _step(
                    1,
                    "open notepad",
                    "AppLauncherSkill",
                ),
                _step(
                    2,
                    "open calculator",
                    "AppLauncherSkill",
                ),
                _step(
                    3,
                    "type hello",
                    "InputControlSkill",
                ),
            )
        )
    )

    assert (
        result.success
        is True
    )

    assert (
        first_launcher.recovery_calls
        == []
    )

    assert (
        second_launcher.recovery_calls
        == [
            second_context,
        ]
    )


# ======================================================
# MALFORMED RECOVERY CONTRACT
# ======================================================


def test_recover_step_focus_fails_closed_on_invalid_result():
    class Owner:
        def recover_focus_context(
            self,
            context,
        ):
            return (
                True,
            )

    recovered, reason = (
        TaskExecutor()
        ._recover_step_focus(
            owner=(
                Owner()
            ),
            context=(
                object()
            ),
        )
    )

    assert (
        recovered
        is False
    )

    assert (
        "invalid result"
        in reason.lower()
    )


def test_recover_step_focus_fails_closed_on_non_boolean_status():
    class Owner:
        def recover_focus_context(
            self,
            context,
        ):
            return (
                "yes",
                "bad status",
            )

    recovered, reason = (
        TaskExecutor()
        ._recover_step_focus(
            owner=(
                Owner()
            ),
            context=(
                object()
            ),
        )
    )

    assert (
        recovered
        is False
    )

    assert (
        "invalid status"
        in reason.lower()
    )


def test_recover_step_focus_fails_closed_on_exception():
    class Owner:
        def recover_focus_context(
            self,
            context,
        ):
            raise RuntimeError(
                "boom"
            )

    recovered, reason = (
        TaskExecutor()
        ._recover_step_focus(
            owner=(
                Owner()
            ),
            context=(
                object()
            ),
        )
    )

    assert (
        recovered
        is False
    )

    assert (
        "could not be safely restored"
        in reason.lower()
    )