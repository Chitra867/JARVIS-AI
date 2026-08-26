from app.core.task_planner import (
    TaskPlanner,
)


def _commands(plan):
    return [
        step.command
        for step
        in plan.steps
    ]


def test_open_chrome_then_navigate_splits_into_two_steps():
    plan = TaskPlanner().plan(
        "open chrome then navigate to https://example.com"
    )

    assert _commands(plan) == [
        "open chrome",
        "navigate to https://example.com",
    ]


def test_open_edge_then_go_to_splits_into_two_steps():
    plan = TaskPlanner().plan(
        "open edge then go to https://example.com"
    )

    assert _commands(plan) == [
        "open edge",
        "go to https://example.com",
    ]


def test_open_firefox_then_browser_search_splits_into_two_steps():
    plan = TaskPlanner().plan(
        "open firefox then browser search for Python automation"
    )

    assert _commands(plan) == [
        "open firefox",
        "browser search for Python automation",
    ]


def test_open_chrome_generic_search_remains_generic():
    plan = TaskPlanner().plan(
        "open chrome then search Python automation"
    )

    assert _commands(plan) == [
        "open chrome",
        "search Python automation",
    ]


def test_open_edge_generic_search_remains_generic():
    plan = TaskPlanner().plan(
        "open edge and search secure browser automation"
    )

    assert _commands(plan) == [
        "open edge",
        "search secure browser automation",
    ]


def test_open_google_generic_search_remains_generic():
    plan = TaskPlanner().plan(
        "open google then search OpenAI"
    )

    assert _commands(plan) == [
        "open google",
        "search OpenAI",
    ]


def test_youtube_context_remains_youtube_specific():
    plan = TaskPlanner().plan(
        "open youtube then search cats"
    )

    assert _commands(plan) == [
        "open youtube",
        "search youtube for cats",
    ]


def test_browser_search_text_is_not_split_without_sequence_marker():
    plan = TaskPlanner().plan(
        "browser search for navigate to documentation"
    )

    assert _commands(plan) == [
        "browser search for navigate to documentation",
    ]
