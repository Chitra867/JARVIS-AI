from app.core.ui_automation import (
    UIAutomationResolution,
    UIAutomationTarget,
)

from app.skills.ui_click_skill import (
    UIAutomationClickSkill,
)


def _target(
    *,
    name: str = "Close",
    control_type: str = "Button",
    left: int = 100,
    top: int = 100,
    right: int = 200,
    bottom: int = 150,
    enabled: bool = True,
    visible: bool = True,
) -> UIAutomationTarget:
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

            enabled=enabled,
            visible=visible,

            automation_id="",
        )
    )


def _resolved(
    target: UIAutomationTarget,
) -> UIAutomationResolution:
    return (
        UIAutomationResolution(
            query=target.name,

            status="resolved",

            target=target,

            candidates=(
                target,
            ),

            reason="test",
        )
    )


def test_click_target_command_is_handled():
    skill = (
        UIAutomationClickSkill()
    )

    assert skill.can_handle(
        "click the close button"
    )

    assert skill.can_handle(
        "click terminal menu item"
    )


def test_bare_click_is_not_handled():
    skill = (
        UIAutomationClickSkill()
    )

    assert not skill.can_handle(
        "click"
    )


def test_ambiguous_target_does_not_click(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
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

    assert not clicked["value"]

    assert (
        "multiple possible matches"
        in result.lower()
    )


def test_disabled_target_does_not_click(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    target = (
        _target(
            enabled=False
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
            "click close button"
        )
    )

    assert not clicked["value"]

    assert (
        "not currently safe"
        in result.lower()
    )


def test_changed_target_is_not_clicked(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    first = (
        _target(
            left=100,
            right=200,
        )
    )

    second = (
        _target(
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
            "click close button"
        )
    )

    assert not clicked["value"]

    assert (
        "changed position"
        in result.lower()
    )


def test_stable_target_is_clicked(
    monkeypatch,
):
    skill = (
        UIAutomationClickSkill()
    )

    target = (
        _target()
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
            "click close button"
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
        "after ui automation verification"
        in result.lower()
    )