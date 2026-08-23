from dataclasses import (
    dataclass,
)

from enum import (
    Enum,
)

from app.core.intent_classifier import (
    IntentType,
    intent_classifier,
)

from app.core.task_context import (
    TaskReference,
    task_context_analyzer,
)

from app.core.task_planner import (
    TaskPlan,
    task_planner,
)

from app.skills.action_guard_skill import (
    ActionGuardSkill,
)

from app.skills.ai_skill import (
    AISkill,
)

from app.skills.registry import (
    skill_registry,
)


# =========================================================
# STEP TYPE
# =========================================================


class StepType(
    str,
    Enum,
):
    SKILL = "skill"
    AI = "ai"
    BLOCKED = "blocked"


# =========================================================
# VALIDATED STEP
# =========================================================


@dataclass(
    frozen=True
)
class ValidatedStep:
    index: int
    command: str
    step_type: StepType
    handler: str | None
    allowed: bool
    reason: str

    # Runtime dependencies attached to the step.
    references: tuple[
        TaskReference,
        ...
    ] = ()


# =========================================================
# VALIDATED PLAN
# =========================================================


@dataclass(
    frozen=True
)
class ValidatedPlan:
    original_command: str

    steps: tuple[
        ValidatedStep,
        ...
    ]

    @property
    def is_multi_step(
        self,
    ) -> bool:
        return (
            len(
                self.steps
            )
            > 1
        )

    @property
    def is_safe_to_execute(
        self,
    ) -> bool:
        return (
            bool(
                self.steps
            )
            and all(
                step.allowed
                for step
                in self.steps
            )
        )

    @property
    def blocked_steps(
        self,
    ) -> tuple[
        ValidatedStep,
        ...
    ]:
        return tuple(
            step
            for step
            in self.steps
            if not step.allowed
        )


# =========================================================
# VALIDATOR
# =========================================================


