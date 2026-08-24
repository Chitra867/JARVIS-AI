from app.core.task_executor import (
    ExecutionStatus,
    TaskExecutor,
)

from app.core.task_validator import (
    StepType,
    ValidatedPlan,
    ValidatedStep,
)


# ======================================================
# TEST SKILLS
# ======================================================


class FakeLauncherSkill:
    def __init__(
        self,
        *,
        ready: bool = True,
        reason: str = "Application is ready.",
    ) -> None:
        self.ready = ready
        self.reason = reason

        self.execute_calls: list[
            str
        ] = []

        self.wait_calls: list[
            str
        ] = []

    def execute(
        self,
        command: str,
    ) -> str:
        self.execute_calls.append(
            command
        )

        return (
            "Opening notepad."
        )

    def wait_until_ready(
        self,
        command: str,
    ) -> tuple[
        bool,
        str,
    ]:
        self.wait_calls.append(
            command
        )

        return (
            self.ready,
            self.reason,
        )


class FakeInputSkill:
    def __init__(
        self,
    ) -> None:
        self.execute_calls: list[
            str
        ] = []

    def execute(
        self,
        command: str,
    ) -> str:
        self.execute_calls.append(
            command
        )

        return (
            "Typed text."
        )


# ======================================================
# PLAN HELPERS
# ======================================================


def _step(
    *,
    index: int,
    command: str,
    handler: str,
) -> ValidatedStep:
    return (
        ValidatedStep(
            index=index,
            command=command,
            step_type=(
                StepType.SKILL
            ),
            handler=handler,
            allowed=True,
            reason=(
                "test"
            ),
            references=(),
        )
    )


def _two_step_plan() -> ValidatedPlan:
    return (
        ValidatedPlan(
            original_command=(
                "open notepad then type hello"
            ),
            steps=(
                _step(
                    index=1,
                    command="open notepad",
                    handler="FakeLauncherSkill",
                ),

                _step(
                    index=2,
                    command="type hello",
                    handler="FakeInputSkill",
                ),
            ),
        )
    )


# ======================================================
# READY → CONTINUE
# ======================================================


def test_executor_waits_for_ready_step_before_continuing(
    monkeypatch,
):
    executor = (
        TaskExecutor()
    )

    launcher = (
        FakeLauncherSkill(
            ready=True,
        )
    )

    input_skill = (
        FakeInputSkill()
    )

    def find_skill(
        command: str,
    ):
        if (
            command
            == "open notepad"
        ):
            return launcher

        if (
            command
            == "type hello"
        ):
            return input_skill

        return None

    monkeypatch.setattr(
        (
            "app.core.task_executor."
            "skill_registry.find_skill"
        ),
        find_skill,
    )

    result = (
        executor.execute_plan(
            _two_step_plan()
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
        launcher.execute_calls
        == [
            "open notepad",
        ]
    )

    assert (
        launcher.wait_calls
        == [
            "open notepad",
        ]
    )

    assert (
        input_skill.execute_calls
        == [
            "type hello",
        ]
    )

    assert len(
        result.steps
    ) == 2

    assert all(
        step.status
        == ExecutionStatus.SUCCESS
        for step
        in result.steps
    )


# ======================================================
# TIMEOUT / NOT READY → STOP
# ======================================================


def test_executor_stops_before_next_step_when_readiness_fails(
    monkeypatch,
):
    executor = (
        TaskExecutor()
    )

    launcher = (
        FakeLauncherSkill(
            ready=False,
            reason=(
                "Timed out waiting for "
                "notepad to become ready."
            ),
        )
    )

    input_skill = (
        FakeInputSkill()
    )

    def find_skill(
        command: str,
    ):
        if (
            command
            == "open notepad"
        ):
            return launcher

        if (
            command
            == "type hello"
        ):
            return input_skill

        return None

    monkeypatch.setattr(
        (
            "app.core.task_executor."
            "skill_registry.find_skill"
        ),
        find_skill,
    )

    result = (
        executor.execute_plan(
            _two_step_plan()
        )
    )

    assert (
        result.success
        is False
    )

    assert (
        result.blocked
        is False
    )

    assert (
        result.stopped_at
        == 1
    )

    assert (
        launcher.wait_calls
        == [
            "open notepad",
        ]
    )

    assert (
        input_skill.execute_calls
        == []
    )

    assert len(
        result.steps
    ) == 1

    assert (
        result.steps[
            0
        ].status
        == ExecutionStatus.FAILED
    )

    assert (
        "timed out"
        in result.steps[
            0
        ].response.lower()
    )


# ======================================================
# SINGLE STEP → DO NOT WAIT
# ======================================================


def test_single_step_does_not_invoke_readiness_wait(
    monkeypatch,
):
    executor = (
        TaskExecutor()
    )

    launcher = (
        FakeLauncherSkill(
            ready=False,
        )
    )

    monkeypatch.setattr(
        (
            "app.core.task_executor."
            "skill_registry.find_skill"
        ),
        lambda _: launcher,
    )

    plan = (
        ValidatedPlan(
            original_command=(
                "open notepad"
            ),
            steps=(
                _step(
                    index=1,
                    command="open notepad",
                    handler="FakeLauncherSkill",
                ),
            ),
        )
    )

    result = (
        executor.execute_plan(
            plan
        )
    )

    assert (
        result.success
        is True
    )

    assert (
        launcher.execute_calls
        == [
            "open notepad",
        ]
    )

    assert (
        launcher.wait_calls
        == []
    )


# ======================================================
# SKILL WITHOUT READINESS HOOK → CONTINUE
# ======================================================


def test_skill_without_readiness_hook_continues_normally():
    executor = (
        TaskExecutor()
    )

    skill = (
        FakeInputSkill()
    )

    ready, reason = (
        executor
        ._wait_for_step_readiness(
            skill=skill,
            command="type hello",
        )
    )

    assert (
        ready
        is True
    )

    assert (
        reason
        == ""
    )


# ======================================================
# INVALID READINESS RESULT → FAIL CLOSED
# ======================================================


def test_invalid_readiness_result_fails_closed():
    executor = (
        TaskExecutor()
    )

    class InvalidSkill:
        def wait_until_ready(
            self,
            command: str,
        ):
            return (
                "yes"
            )

    ready, reason = (
        executor
        ._wait_for_step_readiness(
            skill=(
                InvalidSkill()
            ),
            command=(
                "open notepad"
            ),
        )
    )

    assert (
        ready
        is False
    )

    assert (
        "invalid result"
        in reason.lower()
    )


def test_non_boolean_readiness_status_fails_closed():
    executor = (
        TaskExecutor()
    )

    class InvalidSkill:
        def wait_until_ready(
            self,
            command: str,
        ):
            return (
                "yes",
                "ready",
            )

    ready, reason = (
        executor
        ._wait_for_step_readiness(
            skill=(
                InvalidSkill()
            ),
            command=(
                "open notepad"
            ),
        )
    )

    assert (
        ready
        is False
    )

    assert (
        "invalid status"
        in reason.lower()
    )


# ======================================================
# READINESS EXCEPTION → FAIL CLOSED
# ======================================================


def test_readiness_exception_fails_closed():
    executor = (
        TaskExecutor()
    )

    class BrokenSkill:
        def wait_until_ready(
            self,
            command: str,
        ):
            raise RuntimeError(
                "boom"
            )

    ready, reason = (
        executor
        ._wait_for_step_readiness(
            skill=(
                BrokenSkill()
            ),
            command=(
                "open notepad"
            ),
        )
    )

    assert (
        ready
        is False
    )

    assert (
        "readiness check failed"
        in reason.lower()
    )