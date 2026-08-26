from types import (
    SimpleNamespace,
)

from app.skills import (
    browser_navigation_skill as browser_module,
)

from app.skills.browser_navigation_skill import (
    BrowserNavigationSkill,
)


def _browser_window(
    *,
    hwnd=100,
    process_name="chrome.exe",
    visible=True,
    enabled=True,
):
    return SimpleNamespace(
        hwnd=hwnd,
        process_name=process_name,
        visible=visible,
        enabled=enabled,
    )


def test_browser_control_commands_are_supported():
    skill = BrowserNavigationSkill()

    for command in (
        "browser back",
        "browser forward",
        "refresh browser",
        "browser refresh",
        "open new tab",
        "new browser tab",
    ):
        assert (
            skill.can_handle(
                command
            )
            is True
        )


def test_browser_back_uses_alt_left(
    monkeypatch,
):
    skill = BrowserNavigationSkill()

    windows = [
        _browser_window(),
        _browser_window(),
    ]

    monkeypatch.setattr(
        browser_module.ui_automation_service,
        "get_foreground_window_info",
        lambda: windows.pop(
            0
        ),
    )

    calls = []

    monkeypatch.setattr(
        browser_module.pyautogui,
        "hotkey",
        lambda *keys: calls.append(
            keys
        ),
    )

    result = skill.execute(
        "browser back"
    )

    assert (
        result
        == "Browser moved back."
    )

    assert calls == [
        (
            "alt",
            "left",
        ),
    ]


def test_browser_forward_uses_alt_right(
    monkeypatch,
):
    skill = BrowserNavigationSkill()

    windows = [
        _browser_window(),
        _browser_window(),
    ]

    monkeypatch.setattr(
        browser_module.ui_automation_service,
        "get_foreground_window_info",
        lambda: windows.pop(
            0
        ),
    )

    calls = []

    monkeypatch.setattr(
        browser_module.pyautogui,
        "hotkey",
        lambda *keys: calls.append(
            keys
        ),
    )

    result = skill.execute(
        "browser forward"
    )

    assert (
        result
        == "Browser moved forward."
    )

    assert calls == [
        (
            "alt",
            "right",
        ),
    ]


def test_browser_refresh_uses_ctrl_r(
    monkeypatch,
):
    skill = BrowserNavigationSkill()

    windows = [
        _browser_window(),
        _browser_window(),
    ]

    monkeypatch.setattr(
        browser_module.ui_automation_service,
        "get_foreground_window_info",
        lambda: windows.pop(
            0
        ),
    )

    calls = []

    monkeypatch.setattr(
        browser_module.pyautogui,
        "hotkey",
        lambda *keys: calls.append(
            keys
        ),
    )

    result = skill.execute(
        "refresh browser"
    )

    assert (
        result
        == "Browser refreshed."
    )

    assert calls == [
        (
            "ctrl",
            "r",
        ),
    ]


def test_open_new_tab_uses_ctrl_t(
    monkeypatch,
):
    skill = BrowserNavigationSkill()

    windows = [
        _browser_window(),
        _browser_window(),
    ]

    monkeypatch.setattr(
        browser_module.ui_automation_service,
        "get_foreground_window_info",
        lambda: windows.pop(
            0
        ),
    )

    calls = []

    monkeypatch.setattr(
        browser_module.pyautogui,
        "hotkey",
        lambda *keys: calls.append(
            keys
        ),
    )

    result = skill.execute(
        "open new tab"
    )

    assert (
        result
        == "Opened a new browser tab."
    )

    assert calls == [
        (
            "ctrl",
            "t",
        ),
    ]


def test_browser_control_rejects_non_browser_foreground(
    monkeypatch,
):
    skill = BrowserNavigationSkill()

    monkeypatch.setattr(
        browser_module.ui_automation_service,
        "get_foreground_window_info",
        lambda: _browser_window(
            process_name="notepad.exe"
        ),
    )

    calls = []

    monkeypatch.setattr(
        browser_module.pyautogui,
        "hotkey",
        lambda *keys: calls.append(
            keys
        ),
    )

    result = skill.execute(
        "browser back"
    )

    assert (
        "supported browser"
        in result.lower()
    )

    assert calls == []


def test_browser_control_blocks_if_window_changes(
    monkeypatch,
):
    skill = BrowserNavigationSkill()

    windows = [
        _browser_window(
            hwnd=100
        ),
        _browser_window(
            hwnd=200
        ),
    ]

    monkeypatch.setattr(
        browser_module.ui_automation_service,
        "get_foreground_window_info",
        lambda: windows.pop(
            0
        ),
    )

    monkeypatch.setattr(
        browser_module.pyautogui,
        "hotkey",
        lambda *keys: None,
    )

    result = skill.execute(
        "browser refresh"
    )

    assert (
        "window changed"
        in result.lower()
    )
