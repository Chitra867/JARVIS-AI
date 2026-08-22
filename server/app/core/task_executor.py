from dataclasses import dataclass
from enum import Enum

from app.core.task_validator import (
    ValidatedPlan,
    task_validator,
)

from app.skills.action_guard_skill import (
    ActionGuardSkill,
)

from app.skills.registry import (
    skill_registry,
)


class ExecutionStatus(
    str,
    Enum,
):
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class StepExecutionResult:
    index: int
    command: str
    handler: str | None
    status: ExecutionStatus
    response: str


@dataclass(frozen=True)
class TaskExecutionResult:
    original_command: str
    success: bool
    blocked: bool
    stopped_at: int | None
    steps: tuple[
        StepExecutionResult,
        ...
    ]


class TaskExecutor:
    FAILURE_PREFIXES = (
        "i couldn't ",
        "i could not ",
        "i can't ",
        "i cannot ",
        "failed ",
        "error ",
        "unable to ",
    )

    # ==================================================
    # EXECUTE COMMAND
    # ==================================================

    def execute(
        self,
        command: str,
    ) -> TaskExecutionResult:
        validated_plan = (
            task_validator
            .validate(
                command
            )
        )

        return self.execute_plan(
            validated_plan
        )

    # ==================================================
    # EXECUTE VALIDATED PLAN
    # ==================================================

    def execute_plan(
        self,
        plan: ValidatedPlan,
    ) -> TaskExecutionResult:
        # ----------------------------------------------
        # NEVER partially execute an unsafe plan.
        # ----------------------------------------------

        if not plan.is_safe_to_execute:
            return TaskExecutionResult(
                original_command=(
                    plan.original_command
                ),
                success=False,
                blocked=True,
                stopped_at=None,
                steps=(),
            )

        executed_steps: list[
            StepExecutionResult
        ] = []

        for step in plan.steps:
            skill = (
                skill_registry
                .find_skill(
                    step.command
                )
            )

            # ------------------------------------------
            # Handler disappeared after validation.
            # Fail closed.
            # ------------------------------------------

            if skill is None:
                executed_steps.append(
                    StepExecutionResult(
                        index=step.index,
                        command=step.command,
                        handler=None,
                        status=(
                            ExecutionStatus.FAILED
                        ),
                        response=(
                            "No handler is available "
                            "for this step."
                        ),
                    )
                )

                return TaskExecutionResult(
                    original_command=(
                        plan.original_command
                    ),
                    success=False,
                    blocked=False,
                    stopped_at=step.index,
                    steps=tuple(
                        executed_steps
                    ),
                )

            # ------------------------------------------
            # Guard skills must never execute inside
            # an already validated task plan.
            # ------------------------------------------

            if isinstance(
                skill,
                ActionGuardSkill,
            ):
                executed_steps.append(
                    StepExecutionResult(
                        index=step.index,
                        command=step.command,
                        handler=(
                            type(skill).__name__
                        ),
                        status=(
                            ExecutionStatus.BLOCKED
                        ),
                        response=(
                            "Execution blocked because "
                            "the step has no real action skill."
                        ),
                    )
                )

                return TaskExecutionResult(
                    original_command=(
                        plan.original_command
                    ),
                    success=False,
                    blocked=True,
                    stopped_at=step.index,
                    steps=tuple(
                        executed_steps
                    ),
                )

            # ------------------------------------------
            # Ensure the handler still matches what
            # validation approved.
            # ------------------------------------------

            actual_handler = (
                type(skill).__name__
            )

            if (
                step.handler is not None
                and actual_handler
                != step.handler
            ):
                executed_steps.append(
                    StepExecutionResult(
                        index=step.index,
                        command=step.command,
                        handler=(
                            actual_handler
                        ),
                        status=(
                            ExecutionStatus.FAILED
                        ),
                        response=(
                            "Handler changed after "
                            "task validation."
                        ),
                    )
                )

                return TaskExecutionResult(
                    original_command=(
                        plan.original_command
                    ),
                    success=False,
                    blocked=False,
                    stopped_at=step.index,
                    steps=tuple(
                        executed_steps
                    ),
                )

            # ------------------------------------------
            # EXECUTE STEP
            # ------------------------------------------

            try:
                response = (
                    skill.execute(
                        step.command
                    )
                )

            except Exception as error:
                executed_steps.append(
                    StepExecutionResult(
                        index=step.index,
                        command=step.command,
                        handler=(
                            actual_handler
                        ),
                        status=(
                            ExecutionStatus.FAILED
                        ),
                        response=(
                            f"Step failed: "
                            f"{type(error).__name__}"
                        ),
                    )
                )

                return TaskExecutionResult(
                    original_command=(
                        plan.original_command
                    ),
                    success=False,
                    blocked=False,
                    stopped_at=step.index,
                    steps=tuple(
                        executed_steps
                    ),
                )

            clean_response = str(
                response
            ).strip()

            # ------------------------------------------
            # FAIL FAST
            # ------------------------------------------

            if self._response_indicates_failure(
                clean_response
            ):
                executed_steps.append(
                    StepExecutionResult(
                        index=step.index,
                        command=step.command,
                        handler=(
                            actual_handler
                        ),
                        status=(
                            ExecutionStatus.FAILED
                        ),
                        response=(
                            clean_response
                        ),
                    )
                )

                return TaskExecutionResult(
                    original_command=(
                        plan.original_command
                    ),
                    success=False,
                    blocked=False,
                    stopped_at=step.index,
                    steps=tuple(
                        executed_steps
                    ),
                )

            executed_steps.append(
                StepExecutionResult(
                    index=step.index,
                    command=step.command,
                    handler=(
                        actual_handler
                    ),
                    status=(
                        ExecutionStatus.SUCCESS
                    ),
                    response=(
                        clean_response
                    ),
                )
            )

        return TaskExecutionResult(
            original_command=(
                plan.original_command
            ),
            success=True,
            blocked=False,
            stopped_at=None,
            steps=tuple(
                executed_steps
            ),
        )

    # ==================================================
    # FAILURE DETECTION
    # ==================================================

    def _response_indicates_failure(
        self,
        response: str,
    ) -> bool:
        normalized = (
            response
            .strip()
            .lower()
        )

        if not normalized:
            return True

        return normalized.startswith(
            self.FAILURE_PREFIXES
        )


task_executor = TaskExecutor()