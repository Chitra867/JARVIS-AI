import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TaskStep:
    index: int
    command: str


@dataclass(frozen=True)
class TaskPlan:
    original_command: str
    steps: tuple[
        TaskStep,
        ...
    ]

    @property
    def is_multi_step(
        self,
    ) -> bool:
        return (
            len(self.steps) > 1
        )


class TaskPlanner:
    MAX_STEPS = 8

    DELIMITER = "|||JARVIS_STEP|||"

    # ==================================================
    # STEP STARTS
    # ==================================================

    STEP_START_PATTERN = (
        r"(?:"
        r"open"
        r"|launch"
        r"|start"
        r"|close"
        r"|play"
        r"|pause"
        r"|resume"
        r"|stop"
        r"|search"
        r"|find"
        r"|show"
        r"|create"
        r"|make"
        r"|delete"
        r"|remove"
        r"|rename"
        r"|move"
        r"|copy"
        r"|paste"
        r"|download"
        r"|upload"
        r"|install"
        r"|uninstall"
        r"|send"
        r"|email"
        r"|message"
        r"|call"
        r"|turn\s+on"
        r"|turn\s+off"
        r"|enable"
        r"|disable"
        r"|increase"
        r"|decrease"
        r"|set\s+volume"
        r"|mute"
        r"|unmute"
        r"|lock"
        r"|shutdown"
        r"|restart"
        r"|reboot"
        r"|sleep"
        r"|take\s+screenshot"
        r"|capture\s+screenshot"
        r"|type"
        r"|press"
        r"|click"
        r"|scroll"
        r"|drag"
        r"|select"
        r"|explain"
        r"|summarize"
        r"|compare"
        r"|recommend"
        r"|suggest"
        r"|review"
        r"|evaluate"
        r"|write"
        r"|generate"
        r"|calculate"
        r"|compute"
        r"|translate"
        r")\b"
    )

    # ==================================================
    # EXPLICIT SEQUENCE LANGUAGE
    # ==================================================

    SEQUENCE_PATTERN = re.compile(
        r"\s*(?:"
        r"\band\s+then\b"
        r"|\bafter\s+that\b"
        r"|\bonce\s+that\s+is\s+done\b"
        r"|\bthen\b"
        r"|\bfinally\b"
        r"|\bnext\b"
        r")\s*",
        flags=re.IGNORECASE,
    )

    # ==================================================
    # COMMA / SEMICOLON BETWEEN ACTIONS
    # ==================================================

    COMMA_SEQUENCE_PATTERN = re.compile(
        (
            r"\s*[,;]\s*"
            r"(?="
            r"(?:(?:next|then|finally)\s+)?"
            + STEP_START_PATTERN
            + r")"
        ),
        flags=re.IGNORECASE,
    )

    # ==================================================
    # PLAIN "AND" BETWEEN ACTIONS
    # ==================================================

    ACTION_AND_PATTERN = re.compile(
        (
            r"\s+\band\b\s+"
            r"(?="
            + STEP_START_PATTERN
            + r")"
        ),
        flags=re.IGNORECASE,
    )

    # ==================================================
    # LEADING SEQUENCE WORDS
    # ==================================================

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

    # ==================================================
    # PLAN
    # ==================================================

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

        working = re.sub(
            r"\s+",
            " ",
            original,
        ).strip()

        # --------------------------------------------------
        # Explicit sequencing
        #
        # open chrome THEN search Python
        # --------------------------------------------------

        working = (
            self.SEQUENCE_PATTERN
            .sub(
                self.DELIMITER,
                working,
            )
        )

        # --------------------------------------------------
        # Comma-separated actions
        #
        # open chrome, search Python
        #
        # But not:
        #
        # search React, Vue and Angular
        # --------------------------------------------------

        working = (
            self.COMMA_SEQUENCE_PATTERN
            .sub(
                self.DELIMITER,
                working,
            )
        )

        # --------------------------------------------------
        # Natural "and" between commands
        #
        # open YouTube and search for tutorial
        #
        # But not:
        #
        # search React and Vue
        # --------------------------------------------------

        working = (
            self.ACTION_AND_PATTERN
            .sub(
                self.DELIMITER,
                working,
            )
        )

        raw_parts = (
            working
            .split(
                self.DELIMITER
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

            cleaned = (
                cleaned
                .strip(",;")
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

        # ==================================================
        # APPLY CONTEXT BETWEEN STEPS
        # ==================================================

        cleaned_parts = (
            self._apply_step_context(
                cleaned_parts
            )
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

    # ==================================================
    # STEP CONTEXT
    # ==================================================

    def _apply_step_context(
        self,
        steps: list[str],
    ) -> list[str]:
        contextual_steps: list[str] = []

        active_search_provider: (
            str | None
        ) = None

        for step in steps:
            cleaned = (
                step
                .strip()
            )

            normalized = (
                cleaned
                .lower()
                .rstrip("?.!")
                .strip()
            )

            # ==================================================
            # OPEN / LAUNCH PROVIDERS
            # ==================================================

            if normalized in {
                "open youtube",
                "launch youtube",
                "start youtube",
            }:
                active_search_provider = (
                    "youtube"
                )

                contextual_steps.append(
                    cleaned
                )

                continue

            if normalized in {
                "open chrome",
                "launch chrome",
                "start chrome",
                "open google",
                "launch google",
                "start google",
            }:
                active_search_provider = (
                    "google"
                )

                contextual_steps.append(
                    cleaned
                )

                continue

            # ==================================================
            # EXPLICIT YOUTUBE SEARCH
            # ==================================================

            if (
                normalized.startswith(
                    "search youtube for "
                )
                or normalized.startswith(
                    "youtube search "
                )
            ):
                active_search_provider = (
                    "youtube"
                )

                contextual_steps.append(
                    cleaned
                )

                continue

            # ==================================================
            # EXPLICIT GOOGLE SEARCH
            # ==================================================

            if (
                normalized.startswith(
                    "search google for "
                )
                or normalized.startswith(
                    "google "
                )
            ):
                active_search_provider = (
                    "google"
                )

                contextual_steps.append(
                    cleaned
                )

                continue

            # ==================================================
            # GENERIC SEARCH
            # ==================================================

            generic_prefixes = (
                "search for ",
                "search ",
            )

            matched_prefix: (
                str | None
            ) = None

            for prefix in generic_prefixes:
                if normalized.startswith(
                    prefix
                ):
                    matched_prefix = (
                        prefix
                    )

                    break

            # --------------------------------------------------
            # Generic search after YouTube inherits YouTube.
            # --------------------------------------------------

            if (
                matched_prefix is not None
                and active_search_provider
                == "youtube"
            ):
                query = (
                    cleaned[
                        len(matched_prefix):
                    ]
                    .strip()
                    .rstrip("?.!")
                    .strip()
                )

                if query:
                    contextual_steps.append(
                        (
                            "search youtube for "
                            f"{query}"
                        )
                    )

                else:
                    contextual_steps.append(
                        cleaned
                    )

                continue

            # --------------------------------------------------
            # Generic search after Chrome/Google remains
            # generic because SearchSkill already defaults
            # generic web search to Google.
            # --------------------------------------------------

            contextual_steps.append(
                cleaned
            )

        return contextual_steps


task_planner = TaskPlanner()