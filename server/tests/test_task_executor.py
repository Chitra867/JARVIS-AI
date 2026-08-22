import unittest
from unittest.mock import (
    MagicMock,
    patch,
)

from app.core.task_executor import (
    ExecutionStatus,
    TaskExecutor,
)

from app.core.task_validator import (
    StepType,
    ValidatedPlan,
    ValidatedStep,
)


class TaskExecutorTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.executor = TaskExecutor()

    # ==================================================
    # HELPER
    # ==================================================

    def _step(
        self,
        index: int,
        command: str,
        handler: str,
    ) -> ValidatedStep:
        return ValidatedStep(
            index=index,
            command=command,
            step_type=StepType.SKILL,
            handler=handler,
            allowed=True,
            reason="test",
        )

    # ==================================================
    # BLOCKED PLAN MUST EXECUTE NOTHING
    # ==================================================

    @patch(
        "app.core.task_executor.skill_registry"
    )
    def test_blocked_plan_executes_nothing(
        self,
        mock_registry,
    ) -> None:
        plan = ValidatedPlan(
            original_command=(
                "open chrome then turn off wifi"
            ),
            steps=(
                ValidatedStep(
                    index=1,
                    command="open chrome",
                    step_type=StepType.SKILL,
                    handler="AppLauncherSkill",
                    allowed=True,
                    reason="test",
                ),
                ValidatedStep(
                    index=2,
                    command="turn off wifi",
                    step_type=StepType.BLOCKED,
                    handler="ActionGuardSkill",
                    allowed=False,
                    reason="blocked",
                ),
            ),
        )

        result = (
            self.executor
            .execute_plan(
                plan
            )
        )

        self.assertFalse(
            result.success
        )

        self.assertTrue(
            result.blocked
        )

        self.assertEqual(
            result.steps,
            (),
        )

        self.assertEqual(
            result.runtime_outputs,
            (),
        )

        mock_registry.find_skill\
            .assert_not_called()

    # ==================================================
    # SUCCESSFUL SEQUENTIAL EXECUTION
    # ==================================================

    @patch(
        "app.core.task_executor.skill_registry"
    )
    def test_safe_plan_executes_in_order(
        self,
        mock_registry,
    ) -> None:
        first_skill = MagicMock()
        second_skill = MagicMock()

        first_skill.__class__.__name__ = (
            "AppLauncherSkill"
        )

        second_skill.__class__.__name__ = (
            "SearchSkill"
        )

        first_skill.execute.return_value = (
            "Opened Chrome."
        )

        second_skill.execute.return_value = (
            "Searching Google for Python."
        )

        mock_registry.find_skill.side_effect = [
            first_skill,
            second_skill,
        ]

        plan = ValidatedPlan(
            original_command=(
                "open chrome then search Python"
            ),
            steps=(
                self._step(
                    1,
                    "open chrome",
                    "AppLauncherSkill",
                ),
                self._step(
                    2,
                    "search Python",
                    "SearchSkill",
                ),
            ),
        )

        result = (
            self.executor
            .execute_plan(
                plan
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertFalse(
            result.blocked
        )

        self.assertEqual(
            len(result.steps),
            2,
        )

        self.assertEqual(
            result.steps[0].status,
            ExecutionStatus.SUCCESS,
        )

        self.assertEqual(
            result.steps[1].status,
            ExecutionStatus.SUCCESS,
        )

        first_skill.execute\
            .assert_called_once_with(
                "open chrome"
            )

        second_skill.execute\
            .assert_called_once_with(
                "search Python"
            )

    # ==================================================
    # FAIL FAST ON FAILED RESPONSE
    # ==================================================

    @patch(
        "app.core.task_executor.skill_registry"
    )
    def test_failure_stops_remaining_steps(
        self,
        mock_registry,
    ) -> None:
        first_skill = MagicMock()
        second_skill = MagicMock()
        third_skill = MagicMock()

        first_skill.__class__.__name__ = (
            "FirstSkill"
        )

        second_skill.__class__.__name__ = (
            "SecondSkill"
        )

        third_skill.__class__.__name__ = (
            "ThirdSkill"
        )

        first_skill.execute.return_value = (
            "Step completed."
        )

        second_skill.execute.return_value = (
            "I couldn't complete this step."
        )

        third_skill.execute.return_value = (
            "This should never execute."
        )

        mock_registry.find_skill.side_effect = [
            first_skill,
            second_skill,
            third_skill,
        ]

        plan = ValidatedPlan(
            original_command="test",
            steps=(
                self._step(
                    1,
                    "step one",
                    "FirstSkill",
                ),
                self._step(
                    2,
                    "step two",
                    "SecondSkill",
                ),
                self._step(
                    3,
                    "step three",
                    "ThirdSkill",
                ),
            ),
        )

        result = (
            self.executor
            .execute_plan(
                plan
            )
        )

        self.assertFalse(
            result.success
        )

        self.assertFalse(
            result.blocked
        )

        self.assertEqual(
            result.stopped_at,
            2,
        )

        self.assertEqual(
            len(result.steps),
            2,
        )

        self.assertEqual(
            result.steps[1].status,
            ExecutionStatus.FAILED,
        )

        third_skill.execute\
            .assert_not_called()

    # ==================================================
    # EXCEPTION MUST STOP PLAN
    # ==================================================

    @patch(
        "app.core.task_executor.skill_registry"
    )
    def test_exception_stops_execution(
        self,
        mock_registry,
    ) -> None:
        skill = MagicMock()

        skill.__class__.__name__ = (
            "BrokenSkill"
        )

        skill.execute.side_effect = (
            RuntimeError(
                "boom"
            )
        )

        mock_registry.find_skill.return_value = (
            skill
        )

        plan = ValidatedPlan(
            original_command="broken",
            steps=(
                self._step(
                    1,
                    "broken step",
                    "BrokenSkill",
                ),
            ),
        )

        result = (
            self.executor
            .execute_plan(
                plan
            )
        )

        self.assertFalse(
            result.success
        )

        self.assertEqual(
            result.stopped_at,
            1,
        )

        self.assertEqual(
            len(result.steps),
            1,
        )

        self.assertEqual(
            result.steps[0].status,
            ExecutionStatus.FAILED,
        )

        self.assertEqual(
            result.runtime_outputs,
            (),
        )

    # ==================================================
    # SUCCESSFUL STEPS PUBLISH RUNTIME OUTPUT
    # ==================================================

    @patch(
        "app.core.task_executor.skill_registry"
    )
    def test_successful_steps_publish_runtime_outputs(
        self,
        mock_registry,
    ) -> None:
        first_skill = MagicMock()
        second_skill = MagicMock()

        first_skill.__class__.__name__ = (
            "FirstSkill"
        )

        second_skill.__class__.__name__ = (
            "SecondSkill"
        )

        first_skill.execute.return_value = (
            "First completed."
        )

        second_skill.execute.return_value = (
            "Second completed."
        )

        mock_registry.find_skill.side_effect = [
            first_skill,
            second_skill,
        ]

        plan = ValidatedPlan(
            original_command="test",
            steps=(
                self._step(
                    1,
                    "step one",
                    "FirstSkill",
                ),
                self._step(
                    2,
                    "step two",
                    "SecondSkill",
                ),
            ),
        )

        result = (
            self.executor
            .execute_plan(
                plan
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            len(result.runtime_outputs),
            2,
        )

        self.assertEqual(
            result.runtime_outputs[0].step_index,
            1,
        )

        self.assertEqual(
            result.runtime_outputs[0].output_type.value,
            "text",
        )

        self.assertEqual(
            result.runtime_outputs[0].text,
            "First completed.",
        )

        self.assertEqual(
            result.runtime_outputs[1].step_index,
            2,
        )

        self.assertEqual(
            result.runtime_outputs[1].output_type.value,
            "text",
        )

        self.assertEqual(
            result.runtime_outputs[1].text,
            "Second completed.",
        )

    # ==================================================
    # FAILED STEP MUST NOT PUBLISH RUNTIME OUTPUT
    # ==================================================

    @patch(
        "app.core.task_executor.skill_registry"
    )
    def test_failed_step_does_not_publish_runtime_output(
        self,
        mock_registry,
    ) -> None:
        first_skill = MagicMock()
        second_skill = MagicMock()

        first_skill.__class__.__name__ = (
            "FirstSkill"
        )

        second_skill.__class__.__name__ = (
            "SecondSkill"
        )

        first_skill.execute.return_value = (
            "First completed."
        )

        second_skill.execute.return_value = (
            "I couldn't complete the second step."
        )

        mock_registry.find_skill.side_effect = [
            first_skill,
            second_skill,
        ]

        plan = ValidatedPlan(
            original_command="test",
            steps=(
                self._step(
                    1,
                    "step one",
                    "FirstSkill",
                ),
                self._step(
                    2,
                    "step two",
                    "SecondSkill",
                ),
            ),
        )

        result = (
            self.executor
            .execute_plan(
                plan
            )
        )

        self.assertFalse(
            result.success
        )

        self.assertFalse(
            result.blocked
        )

        self.assertEqual(
            result.stopped_at,
            2,
        )

        # Only the first successful step gets
        # published to runtime context.
        self.assertEqual(
            len(result.runtime_outputs),
            1,
        )

        self.assertEqual(
            result.runtime_outputs[0].step_index,
            1,
        )

        self.assertEqual(
            result.runtime_outputs[0].text,
            "First completed.",
        )

        self.assertEqual(
            result.steps[1].status,
            ExecutionStatus.FAILED,
        )

    # ==================================================
    # EMPTY RESPONSE COUNTS AS FAILURE
    # ==================================================

    def test_empty_response_is_failure(
        self,
    ) -> None:
        self.assertTrue(
            self.executor
            ._response_indicates_failure(
                ""
            )
        )

        self.assertTrue(
            self.executor
            ._response_indicates_failure(
                "   "
            )
        )

    # ==================================================
    # NORMAL RESPONSE IS SUCCESS
    # ==================================================

    def test_normal_response_is_not_failure(
        self,
    ) -> None:
        self.assertFalse(
            self.executor
            ._response_indicates_failure(
                "Opened Chrome."
            )
        )

        self.assertFalse(
            self.executor
            ._response_indicates_failure(
                "Searching Google for Python."
            )
        )


if __name__ == "__main__":
    unittest.main()