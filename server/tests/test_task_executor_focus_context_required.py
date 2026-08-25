from unittest.mock import (
    patch,
)

from app.core.task_executor import (
    ExecutionStatus,
    TaskExecutor,
)

from app.core.task_validator import (
    StepType,
    ValidatedPlan,
    ValidatedStep,
)


class LauncherWithMissingFocusContext:
    def execute(
        self,
        command,
    ):
        return "Opening notepad."

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
        return None


class LauncherWithFocusContext:
    def __init__(
        self,
    ):
        self.context = object()

    def execute(
        self,
        command,
    ):
        return "Opening notepad."

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
        if (
            context
            is self.context
        ):
            return (
                True,
                "",
            )

        return (
            False,
            "Wrong context.",
        )


class FakeInputSkill:
    def execute(
        self,
        command,
    ):
        return "Typed 5 characters."


class FakeSearchSkill:
    def execute(
        self,
        command,
    ):
        return "Searching Google for Python."


def _step(
    index,
    command,
    handler,
):
    return ValidatedStep(
        index=index,
        command=command,
        step_type=StepType.SKILL,
        handler=handler,
        allowed=True,
        reason="test",
    )


def test_missing_launch_focus_context_blocks_focus_sensitive_handoff():
    executor = TaskExecutor()

    launcher = (
        LauncherWithMissingFocusContext()
    )

    input_skill = (
        FakeInputSkill()
    )

    plan = ValidatedPlan(
        original_command=(
            "open notepad then type hello"
        ),
        steps=(
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
        ),
    )

    with patch(
        "app.core.task_executor.skill_registry"
    ) as registry:
        registry.find_skill.side_effect = [
            launcher,
            input_skill,
        ]

        # Match the validated handler names exactly.
        launcher.__class__.__name__ = (
            "AppLauncherSkill"
        )

        input_skill.__class__.__name__ = (
            "InputControlSkill"
        )

        result = (
            executor.execute_plan(
                plan
            )
        )

    assert result.success is False
    assert result.blocked is True
    assert result.stopped_at == 1
    assert len(
        result.steps
    ) == 1
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


def test_missing_launch_focus_context_does_not_block_non_desktop_handoff():
    executor = TaskExecutor()

    launcher = (
        LauncherWithMissingFocusContext()
    )

    search_skill = (
        FakeSearchSkill()
    )

    plan = ValidatedPlan(
        original_command=(
            "open notepad then search Python"
        ),
        steps=(
            _step(
                1,
                "open notepad",
                "AppLauncherSkill",
            ),
            _step(
                2,
                "search Python",
                "SearchSkill",
            ),
        ),
    )

    with patch(
        "app.core.task_executor.skill_registry"
    ) as registry:
        registry.find_skill.side_effect = [
            launcher,
            search_skill,
        ]

        launcher.__class__.__name__ = (
            "AppLauncherSkill"
        )

        search_skill.__class__.__name__ = (
            "SearchSkill"
        )

        result = (
            executor.execute_plan(
                plan
            )
        )

    assert result.success is True
    assert result.blocked is False
    assert result.stopped_at is None
    assert len(
        result.steps
    ) == 2


def test_verified_launch_focus_context_allows_focus_sensitive_handoff():
    executor = TaskExecutor()

    launcher = (
        LauncherWithFocusContext()
    )

    input_skill = (
        FakeInputSkill()
    )

    plan = ValidatedPlan(
        original_command=(
            "open notepad then type hello"
        ),
        steps=(
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
        ),
    )

    with patch(
        "app.core.task_executor.skill_registry"
    ) as registry:
        registry.find_skill.side_effect = [
            launcher,
            input_skill,
        ]

        launcher.__class__.__name__ = (
            "AppLauncherSkill"
        )

        input_skill.__class__.__name__ = (
            "InputControlSkill"
        )

        result = (
            executor.execute_plan(
                plan
            )
        )

    assert result.success is True
    assert result.blocked is False
    assert result.stopped_at is None
    assert len(
        result.steps
    ) == 2