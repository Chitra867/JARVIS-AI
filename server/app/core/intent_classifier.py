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
    ACTION_PREFIXES = (
        "open ",
        "launch ",
        "start ",
        "close ",
        "play ",
        "pause ",
        "stop ",
        "search ",
        "download ",
        "upload ",
        "install ",
        "uninstall ",
        "delete ",
        "remove ",
        "send ",
        "email ",
        "message ",
        "call ",
        "turn on ",
        "turn off ",
        "enable ",
        "disable ",
        "lock ",
        "shutdown ",
        "restart ",
        "reboot ",
        "take screenshot",
        "capture screenshot",
    )

    MULTI_STEP_MARKERS = (
        " and then ",
        " then ",
        " after that ",
        " once that is done ",
        " first ",
        " finally ",
    )

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
                reason="deterministic skill matched",
            )

        if self._looks_multi_step(
            normalized
        ):
            return IntentResult(
                intent=IntentType.MULTI_STEP,
                confidence=0.9,
                reason="multiple sequential actions detected",
            )

        if normalized.startswith(
            self.ACTION_PREFIXES
        ):
            return IntentResult(
                intent=IntentType.ACTION,
                confidence=0.95,
                reason="real-world action pattern detected",
            )

        return IntentResult(
            intent=IntentType.AI,
            confidence=0.8,
            reason="conversational or reasoning request",
        )

    def _looks_multi_step(
        self,
        command: str,
    ) -> bool:
        marker_count = sum(
            1
            for marker in self.MULTI_STEP_MARKERS
            if marker in command
        )

        if marker_count > 0:
            return True

        action_count = sum(
            1
            for prefix in self.ACTION_PREFIXES
            if prefix in command
        )

        return action_count >= 2


intent_classifier = IntentClassifier()