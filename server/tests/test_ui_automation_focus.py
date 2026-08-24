from app.core.ui_automation import (
    UIAutomationFocusResult,
    UIAutomationService,
    UIAutomationWindow,
)


# ======================================================
# HELPERS
# ======================================================


def _window(
    *,
    hwnd: int = 100,
    title: str = "Untitled - Notepad",
    process_id: int = 10,
    process_name: str = "notepad.exe",
    left: int = 10,
    top: int = 10,
    right: int = 800,
    bottom: int = 600,
    visible: bool = True,
    enabled: bool = True,
    minimized: bool = False,
) -> UIAutomationWindow:
    return (
        UIAutomationWindow(
            hwnd=hwnd,
            title=title,
            process_id=process_id,
            process_name=process_name,
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            visible=visible,
            enabled=enabled,
            minimized=minimized,
        )
    )


# ======================================================
# PREFERRED HWND
# ======================================================


def test_resolve_window_prefers_verified_hwnd(
    monkeypatch,
):
    service = (
        UIAutomationService()
    )

    preferred = (
        _window(
            hwnd=444,
        )
    )

    monkeypatch.setattr(
        service,
        "_build_window_info",
        lambda hwnd: (
            preferred
            if hwnd == 444
            else None
        ),
    )

    enumerated = {
        "called": False,
    }

    def fake_enumerate():
        enumerated[
            "called"
        ] = True

        return []

    monkeypatch.setattr(
        service,
        "_enumerate_top_level_windows",
        fake_enumerate,
    )

    resolution = (
        service.resolve_window(
            process_names=(
                "notepad.exe",
            ),
            preferred_hwnd=444,
        )
    )

    assert (
        resolution.resolved
        is True
    )

    assert (
        resolution.window
        == preferred
    )

    assert (
        enumerated["called"]
        is False
    )


# ======================================================
# UNIQUE APPLICATION WINDOW
# ======================================================


def test_resolve_window_accepts_one_unique_match(
    monkeypatch,
):
    service = (
        UIAutomationService()
    )

    notepad = (
        _window(
            hwnd=101,
        )
    )

    chrome = (
        _window(
            hwnd=202,
            title="ChatGPT - Chrome",
            process_id=20,
            process_name="chrome.exe",
        )
    )

    monkeypatch.setattr(
        service,
        "_enumerate_top_level_windows",
        lambda: [
            notepad,
            chrome,
        ],
    )

    resolution = (
        service.resolve_window(
            process_names=(
                "notepad.exe",
            ),
        )
    )

    assert (
        resolution.resolved
        is True
    )

    assert (
        resolution.window
        == notepad
    )


# ======================================================
# AMBIGUITY
# ======================================================


def test_resolve_window_blocks_multiple_equal_matches(
    monkeypatch,
):
    service = (
        UIAutomationService()
    )

    first = (
        _window(
            hwnd=101,
            title="Untitled - Notepad",
            process_id=10,
        )
    )

    second = (
        _window(
            hwnd=102,
            title="Notes - Notepad",
            process_id=11,
        )
    )

    monkeypatch.setattr(
        service,
        "_enumerate_top_level_windows",
        lambda: [
            first,
            second,
        ],
    )

    resolution = (
        service.resolve_window(
            process_names=(
                "notepad.exe",
            ),
        )
    )

    assert (
        resolution.status
        == "ambiguous"
    )

    assert (
        resolution.window
        is None
    )

    assert (
        len(
            resolution.candidates
        )
        == 2
    )


# ======================================================
# TITLE DISAMBIGUATION
# ======================================================


def test_title_can_disambiguate_same_process_windows(
    monkeypatch,
):
    service = (
        UIAutomationService()
    )

    first = (
        _window(
            hwnd=101,
            title="Untitled - Notepad",
            process_id=10,
        )
    )

    second = (
        _window(
            hwnd=102,
            title="Shopping List - Notepad",
            process_id=11,
        )
    )

    monkeypatch.setattr(
        service,
        "_enumerate_top_level_windows",
        lambda: [
            first,
            second,
        ],
    )

    resolution = (
        service.resolve_window(
            process_names=(
                "notepad.exe",
            ),
            title=(
                "Shopping List"
            ),
        )
    )

    assert (
        resolution.resolved
        is True
    )

    assert (
        resolution.window
        == second
    )


