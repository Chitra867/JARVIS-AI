from app.core.ui_automation import (
    UIAutomationResolution,
    UIAutomationTarget,
)

from app.skills import (
    ui_click_skill as ui_click_module,
)

from app.skills.ui_click_skill import (
    UIAutomationClickSkill,
)


# ======================================================
# HELPERS
# ======================================================


def _target(
    *,
    name: str = "File",
    control_type: str = "MenuItem",
    automation_id: str = "FileMenu",
    left: int = 10,
    top: int = 10,
    right: int = 110,
    bottom: int = 50,
):
    return (
        UIAutomationTarget(
            name=name,
            control_type=control_type,
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            center_x=(
                (
                    left
                    + right
                )
                // 2
            ),
            center_y=(
                (
                    top
                    + bottom
                )
                // 2
            ),
            enabled=True,
            visible=True,
            automation_id=automation_id,
        )
    )


def _resolved(
    target=None,
):
    if (
        target
        is None
    ):
        target = (
            _target()
        )

    return (
        UIAutomationResolution(
            query="file menu item",
            status="resolved",
            target=target,
            candidates=(
                target,
            ),
            reason="resolved",
        )
    )


def _not_found():
    return (
        UIAutomationResolution(
            query="file menu item",
            status="not_found",
            target=None,
            candidates=(),
            reason="not found",
        )
    )


def _ambiguous():
    first = (
        _target(
            name="File",
            automation_id="A",
        )
    )

    second = (
        _target(
            name="File",
            automation_id="B",
            left=120,
            right=220,
        )
    )

    return (
        UIAutomationResolution(
            query="file menu item",
            status="ambiguous",
            target=None,
            candidates=(
                first,
                second,
            ),
            reason="ambiguous",
        )
    )


def _error():
    return (
        UIAutomationResolution(
            query="file menu item",
            status="error",
            target=None,
            candidates=(),
            reason="error",
        )
    )


# ======================================================
# TRANSIENT NOT-FOUND
# ======================================================


