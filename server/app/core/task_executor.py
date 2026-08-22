from dataclasses import dataclass
from enum import Enum

from app.core.task_runtime import (
    RuntimeOutputType,
    StepRuntimeOutput,
    TaskRuntimeContext,
)

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

    runtime_outputs: tuple[
        StepRuntimeOutput,
        ...
    ] = ()


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
        runtime_context = (
            TaskRuntimeContext()
        )

        # ==================================================
        # NEVER PARTIALLY EXECUTE AN UNSAFE PLAN
        # ==================================================

        if not plan.is_safe_to_execute:
            return TaskExecutionResult(
                original_command=(
                    plan.original_command
                ),
                success=False,
                blocked=True,
                stopped_at=None,
                steps=(),
                runtime_outputs=(),
            )

        executed_steps: list[
            StepExecutionResult
        ] = []

        # ==================================================
        # EXECUTE STEPS IN ORDER
        # ==================================================

        for step in plan.steps:
            skill = (
                skill_registry
                .find_skill(
                    step.command
                )
            )

            # ==================================================
            # HANDLER DISAPPEARED AFTER VALIDATION
            # ==================================================

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
                    runtime_outputs=(
                        self._runtime_outputs(
                            runtime_context,
                            plan,
                        )
                    ),
                )

            # ==================================================
            # GUARD SKILL MUST NEVER EXECUTE
            # ==================================================

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
                    runtime_outputs=(
                        self._runtime_outputs(
                            runtime_context,
                            plan,
                        )
                    ),
                )

            # ==================================================
            # VERIFY HANDLER DID NOT CHANGE
            # ==================================================

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
                    runtime_outputs=(
                        self._runtime_outputs(
                            runtime_context,
                            plan,
                        )
                    ),
                )

            # ==================================================
            # EXECUTE STEP
            # ==================================================

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
                    runtime_outputs=(
                        self._runtime_outputs(
                            runtime_context,
                            plan,
                        )
                    ),
                )

            clean_response = (
                str(
                    response
                )
                .strip()
            )

            # ==================================================
            # FAIL FAST
            # ==================================================

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
                    runtime_outputs=(
                        self._runtime_outputs(
                            runtime_context,
                            plan,
                        )
                    ),
                )

            # ==================================================
            # RECORD STRUCTURED RUNTIME OUTPUT
            # ==================================================
            #
            # For now all ordinary successful skills publish
            # TEXT output.
            #
            # Later SearchSkill can publish SEARCH_RESULTS,
            # and an actual page-opening skill can publish PAGE.
            #
            # We deliberately do NOT pretend that opening a
            # Google search page means structured search results
            # have already been extracted.

            runtime_context.record(
                StepRuntimeOutput(
                    step_index=step.index,
                    output_type=(
                        RuntimeOutputType.TEXT
                    ),
                    text=clean_response,
                )
            )

            # ==================================================
            # RECORD SUCCESS
            # ==================================================

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

        # ==================================================
        # COMPLETE SUCCESS
        # ==================================================

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
            runtime_outputs=(
                self._runtime_outputs(
                    runtime_context,
                    plan,
                )
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

    # ==================================================
    # RUNTIME OUTPUT SNAPSHOT
    # ==================================================

    def _runtime_outputs(
        self,
        runtime_context: TaskRuntimeContext,
        plan: ValidatedPlan,
    ) -> tuple[
        StepRuntimeOutput,
        ...
    ]:
        outputs: list[
            StepRuntimeOutput
        ] = []

        for step in plan.steps:
            output = (
                runtime_context
                .get(
                    step.index
                )
            )

            if output is not None:
                outputs.append(
                    output
                )

        return tuple(
            outputs
        )


task_executor = TaskExecutor()