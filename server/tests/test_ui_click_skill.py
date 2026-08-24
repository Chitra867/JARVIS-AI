from app.core.ui_automation import (
    UIAutomationResolution,
    UIAutomationTarget,
)

from app.skills.ui_click_skill import (
    UIAutomationClickSkill,
)


# ======================================================
# TEST HELPERS
# ======================================================


def _target(
    *,
    name: str = "Terminal",
    control_type: str = "MenuItem",
    left: int = 100,
    top: int = 100,
    right: int = 200,
    bottom: int = 150,
    enabled: bool = True,
    visible: bool = True,
    automation_id: str = "",
) -> UIAutomationTarget:
    return (
        UIAutomationTarget(
            name=name,

            control_type=(
                control_type
            ),

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

            enabled=enabled,
            visible=visible,

            automation_id=(
                automation_id
            ),
        )
    )


def _resolved(
    target: UIAutomationTarget,
    query: str | None = None,
) -> UIAutomationResolution:
    return (
        UIAutomationResolution(
            query=(
                query
                or target.name
            ),

            status="resolved",

            target=target,

            candidates=(
                target,
            ),

            reason="test",
        )
    )


def _stable_window(
    monkeypatch,
    skill: UIAutomationClickSkill,
    hwnd: int = 12345,
) -> None:
    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: hwnd,
    )


# ======================================================
# ROUTING / COMMAND RECOGNITION
# ======================================================


def test_click_target_command_is_handled():
    skill = (
        UIAutomationClickSkill()
    )

    assert skill.can_handle(
        "click terminal menu item"
    )

    assert skill.can_handle(
        "click close button"
    )


def test_bare_click_is_not_handled():
    skill = (
        UIAutomationClickSkill()
    )

    assert not skill.can_handle(
        "click"
    )


def test_confirmation_command_is_handled():
    skill = (
        UIAutomationClickSkill()
    )

    assert skill.can_handle(
        "confirm click abc123"
    )

    assert skill.can_handle(
        "confirm ui click abc123"
    )


def test_cancel_command_is_handled():
    skill = (
        UIAutomationClickSkill()
    )

    assert skill.can_handle(
        "cancel click"
    )

    assert skill.can_handle(
        "cancel ui click"
    )


# ======================================================
# AMBIGUOUS TARGET
# ======================================================


def test_ambiguous_target_does_not_click(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    _stable_window(
        monkeypatch,
        skill,
    )

    first = (
        _target(
            name="Search",
            control_type="TabItem",
        )
    )

    second = (
        _target(
            name="Search",
            control_type="Group",
        )
    )

    resolution = (
        UIAutomationResolution(
            query="search",

            status="ambiguous",

            target=None,

            candidates=(
                first,
                second,
            ),

            reason="test ambiguity",
        )
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: resolution,
    )

    clicked = {
        "value": False,
    }

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **_: clicked.update(
            value=True
        ),
    )

    result = (
        skill.execute(
            "click search"
        )
    )

    assert not clicked[
        "value"
    ]

    assert (
        "multiple possible matches"
        in result.lower()
    )

    assert (
        "no click"
        in result.lower()
    )


# ======================================================
# DISABLED TARGET
# ======================================================


def test_disabled_target_does_not_click(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    _stable_window(
        monkeypatch,
        skill,
    )

    target = (
        _target(
            name="Terminal",
            enabled=False,
        )
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: _resolved(
            target
        ),
    )

    clicked = {
        "value": False,
    }

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **_: clicked.update(
            value=True
        ),
    )

    result = (
        skill.execute(
            "click terminal menu item"
        )
    )

    assert not clicked[
        "value"
    ]

    assert (
        "not currently safe"
        in result.lower()
    )


# ======================================================
# ORDINARY TARGET MOVEMENT
# ======================================================


def test_changed_target_is_not_clicked(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    _stable_window(
        monkeypatch,
        skill,
    )

    first = (
        _target(
            name="Terminal",

            left=100,
            right=200,
        )
    )

    second = (
        _target(
            name="Terminal",

            left=500,
            right=600,
        )
    )

    resolutions = iter(
        (
            _resolved(
                first
            ),

            _resolved(
                second
            ),
        )
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: next(
            resolutions
        ),
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.time.sleep",
        lambda _: None,
    )

    clicked = {
        "value": False,
    }

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **_: clicked.update(
            value=True
        ),
    )

    result = (
        skill.execute(
            "click terminal menu item"
        )
    )

    assert not clicked[
        "value"
    ]

    assert (
        "changed position"
        in result.lower()
    )


