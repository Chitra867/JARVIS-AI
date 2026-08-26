from app.core.ui_automation import (
    UIAutomationFocusResult,
    UIAutomationWindow,
)

from app.skills.app_launcher_skill import (
    AppLauncherSkill,
    LaunchFocusContext,
    LaunchReadiness,
)

from app.skills import (
    app_launcher_skill as launcher_module,
)


# ======================================================
# HELPERS
# ======================================================


def _window(
    *,
    hwnd: int = 333,
    title: str = "Untitled - Notepad",
    process_id: int = 44,
    process_name: str = "notepad.exe",
):
    return (
        UIAutomationWindow(
            hwnd=hwnd,
            title=title,
            process_id=process_id,
            process_name=process_name,
            left=0,
            top=0,
            right=800,
            bottom=600,
            visible=True,
            enabled=True,
            minimized=False,
        )
    )


def _context():
    return (
        LaunchFocusContext(
            command="open notepad",
            target="notepad",
            hwnd=333,
            process_id=44,
            process_name="notepad.exe",
            process_names=(
                frozenset(
                    {
                        "notepad.exe",
                    }
                )
            ),
            title="Untitled - Notepad",
            created_at=1.0,
        )
    )


# ======================================================
# GET CONTEXT
# ======================================================


def test_get_focus_context_returns_only_matching_launch_command():
    skill = (
        AppLauncherSkill()
    )

    context = (
        _context()
    )

    skill._focus_context = (
        context
    )

    assert (
        skill.get_focus_context(
            "open notepad"
        )
        == context
    )

    assert (
        skill.get_focus_context(
            "open calculator"
        )
        is None
    )


# ======================================================
# OWNED SAME-PROCESS FOREGROUND
# ======================================================


def test_recover_focus_context_preserves_owned_same_process_foreground(
    monkeypatch,
):
    skill = (
        AppLauncherSkill()
    )

    context = (
        _context()
    )

    popup_hwnd = 999

    monkeypatch.setattr(
        (
            launcher_module
            .ui_automation_service
        ),
        "get_foreground_window_info",
        lambda: (
            _window(
                hwnd=popup_hwnd,
                title="File menu",
            )
        ),
    )

    # GW_OWNER = 4.
    # The popup is valid only because it is explicitly
    # owned by the original verified workflow window.
    monkeypatch.setattr(
        launcher_module.win32gui,
        "GetWindow",
        lambda hwnd, relationship: (
            context.hwnd
            if (
                hwnd == popup_hwnd
                and relationship == 4
            )
            else 0
        ),
    )

    focus_calls = []

    monkeypatch.setattr(
        (
            launcher_module
            .ui_automation_service
        ),
        "focus_window",
        lambda *args, **kwargs: (
            focus_calls.append(
                (
                    args,
                    kwargs,
                )
            )
        ),
    )

    ok, reason = (
        skill.recover_focus_context(
            context
        )
    )

    assert (
        ok
        is True
    )

    assert (
        "already owns"
        in reason.lower()
    )

    assert (
        focus_calls
        == []
    )


# ======================================================
# EXACT HWND RECOVERY
# ======================================================


def test_recover_focus_context_uses_exact_verified_hwnd(
    monkeypatch,
):
    skill = (
        AppLauncherSkill()
    )

    context = (
        _context()
    )

    monkeypatch.setattr(
        (
            launcher_module
            .ui_automation_service
        ),
        "get_foreground_window_info",
        lambda: (
            _window(
                hwnd=999,
                title="Visual Studio Code",
                process_id=55,
                process_name="code.exe",
            )
        ),
    )

    calls = []

    def fake_focus_window(
        hwnd,
        *,
        expected_process_names=(),
        expected_title=None,
        timeout_seconds=None,
    ):
        calls.append(
            (
                hwnd,
                expected_process_names,
            )
        )

        return (
            UIAutomationFocusResult(
                status="focused",
                window=(
                    _window()
                ),
                candidates=(
                    _window(),
                ),
                reason="focused",
            )
        )

    monkeypatch.setattr(
        (
            launcher_module
            .ui_automation_service
        ),
        "focus_window",
        fake_focus_window,
    )

    ok, reason = (
        skill.recover_focus_context(
            context
        )
    )

    assert (
        ok
        is True
    )

    assert (
        calls
        == [
            (
                333,
                (
                    "notepad.exe",
                ),
            ),
        ]
    )


# ======================================================
# RECOVERED IDENTITY MUST MATCH ORIGINAL
# ======================================================


def test_recover_focus_context_rejects_different_window_identity(
    monkeypatch,
):
    skill = (
        AppLauncherSkill()
    )

    context = (
        _context()
    )

    monkeypatch.setattr(
        (
            launcher_module
            .ui_automation_service
        ),
        "get_foreground_window_info",
        lambda: (
            None
        ),
    )

    wrong_window = (
        _window(
            hwnd=444,
        )
    )

    monkeypatch.setattr(
        (
            launcher_module
            .ui_automation_service
        ),
        "focus_window",
        lambda *args, **kwargs: (
            UIAutomationFocusResult(
                status="focused",
                window=(
                    wrong_window
                ),
                candidates=(
                    wrong_window,
                ),
                reason="focused",
            )
        ),
    )

    ok, reason = (
        skill.recover_focus_context(
            context
        )
    )

    assert (
        ok
        is False
    )

    assert (
        "originally verified"
        in reason.lower()
    )


# ======================================================
# READINESS CAPTURES CONTEXT
# ======================================================


def test_wait_until_ready_captures_focus_context(
    monkeypatch,
):
    skill = (
        AppLauncherSkill()
    )

    skill.READINESS_STABLE_POLLS = (
        2
    )

    skill.READINESS_POLL_INTERVAL_SECONDS = (
        0.0
    )

    skill.READINESS_TIMEOUT_SECONDS = (
        1.0
    )

    observation = (
        LaunchReadiness(
            command="open notepad",
            target="notepad",
            kind="application",
            process_names=(
                frozenset(
                    {
                        "notepad.exe",
                    }
                )
            ),
            previous_foreground_hwnd=111,
            created_at=0.0,
        )
    )

    skill._last_launch = (
        observation
    )

    context = (
        _context()
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: 333,
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_matches",
        lambda **kwargs: True,
    )

    monkeypatch.setattr(
        skill,
        "_capture_focus_context",
        lambda **kwargs: (
            context
        ),
    )

    monkeypatch.setattr(
        launcher_module.time,
        "sleep",
        lambda _: None,
    )

    ok, reason = (
        skill.wait_until_ready(
            "open notepad"
        )
    )

    assert (
        ok
        is True
    )

    assert (
        skill.get_focus_context(
            "open notepad"
        )
        == context
    )

    assert (
        skill._last_launch
        is None
    )


# ======================================================
# INVALID CONTEXT
# ======================================================


def test_recover_focus_context_rejects_invalid_context():
    skill = (
        AppLauncherSkill()
    )

    ok, reason = (
        skill.recover_focus_context(
            object()
        )
    )

    assert (
        ok
        is False
    )

    assert (
        "invalid"
        in reason.lower()
    )
