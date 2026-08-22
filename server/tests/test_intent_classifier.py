import unittest

from app.core.intent_classifier import (
    IntentClassifier,
    IntentType,
)


class IntentClassifierTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.classifier = (
            IntentClassifier()
        )

    # ==================================================
    # DETERMINISTIC SKILL PRIORITY
    # ==================================================

    def test_matching_skill_has_highest_priority(
        self,
    ) -> None:
        result = (
            self.classifier
            .classify(
                "open chrome",
                has_matching_skill=True,
            )
        )

        self.assertEqual(
            result.intent,
            IntentType.SKILL,
        )

        self.assertEqual(
            result.confidence,
            1.0,
        )

    # ==================================================
    # GENERAL AI REQUEST
    # ==================================================

    def test_general_question_routes_to_ai(
        self,
    ) -> None:
        result = (
            self.classifier
            .classify(
                "Explain dependency injection"
            )
        )

        self.assertEqual(
            result.intent,
            IntentType.AI,
        )

    # ==================================================
    # UNSUPPORTED REAL-WORLD ACTION
    # ==================================================

    def test_unsupported_action_is_detected(
        self,
    ) -> None:
        result = (
            self.classifier
            .classify(
                "turn off wifi"
            )
        )

        self.assertEqual(
            result.intent,
            IntentType.ACTION,
        )

    # ==================================================
    # UI / KEYBOARD ACTION
    # ==================================================

    def test_type_command_is_action(
        self,
    ) -> None:
        result = (
            self.classifier
            .classify(
                "type hello"
            )
        )

        self.assertEqual(
            result.intent,
            IntentType.ACTION,
        )

    # ==================================================
    # MULTI-STEP: AND THEN
    # ==================================================

    def test_multi_step_command_is_detected(
        self,
    ) -> None:
        result = (
            self.classifier
            .classify(
                (
                    "open chrome and then "
                    "search for Python decorators"
                )
            )
        )

        self.assertEqual(
            result.intent,
            IntentType.MULTI_STEP,
        )

    # ==================================================
    # MULTI-STEP: THEN
    # ==================================================

    def test_then_sequence_is_multi_step(
        self,
    ) -> None:
        result = (
            self.classifier
            .classify(
                "open notepad then type hello"
            )
        )

        self.assertEqual(
            result.intent,
            IntentType.MULTI_STEP,
        )

    # ==================================================
    # EMPTY COMMAND
    # ==================================================

    def test_empty_command_has_zero_confidence(
        self,
    ) -> None:
        result = (
            self.classifier
            .classify(
                "   "
            )
        )

        self.assertEqual(
            result.intent,
            IntentType.AI,
        )

        self.assertEqual(
            result.confidence,
            0.0,
        )


if __name__ == "__main__":
    unittest.main()