# ======================================================
# ORDINARY SAFE CLICK
# ======================================================


def test_safe_stable_target_is_clicked(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    _stable_window(
        monkeypatch,
        skill,
    )

    target = (
        _target(
            name="Terminal",
            control_type="MenuItem",
        )
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: _resolved(
            target
        ),
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.time.sleep",
        lambda _: None,
    )

    clicks: list[
        tuple[
            int,
            int,
            str,
        ]
    ] = []

    def fake_click(
        *,
        x: int,
        y: int,
        button: str,
    ) -> None:
        clicks.append(
            (
                x,
                y,
                button,
            )
        )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        fake_click,
    )

    result = (
        skill.execute(
            "click terminal menu item"
        )
    )

    assert clicks == [
        (
            150,
            125,
            "left",
        )
    ]

    assert (
        "clicked"
        in result.lower()
    )

    assert (
        "ui automation verification"
        in result.lower()
    )


# ======================================================
# SENSITIVE ACTION REQUIRES CONFIRMATION
# ======================================================


def test_sensitive_target_requires_confirmation(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    _stable_window(
        monkeypatch,
        skill,
    )

    target = (
        _target(
            name="Delete",
            control_type="Button",
        )
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: _resolved(
            target
        ),
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.secrets.token_hex",
        lambda _: "abc123",
    )

    clicked = {
        "value": False,
    }

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **_: clicked.update(
            value=True
        ),
    )

    result = (
        skill.execute(
            "click delete button"
        )
    )

    assert not clicked[
        "value"
    ]

    assert (
        "sensitive"
        in result.lower()
        or
        "destructive"
        in result.lower()
    )

    assert (
        "confirm click abc123"
        in result.lower()
    )

    assert (
        skill._pending_confirmation
        is not None
    )


# ======================================================
# CLOSE ALSO REQUIRES CONFIRMATION
# ======================================================


def test_close_target_requires_confirmation(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    _stable_window(
        monkeypatch,
        skill,
    )

    target = (
        _target(
            name="Close",
            control_type="Button",
        )
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: _resolved(
            target
        ),
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.secrets.token_hex",
        lambda _: "abc123",
    )

    clicked = {
        "value": False,
    }

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **_: clicked.update(
            value=True
        ),
    )

    result = (
        skill.execute(
            "click close button"
        )
    )

    assert not clicked[
        "value"
    ]

    assert (
        "confirm click abc123"
        in result.lower()
    )


# ======================================================
# WRONG CONFIRMATION TOKEN
# ======================================================


def test_wrong_confirmation_token_does_not_click(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    _stable_window(
        monkeypatch,
        skill,
    )

    target = (
        _target(
            name="Delete",
            control_type="Button",
        )
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: _resolved(
            target
        ),
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.secrets.token_hex",
        lambda _: "abc123",
    )

    clicked = {
        "value": False,
    }

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **_: clicked.update(
            value=True
        ),
    )

    skill.execute(
        "click delete button"
    )

    result = (
        skill.execute(
            "confirm click ffffff"
        )
    )

    assert not clicked[
        "value"
    ]

    assert (
        "does not match"
        in result.lower()
    )

    # A wrong token invalidates the pending request.
    assert (
        skill._pending_confirmation
        is None
    )


# ======================================================
# CORRECT CONFIRMATION
# ======================================================


def test_sensitive_target_clicks_after_correct_confirmation(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    _stable_window(
        monkeypatch,
        skill,
    )

    target = (
        _target(
            name="Delete",
            control_type="Button",
        )
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: _resolved(
            target
        ),
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.secrets.token_hex",
        lambda _: "abc123",
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.time.sleep",
        lambda _: None,
    )

    clicks: list[
        dict[
            str,
            object,
        ]
    ] = []

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **kwargs: clicks.append(
            kwargs
        ),
    )

    initial_result = (
        skill.execute(
            "click delete button"
        )
    )

    assert (
        "confirm click abc123"
        in initial_result.lower()
    )

    assert clicks == []

    confirmed_result = (
        skill.execute(
            "confirm click abc123"
        )
    )

    assert len(
        clicks
    ) == 1

    assert clicks[
        0
    ] == {
        "x": 150,
        "y": 125,
        "button": "left",
    }

    assert (
        "clicked"
        in confirmed_result.lower()
    )

    assert (
        skill._pending_confirmation
        is None
    )


