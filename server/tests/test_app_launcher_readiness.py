from app.skills.app_launcher_skill import (
    AppLauncherSkill,
    LaunchReadiness,
)


# ======================================================
# HELPERS
# ======================================================


def _observation(
    *,
    command: str = "open notepad",
    target: str = "notepad",
    kind: str = "application",
    process_names: frozenset[str] | None = None,
    previous_foreground_hwnd: int = 100,
) -> LaunchReadiness:
    return (
        LaunchReadiness(
            command=command,
            target=target,
            kind=kind,

            process_names=(
                process_names
                if process_names
                is not None
                else frozenset(
                    {
                        "notepad.exe",
                    }
                )
            ),

            previous_foreground_hwnd=(
                previous_foreground_hwnd
            ),

            created_at=0.0,
        )
    )


# ======================================================
# NO PENDING LAUNCH
# ======================================================


def test_wait_without_pending_launch_succeeds_immediately():
    skill = (
        AppLauncherSkill()
    )

    ready, reason = (
        skill.wait_until_ready(
            "open notepad"
        )
    )

    assert ready is True

    assert (
        "no launch readiness wait"
        in reason.lower()
    )


# ======================================================
# COMMAND MISMATCH
# ======================================================


def test_wait_for_different_command_does_not_consume_launch():
    skill = (
        AppLauncherSkill()
    )

    observation = (
        _observation()
    )

    skill._last_launch = (
        observation
    )

    ready, reason = (
        skill.wait_until_ready(
            "open chrome"
        )
    )

    assert ready is True

    assert (
        "does not belong"
        in reason.lower()
    )

    assert (
        skill._last_launch
        is observation
    )


# ======================================================
# STABLE WINDOW READINESS
# ======================================================


def test_wait_succeeds_after_stable_ready_window(
    monkeypatch,
):
    skill = (
        AppLauncherSkill()
    )

    skill._last_launch = (
        _observation()
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: 200,
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_matches",
        lambda **_: True,
    )

    monkeypatch.setattr(
        (
            "app.skills.app_launcher_skill."
            "time.sleep"
        ),
        lambda _: None,
    )

    ready, reason = (
        skill.wait_until_ready(
            "open notepad"
        )
    )

    assert ready is True

    assert (
        "notepad is ready"
        in reason.lower()
    )

    # Readiness is consumed after success.
    assert (
        skill._last_launch
        is None
    )


# ======================================================
# READINESS TIMEOUT
# ======================================================


def test_wait_times_out_when_window_never_becomes_ready(
    monkeypatch,
):
    skill = (
        AppLauncherSkill()
    )

    skill.READINESS_TIMEOUT_SECONDS = (
        0.3
    )

    skill.READINESS_POLL_INTERVAL_SECONDS = (
        0.1
    )

    skill._last_launch = (
        _observation()
    )

    clock = {
        "now": 0.0,
    }

    monkeypatch.setattr(
        (
            "app.skills.app_launcher_skill."
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
            "app.skills.app_launcher_skill."
            "time.sleep"
        ),
        fake_sleep,
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: 200,
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_matches",
        lambda **_: False,
    )

    ready, reason = (
        skill.wait_until_ready(
            "open notepad"
        )
    )

    assert ready is False

    assert (
        "timed out"
        in reason.lower()
    )

    assert (
        skill._last_launch
        is None
    )


# ======================================================
# APPLICATION PROCESS MATCH
# ======================================================


