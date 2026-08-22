from dataclasses import dataclass

from app.core.task_runtime import (
    StepRuntimeOutput,
)


@dataclass(frozen=True)
class SkillExecution:
    response: str
    runtime_output: StepRuntimeOutput | None = None