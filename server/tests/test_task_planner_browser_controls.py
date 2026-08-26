from app.core.task_planner import (
    TaskPlanner,
)


def _commands(command):
    plan = TaskPlanner().plan(
        command
    )

    return [
        step.command
        for step
        in plan.steps
    ]


def test_browser_back_splits_as_followup_step():
    assert _commands(
        (
            "open chrome then navigate to "
            "https://example.com then browser back"
        )
    ) == [
        "open chrome",
        "navigate to https://example.com",
        "browser back",
    ]


def test_browser_forward_splits_as_followup_step():
    assert _commands(
        (
            "open chrome then browser back "
            "then browser forward"
        )
    ) == [
        "open chrome",
        "browser back",
        "browser forward",
    ]


def test_refresh_browser_splits_as_followup_step():
    assert _commands(
        (
            "open chrome then refresh browser"
        )
    ) == [
        "open chrome",
        "refresh browser",
    ]


def test_browser_refresh_splits_as_followup_step():
    assert _commands(
        (
            "open chrome then browser refresh"
        )
    ) == [
        "open chrome",
        "browser refresh",
    ]


def test_new_browser_tab_splits_as_followup_step():
    assert _commands(
        (
            "open chrome then new browser tab"
        )
    ) == [
        "open chrome",
        "new browser tab",
    ]
