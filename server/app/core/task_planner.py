import re

from dataclasses import (
    dataclass,
)


# =========================================================
# TASK STEP
# =========================================================


@dataclass(
    frozen=True
)
class TaskStep:
    index: int
    command: str


# =========================================================
# TASK PLAN
# =========================================================


@dataclass(
    frozen=True
)
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
            len(
                self.steps
            )
            > 1
        )


# =========================================================
# TASK PLANNER
# =========================================================


class TaskPlanner:
    MAX_STEPS = 8

    DELIMITER = (
        "|||JARVIS_STEP|||"
    )

    # =====================================================
    # KNOWN ACTION STARTS
    # =====================================================
    #
    # These are used only to determine whether punctuation,
    # "and", "then", etc. actually separate two commands.
    #
    # IMPORTANT:
    #
    # "confirm" and "cancel" are included because safety
    # confirmations must always become their own task step.
    #
    # Example:
    #
    # click delete button and confirm click abc123
    #
    # must become:
    #
    # 1. click delete button
    # 2. confirm click abc123
    #
    # The validator can then enforce the separate-turn
    # confirmation barrier.
    # =====================================================

    STEP_START_PATTERN = (
        r"(?:"
        r"open"
        r"|save"
        r"|choose"
        r"|browse"
        r"|launch"
        r"|start"
        r"|close"
        r"|play"
        r"|pause"
        r"|resume"
        r"|stop"
        r"|browser\s+search"
        r"|search\s+browser"
        r"|browser\s+back"
        r"|browser\s+forward"
        r"|browser\s+refresh"
        r"|refresh\s+browser"
        r"|new\s+browser\s+tab"
        r"|navigate"
        r"|go\s+to"
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
        r"|confirm"
        r"|cancel"
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

    # =====================================================
    # EXPLICIT SEQUENCE LANGUAGE
    # =====================================================
    #
    # A sequencing word is only treated as a separator when
    # another recognized action follows it.
    #
    # This prevents accidental splitting of text such as:
    #
    # search next.js documentation
    #
    # because ".js documentation" is not another action.
    # =====================================================

    SEQUENCE_PATTERN = re.compile(
        (
            r"\s*"
            r"(?:"
            r"\band\s+then\b"
            r"|\bafter\s+that\b"
            r"|\bonce\s+that\s+is\s+done\b"
            r"|\bafterwards?\b"
            r"|\bthen\b"
            r"|\bfinally\b"
            r"|\bnext\b"
            r")"
            r"[\s,:;-]*"
            r"(?="
            + STEP_START_PATTERN
            + r")"
        ),
        flags=re.IGNORECASE,
    )

    # =====================================================
    # COMMA / SEMICOLON BETWEEN ACTIONS
    # =====================================================
    #
    # Examples:
    #
    # open chrome, search Python
    #
    # open notepad; type hello
    #
    # But:
    #
    # search React, Vue and Angular
    #
    # stays as one search request because "Vue" does not
    # begin another recognized action.
    # =====================================================

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

    # =====================================================
    # PLAIN "AND" BETWEEN ACTIONS
    # =====================================================
    #
    # Examples:
    #
    # open notepad and type hello
    #
    # click delete and confirm click abc123
    #
    # But:
    #
    # search React and Vue
    #
    # remains one step.
    # =====================================================

    ACTION_AND_PATTERN = re.compile(
        (
            r"\s+\band\b\s+"
            r"(?="
            + STEP_START_PATTERN
            + r")"
        ),
        flags=re.IGNORECASE,
    )

    # =====================================================
    # LEADING SEQUENCE WORDS
    # =====================================================

    LEADING_MARKERS = re.compile(
        (
            r"^(?:"
            r"first(?:ly)?"
            r"|next"
            r"|then"
            r"|finally"
            r"|afterwards?"
            r")"
            r"[\s,:;-]*"
        ),
        flags=re.IGNORECASE,
    )

    # =====================================================
    # PLAN
    # =====================================================

    def plan(
        self,
        command: str,
    ) -> TaskPlan:
        original = (
            command
            .strip()
        )

        if not (
            original
        ):
            return TaskPlan(
                original_command="",
                steps=(),
            )

        # Normalize repeated whitespace before attempting
        # to detect step boundaries.
        working = (
            re.sub(
                r"\s+",
                " ",
                original,
            )
            .strip()
        )

        # =================================================
        # EXPLICIT SEQUENCING
        # =================================================
        #
        # open chrome then search Python
        #
        # open notepad and then type hello
        # =================================================

        working = (
            self.SEQUENCE_PATTERN
            .sub(
                self.DELIMITER,
                working,
            )
        )

        # =================================================
        # COMMA / SEMICOLON SEQUENCING
        # =================================================
        #
        # open chrome, search Python
        #
        # open notepad; type hello
        # =================================================

        working = (
            self.COMMA_SEQUENCE_PATTERN
            .sub(
                self.DELIMITER,
                working,
            )
        )

        # =================================================
        # NATURAL "AND" SEQUENCING
        # =================================================
        #
        # open YouTube and search tutorial
        #
        # click delete and confirm click abc123
        # =================================================

        working = (
            self.ACTION_AND_PATTERN
            .sub(
                self.DELIMITER,
                working,
            )
        )

        # =================================================
        # SPLIT
        # =================================================

        raw_parts = (
            working
            .split(
                self.DELIMITER
            )
        )

        cleaned_parts: list[
            str
        ] = []

        for part in (
            raw_parts
        ):
            cleaned = (
                part
                .strip()
                .strip(
                    ",;"
                )
                .strip()
            )

            # Remove leftover sequencing markers from the
            # beginning of a newly created step.
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
                .strip(
                    ",;"
                )
                .strip()
            )

            if not (
                cleaned
            ):
                continue

            cleaned_parts.append(
                cleaned
            )

        if not (
            cleaned_parts
        ):
            return TaskPlan(
                original_command=(
                    original
                ),
                steps=(),
            )

        # =================================================
        # STEP LIMIT
        # =================================================
        #
        # Prevent one command from producing an excessively
        # large deterministic execution chain.
        # =================================================

        if (
            len(
                cleaned_parts
            )
            > self.MAX_STEPS
        ):
            cleaned_parts = (
                cleaned_parts[
                    :self.MAX_STEPS
                ]
            )

        # =================================================
        # APPLY CROSS-STEP CONTEXT
        # =================================================

        contextual_parts = (
            self._apply_step_context(
                cleaned_parts
            )
        )

        # =================================================
        # BUILD IMMUTABLE PLAN
        # =================================================

        steps = tuple(
            TaskStep(
                index=index,
                command=step,
            )
            for index, step
            in enumerate(
                contextual_parts,
                start=1,
            )
        )

        return TaskPlan(
            original_command=(
                original
            ),
            steps=steps,
        )

    # =====================================================
    # STEP CONTEXT
    # =====================================================

    def _apply_step_context(
        self,
        steps: list[
            str
        ],
    ) -> list[
        str
    ]:
        contextual_steps: list[
            str
        ] = []

        active_search_provider: (
            str
            | None
        ) = None

        for step in (
            steps
        ):
            cleaned = (
                step
                .strip()
            )

            normalized = (
                cleaned
                .lower()
                .rstrip(
                    "?.!"
                )
                .strip()
            )

            # =================================================
            # OPEN / LAUNCH YOUTUBE
            # =================================================

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

            # =================================================
            # OPEN / LAUNCH GOOGLE / CHROME
            # =================================================

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

            # =================================================
            # OPEN / LAUNCH OTHER SUPPORTED BROWSERS
            # =================================================

            if normalized in {
                "open edge",
                "launch edge",
                "start edge",
                "open microsoft edge",
                "launch microsoft edge",
                "start microsoft edge",
                "open firefox",
                "launch firefox",
                "start firefox",
                "open brave",
                "launch brave",
                "start brave",
            }:
                active_search_provider = (
                    "browser"
                )

                contextual_steps.append(
                    cleaned
                )

                continue

            # =================================================
            # EXPLICIT YOUTUBE SEARCH
            # =================================================

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

            # =================================================
            # EXPLICIT GOOGLE SEARCH
            # =================================================

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

            # =================================================
            # EXPLICIT BROWSER SEARCH
            # =================================================

            if (
                normalized.startswith(
                    "browser search for "
                )
                or normalized.startswith(
                    "browser search "
                )
                or normalized.startswith(
                    "search browser for "
                )
                or normalized.startswith(
                    "search browser "
                )
            ):
                active_search_provider = (
                    "browser"
                )

                contextual_steps.append(
                    cleaned
                )

                continue

            # =================================================
            # GENERIC SEARCH
            # =================================================

            generic_prefixes = (
                "search for ",
                "search ",
            )

            matched_prefix: (
                str
                | None
            ) = None

            for prefix in (
                generic_prefixes
            ):
                if (
                    normalized.startswith(
                        prefix
                    )
                ):
                    matched_prefix = (
                        prefix
                    )

                    break

            # -------------------------------------------------
            # YouTube context inheritance
            # -------------------------------------------------
            #
            # open youtube and search cats
            #
            # becomes:
            #
            # 1. open youtube
            # 2. search youtube for cats
            # -------------------------------------------------

            if (
                matched_prefix
                is not None
                and active_search_provider
                == "youtube"
            ):
                query = (
                    cleaned[
                        len(
                            matched_prefix
                        ):
                    ]
                    .strip()
                    .rstrip(
                        "?.!"
                    )
                    .strip()
                )

                if (
                    query
                ):
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

            # -------------------------------------------------
            # Generic web search
            # -------------------------------------------------
            #
            # Keep ordinary "search ..." commands unchanged.
            # SearchSkill owns generic web-search semantics.
            #
            # BrowserNavigationSkill is used only when the user
            # explicitly says "browser search ..." or
            # "search browser ...".
            # -------------------------------------------------

            contextual_steps.append(
                cleaned
            )

        return (
            contextual_steps
        )


task_planner = (
    TaskPlanner()
)