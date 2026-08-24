from types import (
    SimpleNamespace,
)

from app.core import (
    task_executor as executor_module,
)

from app.core.task_executor import (
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
    ):
        self.context = (
            object()
        )

        self.recovery_calls = 0

    def execute(
        self,
        command: str,
    ) -> str:
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
        self.recovery_calls += 1

        return (
            True,
            "focus recovered",
        )


class UIAutomationClickSkill:
    def __init__(
        self,
        responses,
    ):
        self.responses = list(
            responses
        )

        self.execute_calls = 0

    def execute(
        self,
        command: str,
    ) -> str:
        self.execute_calls += 1

        return (
            self.responses.pop(
                0
            )
        )


# ======================================================
# RETRY CLASSIFICATION
# ======================================================


def test_not_found_response_is_retryable():
    executor = (
        TaskExecutor()
    )

    assert (
        executor
        ._ui_click_response_retryable(
            (
                "I couldn't find a unique visible "
                "UI Automation target for "
                "'new tab menu item'. "
                "No click was performed."
            )
        )
        is True
    )


def test_ambiguous_response_is_not_retryable():
    executor = (
        TaskExecutor()
    )

    assert (
        executor
        ._ui_click_response_retryable(
            (
                "I found multiple possible matches "
                "for 'search'. Please specify the "
                "exact control. No click was performed."
            )
        )
        is False
    )


def test_confirmation_required_response_is_not_retryable():
    executor = (
        TaskExecutor()
    )

    assert (
        executor
        ._ui_click_response_retryable(
            (
                "'Delete' may perform a sensitive "
                "or destructive action. "
                "No click was performed. "
                "To proceed, send exactly: "
                "confirm click abc123"
            )
        )
        is False
    )


# ======================================================
# DIRECT RETRY HELPER
# ======================================================


def test_retry_ui_click_succeeds_after_focus_recovery(
    monkeypatch,
):
    executor = (
        TaskExecutor()
    )

    executor.WORKFLOW_UI_RETRY_DELAY_SECONDS = (
        0.0
    )

    skill = (
        UIAutomationClickSkill(
            [
                (
                    "Clicked 'File' (MenuItem) "
                    "at screen position (10, 10)."
                ),
            ]
        )
    )

    monkeypatch.setattr(
        executor,
        "_recover_step_focus",
        lambda **kwargs: (
            True,
            "focus recovered",
        ),
    )

    monkeypatch.setattr(
        executor_module.time,
        "sleep",
        lambda _: None,
    )

    (
        response,
        runtime_output,
        ok,
        reason,
    ) = (
        executor
        ._retry_ui_click_step(
            skill=skill,
            step=(
                _step(
                    2,
                    "click file menu item",
                    "UIAutomationClickSkill",
                )
            ),
            resolutions=(),
            focus_owner=(
                object()
            ),
            focus_context=(
                object()
            ),
        )
    )

    assert (
        ok
        is True
    )

    assert (
        response.startswith(
            "Clicked "
        )
    )

    assert (
        runtime_output
        is None
    )

    assert (
        reason
        == ""
    )

    assert (
        skill.execute_calls
        == 1
    )


def test_retry_ui_click_stops_if_focus_recovery_fails(
    monkeypatch,
):
    executor = (
        TaskExecutor()
    )

    skill = (
        UIAutomationClickSkill(
            [
                (
                    "Clicked 'File' (MenuItem) "
                    "at screen position (10, 10)."
                ),
            ]
        )
    )

    monkeypatch.setattr(
        executor,
        "_recover_step_focus",
        lambda **kwargs: (
            False,
            "focus could not be recovered",
        ),
    )

    (
        response,
        runtime_output,
        ok,
        reason,
    ) = (
        executor
        ._retry_ui_click_step(
            skill=skill,
            step=(
                _step(
                    2,
                    "click file menu item",
                    "UIAutomationClickSkill",
                )
            ),
            resolutions=(),
            focus_owner=(
                object()
            ),
            focus_context=(
                object()
            ),
        )
    )

    assert (
        ok
        is False
    )

    assert (
        response
        == ""
    )

    assert (
        runtime_output
        is None
    )

    assert (
        "could not be recovered"
        in reason
    )

    assert (
        skill.execute_calls
        == 0
    )


def test_retry_ui_click_does_not_repeat_nonretryable_result(
    monkeypatch,
):
    executor = (
        TaskExecutor()
    )

    executor.WORKFLOW_UI_RETRY_ATTEMPTS = (
        2
    )

    executor.WORKFLOW_UI_RETRY_DELAY_SECONDS = (
        0.0
    )

    skill = (
        UIAutomationClickSkill(
            [
                (
                    "I found multiple possible "
                    "matches. No click was performed."
                ),
                (
                    "Clicked 'File' (MenuItem) "
                    "at screen position (10, 10)."
                ),
            ]
        )
    )

    monkeypatch.setattr(
        executor,
        "_recover_step_focus",
        lambda **kwargs: (
            True,
            "focus recovered",
        ),
    )

    monkeypatch.setattr(
        executor_module.time,
        "sleep",
        lambda _: None,
    )

    (
        response,
        _,
        ok,
        reason,
    ) = (
        executor
        ._retry_ui_click_step(
            skill=skill,
            step=(
                _step(
                    2,
                    "click file menu item",
                    "UIAutomationClickSkill",
                )
            ),
            resolutions=(),
            focus_owner=(
                object()
            ),
            focus_context=(
                object()
            ),
        )
    )

    assert (
        ok
        is False
    )

    assert (
        "multiple possible"
        in response.lower()
    )

    assert (
        reason
        == response
    )

    assert (
        skill.execute_calls
        == 1
    )


# ======================================================
# FULL EXECUTOR FLOW
# ======================================================


def test_executor_retries_transient_ui_click_once(
    monkeypatch,
):
    launcher = (
        AppLauncherSkill()
    )

    click_skill = (
        UIAutomationClickSkill(
            [
                (
                    "I couldn't find a unique visible "
                    "UI Automation target for "
                    "'file menu item'. "
                    "No click was performed."
                ),
                (
                    "Clicked 'File' (MenuItem) "
                    "at screen position (10, 10)."
                ),
            ]
        )
    )

    mapping = {
        "open notepad":
            launcher,

        "click file menu item":
            click_skill,
    }

    monkeypatch.setattr(
        skill_registry,
        "find_skill",
        lambda command: (
            mapping.get(
                command
            )
        ),
    )

    monkeypatch.setattr(
        executor_module.time,
        "sleep",
        lambda _: None,
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
        result.blocked
        is False
    )

    assert (
        result.stopped_at
        is None
    )

    assert (
        click_skill.execute_calls
        == 2
    )

    # One recovery occurs before the original click and
    # one more before the bounded workflow retry.
    assert (
        launcher.recovery_calls
        == 2
    )