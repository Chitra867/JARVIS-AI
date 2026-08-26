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


def test_can_handle_navigation_and_browser_search():
    skill = BrowserNavigationSkill()

    assert skill.can_handle(
        "navigate to https://example.com"
    )

    assert skill.can_handle(
        "go to https://example.com"
    )

    assert skill.can_handle(
        "browser search for Python tutorials"
    )

    assert not skill.can_handle(
        "search Python tutorials"
    )


def test_validate_web_url_accepts_only_http_and_https():
    skill = BrowserNavigationSkill()

    assert (
        skill._validate_web_url(
            "https://example.com/path"
        )
        == "https://example.com/path"
    )

    assert (
        skill._validate_web_url(
            "http://example.com"
        )
        == "http://example.com"
    )

    assert (
        skill._validate_web_url(
            "javascript:alert(1)"
        )
        is None
    )

    assert (
        skill._validate_web_url(
            "file:///C:/Windows/System32"
        )
        is None
    )


def test_validate_web_url_rejects_embedded_credentials():
    skill = BrowserNavigationSkill()

    assert (
        skill._validate_web_url(
            "https://user:pass@example.com"
        )
        is None
    )


def test_search_query_is_bounded_and_single_line():
    skill = BrowserNavigationSkill()

    assert (
        skill._validate_search_query(
            "  Python   automation  "
        )
        == "Python automation"
    )

    assert (
        skill._validate_search_query(
            "x" * 501
        )
        is None
    )


def test_rejects_non_browser_foreground(
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
            (
                "hotkey",
                keys,
            )
        ),
    )

    result = skill.execute(
        "navigate to https://example.com"
    )

    assert (
        "supported browser"
        in result.lower()
    )

    assert calls == []


def test_navigate_uses_verified_same_browser_window(
    monkeypatch,
):
    skill = BrowserNavigationSkill()

    windows = [
        _browser_window(
            hwnd=100
        ),
        _browser_window(
            hwnd=100
        ),
        _browser_window(
            hwnd=100
        ),
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
            (
                "hotkey",
                keys,
            )
        ),
    )

    monkeypatch.setattr(
        browser_module.pyautogui,
        "write",
        lambda text, interval=0.0: calls.append(
            (
                "write",
                text,
            )
        ),
    )

    monkeypatch.setattr(
        browser_module.pyautogui,
        "press",
        lambda key: calls.append(
            (
                "press",
                key,
            )
        ),
    )

    result = skill.execute(
        "navigate to https://example.com"
    )

    assert (
        result
        == "Navigating to https://example.com."
    )

    assert calls == [
        (
            "hotkey",
            (
                "ctrl",
                "l",
            ),
        ),
        (
            "write",
            "https://example.com",
        ),
        (
            "press",
            "enter",
        ),
    ]


def test_browser_window_change_blocks_before_typing(
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

    writes = []

    monkeypatch.setattr(
        browser_module.pyautogui,
        "hotkey",
        lambda *keys: None,
    )

    monkeypatch.setattr(
        browser_module.pyautogui,
        "write",
        lambda text, interval=0.0: writes.append(
            text
        ),
    )

    result = skill.execute(
        "navigate to https://example.com"
    )

    assert (
        "window changed"
        in result.lower()
    )

    assert writes == []


def test_browser_search_uses_address_bar(
    monkeypatch,
):
    skill = BrowserNavigationSkill()

    windows = [
        _browser_window(),
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
            (
                "hotkey",
                keys,
            )
        ),
    )

    monkeypatch.setattr(
        browser_module.pyautogui,
        "write",
        lambda text, interval=0.0: calls.append(
            (
                "write",
                text,
            )
        ),
    )

    monkeypatch.setattr(
        browser_module.pyautogui,
        "press",
        lambda key: calls.append(
            (
                "press",
                key,
            )
        ),
    )

    result = skill.execute(
        "browser search for Python automation"
    )

    assert (
        result
        == (
            "Browser search submitted "
            "for Python automation."
        )
    )

    assert calls == [
        (
            "hotkey",
            (
                "ctrl",
                "l",
            ),
        ),
        (
            "write",
            "Python automation",
        ),
        (
            "press",
            "enter",
        ),
    ]
