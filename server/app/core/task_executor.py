from dataclasses import (
    dataclass,
)

from enum import (
    Enum,
)

from app.core.conversation import (
    conversation_manager,
)

from app.core.task_runtime import (
    ReferenceResolution,
    RuntimeOutputType,
    StepRuntimeOutput,
    TaskRuntimeContext,
    page_context_store,
    task_reference_resolver,
)

from app.core.task_validator import (
    ValidatedPlan,
    ValidatedStep,
    task_validator,
)

from app.skills.action_guard_skill import (
    ActionGuardSkill,
)

from app.skills.registry import (
    skill_registry,
)


# =========================================================
# EXECUTION STATUS
# =========================================================


class ExecutionStatus(
    str,
    Enum,
):
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"


# =========================================================
# STEP RESULT
# =========================================================


@dataclass(
    frozen=True
)
class StepExecutionResult:
    index: int
    command: str
    handler: str | None
    status: ExecutionStatus
    response: str


# =========================================================
# TASK RESULT
# =========================================================


@dataclass(
    frozen=True
)
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


# =========================================================
# EXECUTOR
# =========================================================


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

    # =====================================================
    # EXECUTE RAW COMMAND
    # =====================================================

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

        return (
            self.execute_plan(
                validated_plan
            )
        )

    # =====================================================
    # EXECUTE VALIDATED PLAN
    # =====================================================

    def execute_plan(
        self,
        plan: ValidatedPlan,
    ) -> TaskExecutionResult:
        runtime_context = (
            TaskRuntimeContext()
        )

        # =================================================
        # NEVER PARTIALLY EXECUTE AN UNSAFE PLAN
        # =================================================

        if not (
            plan.is_safe_to_execute
        ):
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

        # =================================================
        # EXECUTE IN ORDER
        # =================================================

        for step in (
            plan.steps
        ):
            skill = (
                skill_registry
                .find_skill(
                    step.command
                )
            )

            # =================================================
            # HANDLER DISAPPEARED AFTER VALIDATION
            # =================================================

            if skill is None:
                executed_steps.append(
                    StepExecutionResult(
                        index=(
                            step.index
                        ),
                        command=(
                            step.command
                        ),
                        handler=None,
                        status=(
                            ExecutionStatus
                            .FAILED
                        ),
                        response=(
                            "No handler is available "
                            "for this step."
                        ),
                    )
                )

                return (
                    self._failure_result(
                        plan=plan,
                        executed_steps=(
                            executed_steps
                        ),
                        runtime_context=(
                            runtime_context
                        ),
                        stopped_at=(
                            step.index
                        ),
                        blocked=False,
                    )
                )

            # =================================================
            # ACTION GUARD MUST NEVER EXECUTE
            # =================================================

            if isinstance(
                skill,
                ActionGuardSkill,
            ):
                executed_steps.append(
                    StepExecutionResult(
                        index=(
                            step.index
                        ),
                        command=(
                            step.command
                        ),
                        handler=(
                            type(
                                skill
                            ).__name__
                        ),
                        status=(
                            ExecutionStatus
                            .BLOCKED
                        ),
                        response=(
                            "Execution blocked because "
                            "the step has no real "
                            "action skill."
                        ),
                    )
                )

                return (
                    self._failure_result(
                        plan=plan,
                        executed_steps=(
                            executed_steps
                        ),
                        runtime_context=(
                            runtime_context
                        ),
                        stopped_at=(
                            step.index
                        ),
                        blocked=True,
                    )
                )

            # =================================================
            # VERIFY HANDLER DID NOT CHANGE
            # =================================================

            actual_handler = (
                type(
                    skill
                ).__name__
            )

            if (
                step.handler
                is not None
                and actual_handler
                != step.handler
            ):
                executed_steps.append(
                    StepExecutionResult(
                        index=(
                            step.index
                        ),
                        command=(
                            step.command
                        ),
                        handler=(
                            actual_handler
                        ),
                        status=(
                            ExecutionStatus
                            .FAILED
                        ),
                        response=(
                            "Handler changed after "
                            "task validation."
                        ),
                    )
                )

                return (
                    self._failure_result(
                        plan=plan,
                        executed_steps=(
                            executed_steps
                        ),
                        runtime_context=(
                            runtime_context
                        ),
                        stopped_at=(
                            step.index
                        ),
                        blocked=False,
                    )
                )

            # =================================================
            # RESOLVE RUNTIME REFERENCES
            # =================================================

            resolutions = (
                self._resolve_references(
                    step=step,
                    runtime_context=(
                        runtime_context
                    ),
                )
            )

            if (
                resolutions
                is None
            ):
                executed_steps.append(
                    StepExecutionResult(
                        index=(
                            step.index
                        ),
                        command=(
                            step.command
                        ),
                        handler=(
                            actual_handler
                        ),
                        status=(
                            ExecutionStatus
                            .BLOCKED
                        ),
                        response=(
                            "Unable to safely resolve "
                            "the required runtime "
                            "reference."
                        ),
                    )
                )

                return (
                    self._failure_result(
                        plan=plan,
                        executed_steps=(
                            executed_steps
                        ),
                        runtime_context=(
                            runtime_context
                        ),
                        stopped_at=(
                            step.index
                        ),
                        blocked=True,
                    )
                )

            # =================================================
            # EXECUTE STEP
            # =================================================

            try:
                (
                    response,
                    explicit_runtime_output,
                ) = (
                    self._execute_step(
                        skill=skill,
                        step=step,
                        resolutions=(
                            resolutions
                        ),
                    )
                )

            except Exception as error:
                executed_steps.append(
                    StepExecutionResult(
                        index=(
                            step.index
                        ),
                        command=(
                            step.command
                        ),
                        handler=(
                            actual_handler
                        ),
                        status=(
                            ExecutionStatus
                            .FAILED
                        ),
                        response=(
                            "Step failed: "
                            f"{type(error).__name__}"
                        ),
                    )
                )

                return (
                    self._failure_result(
                        plan=plan,
                        executed_steps=(
                            executed_steps
                        ),
                        runtime_context=(
                            runtime_context
                        ),
                        stopped_at=(
                            step.index
                        ),
                        blocked=False,
                    )
                )

            clean_response = (
                str(
                    response
                )
                .strip()
            )

            # =================================================
            # FAIL FAST
            # =================================================

            if (
                self
                ._response_indicates_failure(
                    clean_response
                )
            ):
                executed_steps.append(
                    StepExecutionResult(
                        index=(
                            step.index
                        ),
                        command=(
                            step.command
                        ),
                        handler=(
                            actual_handler
                        ),
                        status=(
                            ExecutionStatus
                            .FAILED
                        ),
                        response=(
                            clean_response
                        ),
                    )
                )

                return (
                    self._failure_result(
                        plan=plan,
                        executed_steps=(
                            executed_steps
                        ),
                        runtime_context=(
                            runtime_context
                        ),
                        stopped_at=(
                            step.index
                        ),
                        blocked=False,
                    )
                )

            # =================================================
            # RUNTIME OUTPUT
            # =================================================

            runtime_output = (
                explicit_runtime_output
            )

            if (
                runtime_output
                is None
            ):
                runtime_output = (
                    self._build_runtime_output(
                        skill=skill,
                        step_index=(
                            step.index
                        ),
                        command=(
                            step.command
                        ),
                        response=(
                            clean_response
                        ),
                    )
                )

            # Never let a skill publish data as if it
            # belonged to another task step.
            if (
                runtime_output
                .step_index
                != step.index
            ):
                executed_steps.append(
                    StepExecutionResult(
                        index=(
                            step.index
                        ),
                        command=(
                            step.command
                        ),
                        handler=(
                            actual_handler
                        ),
                        status=(
                            ExecutionStatus
                            .FAILED
                        ),
                        response=(
                            "Runtime output step "
                            "index mismatch."
                        ),
                    )
                )

                return (
                    self._failure_result(
                        plan=plan,
                        executed_steps=(
                            executed_steps
                        ),
                        runtime_context=(
                            runtime_context
                        ),
                        stopped_at=(
                            step.index
                        ),
                        blocked=False,
                    )
                )

            # =================================================
            # RECORD PER-TASK RUNTIME OUTPUT
            # =================================================

            runtime_context.record(
                runtime_output
            )

            # =================================================
            # REMEMBER ACTIVE WEBPAGE
            # =================================================
            #
            # PAGE output must survive beyond this single
            # TaskRuntimeContext so a later command can say:
            #
            # "What are its advantages?"
            #
            # and AISkill can use the previously opened page.
            # =================================================

            if (
                runtime_output
                .output_type
                == RuntimeOutputType.PAGE
                and runtime_output.page
                is not None
                and runtime_output.page.url
                .strip()
            ):
                page_context_store.record(
                    page=(
                        runtime_output.page
                    ),
                    conversation_id=(
                        conversation_manager
                        .get_active_conversation_id()
                    ),
                )

            # =================================================
            # SUCCESS
            # =================================================

            executed_steps.append(
                StepExecutionResult(
                    index=(
                        step.index
                    ),
                    command=(
                        step.command
                    ),
                    handler=(
                        actual_handler
                    ),
                    status=(
                        ExecutionStatus
                        .SUCCESS
                    ),
                    response=(
                        clean_response
                    ),
                )
            )

        # =====================================================
        # COMPLETE SUCCESS
        # =====================================================

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

    # =====================================================
    # RESOLVE REFERENCES
    # =====================================================

    def _resolve_references(
        self,
        step: ValidatedStep,
        runtime_context:
            TaskRuntimeContext,
    ) -> (
        tuple[
            ReferenceResolution,
            ...
        ]
        | None
    ):
        if not (
            step.references
        ):
            return ()

        resolutions: list[
            ReferenceResolution
        ] = []

        for reference in (
            step.references
        ):
            resolution = (
                task_reference_resolver
                .resolve(
                    reference,
                    runtime_context,
                )
            )

            if not (
                resolution.resolved
            ):
                return None

            resolutions.append(
                resolution
            )

        return tuple(
            resolutions
        )

    # =====================================================
    # EXECUTE ONE STEP
    # =====================================================

    def _execute_step(
        self,
        skill: object,
        step: ValidatedStep,
        resolutions: tuple[
            ReferenceResolution,
            ...
        ],
    ) -> tuple[
        str,
        StepRuntimeOutput | None,
    ]:
        # -------------------------------------------------
        # CONTEXTUAL EXECUTION
        # -------------------------------------------------

        if resolutions:
            contextual_executor = (
                getattr(
                    skill,
                    "execute_with_references",
                    None,
                )
            )

            if not callable(
                contextual_executor
            ):
                raise RuntimeError(
                    (
                        "Context-aware skill "
                        "execution is unavailable."
                    )
                )

            result = (
                contextual_executor(
                    step.index,
                    step.command,
                    resolutions,
                )
            )

            if (
                not isinstance(
                    result,
                    tuple,
                )
                or len(
                    result
                )
                != 2
            ):
                raise RuntimeError(
                    (
                        "Context-aware skill returned "
                        "an invalid execution result."
                    )
                )

            response = (
                str(
                    result[
                        0
                    ]
                )
            )

            runtime_output = (
                result[
                    1
                ]
            )

            if (
                runtime_output
                is not None
                and not isinstance(
                    runtime_output,
                    StepRuntimeOutput,
                )
            ):
                raise RuntimeError(
                    (
                        "Context-aware skill returned "
                        "an invalid runtime output."
                    )
                )

            return (
                response,
                runtime_output,
            )

        # -------------------------------------------------
        # NORMAL EXECUTION
        # -------------------------------------------------

        normal_executor = (
            getattr(
                skill,
                "execute",
                None,
            )
        )

        if not callable(
            normal_executor
        ):
            raise RuntimeError(
                (
                    "Skill has no executable "
                    "handler."
                )
            )

        return (
            str(
                normal_executor(
                    step.command
                )
            ),
            None,
        )

    # =====================================================
    # BUILD RUNTIME OUTPUT
    # =====================================================

    def _build_runtime_output(
        self,
        skill: object,
        step_index: int,
        command: str,
        response: str,
    ) -> StepRuntimeOutput:
        builder = (
            getattr(
                skill,
                "build_runtime_output",
                None,
            )
        )

        if callable(
            builder
        ):
            try:
                output = (
                    builder(
                        step_index,
                        command,
                        response,
                    )
                )

                if isinstance(
                    output,
                    StepRuntimeOutput,
                ):
                    if (
                        output.step_index
                        == step_index
                    ):
                        return output

            except Exception as error:
                print(
                    (
                        "Runtime output builder "
                        "failed for "
                        f"{type(skill).__name__}: "
                        f"{error}"
                    )
                )

        return StepRuntimeOutput(
            step_index=(
                step_index
            ),
            output_type=(
                RuntimeOutputType.TEXT
            ),
            text=(
                response
            ),
        )

    # =====================================================
    # FAILURE RESULT
    # =====================================================

    def _failure_result(
        self,
        plan: ValidatedPlan,
        executed_steps: list[
            StepExecutionResult
        ],
        runtime_context:
            TaskRuntimeContext,
        stopped_at: int,
        blocked: bool,
    ) -> TaskExecutionResult:
        return TaskExecutionResult(
            original_command=(
                plan.original_command
            ),
            success=False,
            blocked=(
                blocked
            ),
            stopped_at=(
                stopped_at
            ),
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

    # =====================================================
    # FAILURE DETECTION
    # =====================================================

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

        return (
            normalized
            .startswith(
                self.FAILURE_PREFIXES
            )
        )

    # =====================================================
    # RUNTIME OUTPUT SNAPSHOT
    # =====================================================

    def _runtime_outputs(
        self,
        runtime_context:
            TaskRuntimeContext,
        plan: ValidatedPlan,
    ) -> tuple[
        StepRuntimeOutput,
        ...
    ]:
        outputs: list[
            StepRuntimeOutput
        ] = []

        for step in (
            plan.steps
        ):
            output = (
                runtime_context
                .get(
                    step.index
                )
            )

            if (
                output
                is not None
            ):
                outputs.append(
                    output
                )

        return tuple(
            outputs
        )


task_executor = (
    TaskExecutor()
)