# ======================================================
# CONFIRMATION REPLAY PROTECTION
# ======================================================


def test_confirmation_token_cannot_be_replayed(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    _stable_window(
        monkeypatch,
        skill,
    )

    target = (
        _target(
            name="Delete",
            control_type="Button",
        )
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: _resolved(
            target
        ),
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.secrets.token_hex",
        lambda _: "abc123",
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.time.sleep",
        lambda _: None,
    )

    clicks: list[
        dict[
            str,
            object,
        ]
    ] = []

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **kwargs: clicks.append(
            kwargs
        ),
    )

    skill.execute(
        "click delete button"
    )

    first_confirmation = (
        skill.execute(
            "confirm click abc123"
        )
    )

    assert (
        "clicked"
        in first_confirmation.lower()
    )

    assert len(
        clicks
    ) == 1

    replay_result = (
        skill.execute(
            "confirm click abc123"
        )
    )

    assert len(
        clicks
    ) == 1

    assert (
        "no pending"
        in replay_result.lower()
    )


# ======================================================
# CANCELLATION
# ======================================================


def test_pending_click_can_be_cancelled(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    _stable_window(
        monkeypatch,
        skill,
    )

    target = (
        _target(
            name="Delete",
            control_type="Button",
        )
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: _resolved(
            target
        ),
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.secrets.token_hex",
        lambda _: "abc123",
    )

    skill.execute(
        "click delete button"
    )

    assert (
        skill._pending_confirmation
        is not None
    )

    result = (
        skill.execute(
            "cancel click"
        )
    )

    assert (
        skill._pending_confirmation
        is None
    )

    assert (
        "cancelled"
        in result.lower()
    )


# ======================================================
# EXPIRATION
# ======================================================


def test_expired_confirmation_does_not_click(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    _stable_window(
        monkeypatch,
        skill,
    )

    target = (
        _target(
            name="Delete",
            control_type="Button",
        )
    )

    clock = {
        "value": 100.0,
    }

    monkeypatch.setattr(
        "app.skills.ui_click_skill.time.monotonic",
        lambda: clock[
            "value"
        ],
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.secrets.token_hex",
        lambda _: "abc123",
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: _resolved(
            target
        ),
    )

    clicked = {
        "value": False,
    }

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **_: clicked.update(
            value=True
        ),
    )

    skill.execute(
        "click delete button"
    )

    clock[
        "value"
    ] = 200.0

    result = (
        skill.execute(
            "confirm click abc123"
        )
    )

    assert not clicked[
        "value"
    ]

    assert (
        "expired"
        in result.lower()
    )

    assert (
        skill._pending_confirmation
        is None
    )


# ======================================================
# SENSITIVE ACTION — WINDOW CHANGE
# ======================================================


def test_sensitive_click_is_cancelled_if_window_changes(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    current_window = {
        "hwnd": 100,
    }

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: current_window[
            "hwnd"
        ],
    )

    target = (
        _target(
            name="Delete",
            control_type="Button",
        )
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: _resolved(
            target
        ),
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.secrets.token_hex",
        lambda _: "abc123",
    )

    clicked = {
        "value": False,
    }

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **_: clicked.update(
            value=True
        ),
    )

    initial_result = (
        skill.execute(
            "click delete button"
        )
    )

    assert (
        "confirm click abc123"
        in initial_result.lower()
    )

    current_window[
        "hwnd"
    ] = 200

    result = (
        skill.execute(
            "confirm click abc123"
        )
    )

    assert not clicked[
        "value"
    ]

    assert (
        "active window changed"
        in result.lower()
    )

    assert (
        skill._pending_confirmation
        is None
    )


# ======================================================
# SENSITIVE ACTION — TARGET MOVEMENT
# ======================================================


def test_sensitive_target_movement_blocks_confirmed_click(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    _stable_window(
        monkeypatch,
        skill,
    )

    original = (
        _target(
            name="Delete",
            control_type="Button",

            left=100,
            right=200,
        )
    )

    moved = (
        _target(
            name="Delete",
            control_type="Button",

            left=500,
            right=600,
        )
    )

    resolutions = iter(
        (
            _resolved(
                original
            ),

            _resolved(
                moved
            ),
        )
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: next(
            resolutions
        ),
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.secrets.token_hex",
        lambda _: "abc123",
    )

    clicked = {
        "value": False,
    }

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **_: clicked.update(
            value=True
        ),
    )

    initial_result = (
        skill.execute(
            "click delete button"
        )
    )

    assert (
        "confirm click abc123"
        in initial_result.lower()
    )

    result = (
        skill.execute(
            "confirm click abc123"
        )
    )

    assert not clicked[
        "value"
    ]

    assert (
        "changed"
        in result.lower()
    )

    assert (
        "no click"
        in result.lower()
    )


