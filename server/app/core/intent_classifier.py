import re
from dataclasses import dataclass
from enum import Enum


class IntentType(str, Enum):
    SKILL = "skill"
    AI = "ai"
    ACTION = "action"
    MULTI_STEP = "multi_step"


@dataclass(frozen=True)
class IntentResult:
    intent: IntentType
    confidence: float
    reason: str


class IntentClassifier:
    # ==================================================
    # REAL COMPUTER ACTIONS
    # ==================================================

    ACTION_PREFIXES = (
        "open ",
        "launch ",
        "start ",
        "close ",
        "play ",
        "pause ",
        "resume ",
        "stop ",
        "search ",
        "download ",
        "upload ",
        "install ",
        "uninstall ",
        "delete ",
        "remove ",
        "rename ",
        "move ",
        "copy ",
        "paste ",
        "send ",
        "email ",
        "message ",
        "call ",
        "turn on ",
        "turn off ",
        "enable ",
        "disable ",
        "increase ",
        "decrease ",
        "set volume ",
        "mute ",
        "unmute ",
        "lock ",
        "shutdown ",
        "restart ",
        "reboot ",
        "sleep ",
        "take screenshot",
        "capture screenshot",
        "type ",
        "press ",
        "click ",
        "scroll ",
        "drag ",
        "select ",
    )

    # ==================================================
    # REASONING STEPS
    # ==================================================

    REASONING_PREFIXES = (
        "explain ",
        "summarize ",
        "compare ",
        "recommend ",
        "suggest ",
        "review ",
        "evaluate ",
        "write ",
        "generate ",
        "calculate ",
        "compute ",
        "translate ",
    )

    STEP_PREFIXES = (
        ACTION_PREFIXES
        + REASONING_PREFIXES
    )

    # ==================================================
    # EXPLICIT MULTI-STEP MARKERS
    # ==================================================

    MULTI_STEP_MARKERS = (
        " and then ",
        " then ",
        " after that ",
        " once that is done ",
        " finally ",
    )

    # ==================================================
    # CLASSIFY
    # ==================================================

    def classify(
        self,
        command: str,
        has_matching_skill: bool = False,
    ) -> IntentResult:
        normalized = (
            command
            .strip()
            .lower()
        )

        if not normalized:
            return IntentResult(
                intent=IntentType.AI,
                confidence=0.0,
                reason="empty command",
            )

        if has_matching_skill:
            return IntentResult(
                intent=IntentType.SKILL,
                confidence=1.0,
                reason=(
                    "deterministic skill matched"
                ),
            )

        if self._looks_multi_step(
            normalized
        ):
            return IntentResult(
                intent=IntentType.MULTI_STEP,
                confidence=0.9,
                reason=(
                    "multiple sequential "
                    "actions detected"
                ),
            )

        if normalized.startswith(
            self.ACTION_PREFIXES
        ):
            return IntentResult(
                intent=IntentType.ACTION,
                confidence=0.95,
                reason=(
                    "real-world action "
                    "pattern detected"
                ),
            )

        return IntentResult(
            intent=IntentType.AI,
            confidence=0.8,
            reason=(
                "conversational or "
                "reasoning request"
            ),
        )

    # ==================================================
    # MULTI-STEP DETECTION
    # ==================================================

    def _looks_multi_step(
        self,
        command: str,
    ) -> bool:
        if any(
            marker in command
            for marker
            in self.MULTI_STEP_MARKERS
        ):
            return True

        step_count = 0

        for prefix in self.STEP_PREFIXES:
            phrase = (
                prefix
                .strip()
            )

            if not phrase:
                continue

            pattern = (
                r"(?<![a-z0-9_])"
                + re.escape(
                    phrase
                )
                + r"(?=\s|$)"
            )

            occurrences = (
                re.findall(
                    pattern,
                    command,
                    flags=re.IGNORECASE,
                )
            )

            step_count += len(
                occurrences
            )

            if step_count >= 2:
                return True

        return False


intent_classifier = IntentClassifier()