class TaskValidator:
    # =====================================================
    # VALIDATE RAW COMMAND
    # =====================================================

    def validate(
        self,
        command: str,
    ) -> ValidatedPlan:
        plan = (
            task_planner
            .plan(
                command
            )
        )

        return (
            self.validate_plan(
                plan
            )
        )

    # =====================================================
    # VALIDATE PLAN
    # =====================================================

    def validate_plan(
        self,
        plan: TaskPlan,
    ) -> ValidatedPlan:
        contextual_plan = (
            task_context_analyzer
            .analyze(
                plan
            )
        )

        validated_steps: list[
            ValidatedStep
        ] = []

        for step in (
            contextual_plan.steps
        ):
            # =================================================
            # UNRESOLVED DEPENDENCY SOURCE
            # =================================================
            #
            # Example:
            #
            # "open the first result"
            #
            # with no earlier search.
            #
            # This must remain fail-closed.
            # =================================================

            unresolved = any(
                not reference.is_resolved
                for reference
                in step.references
            )

            if unresolved:
                validated_steps.append(
                    ValidatedStep(
                        index=step.index,
                        command=step.command,
                        step_type=(
                            StepType.BLOCKED
                        ),
                        handler=None,
                        allowed=False,
                        reason=(
                            "Context reference has no "
                            "earlier source step."
                        ),
                        references=(
                            step.references
                        ),
                    )
                )

                continue

            # =================================================
            # NORMAL / RESOLVABLE STEP
            # =================================================
            #
            # At validation time we only establish that:
            #
            # 1. dependency source exists
            # 2. a deterministic skill can handle this step
            #
            # The actual SearchResult/PageResource value is
            # resolved later by TaskExecutor.
            # =================================================

            validated_steps.append(
                self._validate_step(
                    index=step.index,
                    command=step.command,
                    references=(
                        step.references
                    ),
                )
            )

        # =====================================================
        # BLOCK AI INSIDE MULTI-STEP EXECUTION
        # =====================================================
        #
        # We intentionally preserve your current safety rule.
        #
        # Therefore:
        #
        # search X -> open first result
        #
        # can now execute.
        #
        # But:
        #
        # search X -> open first result -> summarize that page
        #
        # remains blocked until AI substeps are integrated
        # with JARVIS conversation/memory lifecycle.
        # =====================================================

        if (
            len(
                validated_steps
            )
            > 1
            and any(
                step.step_type
                == StepType.AI
                for step
                in validated_steps
            )
        ):
            protected_steps: list[
                ValidatedStep
            ] = []

            for step in (
                validated_steps
            ):
                if (
                    step.step_type
                    == StepType.AI
                ):
                    protected_steps.append(
                        ValidatedStep(
                            index=step.index,
                            command=step.command,
                            step_type=(
                                StepType.BLOCKED
                            ),
                            handler=(
                                step.handler
                            ),
                            allowed=False,
                            reason=(
                                "AI reasoning cannot yet "
                                "run inside a multi-step "
                                "execution plan."
                            ),
                            references=(
                                step.references
                            ),
                        )
                    )

                else:
                    protected_steps.append(
                        step
                    )

            validated_steps = (
                protected_steps
            )

        return ValidatedPlan(
            original_command=(
                plan.original_command
            ),
            steps=tuple(
                validated_steps
            ),
        )

    # =====================================================
    # VALIDATE INDIVIDUAL STEP
    # =====================================================

    def _validate_step(
        self,
        index: int,
        command: str,
        references: tuple[
            TaskReference,
            ...
        ] = (),
    ) -> ValidatedStep:
        command = (
            command
            .strip()
        )

        if not command:
            return ValidatedStep(
                index=index,
                command=command,
                step_type=(
                    StepType.BLOCKED
                ),
                handler=None,
                allowed=False,
                reason=(
                    "Empty task step."
                ),
                references=(
                    references
                ),
            )

        skill = (
            skill_registry
            .find_skill(
                command
            )
        )

        # =====================================================
        # REAL DETERMINISTIC SKILL
        # =====================================================

        if (
            skill is not None
            and not isinstance(
                skill,
                (
                    AISkill,
                    ActionGuardSkill,
                ),
            )
        ):
            result = (
                intent_classifier
                .classify(
                    command,
                    has_matching_skill=True,
                )
            )

            return ValidatedStep(
                index=index,
                command=command,
                step_type=(
                    StepType.SKILL
                ),
                handler=(
                    type(
                        skill
                    ).__name__
                ),
                allowed=True,
                reason=(
                    result.reason
                ),
                references=(
                    references
                ),
            )

        # =====================================================
        # CLASSIFY NON-DETERMINISTIC STEP
        # =====================================================

        result = (
            intent_classifier
            .classify(
                command,
                has_matching_skill=False,
            )
        )

        # =====================================================
        # UNSUPPORTED REAL-WORLD ACTION
        # =====================================================

        if (
            isinstance(
                skill,
                ActionGuardSkill,
            )
            or (
                result.intent
                == IntentType.ACTION
            )
        ):
            return ValidatedStep(
                index=index,
                command=command,
                step_type=(
                    StepType.BLOCKED
                ),
                handler=(
                    type(
                        skill
                    ).__name__
                    if skill is not None
                    else None
                ),
                allowed=False,
                reason=(
                    "No real skill can safely "
                    "perform this action."
                ),
                references=(
                    references
                ),
            )

        # =====================================================
        # NESTED MULTI-STEP COMMAND
        # =====================================================

        if (
            result.intent
            == IntentType.MULTI_STEP
        ):
            return ValidatedStep(
                index=index,
                command=command,
                step_type=(
                    StepType.BLOCKED
                ),
                handler=None,
                allowed=False,
                reason=(
                    "Nested multi-step command "
                    "requires additional planning."
                ),
                references=(
                    references
                ),
            )

        # =====================================================
        # AI REASONING
        # =====================================================

        if isinstance(
            skill,
            AISkill,
        ):
            return ValidatedStep(
                index=index,
                command=command,
                step_type=(
                    StepType.AI
                ),
                handler="AISkill",
                allowed=True,
                reason=(
                    "Conversational reasoning "
                    "can be handled by AI."
                ),
                references=(
                    references
                ),
            )

        # =====================================================
        # NO HANDLER
        # =====================================================

        return ValidatedStep(
            index=index,
            command=command,
            step_type=(
                StepType.BLOCKED
            ),
            handler=None,
            allowed=False,
            reason=(
                "No handler is available "
                "for this step."
            ),
            references=(
                references
            ),
        )


task_validator = (
    TaskValidator()
)