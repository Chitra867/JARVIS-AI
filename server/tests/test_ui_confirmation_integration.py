from app.core.task_executor import (
    task_executor,
)

from app.core.task_validator import (
    StepType,
    task_validator,
)


# ======================================================
# VALIDATOR — MULTI-STEP SELF-CONFIRMATION
# ======================================================


def test_ui_click_confirmation_is_blocked_inside_multi_step_plan():
    plan = (
        task_validator
        .validate(
            (
                "click delete button "
                "then confirm click abc123"
            )
        )
    )

    assert not (
        plan.is_safe_to_execute
    )

    assert len(
        plan.steps
    ) == 2

    first = (
        plan.steps[0]
    )

    second = (
        plan.steps[1]
    )

    assert (
        first.handler
        == "UIAutomationClickSkill"
    )

    assert (
        first.step_type
        == StepType.SKILL
    )

    assert (
        first.allowed
        is True
    )

    assert (
        second.handler
        == "UIAutomationClickSkill"
    )

    assert (
        second.step_type
        == StepType.BLOCKED
    )

    assert (
        second.allowed
        is False
    )

    assert (
        "separate user command"
        in second.reason.lower()
    )


# ======================================================
# VALIDATOR — EXPLICIT UI PREFIX
# ======================================================


def test_ui_prefixed_confirmation_is_blocked_inside_multi_step_plan():
    plan = (
        task_validator
        .validate(
            (
                "click delete button "
                "then confirm ui click abc123"
            )
        )
    )

    assert not (
        plan.is_safe_to_execute
    )

    assert len(
        plan.steps
    ) == 2

    confirmation = (
        plan.steps[1]
    )

    assert (
        confirmation.handler
        == "UIAutomationClickSkill"
    )

    assert (
        confirmation.step_type
        == StepType.BLOCKED
    )

    assert not (
        confirmation.allowed
    )


# ======================================================
# VALIDATOR — SEPARATE TURN
# ======================================================


def test_single_ui_click_confirmation_is_allowed_by_validator():
    plan = (
        task_validator
        .validate(
            "confirm click abc123"
        )
    )

    assert (
        plan.is_safe_to_execute
    )

    assert len(
        plan.steps
    ) == 1

    step = (
        plan.steps[0]
    )

    assert (
        step.handler
        == "UIAutomationClickSkill"
    )

    assert (
        step.step_type
        == StepType.SKILL
    )

    assert (
        step.allowed
        is True
    )


def test_single_ui_prefixed_confirmation_is_allowed_by_validator():
    plan = (
        task_validator
        .validate(
            "confirm ui click abc123"
        )
    )

    assert (
        plan.is_safe_to_execute
    )

    assert len(
        plan.steps
    ) == 1

    step = (
        plan.steps[0]
    )

    assert (
        step.handler
        == "UIAutomationClickSkill"
    )

    assert (
        step.allowed
        is True
    )


# ======================================================
# EXECUTOR — SUCCESS CLASSIFICATION
# ======================================================


def test_executor_accepts_verified_ui_click_as_success():
    assert (
        task_executor
        ._ui_click_response_succeeded(
            (
                "Clicked 'Terminal' "
                "(MenuItem) at screen position "
                "(404, 22) after UI Automation "
                "verification."
            )
        )
    )


def test_executor_accepts_explicit_ui_click_cancellation():
    assert (
        task_executor
        ._ui_click_response_succeeded(
            "Pending UI click cancelled."
        )
    )


# ======================================================
# EXECUTOR — BLOCKED / PENDING CLASSIFICATION
# ======================================================


def test_executor_rejects_sensitive_confirmation_request_as_success():
    assert not (
        task_executor
        ._ui_click_response_succeeded(
            (
                "'Delete' may perform a sensitive "
                "or destructive action. "
                "No click was performed. "
                "To proceed, send exactly: "
                "confirm click abc123"
            )
        )
    )


def test_executor_rejects_ambiguous_ui_result_as_success():
    assert not (
        task_executor
        ._ui_click_response_succeeded(
            (
                "I found multiple possible matches "
                "for 'search'. "
                "No click was performed."
            )
        )
    )


def test_executor_rejects_missing_target_as_success():
    assert not (
        task_executor
        ._ui_click_response_succeeded(
            (
                "I couldn't find a unique visible "
                "UI Automation target. "
                "No click was performed."
            )
        )
    )


def test_executor_rejects_empty_ui_response_as_success():
    assert not (
        task_executor
        ._ui_click_response_succeeded(
            ""
        )
    )