# ======================================================
# RECOVER FOCUS — AMBIGUITY
# ======================================================


def test_recover_focus_does_not_choose_ambiguous_window(
    monkeypatch,
):
    service = (
        UIAutomationService()
    )

    first = (
        _window(
            hwnd=101,
            process_id=10,
        )
    )

    second = (
        _window(
            hwnd=102,
            process_id=11,
        )
    )

    monkeypatch.setattr(
        service,
        "_enumerate_top_level_windows",
        lambda: [
            first,
            second,
        ],
    )

    focus_called = {
        "value": False,
    }

    def fake_focus_window(
        *args,
        **kwargs,
    ):
        focus_called[
            "value"
        ] = True

        return (
            UIAutomationFocusResult(
                status="focused",
                window=first,
                candidates=(
                    first,
                ),
                reason="should not run",
            )
        )

    monkeypatch.setattr(
        service,
        "focus_window",
        fake_focus_window,
    )

    result = (
        service.recover_focus(
            process_names=(
                "notepad.exe",
            ),
        )
    )

    assert (
        result.status
        == "ambiguous"
    )

    assert (
        result.success
        is False
    )

    assert (
        focus_called["value"]
        is False
    )


# ======================================================
# ALREADY FOCUSED
# ======================================================


def test_focus_window_succeeds_when_already_foreground(
    monkeypatch,
):
    service = (
        UIAutomationService()
    )

    target = (
        _window(
            hwnd=333,
        )
    )

    monkeypatch.setattr(
        service,
        "_build_window_info",
        lambda hwnd: (
            target
            if hwnd == 333
            else None
        ),
    )

    monkeypatch.setattr(
        service,
        "_foreground_window_handle",
        lambda: 333,
    )

    result = (
        service.focus_window(
            333,
            expected_process_names=(
                "notepad.exe",
            ),
        )
    )

    assert (
        result.success
        is True
    )

    assert (
        result.status
        == "already_focused"
    )

    assert (
        result.window
        == target
    )


# ======================================================
# IDENTITY MISMATCH
# ======================================================


def test_focus_window_blocks_process_identity_mismatch(
    monkeypatch,
):
    service = (
        UIAutomationService()
    )

    wrong = (
        _window(
            hwnd=333,
            title="Chrome",
            process_id=99,
            process_name="chrome.exe",
        )
    )

    monkeypatch.setattr(
        service,
        "_build_window_info",
        lambda _: wrong,
    )

    result = (
        service.focus_window(
            333,
            expected_process_names=(
                "notepad.exe",
            ),
        )
    )

    assert (
        result.success
        is False
    )

    assert (
        result.status
        == "mismatch"
    )


# ======================================================
# SUCCESSFUL FOCUS RECOVERY
# ======================================================


def test_focus_window_recovers_expected_window(
    monkeypatch,
):
    service = (
        UIAutomationService()
    )

    target = (
        _window(
            hwnd=333,
        )
    )

    monkeypatch.setattr(
        service,
        "_build_window_info",
        lambda hwnd: (
            target
            if hwnd == 333
            else None
        ),
    )

    foreground = {
        "hwnd": 999,
    }

    monkeypatch.setattr(
        service,
        "_foreground_window_handle",
        lambda: foreground[
            "hwnd"
        ],
    )

    class FakeWrapper:
        def set_focus(
            self,
        ) -> None:
            foreground[
                "hwnd"
            ] = 333

    class FakeWindowSpec:
        def wrapper_object(
            self,
        ):
            return (
                FakeWrapper()
            )

    class FakeDesktop:
        def __init__(
            self,
            *,
            backend: str,
        ) -> None:
            assert (
                backend
                == "uia"
            )

        def window(
            self,
            *,
            handle: int,
        ):
            assert (
                handle
                == 333
            )

            return (
                FakeWindowSpec()
            )

    monkeypatch.setattr(
        (
            "app.core.ui_automation."
            "Desktop"
        ),
        FakeDesktop,
    )

    monkeypatch.setattr(
        (
            "app.core.ui_automation."
            "time.sleep"
        ),
        lambda _: None,
    )

    result = (
        service.focus_window(
            333,
            expected_process_names=(
                "notepad.exe",
            ),
            timeout_seconds=0.1,
        )
    )

    assert (
        result.success
        is True
    )

    assert (
        result.status
        == "focused"
    )

    assert (
        foreground["hwnd"]
        == 333
    )


