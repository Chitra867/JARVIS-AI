import unittest
from unittest.mock import (
    MagicMock,
    patch,
)

from app.core.intent_classifier import (
    IntentResult,
    IntentType,
)

from app.core.jarvis import Jarvis

from app.core.task_executor import (
    ExecutionStatus,
    StepExecutionResult,
    TaskExecutionResult,
)


class JarvisMultiStepRegressionTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.jarvis = Jarvis()

    # ==================================================
    # MULTI-STEP ROUTING
    # ==================================================

    @patch(
        "app.core.jarvis.task_executor"
    )
    @patch(
        "app.core.jarvis.skill_registry"
    )
    @patch(
        "app.core.jarvis.intent_classifier"
    )
    def test_multi_step_routes_to_executor(
        self,
        mock_classifier,
        mock_registry,
        mock_executor,
    ) -> None:
        (
            mock_classifier
            .classify
            .return_value
        ) = IntentResult(
            intent=IntentType.MULTI_STEP,
            confidence=0.9,
            reason="test",
        )

        (
            mock_executor
            .execute
            .return_value
        ) = TaskExecutionResult(
            original_command=(
                "open chrome then search Python"
            ),
            success=True,
            blocked=False,
            stopped_at=None,
            steps=(
                StepExecutionResult(
                    index=1,
                    command="open chrome",
                    handler="AppLauncherSkill",
                    status=ExecutionStatus.SUCCESS,
                    response="Opened Chrome.",
                ),
                StepExecutionResult(
                    index=2,
                    command="search Python",
                    handler="SearchSkill",
                    status=ExecutionStatus.SUCCESS,
                    response=(
                        "Searching Google for Python."
                    ),
                ),
            ),
        )

        response = (
            self.jarvis
            ._route_command(
                "open chrome then search Python"
            )
        )

        mock_executor.execute\
            .assert_called_once_with(
                "open chrome then search Python"
            )

        mock_registry.find_skill\
            .assert_not_called()

        self.assertIn(
            "Opened Chrome.",
            response,
        )

        self.assertIn(
            "Searching Google for Python.",
            response,
        )

    # ==================================================
    # BLOCKED PLAN
    # ==================================================

    def test_blocked_plan_response(
        self,
    ) -> None:
        result = TaskExecutionResult(
            original_command=(
                "open chrome then turn off wifi"
            ),
            success=False,
            blocked=True,
            stopped_at=None,
            steps=(),
        )

        response = (
            self.jarvis
            ._format_task_result(
                result
            )
        )

        self.assertIn(
            "didn't execute",
            response.lower(),
        )

        self.assertIn(
            "unsupported or unsafe",
            response.lower(),
        )

    # ==================================================
    # FAIL-FAST RESPONSE
    # ==================================================

    def test_failed_step_is_reported(
        self,
    ) -> None:
        result = TaskExecutionResult(
            original_command="test",
            success=False,
            blocked=False,
            stopped_at=2,
            steps=(
                StepExecutionResult(
                    index=1,
                    command="step one",
                    handler="FirstSkill",
                    status=ExecutionStatus.SUCCESS,
                    response="Step one completed.",
                ),
                StepExecutionResult(
                    index=2,
                    command="step two",
                    handler="SecondSkill",
                    status=ExecutionStatus.FAILED,
                    response=(
                        "I couldn't complete step two."
                    ),
                ),
            ),
        )

        response = (
            self.jarvis
            ._format_task_result(
                result
            )
        )

        self.assertIn(
            "stopped at step 2",
            response.lower(),
        )

        self.assertIn(
            "couldn't complete step two",
            response.lower(),
        )

    # ==================================================
    # SINGLE COMMAND STILL USES NORMAL ROUTING
    # ==================================================

    @patch(
        "app.core.jarvis.skill_registry"
    )
    @patch(
        "app.core.jarvis.intent_classifier"
    )
    def test_single_command_keeps_existing_routing(
        self,
        mock_classifier,
        mock_registry,
    ) -> None:
        (
            mock_classifier
            .classify
            .return_value
        ) = IntentResult(
            intent=IntentType.ACTION,
            confidence=0.95,
            reason="test",
        )

        skill = MagicMock()

        skill.execute.return_value = (
            "Opened Chrome."
        )

        mock_registry.find_skill.return_value = (
            skill
        )

        response = (
            self.jarvis
            ._route_command(
                "open chrome"
            )
        )

        mock_registry.find_skill\
            .assert_called_once_with(
                "open chrome"
            )

        skill.execute\
            .assert_called_once_with(
                "open chrome"
            )

        self.assertEqual(
            response,
            "Opened Chrome.",
        )


if __name__ == "__main__":
    unittest.main()