# ======================================================
# ORDINARY ACTION — WINDOW CHANGE
# ======================================================


def test_safe_click_is_cancelled_if_window_changes(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    target = (
        _target(
            name="Terminal",
            control_type="MenuItem",
        )
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: _resolved(
            target
        ),
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.time.sleep",
        lambda _: None,
    )

    calls = {
        "count": 0,
    }

    def fake_foreground_window() -> int:
        calls[
            "count"
        ] += 1

        # Initial target lookup remains on the same
        # foreground window.
        #
        # During immediate revalidation, the active
        # window changes.
        if (
            calls[
                "count"
            ]
            <= 3
        ):
            return 100

        return 200

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        fake_foreground_window,
    )

    clicked = {
        "value": False,
    }

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **_: clicked.update(
            value=True
        ),
    )

    result = (
        skill.execute(
            "click terminal menu item"
        )
    )

    assert not clicked[
        "value"
    ]

    assert (
        "active window changed"
        in result.lower()
    )


# ======================================================
# NEW CLICK INVALIDATES OLD CONFIRMATION
# ======================================================


def test_new_click_request_clears_old_confirmation(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    _stable_window(
        monkeypatch,
        skill,
    )

    delete_target = (
        _target(
            name="Delete",
            control_type="Button",
        )
    )

    terminal_target = (
        _target(
            name="Terminal",
            control_type="MenuItem",
        )
    )

    def resolve(
        query: str,
    ) -> UIAutomationResolution:
        if (
            "delete"
            in query.lower()
        ):
            return (
                _resolved(
                    delete_target,
                    query=query,
                )
            )

        return (
            _resolved(
                terminal_target,
                query=query,
            )
        )

    monkeypatch.setattr(
        skill,
        "_resolve",
        resolve,
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.secrets.token_hex",
        lambda _: "abc123",
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.time.sleep",
        lambda _: None,
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **_: None,
    )

    first_result = (
        skill.execute(
            "click delete button"
        )
    )

    assert (
        "confirm click abc123"
        in first_result.lower()
    )

    assert (
        skill._pending_confirmation
        is not None
    )

    # A new click request must invalidate the previous
    # sensitive confirmation.
    skill.execute(
        "click terminal menu item"
    )

    assert (
        skill._pending_confirmation
        is None
    )

    old_confirmation = (
        skill.execute(
            "confirm click abc123"
        )
    )

    assert (
        "no pending"
        in old_confirmation.lower()
    )


# ======================================================
# AUTOMATION ID IDENTITY CHECK
# ======================================================


def test_changed_automation_id_blocks_click(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    _stable_window(
        monkeypatch,
        skill,
    )

    first = (
        _target(
            name="Terminal",
            automation_id="terminal-one",
        )
    )

    second = (
        _target(
            name="Terminal",
            automation_id="terminal-two",
        )
    )

    resolutions = iter(
        (
            _resolved(
                first
            ),

            _resolved(
                second
            ),
        )
    )

    monkeypatch.setattr(
        skill,
        "_resolve",
        lambda _: next(
            resolutions
        ),
    )

    monkeypatch.setattr(
        "app.skills.ui_click_skill.time.sleep",
        lambda _: None,
    )

    clicked = {
        "value": False,
    }

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **_: clicked.update(
            value=True
        ),
    )

    result = (
        skill.execute(
            "click terminal menu item"
        )
    )

    assert not clicked[
        "value"
    ]

    assert (
        "identity"
        in result.lower()
    )


# ======================================================
# NO FOREGROUND WINDOW
# ======================================================


def test_click_is_blocked_without_foreground_window(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    monkeypatch.setattr(
        skill,
        "_foreground_window_handle",
        lambda: 0,
    )

    clicked = {
        "value": False,
    }

    monkeypatch.setattr(
        "app.skills.ui_click_skill.pyautogui.click",
        lambda **_: clicked.update(
            value=True
        ),
    )

    result = (
        skill.execute(
            "click terminal menu item"
        )
    )

    assert not clicked[
        "value"
    ]

    assert (
        "active window"
        in result.lower()
    )