# ======================================================
# MINIMIZED WINDOW RESTORE
# ======================================================


def test_focus_window_restores_minimized_window(
    monkeypatch,
):
    service = (
        UIAutomationService()
    )

    minimized = (
        _window(
            hwnd=333,
            minimized=True,
        )
    )

    restored = (
        _window(
            hwnd=333,
            minimized=False,
        )
    )

    build_calls = {
        "count": 0,
    }

    def fake_build_window_info(
        hwnd: int,
    ):
        assert (
            hwnd
            == 333
        )

        build_calls[
            "count"
        ] += 1

        if (
            build_calls["count"]
            == 1
        ):
            return minimized

        return restored

    monkeypatch.setattr(
        service,
        "_build_window_info",
        fake_build_window_info,
    )

    foreground = {
        "hwnd": 999,
    }

    monkeypatch.setattr(
        service,
        "_foreground_window_handle",
        lambda: foreground[
            "hwnd"
        ],
    )

    restore_calls = []

    def fake_show_window(
        hwnd: int,
        command: int,
    ) -> None:
        restore_calls.append(
            (
                hwnd,
                command,
            )
        )

    monkeypatch.setattr(
        (
            "app.core.ui_automation."
            "win32gui.ShowWindow"
        ),
        fake_show_window,
    )

    class FakeWrapper:
        def set_focus(
            self,
        ) -> None:
            foreground[
                "hwnd"
            ] = 333

    class FakeWindowSpec:
        def wrapper_object(
            self,
        ):
            return (
                FakeWrapper()
            )

    class FakeDesktop:
        def __init__(
            self,
            *,
            backend: str,
        ) -> None:
            pass

        def window(
            self,
            *,
            handle: int,
        ):
            return (
                FakeWindowSpec()
            )

    monkeypatch.setattr(
        (
            "app.core.ui_automation."
            "Desktop"
        ),
        FakeDesktop,
    )

    monkeypatch.setattr(
        (
            "app.core.ui_automation."
            "time.sleep"
        ),
        lambda _: None,
    )

    result = (
        service.focus_window(
            333,
            expected_process_names=(
                "notepad.exe",
            ),
            timeout_seconds=0.1,
        )
    )

    assert (
        result.success
        is True
    )

    assert len(
        restore_calls
    ) == 1

    assert (
        restore_calls[
            0
        ][0]
        == 333
    )


# ======================================================
# FOCUS TIMEOUT
# ======================================================


def test_focus_window_times_out_if_foreground_never_changes(
    monkeypatch,
):
    service = (
        UIAutomationService()
    )

    target = (
        _window(
            hwnd=333,
        )
    )

    monkeypatch.setattr(
        service,
        "_build_window_info",
        lambda _: target,
    )

    monkeypatch.setattr(
        service,
        "_foreground_window_handle",
        lambda: 999,
    )

    class FakeWrapper:
        def set_focus(
            self,
        ) -> None:
            # Simulate Windows ignoring the focus request.
            return None

    class FakeWindowSpec:
        def wrapper_object(
            self,
        ):
            return (
                FakeWrapper()
            )

    class FakeDesktop:
        def __init__(
            self,
            *,
            backend: str,
        ) -> None:
            pass

        def window(
            self,
            *,
            handle: int,
        ):
            return (
                FakeWindowSpec()
            )

    monkeypatch.setattr(
        (
            "app.core.ui_automation."
            "Desktop"
        ),
        FakeDesktop,
    )

    clock = {
        "now": 0.0,
    }

    monkeypatch.setattr(
        (
            "app.core.ui_automation."
            "time.monotonic"
        ),
        lambda: clock[
            "now"
        ],
    )

    def fake_sleep(
        seconds: float,
    ) -> None:
        clock[
            "now"
        ] += seconds

    monkeypatch.setattr(
        (
            "app.core.ui_automation."
            "time.sleep"
        ),
        fake_sleep,
    )

    result = (
        service.focus_window(
            333,
            expected_process_names=(
                "notepad.exe",
            ),
            timeout_seconds=0.1,
        )
    )

    assert (
        result.success
        is False
    )

    assert (
        result.status
        == "timeout"
    )