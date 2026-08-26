from types import (
    SimpleNamespace,
)

from app.core.task_executor import (
    ExecutionStatus,
    TaskExecutor,
)

from app.skills.registry import (
    skill_registry,
)


def _step(
    index,
    command,
    handler,
):
    return SimpleNamespace(
        index=index,
        command=command,
        handler=handler,
        references=(),
    )


def _plan(
    *steps,
):
    return SimpleNamespace(
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


class AppLauncherSkill:
    def __init__(
        self,
        *,
        recovery_result=(
            True,
            "",
        ),
    ):
        self.context = object()
        self.recovery_result = recovery_result
        self.recovery_calls = []

    def execute(
        self,
        command,
    ):
        return "Opening chrome."

    def wait_until_ready(
        self,
        command,
    ):
        return (
            True,
            "",
        )

    def get_focus_context(
        self,
        command,
    ):
        return self.context

    def recover_focus_context(
        self,
        context,
    ):
        self.recovery_calls.append(
            context
        )

        return self.recovery_result


class BrowserNavigationSkill:
    def __init__(
        self,
    ):
        self.executed = []

    def execute(
        self,
        command,
    ):
        self.executed.append(
            command
        )

        return (
            "Navigating to https://example.com."
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


def test_browser_navigation_skill_is_focus_sensitive():
    executor = TaskExecutor()

    assert (
        "BrowserNavigationSkill"
        in executor.FOCUS_SENSITIVE_HANDLERS
    )


def test_executor_recovers_focus_before_browser_navigation(
    monkeypatch,
):
    launcher = AppLauncherSkill()
    browser = BrowserNavigationSkill()

    _install_registry(
        monkeypatch,
        {
            "open chrome":
                launcher,

            "navigate to https://example.com":
                browser,
        },
    )

    result = (
        TaskExecutor()
        .execute_plan(
            _plan(
                _step(
                    1,
                    "open chrome",
                    "AppLauncherSkill",
                ),
                _step(
                    2,
                    "navigate to https://example.com",
                    "BrowserNavigationSkill",
                ),
            )
        )
    )

    assert result.success is True
    assert result.blocked is False

    assert (
        launcher.recovery_calls
        == [
            launcher.context,
        ]
    )

    assert (
        browser.executed
        == [
            "navigate to https://example.com",
        ]
    )


def test_executor_blocks_browser_navigation_when_focus_recovery_fails(
    monkeypatch,
):
    launcher = AppLauncherSkill(
        recovery_result=(
            False,
            (
                "The expected browser window "
                "could not be safely restored."
            ),
        )
    )

    browser = BrowserNavigationSkill()

    _install_registry(
        monkeypatch,
        {
            "open chrome":
                launcher,

            "navigate to https://example.com":
                browser,
        },
    )

    result = (
        TaskExecutor()
        .execute_plan(
            _plan(
                _step(
                    1,
                    "open chrome",
                    "AppLauncherSkill",
                ),
                _step(
                    2,
                    "navigate to https://example.com",
                    "BrowserNavigationSkill",
                ),
            )
        )
    )

    assert result.success is False
    assert result.blocked is True
    assert result.stopped_at == 2

    assert (
        browser.executed
        == []
    )

    assert (
        result.steps[
            -1
        ].status
        == ExecutionStatus.BLOCKED
    )
