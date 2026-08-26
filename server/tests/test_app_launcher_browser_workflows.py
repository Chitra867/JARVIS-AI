from types import (
    SimpleNamespace,
)

from app.skills import (
    app_launcher_skill as launcher_module,
)

from app.skills.app_launcher_skill import (
    AppLauncherSkill,
    LaunchFocusContext,
)


def _focus_context():
    return LaunchFocusContext(
        command="open chrome",
        target="chrome",
        hwnd=100,
        process_id=200,
        process_name="chrome.exe",
        process_names=frozenset(
            {
                "chrome.exe",
            }
        ),
        title="Chrome",
        created_at=1.0,
    )


def test_resolve_web_url_accepts_http_and_https():
    skill = AppLauncherSkill()

    assert (
        skill._resolve_web_url(
            "https://example.com/path"
        )
        == "https://example.com/path"
    )

    assert (
        skill._resolve_web_url(
            "http://example.com"
        )
        == "http://example.com"
    )


def test_resolve_web_url_rejects_unsafe_or_implicit_targets():
    skill = AppLauncherSkill()

    assert (
        skill._resolve_web_url(
            "file:///C:/Windows/System32"
        )
        is None
    )

    assert (
        skill._resolve_web_url(
            "example.com"
        )
        is None
    )

    assert (
        skill._resolve_web_url(
            "https://user:pass@example.com"
        )
        is None
    )


def test_execute_explicit_https_url_records_browser_launch(
    monkeypatch,
):
    skill = AppLauncherSkill()

    opened = []

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: 77,
    )

    monkeypatch.setattr(
        launcher_module.webbrowser,
        "open",
        lambda url: (
            opened.append(
                url
            )
            or True
        ),
    )

    result = skill.execute(
        "open https://example.com/test"
    )

    assert (
        result
        == "Opening https://example.com/test."
    )

    assert opened == [
        "https://example.com/test",
    ]

    observation = (
        skill._last_launch
    )

    assert observation is not None
    assert observation.kind == "website"

    assert (
        observation.process_names
        == skill.BROWSER_PROCESS_NAMES
    )

    assert (
        observation.previous_foreground_hwnd
        == 77
    )


def test_edge_firefox_and_brave_are_supported_aliases(
    monkeypatch,
):
    skill = AppLauncherSkill()

    resolved = {
        "msedge.exe":
            r"C:\Browser\msedge.exe",

        "firefox.exe":
            r"C:\Browser\firefox.exe",

        "brave.exe":
            r"C:\Browser\brave.exe",
    }

    monkeypatch.setattr(
        launcher_module.shutil,
        "which",
        lambda name: (
            resolved.get(
                name
            )
        ),
    )

    assert (
        skill._resolve_app(
            "edge"
        )
        == r"C:\Browser\msedge.exe"
    )

    assert (
        skill._resolve_app(
            "microsoft edge"
        )
        == r"C:\Browser\msedge.exe"
    )

    assert (
        skill._resolve_app(
            "firefox"
        )
        == r"C:\Browser\firefox.exe"
    )

    assert (
        skill._resolve_app(
            "brave"
        )
        == r"C:\Browser\brave.exe"
    )


def test_exact_verified_foreground_is_accepted():
    skill = AppLauncherSkill()
    context = _focus_context()

    foreground = SimpleNamespace(
        hwnd=100,
        process_id=200,
        process_name="chrome.exe",
    )

    assert (
        skill._foreground_belongs_to_focus_context(
            foreground=foreground,
            context=context,
        )
        is True
    )


def test_owned_same_process_popup_is_accepted(
    monkeypatch,
):
    skill = AppLauncherSkill()
    context = _focus_context()

    foreground = SimpleNamespace(
        hwnd=150,
        process_id=200,
        process_name="chrome.exe",
    )

    monkeypatch.setattr(
        launcher_module.win32gui,
        "GetWindow",
        lambda hwnd, relationship: (
            100
            if (
                hwnd == 150
                and relationship == 4
            )
            else 0
        ),
    )

    assert (
        skill._foreground_belongs_to_focus_context(
            foreground=foreground,
            context=context,
        )
        is True
    )


def test_unrelated_same_process_window_is_not_accepted(
    monkeypatch,
):
    skill = AppLauncherSkill()
    context = _focus_context()

    foreground = SimpleNamespace(
        hwnd=175,
        process_id=200,
        process_name="chrome.exe",
    )

    monkeypatch.setattr(
        launcher_module.win32gui,
        "GetWindow",
        lambda hwnd, relationship: 0,
    )

    assert (
        skill._foreground_belongs_to_focus_context(
            foreground=foreground,
            context=context,
        )
        is False
    )


def test_recover_focus_refocuses_original_for_unrelated_same_process_window(
    monkeypatch,
):
    skill = AppLauncherSkill()
    context = _focus_context()

    foreground = SimpleNamespace(
        hwnd=175,
        process_id=200,
        process_name="chrome.exe",
    )

    recovered_window = SimpleNamespace(
        hwnd=100,
        process_id=200,
        process_name="chrome.exe",
    )

    calls = []

    monkeypatch.setattr(
        launcher_module.ui_automation_service,
        "get_foreground_window_info",
        lambda: foreground,
    )

    monkeypatch.setattr(
        launcher_module.win32gui,
        "GetWindow",
        lambda hwnd, relationship: 0,
    )

    monkeypatch.setattr(
        launcher_module.ui_automation_service,
        "focus_window",
        lambda hwnd, expected_process_names=(): (
            calls.append(
                (
                    hwnd,
                    expected_process_names,
                )
            )
            or SimpleNamespace(
                success=True,
                reason="",
                window=recovered_window,
            )
        ),
    )

    recovered, reason = (
        skill.recover_focus_context(
            context
        )
    )

    assert recovered is True

    assert (
        "safely restored"
        in reason.lower()
    )

    assert calls == [
        (
            100,
            (
                "chrome.exe",
            ),
        ),
    ]
