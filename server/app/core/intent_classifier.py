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
    # REAL-WORLD / COMPUTER ACTION PATTERNS
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

        # UI / keyboard / mouse actions
        "type ",
        "press ",
        "click ",
        "scroll ",
        "drag ",
        "select ",
    )

    # ==================================================
    # MULTI-STEP MARKERS
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

        # A verified deterministic skill always wins.
        if has_matching_skill:
            return IntentResult(
                intent=IntentType.SKILL,
                confidence=1.0,
                reason=(
                    "deterministic skill matched"
                ),
            )

        # Detect sequential/multi-step work before
        # classifying individual actions.
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

        # An action without a matching real skill
        # must not silently fall through to AI.
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

        # Everything else is conversational,
        # explanatory, analytical, or reasoning work.
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
        # Explicit sequence language is the
        # strongest multi-step signal.
        if any(
            marker in command
            for marker
            in self.MULTI_STEP_MARKERS
        ):
            return True

        # Also detect commands containing multiple
        # independently recognizable action phrases.
        action_count = sum(
            1
            for prefix
            in self.ACTION_PREFIXES
            if prefix in command
        )

        return (
            action_count >= 2
        )


intent_classifier = IntentClassifier()