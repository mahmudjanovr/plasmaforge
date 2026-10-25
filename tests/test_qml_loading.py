from PySide6.QtGui import QColor, QGuiApplication
import pytest

from plasmaforge.main import create_application


@pytest.fixture(scope="session")
def qapp() -> QGuiApplication:
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(["test", "-platform", "offscreen"])
    return app


def test_qml_full_startup(qapp: QGuiApplication) -> None:
    """Verify that main.qml and all subviews load cleanly in QQmlApplicationEngine."""
    app, engine = create_application(["test", "-platform", "offscreen"])
    assert app is not None
    assert engine is not None
    root_objects = engine.rootObjects()
    assert len(root_objects) > 0, "Failed to instantiate QML root ApplicationWindow"

    window = root_objects[0]
    assert window.property("title") == "PlasmaForge - KDE Plasma 6 Customization Studio"

    # Verify controller references
    app_ctrl = engine._controllers["app"]
    assert app_ctrl.activeSection == "Overview"

    # Cycle through all views
    sections = [
        "Overview",
        "Theme Studio",
        "Desktop Builder",
        "Setup Gallery",
        "Backups & Restore",
        "Settings",
    ]
    for section in sections:
        app_ctrl.navigateTo(section)
        assert app_ctrl.activeSection == section

    # Test responsive window resizing (minimum laptop dimensions 800x560 and wide 1440x900)
    window.setProperty("width", 800)
    window.setProperty("height", 560)
    theme_ctrl = engine._controllers["theme"]
    desktop_ctrl = engine._controllers["desktop"]
    backup_ctrl = engine._controllers["backup"]

    for sec in sections:
        app_ctrl.navigateTo(sec)
        assert app_ctrl.activeSection == sec
        app.processEvents()

    # Verify modal dialogs open and cancel cleanly on small screens
    app_ctrl.navigateTo("Theme Studio")
    theme_ctrl.requestApplySelected()
    assert theme_ctrl.showConfirmDialog is True
    app.processEvents()
    theme_ctrl.cancelApply()
    assert theme_ctrl.showConfirmDialog is False
    app.processEvents()

    app_ctrl.navigateTo("Desktop Builder")
    desktop_ctrl.requestApplyDraft()
    assert desktop_ctrl.showConfirmDialog is True
    app.processEvents()
    desktop_ctrl.cancelApply()
    assert desktop_ctrl.showConfirmDialog is False
    app.processEvents()

    app_ctrl.navigateTo("Backups & Restore")
    backup_ctrl.requestDeleteSnapshot("mock_target")
    assert backup_ctrl.showDeleteConfirmDialog is True
    app.processEvents()
    backup_ctrl.cancelDelete()
    assert backup_ctrl.showDeleteConfirmDialog is False
    app.processEvents()

    # Wide screen test
    window.setProperty("width", 1440)
    window.setProperty("height", 900)
    for sec in sections:
        app_ctrl.navigateTo(sec)
        app.processEvents()

    # Desktop Builder Blueprint & Header Regression Checks
    app_ctrl.navigateTo("Desktop Builder")
    for _ in range(8):
        app.processEvents()

    # Test position toggling (which previously triggered anchor overlap and huge circle capsule)
    desktop_ctrl.setDockPosition("top")
    desktop_ctrl.setDockPosition("bottom")
    desktop_ctrl.setPanelPosition("bottom")
    desktop_ctrl.setPanelPosition("top")
    for _ in range(8):
        app.processEvents()

    def find_screen(it):
        if it.metaObject().className().startswith("QQuickRectangle"):
            col = it.property("color")
            if isinstance(col, QColor) and col.name() == "#12141a":
                return it
        for ch in it.childItems():
            r = find_screen(ch)
            if r is not None:
                return r
        return None

    screen_rect = find_screen(window.contentItem())
    assert screen_rect is not None, "Desktop Builder monitor preview screenArea should exist"
    sw = screen_rect.width()
    sh = screen_rect.height()
    assert sw > 200 and sh > 100

    panel_item = None
    dock_item = None
    for ch in screen_rect.childItems():
        if not ch.isVisible():
            continue
        if int(ch.z()) == 10:
            panel_item = ch
        elif int(ch.z()) == 20:
            dock_item = ch

    assert panel_item is not None, "visualTopPanel must exist"
    assert dock_item is not None, "visualDock must exist"
    # Neither panel nor dock should balloon to fill the screen or exceed 40% height
    assert panel_item.height() <= sh * 0.4, f"Panel height {panel_item.height()} exceeded 40% of {sh}"
    assert dock_item.height() <= sh * 0.4, f"Dock height {dock_item.height()} exceeded 40% of {sh}"
    assert dock_item.property("radius") <= (dock_item.height() / 2) + 1.0, "Dock radius must be bounded by half-height"

    # Header action button should stay within window bounds across widths
    for test_w in [1100, 880, 800]:
        window.setProperty("width", test_w)
        for _ in range(8):
            app.processEvents()

        def find_btn(it, text):
            if it.property("text") == text:
                return it
            for ch in it.childItems():
                r = find_btn(ch, text)
                if r is not None:
                    return r
            return None

        apply_btn = find_btn(window.contentItem(), "Apply Layout")
        assert apply_btn is not None
        btn_scene_r = apply_btn.mapRectToScene(apply_btn.boundingRect()).right()
        assert btn_scene_r <= test_w + 1.0, f"Apply Layout button right {btn_scene_r} overflowed window width {test_w}"

    # Backups & Restore Two-Column Layout Regression Checks
    window.setProperty("width", 1400)
    window.setProperty("height", 860)
    app_ctrl.navigateTo("Backups & Restore")
    for _ in range(8):
        app.processEvents()

    def find_cards(it, cards=None):
        if cards is None:
            cards = []
        if "PFCard" in it.metaObject().className():
            cards.append(it)
        for ch in it.childItems():
            find_cards(ch, cards)
        return cards

    cards = find_cards(window.contentItem())
    large_cards = [c for c in cards if c.width() > 300 and c.height() > 400]
    # Both snapshots list card and detail diff card must be allocated proper widths in two-column mode
    assert len(large_cards) >= 2, f"Expected at least 2 large cards in 2-column mode, found {len(large_cards)}"
    for card in large_cards[:2]:
        assert card.width() >= 350, f"Card width {card.width()} was too narrow (collapsed column defect)"



