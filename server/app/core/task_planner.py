import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TaskStep:
    index: int
    command: str


@dataclass(frozen=True)
class TaskPlan:
    original_command: str
    steps: tuple[TaskStep, ...]

    @property
    def is_multi_step(self) -> bool:
        return len(self.steps) > 1


class TaskPlanner:
    MAX_STEPS = 8

    SEQUENCE_PATTERN = re.compile(
        r"\s*(?:"
        r"\band\s+then\b"
        r"|\bafter\s+that\b"
        r"|\bonce\s+that\s+is\s+done\b"
        r"|\bthen\b"
        r"|\bfinally\b"
        r")\s*",
        flags=re.IGNORECASE,
    )

    LEADING_MARKERS = re.compile(
        r"^(?:"
        r"first(?:ly)?"
        r"|next"
        r"|then"
        r"|finally"
        r")"
        r"[\s,:;-]*",
        flags=re.IGNORECASE,
    )

    def plan(
        self,
        command: str,
    ) -> TaskPlan:
        original = (
            command
            .strip()
        )

        if not original:
            return TaskPlan(
                original_command="",
                steps=(),
            )

        raw_parts = (
            self.SEQUENCE_PATTERN
            .split(
                original
            )
        )

        cleaned_parts: list[str] = []

        for part in raw_parts:
            cleaned = (
                part
                .strip()
                .strip(",;")
                .strip()
            )

            cleaned = (
                self.LEADING_MARKERS
                .sub(
                    "",
                    cleaned,
                )
                .strip()
            )

            if not cleaned:
                continue

            cleaned_parts.append(
                cleaned
            )

        if not cleaned_parts:
            return TaskPlan(
                original_command=original,
                steps=(),
            )

        if (
            len(cleaned_parts)
            > self.MAX_STEPS
        ):
            cleaned_parts = (
                cleaned_parts[
                    :self.MAX_STEPS
                ]
            )

        steps = tuple(
            TaskStep(
                index=index,
                command=step,
            )
            for index, step
            in enumerate(
                cleaned_parts,
                start=1,
            )
        )

        return TaskPlan(
            original_command=original,
            steps=steps,
        )


task_planner = TaskPlanner()