def test_application_window_matches_expected_process(
    monkeypatch,
):
    skill = (
        AppLauncherSkill()
    )

    observation = (
        _observation(
            process_names=(
                frozenset(
                    {
                        "notepad.exe",
                    }
                )
            )
        )
    )

    monkeypatch.setattr(
        (
            "app.skills.app_launcher_skill."
            "win32gui.IsWindow"
        ),
        lambda _: True,
    )

    monkeypatch.setattr(
        (
            "app.skills.app_launcher_skill."
            "win32gui.IsWindowVisible"
        ),
        lambda _: True,
    )

    monkeypatch.setattr(
        (
            "app.skills.app_launcher_skill."
            "win32gui.IsWindowEnabled"
        ),
        lambda _: True,
    )

    monkeypatch.setattr(
        skill,
        "_window_process_name",
        lambda _: "notepad.exe",
    )

    assert (
        skill._foreground_window_matches(
            hwnd=200,
            observation=observation,
        )
        is True
    )

    monkeypatch.setattr(
        skill,
        "_window_process_name",
        lambda _: "chrome.exe",
    )

    assert (
        skill._foreground_window_matches(
            hwnd=200,
            observation=observation,
        )
        is False
    )


# ======================================================
# GENERIC PATH FOREGROUND TRANSITION
# ======================================================


def test_generic_path_requires_foreground_window_change(
    monkeypatch,
):
    skill = (
        AppLauncherSkill()
    )

    observation = (
        _observation(
            target=(
                r"C:\Users\Test\document.txt"
            ),

            kind="foreground_change",

            process_names=(
                frozenset()
            ),

            previous_foreground_hwnd=(
                100
            ),
        )
    )

    monkeypatch.setattr(
        (
            "app.skills.app_launcher_skill."
            "win32gui.IsWindow"
        ),
        lambda _: True,
    )

    monkeypatch.setattr(
        (
            "app.skills.app_launcher_skill."
            "win32gui.IsWindowVisible"
        ),
        lambda _: True,
    )

    monkeypatch.setattr(
        (
            "app.skills.app_launcher_skill."
            "win32gui.IsWindowEnabled"
        ),
        lambda _: True,
    )

    # Same window as before launch.
    assert (
        skill._foreground_window_matches(
            hwnd=100,
            observation=observation,
        )
        is False
    )

    # A different foreground window appeared.
    assert (
        skill._foreground_window_matches(
            hwnd=200,
            observation=observation,
        )
        is True
    )


# ======================================================
# APPLICATION EXECUTION RECORDS READINESS
# ======================================================


def test_open_application_records_readiness_state(
    monkeypatch,
):
    skill = (
        AppLauncherSkill()
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: 100,
    )

    monkeypatch.setattr(
        skill,
        "_resolve_app",
        lambda _: (
            r"C:\Windows\System32\notepad.exe"
        ),
    )

    popen_calls: list[
        list[str]
    ] = []

    class FakeProcess:
        pass

    def fake_popen(
        args,
        **_,
    ):
        popen_calls.append(
            args
        )

        return (
            FakeProcess()
        )

    monkeypatch.setattr(
        (
            "app.skills.app_launcher_skill."
            "subprocess.Popen"
        ),
        fake_popen,
    )

    result = (
        skill.execute(
            "open notepad"
        )
    )

    assert (
        "opening notepad"
        in result.lower()
    )

    assert len(
        popen_calls
    ) == 1

    assert (
        skill._last_launch
        is not None
    )

    observation = (
        skill._last_launch
    )

    assert (
        observation.command
        == "open notepad"
    )

    assert (
        observation.target
        == "notepad"
    )

    assert (
        observation.kind
        == "application"
    )

    assert (
        "notepad.exe"
        in observation.process_names
    )

    assert (
        observation
        .previous_foreground_hwnd
        == 100
    )


# ======================================================
# PROCESS ALIAS RESOLUTION
# ======================================================


def test_terminal_readiness_includes_real_terminal_processes():
    skill = (
        AppLauncherSkill()
    )

    names = (
        skill
        ._readiness_process_names(
            app_name="terminal",
            executable=(
                r"C:\Windows\System32\wt.exe"
            ),
        )
    )

    assert (
        "windowsterminal.exe"
        in names
    )

    assert (
        "wt.exe"
        in names
    )

    assert (
        "powershell.exe"
        in names
    )