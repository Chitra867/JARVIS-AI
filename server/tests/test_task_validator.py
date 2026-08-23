import unittest

from app.core.task_context import (
    ReferenceType,
)

from app.core.task_validator import (
    StepType,
    TaskValidator,
)


class TaskValidatorTests(
    unittest.TestCase
):
    def setUp(
        self,
    ) -> None:
        self.validator = (
            TaskValidator()
        )

    # ==================================================
    # SUPPORTED MULTI-STEP PLAN
    # ==================================================

    def test_supported_two_step_plan_is_safe(
        self,
    ) -> None:
        result = (
            self.validator
            .validate(
                (
                    "open chrome and then "
                    "search Python decorators"
                )
            )
        )

        self.assertTrue(
            result.is_multi_step
        )

        self.assertTrue(
            result.is_safe_to_execute
        )

        self.assertEqual(
            len(
                result.steps
            ),
            2,
        )

        self.assertEqual(
            result.steps[0].handler,
            "AppLauncherSkill",
        )

        self.assertEqual(
            result.steps[1].handler,
            "SearchSkill",
        )

        self.assertTrue(
            result.steps[0].allowed
        )

        self.assertTrue(
            result.steps[1].allowed
        )

    # ==================================================
    # UNSUPPORTED ACTION
    # ==================================================

    def test_unsupported_action_blocks_plan(
        self,
    ) -> None:
        result = (
            self.validator
            .validate(
                (
                    "open chrome and then "
                    "turn off wifi"
                )
            )
        )

        self.assertFalse(
            result.is_safe_to_execute
        )

        self.assertEqual(
            len(
                result.blocked_steps
            ),
            1,
        )

        self.assertEqual(
            result
            .blocked_steps[0]
            .command,
            "turn off wifi",
        )

    # ==================================================
    # UI ACTION
    # ==================================================

    def test_type_action_is_blocked(
        self,
    ) -> None:
        result = (
            self.validator
            .validate(
                (
                    "open notepad then "
                    "type hello"
                )
            )
        )

        self.assertFalse(
            result.is_safe_to_execute
        )

        self.assertEqual(
            result.steps[1].step_type,
            StepType.BLOCKED,
        )

        self.assertFalse(
            result.steps[1].allowed
        )

    # ==================================================
    # SINGLE AI STEP
    # ==================================================

    def test_ai_reasoning_step_is_allowed(
        self,
    ) -> None:
        result = (
            self.validator
            .validate(
                (
                    "explain dependency "
                    "injection"
                )
            )
        )

        self.assertTrue(
            result.is_safe_to_execute
        )

        self.assertEqual(
            result.steps[0].step_type,
            StepType.AI,
        )

        self.assertEqual(
            result.steps[0].handler,
            "AISkill",
        )

        self.assertTrue(
            result.steps[0].allowed
        )

    # ==================================================
    # AI INSIDE MULTI-STEP PLAN
    # ==================================================

    def test_ai_step_inside_multi_step_plan_is_blocked(
        self,
    ) -> None:
        result = (
            self.validator
            .validate(
                (
                    "open chrome then "
                    "explain dependency "
                    "injection"
                )
            )
        )

        self.assertTrue(
            result.is_multi_step
        )

        self.assertFalse(
            result.is_safe_to_execute
        )

        self.assertEqual(
            result.steps[0].step_type,
            StepType.SKILL,
        )

        self.assertEqual(
            result.steps[0].handler,
            "AppLauncherSkill",
        )

        self.assertTrue(
            result.steps[0].allowed
        )

        self.assertEqual(
            result.steps[1].step_type,
            StepType.BLOCKED,
        )

        self.assertEqual(
            result.steps[1].handler,
            "AISkill",
        )

        self.assertFalse(
            result.steps[1].allowed
        )

        self.assertIn(
            "AI reasoning cannot yet",
            result.steps[1].reason,
        )

    # ==================================================
    # RESOLVED CONTEXT REFERENCE
    # ==================================================

    def test_resolved_context_reference_is_allowed(
        self,
    ) -> None:
        result = (
            self.validator
            .validate(
                (
                    "search google for FastAPI "
                    "then open the first result"
                )
            )
        )

        # --------------------------------------------------
        # PLAN
        # --------------------------------------------------

        self.assertTrue(
            result.is_multi_step
        )

        self.assertTrue(
            result.is_safe_to_execute
        )

        self.assertEqual(
            len(
                result.steps
            ),
            2,
        )

        # --------------------------------------------------
        # SEARCH STEP
        # --------------------------------------------------

        search_step = (
            result.steps[0]
        )

        self.assertEqual(
            search_step.index,
            1,
        )

        self.assertEqual(
            search_step.command,
            (
                "search google "
                "for FastAPI"
            ),
        )

        self.assertEqual(
            search_step.step_type,
            StepType.SKILL,
        )

        self.assertEqual(
            search_step.handler,
            "SearchSkill",
        )

        self.assertTrue(
            search_step.allowed
        )

        self.assertEqual(
            search_step.references,
            (),
        )

        # --------------------------------------------------
        # OPEN-FIRST-RESULT STEP
        # --------------------------------------------------

        open_step = (
            result.steps[1]
        )

        self.assertEqual(
            open_step.index,
            2,
        )

        self.assertEqual(
            open_step.command,
            (
                "open the first "
                "result"
            ),
        )

        self.assertEqual(
            open_step.step_type,
            StepType.SKILL,
        )

        self.assertEqual(
            open_step.handler,
            "PageOpenSkill",
        )

        self.assertTrue(
            open_step.allowed
        )

        # --------------------------------------------------
        # RUNTIME REFERENCE
        # --------------------------------------------------

        self.assertEqual(
            len(
                open_step.references
            ),
            1,
        )

        reference = (
            open_step.references[0]
        )

        self.assertEqual(
            reference.reference_type,
            (
                ReferenceType
                .FIRST_SEARCH_RESULT
            ),
        )

        self.assertEqual(
            reference.raw_text.lower(),
            "the first result",
        )

        self.assertEqual(
            reference.source_step_index,
            1,
        )

        self.assertTrue(
            reference.is_resolved
        )

    # ==================================================
    # ORPHAN CONTEXT REFERENCE
    # ==================================================

    def test_orphan_context_reference_is_blocked(
        self,
    ) -> None:
        result = (
            self.validator
            .validate(
                (
                    "open the first "
                    "result"
                )
            )
        )

        self.assertFalse(
            result.is_safe_to_execute
        )

        self.assertEqual(
            len(
                result.steps
            ),
            1,
        )

        step = (
            result.steps[0]
        )

        self.assertEqual(
            step.step_type,
            StepType.BLOCKED,
        )

        self.assertFalse(
            step.allowed
        )

        self.assertIsNone(
            step.handler
        )

        self.assertIn(
            "no earlier source step",
            step.reason,
        )

        # Reference still exists, but there is no
        # previous search step capable of producing
        # its runtime value.
        self.assertEqual(
            len(
                step.references
            ),
            1,
        )

        reference = (
            step.references[0]
        )

        self.assertEqual(
            reference.reference_type,
            (
                ReferenceType
                .FIRST_SEARCH_RESULT
            ),
        )

        self.assertIsNone(
            reference.source_step_index
        )

        self.assertFalse(
            reference.is_resolved
        )

    # ==================================================
    # EMPTY PLAN
    # ==================================================

    def test_empty_plan_is_not_safe(
        self,
    ) -> None:
        result = (
            self.validator
            .validate(
                "   "
            )
        )

        self.assertFalse(
            result.is_safe_to_execute
        )

        self.assertEqual(
            result.steps,
            (),
        )


if __name__ == "__main__":
    unittest.main()