def test_retry_recovers_from_transient_not_found(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    skill.RESOLUTION_RETRY_ATTEMPTS = (
        3
    )

    resolutions = [
        _not_found(),
        _resolved(),
    ]

    calls = {
        "count": 0,
    }

    def fake_resolve(
        query: str,
    ):
        calls["count"] += 1

        return (
            resolutions.pop(
                0
            )
        )

    monkeypatch.setattr(
        skill,
        "_resolve",
        fake_resolve,
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: 123,
    )

    monkeypatch.setattr(
        ui_click_module.time,
        "sleep",
        lambda _: None,
    )

    resolution, failure = (
        skill._resolve_with_bounded_retry(
            query="file menu item",
            expected_hwnd=123,
        )
    )

    assert (
        failure
        is None
    )

    assert (
        resolution.resolved
        is True
    )

    assert (
        calls["count"]
        == 2
    )


# ======================================================
# RETRY BOUND
# ======================================================


def test_retry_stops_after_configured_attempts(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    skill.RESOLUTION_RETRY_ATTEMPTS = (
        3
    )

    calls = {
        "count": 0,
    }

    def fake_resolve(
        query: str,
    ):
        calls["count"] += 1

        return (
            _not_found()
        )

    monkeypatch.setattr(
        skill,
        "_resolve",
        fake_resolve,
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: 123,
    )

    monkeypatch.setattr(
        ui_click_module.time,
        "sleep",
        lambda _: None,
    )

    resolution, failure = (
        skill._resolve_with_bounded_retry(
            query="file menu item",
            expected_hwnd=123,
        )
    )

    assert (
        failure
        is None
    )

    assert (
        resolution.status
        == "not_found"
    )

    assert (
        calls["count"]
        == 3
    )


# ======================================================
# AMBIGUITY MUST NOT RETRY
# ======================================================


def test_ambiguity_blocks_retry_immediately(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    calls = {
        "count": 0,
    }

    def fake_resolve(
        query: str,
    ):
        calls["count"] += 1

        return (
            _ambiguous()
        )

    monkeypatch.setattr(
        skill,
        "_resolve",
        fake_resolve,
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: 123,
    )

    resolution, failure = (
        skill._resolve_with_bounded_retry(
            query="file menu item",
            expected_hwnd=123,
        )
    )

    assert (
        failure
        is None
    )

    assert (
        resolution.ambiguous
        is True
    )

    assert (
        calls["count"]
        == 1
    )


# ======================================================
# ERROR MUST NOT RETRY
# ======================================================


def test_error_blocks_retry_immediately(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    calls = {
        "count": 0,
    }

    def fake_resolve(
        query: str,
    ):
        calls["count"] += 1

        return (
            _error()
        )

    monkeypatch.setattr(
        skill,
        "_resolve",
        fake_resolve,
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: 123,
    )

    resolution, failure = (
        skill._resolve_with_bounded_retry(
            query="file menu item",
            expected_hwnd=123,
        )
    )

    assert (
        failure
        is None
    )

    assert (
        resolution.status
        == "error"
    )

    assert (
        calls["count"]
        == 1
    )


# ======================================================
# FOREGROUND CHANGE DURING RETRY
# ======================================================


def test_retry_fails_closed_when_foreground_changes(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    foreground_values = iter(
        [
            123,
            123,
            999,
        ]
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: next(
            foreground_values
        ),
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda query: (
            _not_found()
        ),
    )

    monkeypatch.setattr(
        ui_click_module.time,
        "sleep",
        lambda _: None,
    )

    resolution, failure = (
        skill._resolve_with_bounded_retry(
            query="file menu item",
            expected_hwnd=123,
        )
    )

    assert (
        resolution.status
        == "not_found"
    )

    assert (
        failure
        is not None
    )

    assert (
        "active window changed"
        in failure.lower()
    )


# ======================================================
# FULL CLICK FLOW — RETRY + REVALIDATION
# ======================================================


def test_click_request_uses_retry_and_still_revalidates_before_click(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    skill.RESOLUTION_RETRY_ATTEMPTS = (
        3
    )

    first_target = (
        _target()
    )

    second_target = (
        _target()
    )

    resolutions = [
        _not_found(),
        _resolved(
            first_target
        ),
        _resolved(
            second_target
        ),
    ]

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda query: (
            resolutions.pop(
                0
            )
        ),
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: 123,
    )

    monkeypatch.setattr(
        ui_click_module.time,
        "sleep",
        lambda _: None,
    )

    clicks = []

    monkeypatch.setattr(
        ui_click_module.pyautogui,
        "click",
        lambda **kwargs: (
            clicks.append(
                kwargs
            )
        ),
    )

    response = (
        skill._handle_click_request(
            "file menu item"
        )
    )

    assert (
        response.startswith(
            "Clicked "
        )
    )

    assert (
        len(
            clicks
        )
        == 1
    )

    assert (
        clicks[
            0
        ]["x"]
        == first_target.center_x
    )

    assert (
        clicks[
            0
        ]["y"]
        == first_target.center_y
    )


# ======================================================
# FULL CLICK FLOW — EXHAUSTED RETRY
# ======================================================


def test_click_request_does_not_click_after_retry_exhaustion(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    skill.RESOLUTION_RETRY_ATTEMPTS = (
        3
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda query: (
            _not_found()
        ),
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: 123,
    )

    monkeypatch.setattr(
        ui_click_module.time,
        "sleep",
        lambda _: None,
    )

    clicks = []

    monkeypatch.setattr(
        ui_click_module.pyautogui,
        "click",
        lambda **kwargs: (
            clicks.append(
                kwargs
            )
        ),
    )

    response = (
        skill._handle_click_request(
            "file menu item"
        )
    )

    assert (
        "couldn't find"
        in response.lower()
    )

    assert (
        clicks
        == []
    )