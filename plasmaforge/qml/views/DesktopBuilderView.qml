import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import PlasmaForge.Controllers 1.0
import plasmaforge.qml.theme 1.0
import plasmaforge.qml.components 1.0

ScrollView {
    id: desktopBuilderRoot
    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        width: Math.min(desktopBuilderRoot.width - (Theme.spaceXxl * 2), 1140)
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Theme.spaceXl

        Item { height: Theme.spaceXs; Layout.fillWidth: true }

        PFSectionHeader {
            title: "Desktop Builder"
            subtitle: "Visual desktop workspace for planning, previewing, and managing KDE Plasma 6 panel layouts"

            RowLayout {
                spacing: Theme.spaceSm

                PFButton {
                    text: "Reset Draft"
                    iconText: "↺"
                    variant: "secondary"
                    size: "sm"
                    enabled: DesktopCtrl.isDraftModified
                    onClicked: {
                        DesktopCtrl.resetDraft()
                        AppCtrl.showToast("Draft layout reset to detected desktop configuration.", "info")
                    }
                }

                PFButton {
                    text: "Preview Changes (Diff)"
                    iconText: "⚡"
                    variant: "outline"
                    size: "sm"
                    onClicked: {
                        DesktopCtrl.requestDiffPreview()
                        diffDrawer.open()
                    }
                }

                PFButton {
                    text: "Apply Layout"
                    iconText: AppCtrl.safeMode ? "🛡" : "✓"
                    variant: "primary"
                    size: "sm"
                    onClicked: DesktopCtrl.requestApplyDraft()
                }

                PFButton {
                    text: "Restore Previous"
                    iconText: "↩"
                    variant: "secondary"
                    size: "sm"
                    visible: DesktopCtrl.canRestorePrevious
                    onClicked: DesktopCtrl.restorePreviousLayout()
                }
            }
        }

        // Layout Status Strip
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceMd

            PFBadge {
                text: "Detected: " + (DesktopCtrl.detectedLayout.name || "KDE Desktop")
                variant: "neutral"
                size: "sm"
            }

            PFBadge {
                text: DesktopCtrl.isDraftModified ? "Draft: Modified" : "Draft: In Sync"
                variant: DesktopCtrl.isDraftModified ? "accent" : "neutral"
                size: "sm"
            }

            PFBadge {
                text: AppCtrl.safeMode ? "Safe Mode (Simulation)" : "Live Mode"
                variant: AppCtrl.safeMode ? "accent" : "warning"
                size: "sm"
            }

            Item { Layout.fillWidth: true }

            Text {
                text: "Live applicable: panel & dock positions, thickness, visibility"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSizeXs
                color: Theme.textMuted
            }
        }

        // Visual Display Blueprint Card
        PFCard {
            Layout.fillWidth: true
            implicitHeight: 380

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceLg
                spacing: Theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Text {
                        text: "INTERACTIVE DISPLAY BLUEPRINT"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeXs
                        font.weight: Font.DemiBold
                        color: Theme.textMuted
                    }

                    Item { Layout.fillWidth: true }

                    PFBadge {
                        text: "Output: Wayland (1920×1080)"
                        variant: "neutral"
                        size: "xs"
                    }
                    PFBadge {
                        text: "Live: Panel Containment 47"
                        variant: "neutral"
                        size: "xs"
                    }
                    PFBadge {
                        text: "Simulation: Dock Float & Widgets"
                        variant: "accent"
                        size: "xs"
                    }
                }

                // Blueprint Monitor Canvas
                Rectangle {
                    id: monitorCanvas
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: Theme.radiusMd
                    color: "#0a0c10"
                    border.color: Theme.borderSubtle
                    border.width: 1
                    clip: true

                    // Monitor Bezel Frame
                    Rectangle {
                        id: screenArea
                        anchors.centerIn: parent
                        width: Math.min(parent.width - 32, (parent.height - 32) * (16 / 9))
                        height: Math.min(parent.height - 32, (parent.width - 32) * (9 / 16))
                        radius: Theme.radiusSm
                        color: "#12141a"
                        border.color: DesktopCtrl.isDraftModified ? Theme.accent : Theme.borderActive
                        border.width: 1
                        clip: true

                        // Wallpaper subtle matrix / grid
                        Grid {
                            anchors.centerIn: parent
                            columns: 6
                            spacing: Math.max(12, Math.min(36, Math.round(parent.width * 0.05)))
                            opacity: 0.12
                            Repeater {
                                model: 18
                                delegate: Rectangle {
                                    width: Math.max(20, Math.min(44, Math.round(screenArea.width * 0.08)))
                                    height: Math.max(14, Math.min(28, Math.round(screenArea.height * 0.09)))
                                    color: "transparent"
                                    border.color: Theme.accentLight
                                    border.width: 1
                                    radius: 2
                                }
                            }
                        }

                        // Optional Desktop Widgets Representation (e.g. Nothing-inspired clock & stats)
                        Rectangle {
                            visible: DesktopCtrl.showWidgets
                            x: {
                                var base = Math.max(16, Math.round(parent.width * 0.05))
                                if (DesktopCtrl.panelPosition === "left") {
                                    base = Math.max(base, visualTopPanel.width + 12)
                                }
                                if (DesktopCtrl.dockPosition === "left") {
                                    base = Math.max(base, visualDock.x + visualDock.width + 12)
                                }
                                return base
                            }
                            anchors.verticalCenter: parent.verticalCenter
                            width: Math.max(100, Math.min(140, Math.round(parent.width * 0.28)))
                            height: Math.max(64, Math.min(84, Math.round(parent.height * 0.3)))
                            radius: Theme.radiusMd
                            color: Qt.rgba(0.08, 0.09, 0.12, 0.75)
                            border.color: Qt.rgba(1, 1, 1, 0.12)
                            border.width: 1

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 2

                                Text {
                                    text: "22:04"
                                    font.family: Theme.fontMono
                                    font.pixelSize: 22
                                    font.weight: Font.Bold
                                    color: Theme.textPrimary
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Text {
                                    text: "SUN, OCT 25 • ARCH"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 8
                                    font.weight: Font.DemiBold
                                    color: Theme.accentLight
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                RowLayout {
                                    spacing: 4
                                    Layout.alignment: Qt.AlignHCenter
                                    Layout.topMargin: 4
                                    Rectangle { width: 6; height: 6; radius: 3; color: Theme.accent }
                                    Text { text: "RAM 38%  CPU 14%"; font.pixelSize: 8; color: Theme.textMuted }
                                }
                            }
                        }

                        // Top/Edge Panel Representation
                        Rectangle {
                            id: visualTopPanel
                            visible: DesktopCtrl.panelPosition !== "none"
                            readonly property bool isHorizontal: DesktopCtrl.panelPosition === "top" || DesktopCtrl.panelPosition === "bottom"
                            readonly property int panelThicknessPx: Math.max(16, Math.min(Math.round(parent.height * 0.14), Math.round(DesktopCtrl.panelThickness * (parent.height / 540))))

                            x: DesktopCtrl.panelPosition === "right" ? (parent.width - width) : 0
                            y: DesktopCtrl.panelPosition === "bottom" ? (parent.height - height) : (isHorizontal ? 0 : Math.round((parent.height - height) / 2))
                            width: isHorizontal ? parent.width : panelThicknessPx
                            height: isHorizontal ? panelThicknessPx : Math.max(80, Math.min(Math.round(parent.height * 0.38), 160))

                            color: Qt.rgba(0.09, 0.10, 0.14, 0.92)
                            border.color: Qt.rgba(1, 1, 1, 0.08)
                            border.width: 1
                            z: 10
                            clip: true

                            RowLayout {
                                visible: visualTopPanel.isHorizontal
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                spacing: 8

                                // App launcher icon
                                Rectangle {
                                    width: Math.max(10, Math.round(visualTopPanel.height * 0.55))
                                    height: width
                                    radius: 3
                                    color: Theme.accent
                                }

                                Text {
                                    text: "Applications"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 9
                                    font.weight: Font.DemiBold
                                    color: Theme.textSecondary
                                    visible: visualTopPanel.width > 220
                                }

                                Item { Layout.fillWidth: true }

                                // Center Clock (Nothing style or top status)
                                Text {
                                    text: "Sunday 22:04"
                                    font.family: Theme.fontMono
                                    font.pixelSize: 9
                                    color: Theme.textPrimary
                                }

                                Item { Layout.fillWidth: true }

                                // System Tray icons
                                RowLayout {
                                    spacing: 4
                                    Repeater {
                                        model: 4
                                        delegate: Rectangle {
                                            width: Math.max(6, Math.round(visualTopPanel.height * 0.4))
                                            height: width
                                            radius: 2
                                            color: Qt.rgba(1, 1, 1, 0.25)
                                        }
                                    }
                                }

                                Text {
                                    text: DesktopCtrl.panelVisibility === "auto_hide" ? "Auto-Hide" : (DesktopCtrl.panelVisibility === "dodge_windows" ? "Dodge" : "Visible")
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 8
                                    color: Theme.accentLight
                                    visible: visualTopPanel.width > 360
                                }
                            }

                            ColumnLayout {
                                visible: !visualTopPanel.isHorizontal
                                anchors.fill: parent
                                anchors.topMargin: 8
                                anchors.bottomMargin: 8
                                spacing: 6

                                Rectangle {
                                    Layout.alignment: Qt.AlignHCenter
                                    width: Math.max(10, Math.round(visualTopPanel.width * 0.55))
                                    height: width
                                    radius: 2
                                    color: Theme.accent
                                }

                                Item { Layout.fillHeight: true }

                                ColumnLayout {
                                    Layout.alignment: Qt.AlignHCenter
                                    spacing: 3
                                    Repeater {
                                        model: 3
                                        delegate: Rectangle {
                                            width: Math.max(6, Math.round(visualTopPanel.width * 0.35))
                                            height: width
                                            radius: 1
                                            color: Qt.rgba(1, 1, 1, 0.25)
                                        }
                                    }
                                }
                            }
                        }

                        // Bottom/Edge Dock Representation
                        Rectangle {
                            id: visualDock
                            visible: DesktopCtrl.dockPosition !== "none"
                            readonly property bool isHorizontal: DesktopCtrl.dockPosition === "bottom" || DesktopCtrl.dockPosition === "top"
                            readonly property int dockThicknessPx: Math.max(22, Math.min(Math.round(parent.height * 0.16), Math.round(DesktopCtrl.dockThickness * (parent.height / 500))))
                            readonly property int dockLengthPx: isHorizontal
                                ? Math.max(140, Math.min(Math.round(parent.width * 0.65), 330))
                                : Math.max(80, Math.min(Math.round(parent.height * 0.38), 160))

                            width: isHorizontal ? dockLengthPx : dockThicknessPx
                            height: isHorizontal ? dockThicknessPx : dockLengthPx
                            radius: Math.round(Math.min(width, height) / 2)

                            x: {
                                if (DesktopCtrl.dockPosition === "left") {
                                    return (DesktopCtrl.panelPosition === "left" ? (visualTopPanel.width + 6) : 8)
                                }
                                if (DesktopCtrl.dockPosition === "right") {
                                    var offR = (DesktopCtrl.panelPosition === "right" ? (visualTopPanel.width + 6) : 8)
                                    return parent.width - width - offR
                                }
                                return Math.round((parent.width - width) / 2)
                            }

                            y: {
                                if (DesktopCtrl.dockPosition === "top") {
                                    return (DesktopCtrl.panelPosition === "top" ? (visualTopPanel.height + 6) : 8)
                                }
                                if (DesktopCtrl.dockPosition === "bottom") {
                                    var offB = (DesktopCtrl.panelPosition === "bottom" ? (visualTopPanel.height + 6) : 8)
                                    return parent.height - height - offB
                                }
                                return Math.round((parent.height - height) / 2)
                            }

                            color: Qt.rgba(0.08, 0.09, 0.13, 0.94)
                            border.color: Qt.rgba(0.08, 0.72, 0.65, 0.45)
                            border.width: 1
                            z: 20
                            clip: true

                            RowLayout {
                                visible: visualDock.isHorizontal
                                anchors.centerIn: parent
                                spacing: 10

                                Repeater {
                                    model: 6
                                    delegate: Rectangle {
                                        width: Math.max(14, Math.min(28, Math.round(DesktopCtrl.dockIconSize * 0.55)))
                                        height: width
                                        radius: 6
                                        color: index === 0 ? Theme.accent : (index === 1 ? "#3b82f6" : (index === 2 ? "#eab308" : Qt.rgba(1, 1, 1, 0.22)))

                                        // Subtle running dot indicator under icons
                                        Rectangle {
                                            anchors.bottom: parent.bottom
                                            anchors.bottomMargin: -3
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            width: 3
                                            height: 3
                                            radius: 1.5
                                            color: Theme.accentLight
                                            visible: index < 3
                                        }
                                    }
                                }
                            }

                            ColumnLayout {
                                visible: !visualDock.isHorizontal
                                anchors.centerIn: parent
                                spacing: 6

                                Repeater {
                                    model: 4
                                    delegate: Rectangle {
                                        width: Math.max(14, Math.min(28, Math.round(DesktopCtrl.dockIconSize * 0.55)))
                                        height: width
                                        radius: 6
                                        color: index === 0 ? Theme.accent : (index === 1 ? "#3b82f6" : (index === 2 ? "#eab308" : Qt.rgba(1, 1, 1, 0.22)))
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // Layout Presets Section
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            Text {
                text: "LAYOUT PRESETS"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSizeXs
                font.weight: Font.DemiBold
                color: Theme.textMuted
            }

            GridLayout {
                Layout.fillWidth: true
                columns: desktopBuilderRoot.width > 860 ? 3 : (desktopBuilderRoot.width > 560 ? 2 : 1)
                columnSpacing: Theme.spaceMd
                rowSpacing: Theme.spaceMd

                Repeater {
                    model: DesktopCtrl.presets

                    delegate: PFCard {
                        Layout.fillWidth: true
                        implicitHeight: 108
                        color: DesktopCtrl.selectedPresetId === modelData.id ? Qt.rgba(0.08, 0.72, 0.65, 0.08) : Theme.surface
                        border.color: DesktopCtrl.selectedPresetId === modelData.id ? Theme.accent : Theme.borderSubtle

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                DesktopCtrl.loadPreset(modelData.id)
                                AppCtrl.showToast("Loaded preset: " + modelData.name, "info")
                            }
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: modelData.name
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeSm
                                    font.weight: Font.DemiBold
                                    color: DesktopCtrl.selectedPresetId === modelData.id ? Theme.accentLight : Theme.textPrimary
                                    Layout.fillWidth: true
                                }
                                PFBadge {
                                    text: modelData.id === "nothing_inspired" ? "Dual Panel" : (modelData.id === "classic_kde" ? "Conventional" : "Minimal")
                                    variant: DesktopCtrl.selectedPresetId === modelData.id ? "accent" : "neutral"
                                    size: "xs"
                                }
                            }

                            Text {
                                text: modelData.description
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.textSecondary
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                                maximumLineCount: 2
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }

        // Workbench Controls: 2-Column Responsive Layout
        GridLayout {
            Layout.fillWidth: true
            columns: desktopBuilderRoot.width > 860 ? 2 : 1
            columnSpacing: Theme.spaceLg
            rowSpacing: Theme.spaceLg

            // Column 1: Top Panel Controls
            PFCard {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                implicitHeight: 330

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.spaceMd

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "TOP STATUS PANEL"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            font.weight: Font.DemiBold
                            color: Theme.accentLight
                            Layout.fillWidth: true
                        }
                        PFBadge {
                            text: "Live Applicable"
                            variant: "accent"
                            size: "xs"
                        }
                    }

                    // Panel Position
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text { text: "Panel Position"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                        RowLayout {
                            spacing: 6
                            PFButton {
                                text: "Top"
                                size: "sm"
                                variant: DesktopCtrl.panelPosition === "top" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setPanelPosition("top")
                            }
                            PFButton {
                                text: "Bottom"
                                size: "sm"
                                variant: DesktopCtrl.panelPosition === "bottom" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setPanelPosition("bottom")
                            }
                            PFButton {
                                text: "None"
                                size: "sm"
                                variant: DesktopCtrl.panelPosition === "none" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setPanelPosition("none")
                            }
                        }
                    }

                    // Panel Thickness
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Thickness"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                            Item { Layout.fillWidth: true }
                            Text { text: DesktopCtrl.panelThickness + " px"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeXs; color: Theme.textPrimary }
                        }
                        Slider {
                            Layout.fillWidth: true
                            from: 24
                            to: 64
                            stepSize: 2
                            value: DesktopCtrl.panelThickness
                            onMoved: DesktopCtrl.setPanelThickness(Math.round(value))
                        }
                    }

                    // Panel Visibility
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text { text: "Visibility Mode"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                        RowLayout {
                            spacing: 6
                            PFButton {
                                text: "Always Visible"
                                size: "sm"
                                variant: DesktopCtrl.panelVisibility === "always_visible" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setPanelVisibility("always_visible")
                            }
                            PFButton {
                                text: "Auto-Hide"
                                size: "sm"
                                variant: DesktopCtrl.panelVisibility === "auto_hide" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setPanelVisibility("auto_hide")
                            }
                            PFButton {
                                text: "Dodge"
                                size: "sm"
                                variant: DesktopCtrl.panelVisibility === "dodge_windows" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setPanelVisibility("dodge_windows")
                            }
                        }
                    }
                }
            }

            // Column 2: Dock Controls
            PFCard {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                implicitHeight: 330

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.spaceMd

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "BOTTOM DOCK"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            font.weight: Font.DemiBold
                            color: Theme.accentLight
                            Layout.fillWidth: true
                        }
                        PFBadge {
                            text: "Live Applicable"
                            variant: "accent"
                            size: "xs"
                        }
                    }

                    // Dock Position
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text { text: "Dock Position"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                        RowLayout {
                            spacing: 6
                            PFButton {
                                text: "Bottom"
                                size: "sm"
                                variant: DesktopCtrl.dockPosition === "bottom" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setDockPosition("bottom")
                            }
                            PFButton {
                                text: "Top"
                                size: "sm"
                                variant: DesktopCtrl.dockPosition === "top" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setDockPosition("top")
                            }
                            PFButton {
                                text: "None"
                                size: "sm"
                                variant: DesktopCtrl.dockPosition === "none" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setDockPosition("none")
                            }
                        }
                    }

                    // Dock Icon Size
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Icon Size"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                            Item { Layout.fillWidth: true }
                            Text { text: DesktopCtrl.dockIconSize + " px"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeXs; color: Theme.textPrimary }
                        }
                        Slider {
                            Layout.fillWidth: true
                            from: 24
                            to: 64
                            stepSize: 2
                            value: DesktopCtrl.dockIconSize
                            onMoved: DesktopCtrl.setDockIconSize(Math.round(value))
                        }
                    }

                    // Dock Visibility
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text { text: "Visibility Mode"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                        RowLayout {
                            spacing: 6
                            PFButton {
                                text: "Always Visible"
                                size: "sm"
                                variant: DesktopCtrl.dockVisibility === "always_visible" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setDockVisibility("always_visible")
                            }
                            PFButton {
                                text: "Auto-Hide"
                                size: "sm"
                                variant: DesktopCtrl.dockVisibility === "auto_hide" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setDockVisibility("auto_hide")
                            }
                            PFButton {
                                text: "Dodge"
                                size: "sm"
                                variant: DesktopCtrl.dockVisibility === "dodge_windows" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setDockVisibility("dodge_windows")
                            }
                        }
                    }
                }
            }
        }

        // Widgets & Simulation Toggle Card
        PFCard {
            Layout.fillWidth: true
            implicitHeight: 84

            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceLg
                spacing: Theme.spaceMd

                Rectangle {
                    width: 36
                    height: 36
                    radius: Theme.radiusMd
                    color: Qt.rgba(0.08, 0.72, 0.65, 0.12)
                    border.color: Theme.borderSubtle
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "🧩"
                        font.pixelSize: 16
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    RowLayout {
                        spacing: Theme.spaceSm
                        Text {
                            text: "Desktop Widgets (Nothing-Inspired Clock & Stats)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                        }
                        PFBadge {
                            text: "Simulation Preview"
                            variant: "neutral"
                            size: "xs"
                        }
                    }
                    Text {
                        text: "Renders the Nothing OS typographic clock and system telemetry widget on the desktop canvas"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeXs
                        color: Theme.textSecondary
                    }
                }

                PFButton {
                    text: DesktopCtrl.showWidgets ? "Hide Widget" : "Show Widget"
                    variant: DesktopCtrl.showWidgets ? "primary" : "secondary"
                    size: "sm"
                    onClicked: DesktopCtrl.setShowWidgets(!DesktopCtrl.showWidgets)
                }
            }
        }

        Item { height: Theme.spaceXl; Layout.fillWidth: true }
    }

    // Slide-out Drawer for Diff Preview
    Drawer {
        id: diffDrawer
        width: Math.min(desktopBuilderRoot.width * 0.85, 780)
        height: desktopBuilderRoot.height
        edge: Qt.RightEdge
        dim: true

        background: Rectangle {
            color: Theme.background
            border.color: Theme.border
            border.width: 1
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceXl
            spacing: Theme.spaceMd

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "Configuration Changeset (Unified Diff)"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSizeLg
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                    Layout.fillWidth: true
                }
                PFButton {
                    text: "Close"
                    size: "sm"
                    variant: "secondary"
                    onClicked: diffDrawer.close()
                }
            }

            Text {
                text: "Target: ~/.config/plasma-org.kde.plasma.desktop-appletsrc"
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontSizeXs
                color: Theme.accentLight
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Theme.radiusMd
                color: "#0c0e12"
                border.color: Theme.borderSubtle
                border.width: 1

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceMd
                    clip: true

                    Text {
                        text: DesktopCtrl.currentDiffPreview || "No differences detected."
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSizeXs
                        color: Theme.textSecondary
                        wrapMode: Text.NoWrap
                    }
                }
            }
        }
    }

    // In-Window Confirmation Modal Overlay
    Rectangle {
        id: layoutConfirmOverlay
        visible: DesktopCtrl.showConfirmDialog
        anchors.fill: parent
        color: Qt.rgba(0.04, 0.05, 0.07, 0.78)
        z: 9999

        MouseArea {
            anchors.fill: parent
            onClicked: DesktopCtrl.cancelApply()
        }

        Rectangle {
            id: layoutModalCard
            width: Math.min(desktopBuilderRoot.width - 48, 580)
            height: Math.min(desktopBuilderRoot.height - 48, 520)
            anchors.centerIn: parent
            radius: Theme.radiusLg
            color: Theme.card
            border.color: AppCtrl.safeMode ? Theme.accent : Theme.warning
            border.width: 1

            MouseArea {
                anchors.fill: parent
                // absorb clicks inside modal card
            }

            ScrollView {
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                clip: true

                ColumnLayout {
                    width: layoutModalCard.width - (Theme.spaceXl * 2) - 16
                    spacing: Theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    Rectangle {
                        width: 36
                        height: 36
                        radius: Theme.radiusMd
                        color: AppCtrl.safeMode ? Qt.rgba(0.08, 0.72, 0.65, 0.15) : Qt.rgba(0.96, 0.62, 0.04, 0.15)
                        border.color: AppCtrl.safeMode ? Theme.accent : Theme.warning
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: AppCtrl.safeMode ? "🛡" : "⚡"
                            font.pixelSize: 18
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            text: "Confirm Desktop Layout Application"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeLg
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                        }

                        Text {
                            text: "Target: plasma-org.kde.plasma.desktop-appletsrc"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.accentLight
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderSubtle
                }

                // Safety Note
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: layoutSafetyCol.implicitHeight + 16
                    radius: Theme.radiusMd
                    color: AppCtrl.safeMode ? Qt.rgba(0.08, 0.72, 0.65, 0.1) : Qt.rgba(0.96, 0.62, 0.04, 0.1)
                    border.color: AppCtrl.safeMode ? Qt.rgba(0.08, 0.72, 0.65, 0.25) : Qt.rgba(0.96, 0.62, 0.04, 0.25)
                    border.width: 1

                    ColumnLayout {
                        id: layoutSafetyCol
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 4

                        Text {
                            text: AppCtrl.safeMode ? "Safe Mode Simulation:" : "Live Desktop Configuration Modification:"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            font.weight: Font.DemiBold
                            color: AppCtrl.safeMode ? Theme.accentLight : Theme.warning
                        }
                        Text {
                            text: AppCtrl.safeMode
                                ? "Safe Mode is active. A simulated dry-run will create a test snapshot and generate unified diffs without modifying your live configuration."
                                : "A verified cryptographic snapshot will be created before modifying any files. Supported panel position, thickness, and visibility keys will be applied. plasmashell will NOT be terminated."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textSecondary
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                // Pipeline Step Badges
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Rectangle {
                        height: 22
                        radius: Theme.radiusSm
                        color: Qt.rgba(1, 1, 1, 0.04)
                        border.color: Theme.borderSubtle
                        border.width: 1
                        Layout.fillWidth: true
                        Text { anchors.centerIn: parent; text: "1. Diff Preview"; font.pixelSize: 10; font.weight: Font.DemiBold; color: Theme.textMuted }
                    }
                    Rectangle {
                        height: 22
                        radius: Theme.radiusSm
                        color: Qt.rgba(0.08, 0.72, 0.65, 0.1)
                        border.color: Qt.rgba(0.08, 0.72, 0.65, 0.25)
                        border.width: 1
                        Layout.fillWidth: true
                        Text { anchors.centerIn: parent; text: "2. SHA256 Backup"; font.pixelSize: 10; font.weight: Font.DemiBold; color: Theme.accentLight }
                    }
                    Rectangle {
                        height: 22
                        radius: Theme.radiusSm
                        color: Qt.rgba(1, 1, 1, 0.04)
                        border.color: Theme.borderSubtle
                        border.width: 1
                        Layout.fillWidth: true
                        Text { anchors.centerIn: parent; text: "3. Safe Write"; font.pixelSize: 10; font.weight: Font.DemiBold; color: Theme.textMuted }
                    }
                    Rectangle {
                        height: 22
                        radius: Theme.radiusSm
                        color: Qt.rgba(0.08, 0.72, 0.65, 0.1)
                        border.color: Qt.rgba(0.08, 0.72, 0.65, 0.25)
                        border.width: 1
                        Layout.fillWidth: true
                        Text { anchors.centerIn: parent; text: "4. Verify & Rollback"; font.pixelSize: 10; font.weight: Font.DemiBold; color: Theme.accentLight }
                    }
                }

                // Diff preview block
                Rectangle {
                    Layout.fillWidth: true
                    height: 120
                    radius: Theme.radiusMd
                    color: "#0c0e12"
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ScrollView {
                        anchors.fill: parent
                        anchors.margins: Theme.spaceMd
                        clip: true

                        Text {
                            text: DesktopCtrl.currentDiffPreview || "No differences."
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textSecondary
                            wrapMode: Text.NoWrap
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                // Actions
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    Item { Layout.fillWidth: true }

                    PFButton {
                        text: "Cancel"
                        variant: "secondary"
                        size: "md"
                        onClicked: DesktopCtrl.cancelApply()
                    }

                        PFButton {
                            text: AppCtrl.safeMode ? "Confirm Simulation" : "Apply Layout to KDE"
                            iconText: AppCtrl.safeMode ? "🛡" : "✓"
                            variant: "primary"
                            size: "md"
                            onClicked: DesktopCtrl.confirmApplyDraft()
                        }
                    }
                }
            }
        }
    }
}
