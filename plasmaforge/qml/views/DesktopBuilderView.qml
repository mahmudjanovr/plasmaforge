import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import PlasmaForge.Controllers 1.0
import plasmaforge.qml.theme 1.0
import plasmaforge.qml.components 1.0

Item {
    id: desktopBuilderRoot

    property string widgetSearchQuery: ""
    property string selectedCategory: "All"
    property string selectedTargetFilter: "all"
    property bool showSavePresetDialog: false

    function getFilteredWidgets() {
        var list = DesktopCtrl.installedWidgets
        var q = widgetSearchQuery.toLowerCase().trim()
        var cat = selectedCategory
        var target = selectedTargetFilter
        return list.filter(function(w) {
            if (cat !== "All" && w.category !== cat) return false
            if (target === "panel" && (!w.suitable_for || w.suitable_for.indexOf("panel") === -1)) return false
            if (target === "desktop" && (!w.suitable_for || w.suitable_for.indexOf("desktop") === -1)) return false
            if (q) {
                var name = (w.name || "").toLowerCase()
                var desc = (w.description || "").toLowerCase()
                var pid = (w.plugin_id || "").toLowerCase()
                return name.indexOf(q) !== -1 || desc.indexOf(q) !== -1 || pid.indexOf(q) !== -1
            }
            return true
        })
    }

    Connections {
        target: DesktopCtrl
        function onApplyFinished(success, message, isDryRun) {
            var level = success ? (isDryRun ? "info" : "success") : "error"
            AppCtrl.showToast(message, level)
        }
        function onRestoreFinished(success, message) {
            AppCtrl.showToast(message, success ? "success" : "error")
        }
    }

    ScrollView {
        id: desktopScrollView
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        Item {
            width: desktopScrollView.availableWidth
            implicitHeight: desktopMainCol.implicitHeight + Theme.spaceXl * 2

            ColumnLayout {
                id: desktopMainCol
                width: Math.min(parent.width - (Theme.spaceXxl * 2), 1140)
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Theme.spaceXl

                Item { height: Theme.spaceXs; Layout.fillWidth: true }

        PFSectionHeader {
            title: "Desktop Builder"
            subtitle: "Visual desktop workspace for planning, previewing, and managing KDE Plasma 6 panel layouts"

            RowLayout {
                spacing: Theme.spaceSm

                PFButton {
                    text: DesktopCtrl.isInspecting ? "Inspecting..." : "Refresh Inspection"
                    iconText: "⟳"
                    variant: "secondary"
                    size: "sm"
                    enabled: !DesktopCtrl.isInspecting
                    onClicked: {
                        DesktopCtrl.refreshInspection()
                        AppCtrl.showToast("Inspecting live KDE Plasma desktop...", "info")
                    }
                }

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
        Flow {
            Layout.fillWidth: true
            spacing: Theme.spaceMd

            PFBadge {
                text: "Source: " + (DesktopCtrl.inspectionSource === "live_system" ? "Live D-Bus" : (DesktopCtrl.inspectionSource === "inferred_config" ? "Inferred Config" : "Unavailable"))
                variant: DesktopCtrl.inspectionSource === "live_system" ? "accent" : (DesktopCtrl.inspectionSource === "inferred_config" ? "warning" : "neutral")
                size: "sm"
            }

            PFBadge {
                text: "Inspected: " + (DesktopCtrl.lastInspectionTime || "Never")
                variant: "neutral"
                size: "sm"
            }

            PFBadge {
                text: "Plasma " + (DesktopCtrl.environmentInfo.plasma_version || "6") + " (" + (DesktopCtrl.environmentInfo.session_type || "Wayland") + ")"
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

            PFBadge {
                visible: DesktopCtrl.hasProposedChanges
                text: DesktopCtrl.proposedChanges.length + " Proposed Change" + (DesktopCtrl.proposedChanges.length > 1 ? "s" : "")
                variant: "accent"
                size: "sm"
            }

            Text {
                text: "• Live applicable: panel & dock positions, thickness, visibility"
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

                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Text {
                        text: "INTERACTIVE DISPLAY BLUEPRINT"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeXs
                        font.weight: Font.DemiBold
                        color: Theme.textMuted
                    }

                    Item { width: Theme.spaceSm; height: 1 }

                    PFBadge {
                        text: "Display: " + (DesktopCtrl.environmentInfo.display_summary || "Output")
                        variant: "neutral"
                        size: "xs"
                    }

                    Repeater {
                        model: DesktopCtrl.livePanels
                        delegate: PFBadge {
                            text: (modelData.is_dock ? "Dock" : "Panel") + (modelData.containment_id ? (" #" + modelData.containment_id) : "") + ": " + modelData.position + " (" + modelData.thickness + "px)"
                            variant: "neutral"
                            size: "xs"
                        }
                    }

                    PFBadge {
                        text: "Live Widgets: " + DesktopCtrl.liveDesktopWidgets.length + " detected"
                        variant: "neutral"
                        size: "xs"
                    }

                    PFBadge {
                        text: "Theme: " + (DesktopCtrl.environmentInfo.active_look_and_feel || "Breeze")
                        variant: "neutral"
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

        // Proposed Changes Preview Card (Draft Workbench vs Detected Live)
        PFCard {
            visible: DesktopCtrl.hasProposedChanges
            Layout.fillWidth: true
            implicitHeight: proposedChangesCol.implicitHeight + (Theme.spaceLg * 2)

            ColumnLayout {
                id: proposedChangesCol
                anchors.fill: parent
                anchors.margins: Theme.spaceLg
                spacing: Theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Rectangle {
                        width: 28
                        height: 28
                        radius: Theme.radiusSm
                        color: Qt.rgba(0.08, 0.72, 0.65, 0.15)
                        border.color: Theme.accent
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "Δ"
                            font.pixelSize: 14
                            font.weight: Font.Bold
                            color: Theme.accentLight
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: "PROPOSED BLUEPRINT CHANGES (" + DesktopCtrl.proposedChanges.length + ")"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            font.weight: Font.DemiBold
                            color: Theme.accentLight
                        }
                        Text {
                            text: "Modifications staged in draft workbench ready for transactional review and apply"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }
                    }

                    PFBadge {
                        text: "Staged Changes"
                        variant: "accent"
                        size: "sm"
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderSubtle
                }

                // Changes Repeater
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Repeater {
                        model: DesktopCtrl.proposedChanges

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: changeItemCol.implicitHeight + 16
                            radius: Theme.radiusSm
                            color: Qt.rgba(1, 1, 1, 0.02)
                            border.color: Theme.borderSubtle
                            border.width: 1

                            ColumnLayout {
                                id: changeItemCol
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 6

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spaceSm

                                    Text {
                                        text: modelData.component
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeSm
                                        font.weight: Font.DemiBold
                                        color: Theme.textPrimary
                                        Layout.fillWidth: true
                                    }

                                    PFBadge {
                                        text: modelData.is_supported_live ? "Live Applicable" : "Preview Simulation"
                                        variant: modelData.is_supported_live ? "success" : "neutral"
                                        size: "xs"
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spaceMd

                                    RowLayout {
                                        spacing: 6
                                        Text { text: "Current:"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                                        Text { text: modelData.current_value; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeXs; font.weight: Font.DemiBold; color: Theme.textSecondary }
                                    }

                                    Text { text: "→"; font.pixelSize: Theme.fontSizeSm; color: Theme.accentLight }

                                    RowLayout {
                                        spacing: 6
                                        Text { text: "Proposed:"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                                        Text { text: modelData.proposed_value; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeXs; font.weight: Font.Bold; color: Theme.accentLight }
                                    }

                                    Item { Layout.fillWidth: true }
                                }

                                Text {
                                    text: modelData.description
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeXs
                                    color: Theme.textMuted
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }
                }
            }
        }

        // Live Detected Desktop Environment & Panels Inspector
        PFCard {
            Layout.fillWidth: true
            implicitHeight: liveInspectorCol.implicitHeight + (Theme.spaceLg * 2)

            ColumnLayout {
                id: liveInspectorCol
                anchors.fill: parent
                anchors.margins: Theme.spaceLg
                spacing: Theme.spaceMd

                // Header
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Rectangle {
                        width: 28
                        height: 28
                        radius: Theme.radiusSm
                        color: Qt.rgba(0.23, 0.51, 0.96, 0.15)
                        border.color: "#3b82f6"
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "🔍"
                            font.pixelSize: 14
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            spacing: Theme.spaceSm
                            Text {
                                text: "LIVE KDE PLASMA 6 INSPECTOR"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                font.weight: Font.DemiBold
                                color: "#60a5fa"
                            }
                            PFBadge {
                                text: "Read-Only Discovery"
                                variant: "neutral"
                                size: "xs"
                            }
                        }
                        Text {
                            text: DesktopCtrl.inspectionStatusText || "Real-time state discovered via KDE Plasma D-Bus & configuration"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }

                    PFButton {
                        text: DesktopCtrl.isInspecting ? "Inspecting..." : "Refresh"
                        iconText: "⟳"
                        variant: "secondary"
                        size: "sm"
                        enabled: !DesktopCtrl.isInspecting
                        onClicked: DesktopCtrl.refreshInspection()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderSubtle
                }

                // Environment Summary Grid
                GridLayout {
                    Layout.fillWidth: true
                    columns: desktopBuilderRoot.width > 760 ? 4 : (desktopBuilderRoot.width > 520 ? 2 : 1)
                    columnSpacing: Theme.spaceMd
                    rowSpacing: Theme.spaceSm

                    ColumnLayout {
                        spacing: 2
                        Text { text: "Plasma & Session"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                        Text {
                            text: (DesktopCtrl.environmentInfo.plasma_version || "6.x") + " • " + (DesktopCtrl.environmentInfo.session_type || "Wayland")
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSm
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Text { text: "Display Resolution"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                        Text {
                            text: DesktopCtrl.environmentInfo.display_summary || "1920×1080"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSm
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Text { text: "Global Theme / Look&Feel"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                        Text {
                            text: DesktopCtrl.environmentInfo.active_look_and_feel || "org.kde.breeze.desktop"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSm
                            font.weight: Font.DemiBold
                            color: Theme.accentLight
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Text { text: "Inspection Source"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                        RowLayout {
                            spacing: 4
                            Rectangle {
                                width: 8
                                height: 8
                                radius: 4
                                color: DesktopCtrl.inspectionSource === "live_system" ? "#10b981" : "#f59e0b"
                            }
                            Text {
                                text: DesktopCtrl.inspectionSource === "live_system" ? "Live D-Bus Session" : "Inferred On-Disk Config"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                            }
                        }
                    }
                }

                // Detected Panels Header
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm
                    Layout.topMargin: Theme.spaceSm

                    Text {
                        text: "DETECTED PLASMA CONTAINMENTS (" + DesktopCtrl.livePanels.length + ")"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeXs
                        font.weight: Font.DemiBold
                        color: Theme.textMuted
                    }
                }

                // Empty state if 0 panels
                PFEmptyState {
                    visible: DesktopCtrl.livePanels.length === 0 && !DesktopCtrl.isInspecting
                    title: "No Panels Detected"
                    description: "No KDE Plasma panels or docks found on the active screen output."
                    statusTag: "Inspection Result"
                    iconSymbol: "◫"
                    Layout.fillWidth: true
                }

                // Detected Panels Breakdown
                ColumnLayout {
                    visible: DesktopCtrl.livePanels.length > 0
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Repeater {
                        model: DesktopCtrl.livePanels

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: panelCardCol.implicitHeight + 16
                            radius: Theme.radiusSm
                            color: Qt.rgba(1, 1, 1, 0.02)
                            border.color: Theme.borderSubtle
                            border.width: 1

                            ColumnLayout {
                                id: panelCardCol
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 6

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spaceSm

                                    Text {
                                        text: (modelData.is_dock ? "Dock" : "Panel") + " (" + modelData.position.toUpperCase() + ")"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeSm
                                        font.weight: Font.DemiBold
                                        color: Theme.textPrimary
                                    }

                                    PFBadge {
                                        visible: Boolean(modelData.containment_id)
                                        text: "Containment #" + modelData.containment_id
                                        variant: "neutral"
                                        size: "xs"
                                    }

                                    PFBadge {
                                        text: modelData.thickness + "px"
                                        variant: "neutral"
                                        size: "xs"
                                    }

                                    PFBadge {
                                        text: modelData.visibility
                                        variant: "neutral"
                                        size: "xs"
                                    }

                                    PFBadge {
                                        text: modelData.source === "live_system" ? "Live D-Bus" : "Disk Config"
                                        variant: modelData.source === "live_system" ? "success" : "warning"
                                        size: "xs"
                                    }

                                    Item { Layout.fillWidth: true }

                                    Text {
                                        text: modelData.applets.length + " Applets"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeXs
                                        color: Theme.textMuted
                                    }
                                }

                                // Applets flow
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Repeater {
                                        model: modelData.applets

                                        delegate: Rectangle {
                                            height: 20
                                            implicitWidth: appletRow.implicitWidth + 12
                                            radius: 3
                                            color: Qt.rgba(1, 1, 1, 0.05)
                                            border.color: Qt.rgba(1, 1, 1, 0.1)
                                            border.width: 1

                                            RowLayout {
                                                id: appletRow
                                                anchors.centerIn: parent
                                                spacing: 4
                                                Text {
                                                    text: modelData.title || modelData.plugin.replace("org.kde.plasma.", "").replace("org.kde.", "")
                                                    font.family: Theme.fontMono
                                                    font.pixelSize: 9
                                                    color: Theme.textSecondary
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Desktop Widgets & Wallpaper info row
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd
                    Layout.topMargin: Theme.spaceSm

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text { text: "Desktop Wallpaper"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                        Text {
                            text: DesktopCtrl.liveWallpaper ? DesktopCtrl.liveWallpaper.split("/").pop() : "Default KDE Wallpaper"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textSecondary
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Text { text: "Desktop Widgets"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                        Text {
                            text: DesktopCtrl.liveDesktopWidgets.length > 0
                                ? DesktopCtrl.liveDesktopWidgets.length + " widgets detected"
                                : "No widgets on desktop layer"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textSecondary
                        }
                    }
                }

                // Explicit Unsupported Capabilities Notice
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: unsuppCol.implicitHeight + 16
                    radius: Theme.radiusSm
                    color: Qt.rgba(0.96, 0.62, 0.04, 0.08)
                    border.color: Qt.rgba(0.96, 0.62, 0.04, 0.25)
                    border.width: 1

                    ColumnLayout {
                        id: unsuppCol
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 4

                        RowLayout {
                            spacing: 6
                            Text { text: "⚠️"; font.pixelSize: 12 }
                            Text {
                                text: "Platform Capabilities & Safe Boundaries:"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                font.weight: Font.DemiBold
                                color: Theme.warning
                            }
                        }

                        Text {
                            text: "• Supported Live: Panel edge position, thickness, and visibility mode.\n• Unsupported / Preview Only: Freeform desktop widget coordinate dragging, dynamic applet injection, and live desktop framebuffer capture are not exposed through safe KDE scripting interfaces and remain preview-only."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textSecondary
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }

        // Layout Presets Section
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "LAYOUT PRESETS"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSizeXs
                    font.weight: Font.DemiBold
                    color: Theme.textMuted
                    Layout.fillWidth: true
                }
                PFButton {
                    text: "Save Draft as Preset"
                    iconText: "💾"
                    variant: "secondary"
                    size: "sm"
                    onClicked: desktopBuilderRoot.showSavePresetDialog = true
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: desktopBuilderRoot.width > 740 ? 3 : (desktopBuilderRoot.width > 560 ? 2 : 1)
                columnSpacing: Theme.spaceMd
                rowSpacing: Theme.spaceMd

                Repeater {
                    model: DesktopCtrl.presets

                    delegate: PFCard {
                        readonly property var missingWidgets: DesktopCtrl.checkPresetMissingWidgets(modelData.id)
                        Layout.fillWidth: true
                        implicitHeight: 116
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
                                    elide: Text.ElideRight
                                }
                                PFBadge {
                                    text: modelData.is_builtin ? (modelData.id === "nothing_inspired" ? "Dual Panel" : (modelData.id === "classic_kde" ? "Conventional" : (modelData.id === "dual_status_dock" ? "Status & Dock" : "Minimal"))) : "Custom"
                                    variant: DesktopCtrl.selectedPresetId === modelData.id ? "accent" : (modelData.is_builtin ? "neutral" : "success")
                                    size: "xs"
                                }
                                Rectangle {
                                    visible: !modelData.is_builtin
                                    width: 18
                                    height: 18
                                    radius: 9
                                    color: Qt.rgba(0.94, 0.27, 0.27, 0.15)
                                    Text {
                                        anchors.centerIn: parent
                                        text: "✕"
                                        font.pixelSize: 9
                                        color: "#f87171"
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            DesktopCtrl.deleteCustomPreset(modelData.id)
                                            AppCtrl.showToast("Deleted custom preset: " + modelData.name, "info")
                                        }
                                    }
                                }
                            }

                            RowLayout {
                                visible: missingWidgets.length > 0
                                spacing: 4
                                PFBadge {
                                    text: "Missing " + missingWidgets.length + " plasmoid(s)"
                                    variant: "warning"
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

        // Safe Panel Editing Workbench Card (Multi-Panel Selection & Editing)
        PFCard {
            Layout.fillWidth: true
            implicitHeight: selectedPanelCol.implicitHeight + (Theme.spaceLg * 2)

            ColumnLayout {
                id: selectedPanelCol
                anchors.fill: parent
                anchors.margins: Theme.spaceLg
                spacing: Theme.spaceMd

                // Header: Title, Live applicability, and reset button
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Rectangle {
                        width: 28
                        height: 28
                        radius: Theme.radiusSm
                        color: Qt.rgba(0.08, 0.72, 0.65, 0.15)
                        border.color: Theme.accent
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "◫"
                            font.pixelSize: 14
                            color: Theme.accentLight
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            spacing: Theme.spaceSm
                            Text {
                                text: "SELECTED PANEL WORKBENCH"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                font.weight: Font.DemiBold
                                color: Theme.accentLight
                            }
                            PFBadge {
                                visible: Boolean(DesktopCtrl.selectedPanelId)
                                text: "Containment #" + DesktopCtrl.selectedPanelId
                                variant: "neutral"
                                size: "xs"
                            }
                            PFBadge {
                                text: DesktopCtrl.selectedPanelIsLiveSupported ? "Live D-Bus Supported" : "Deferred to Session Reload"
                                variant: DesktopCtrl.selectedPanelIsLiveSupported ? "accent" : "warning"
                                size: "xs"
                            }
                            PFBadge {
                                visible: DesktopCtrl.selectedPanelHasChanges
                                text: "Changes Staged"
                                variant: "accent"
                                size: "xs"
                            }
                        }
                        Text {
                            text: "Configure screen position, thickness, and visibility mode for the selected Plasma containment"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }
                    }

                    PFButton {
                        text: "Discard Draft"
                        iconText: "↺"
                        variant: "secondary"
                        size: "sm"
                        enabled: DesktopCtrl.isDraftModified
                        onClicked: {
                            DesktopCtrl.resetDraft()
                            AppCtrl.showToast("Draft changes discarded.", "info")
                        }
                    }
                }

                // Panel Selection Strip (Repeater of detected panels)
                ColumnLayout {
                    visible: DesktopCtrl.livePanels.length > 0
                    Layout.fillWidth: true
                    spacing: 6

                    Text {
                        text: "Select Target Panel / Containment:"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeXs
                        color: Theme.textMuted
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        Repeater {
                            model: DesktopCtrl.livePanels

                            delegate: Rectangle {
                                readonly property bool isSelected: DesktopCtrl.selectedPanelId === (modelData.containment_id || modelData.id)
                                height: 38
                                implicitWidth: panelChipRow.implicitWidth + 24
                                radius: Theme.radiusSm
                                color: isSelected ? Qt.rgba(0.08, 0.72, 0.65, 0.15) : Qt.rgba(1, 1, 1, 0.03)
                                border.color: isSelected ? Theme.accent : Theme.borderSubtle
                                border.width: isSelected ? 2 : 1

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: DesktopCtrl.selectPanel(modelData.containment_id || modelData.id)
                                }

                                RowLayout {
                                    id: panelChipRow
                                    anchors.centerIn: parent
                                    spacing: Theme.spaceSm

                                    Text {
                                        text: (modelData.is_dock ? "⚓ Dock" : "◫ Panel") + (modelData.containment_id ? (" #" + modelData.containment_id) : "")
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeXs
                                        font.weight: isSelected ? Font.Bold : Font.Normal
                                        color: isSelected ? Theme.accentLight : Theme.textPrimary
                                    }

                                    PFBadge {
                                        text: modelData.position.toUpperCase()
                                        variant: isSelected ? "accent" : "neutral"
                                        size: "xs"
                                    }

                                    PFBadge {
                                        text: modelData.thickness + "px"
                                        variant: "neutral"
                                        size: "xs"
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderSubtle
                }

                // Controls Grid: Position, Thickness, Visibility
                GridLayout {
                    Layout.fillWidth: true
                    columns: desktopBuilderRoot.width > 700 ? 3 : 1
                    columnSpacing: Theme.spaceLg
                    rowSpacing: Theme.spaceMd

                    // 1. Edge Position
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceXs

                        RowLayout {
                            Text { text: "Screen-Edge Position"; font.pixelSize: Theme.fontSizeXs; font.weight: Font.DemiBold; color: Theme.textSecondary }
                            Item { Layout.fillWidth: true }
                            Text { text: DesktopCtrl.selectedPanelPosition.toUpperCase(); font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeXs; font.weight: Font.Bold; color: Theme.accentLight }
                        }

                        GridLayout {
                            columns: 2
                            Layout.fillWidth: true
                            columnSpacing: 6
                            rowSpacing: 6

                            PFButton {
                                Layout.fillWidth: true
                                text: "Top"
                                size: "sm"
                                variant: DesktopCtrl.selectedPanelPosition === "top" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setSelectedPanelPosition("top")
                            }
                            PFButton {
                                Layout.fillWidth: true
                                text: "Bottom"
                                size: "sm"
                                variant: DesktopCtrl.selectedPanelPosition === "bottom" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setSelectedPanelPosition("bottom")
                            }
                            PFButton {
                                Layout.fillWidth: true
                                text: "Left"
                                size: "sm"
                                variant: DesktopCtrl.selectedPanelPosition === "left" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setSelectedPanelPosition("left")
                            }
                            PFButton {
                                Layout.fillWidth: true
                                text: "Right"
                                size: "sm"
                                variant: DesktopCtrl.selectedPanelPosition === "right" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setSelectedPanelPosition("right")
                            }
                        }
                    }

                    // 2. Thickness
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceXs

                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Panel Thickness"; font.pixelSize: Theme.fontSizeXs; font.weight: Font.DemiBold; color: Theme.textSecondary }
                            Item { Layout.fillWidth: true }
                            Text { text: DesktopCtrl.selectedPanelThickness + " px"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeXs; font.weight: Font.Bold; color: Theme.accentLight }
                        }

                        Slider {
                            Layout.fillWidth: true
                            from: 16
                            to: 128
                            stepSize: 2
                            value: DesktopCtrl.selectedPanelThickness
                            onMoved: DesktopCtrl.setSelectedPanelThickness(Math.round(value))
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "16 px (Min)"; font.pixelSize: 9; color: Theme.textMuted }
                            Item { Layout.fillWidth: true }
                            Text { text: "128 px (Max)"; font.pixelSize: 9; color: Theme.textMuted }
                        }
                    }

                    // 3. Visibility Mode
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceXs

                        RowLayout {
                            Text { text: "Visibility Mode"; font.pixelSize: Theme.fontSizeXs; font.weight: Font.DemiBold; color: Theme.textSecondary }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: DesktopCtrl.selectedPanelVisibility.replace("_", " ")
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeXs
                                font.weight: Font.Bold
                                color: Theme.accentLight
                            }
                        }

                        GridLayout {
                            columns: 2
                            Layout.fillWidth: true
                            columnSpacing: 6
                            rowSpacing: 6

                            PFButton {
                                Layout.fillWidth: true
                                text: "Always Visible"
                                size: "sm"
                                variant: DesktopCtrl.selectedPanelVisibility === "always_visible" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setSelectedPanelVisibility("always_visible")
                            }
                            PFButton {
                                Layout.fillWidth: true
                                text: "Auto-Hide"
                                size: "sm"
                                variant: DesktopCtrl.selectedPanelVisibility === "auto_hide" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setSelectedPanelVisibility("auto_hide")
                            }
                            PFButton {
                                Layout.fillWidth: true
                                text: "Dodge Windows"
                                size: "sm"
                                variant: DesktopCtrl.selectedPanelVisibility === "dodge_windows" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setSelectedPanelVisibility("dodge_windows")
                            }
                            PFButton {
                                Layout.fillWidth: true
                                text: "Windows Below"
                                size: "sm"
                                variant: DesktopCtrl.selectedPanelVisibility === "windows_go_below" ? "primary" : "secondary"
                                onClicked: DesktopCtrl.setSelectedPanelVisibility("windows_go_below")
                            }
                        }
                    }
                }

                // Panel Applets Strip
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Panel Applets (" + DesktopCtrl.selectedPanelApplets.length + "):"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            font.weight: Font.DemiBold
                            color: Theme.textSecondary
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: "Add widgets from catalog below"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        Repeater {
                            model: DesktopCtrl.selectedPanelApplets

                            delegate: Rectangle {
                                height: 32
                                implicitWidth: appletChipRow.implicitWidth + 20
                                radius: Theme.radiusSm
                                color: Qt.rgba(1, 1, 1, 0.04)
                                border.color: Theme.borderSubtle
                                border.width: 1

                                RowLayout {
                                    id: appletChipRow
                                    anchors.centerIn: parent
                                    spacing: 6

                                    Text {
                                        text: "#" + (index + 1)
                                        font.family: Theme.fontMono
                                        font.pixelSize: 10
                                        font.weight: Font.Bold
                                        color: Theme.accentLight
                                    }

                                    Text {
                                        text: modelData.replace("org.kde.plasma.", "").replace("org.kde.", "")
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeXs
                                        font.weight: Font.DemiBold
                                        color: Theme.textPrimary
                                    }

                                    // Move Left / Up button
                                    Text {
                                        visible: index > 0
                                        text: "◀"
                                        font.pixelSize: 10
                                        color: Theme.textMuted
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: DesktopCtrl.moveAppletInDraft(DesktopCtrl.selectedPanelId, index, index - 1)
                                        }
                                    }

                                    // Move Right / Down button
                                    Text {
                                        visible: index < DesktopCtrl.selectedPanelApplets.length - 1
                                        text: "▶"
                                        font.pixelSize: 10
                                        color: Theme.textMuted
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: DesktopCtrl.moveAppletInDraft(DesktopCtrl.selectedPanelId, index, index + 1)
                                        }
                                    }

                                    // Remove applet button
                                    Rectangle {
                                        width: 16
                                        height: 16
                                        radius: 8
                                        color: Qt.rgba(0.94, 0.27, 0.27, 0.15)
                                        Text {
                                            anchors.centerIn: parent
                                            text: "✕"
                                            font.pixelSize: 9
                                            color: "#f87171"
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: DesktopCtrl.removeAppletFromDraft(DesktopCtrl.selectedPanelId, index)
                                        }
                                    }
                                }
                            }
                        }

                        Text {
                            visible: DesktopCtrl.selectedPanelApplets.length === 0
                            text: "No applets currently staged on this panel. Use the catalog below to add applets."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }
                    }
                }

                // Live Diff readout for this panel
                Rectangle {
                    visible: DesktopCtrl.selectedPanelHasChanges
                    Layout.fillWidth: true
                    implicitHeight: panelDiffRow.implicitHeight + 16
                    radius: Theme.radiusSm
                    color: Qt.rgba(0.08, 0.72, 0.65, 0.08)
                    border.color: Qt.rgba(0.08, 0.72, 0.65, 0.25)
                    border.width: 1

                    RowLayout {
                        id: panelDiffRow
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: Theme.spaceMd

                        Text { text: "Δ"; font.pixelSize: 14; font.weight: Font.Bold; color: Theme.accentLight }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: "Pending Changes for Selected Panel:"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                font.weight: Font.DemiBold
                                color: Theme.accentLight
                            }
                            Text {
                                text: "Current: " + (DesktopCtrl.selectedPanelInfo.position || "top") + " • " + (DesktopCtrl.selectedPanelInfo.thickness || 32) + "px • " + (DesktopCtrl.selectedPanelInfo.visibility || "always_visible") +
                                      "  ➔  Draft: " + DesktopCtrl.selectedPanelPosition + " • " + DesktopCtrl.selectedPanelThickness + "px • " + DesktopCtrl.selectedPanelVisibility
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.textPrimary
                            }
                        }

                        PFButton {
                            text: "Review & Apply"
                            iconText: "✓"
                            size: "sm"
                            variant: "primary"
                            onClicked: DesktopCtrl.requestApplyDraft()
                        }
                    }
                }
            }
        }

        // Installed Widget Catalog & Layout Builder Card
        PFCard {
            Layout.fillWidth: true
            implicitHeight: widgetCatalogCol.implicitHeight + (Theme.spaceLg * 2)

            ColumnLayout {
                id: widgetCatalogCol
                anchors.fill: parent
                anchors.margins: Theme.spaceLg
                spacing: Theme.spaceMd

                // Header
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Rectangle {
                        width: 28
                        height: 28
                        radius: Theme.radiusSm
                        color: Qt.rgba(0.08, 0.72, 0.65, 0.15)
                        border.color: Theme.accent
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "🧩"
                            font.pixelSize: 14
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            spacing: Theme.spaceSm
                            Text {
                                text: "INSTALLED WIDGET CATALOG"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                font.weight: Font.DemiBold
                                color: Theme.accentLight
                            }
                            PFBadge {
                                text: DesktopCtrl.installedWidgets.length + " Discovered"
                                variant: "accent"
                                size: "xs"
                            }
                            PFBadge {
                                text: DesktopCtrl.isCatalogLoading ? "Scanning..." : "Read-Only Discovery"
                                variant: DesktopCtrl.isCatalogLoading ? "warning" : "neutral"
                                size: "xs"
                            }
                        }
                        Text {
                            text: "Discover verified Plasma 6 plasmoids & applets installed on this system and stage them into panels or desktop"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }
                    }

                    PFButton {
                        text: DesktopCtrl.isCatalogLoading ? "Scanning..." : "Refresh Catalog"
                        iconText: "⟳"
                        variant: "secondary"
                        size: "sm"
                        enabled: !DesktopCtrl.isCatalogLoading
                        onClicked: DesktopCtrl.loadWidgetCatalog()
                    }
                }

                // Filter & Search Toolbar
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    // Search box
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        radius: Theme.radiusSm
                        color: Theme.surface
                        border.color: searchWidgetField.activeFocus ? Theme.accent : Theme.borderSubtle
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            spacing: 6

                            Text {
                                text: "🔍"
                                font.pixelSize: 11
                                color: Theme.textMuted
                            }

                            TextInput {
                                id: searchWidgetField
                                Layout.fillWidth: true
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.textPrimary
                                selectByMouse: true
                                text: desktopBuilderRoot.widgetSearchQuery
                                onTextChanged: desktopBuilderRoot.widgetSearchQuery = text

                                Text {
                                    visible: !searchWidgetField.text && !searchWidgetField.activeFocus
                                    text: "Search installed widgets by name, ID, or description..."
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeSm
                                    color: Theme.textMuted
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            Text {
                                visible: searchWidgetField.text.length > 0
                                text: "✕"
                                font.pixelSize: 11
                                color: Theme.textMuted
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        searchWidgetField.text = ""
                                        desktopBuilderRoot.widgetSearchQuery = ""
                                    }
                                }
                            }
                        }
                    }

                    // Target Filter Toggle (All, Panel, Desktop)
                    RowLayout {
                        spacing: 4
                        PFButton {
                            text: "All"
                            size: "sm"
                            variant: desktopBuilderRoot.selectedTargetFilter === "all" ? "primary" : "secondary"
                            onClicked: desktopBuilderRoot.selectedTargetFilter = "all"
                        }
                        PFButton {
                            text: "Panel"
                            size: "sm"
                            variant: desktopBuilderRoot.selectedTargetFilter === "panel" ? "primary" : "secondary"
                            onClicked: desktopBuilderRoot.selectedTargetFilter = "panel"
                        }
                        PFButton {
                            text: "Desktop"
                            size: "sm"
                            variant: desktopBuilderRoot.selectedTargetFilter === "desktop" ? "primary" : "secondary"
                            onClicked: desktopBuilderRoot.selectedTargetFilter = "desktop"
                        }
                    }
                }

                // Category Chips Strip
                Flow {
                    Layout.fillWidth: true
                    spacing: 6

                    Repeater {
                        model: DesktopCtrl.widgetCategories

                        delegate: Rectangle {
                            readonly property bool isSelected: desktopBuilderRoot.selectedCategory === modelData
                            height: 26
                            implicitWidth: catRow.implicitWidth + 16
                            radius: Theme.radiusSm
                            color: isSelected ? Qt.rgba(0.08, 0.72, 0.65, 0.2) : Qt.rgba(1, 1, 1, 0.03)
                            border.color: isSelected ? Theme.accent : Theme.borderSubtle
                            border.width: 1

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: desktopBuilderRoot.selectedCategory = modelData
                            }

                            RowLayout {
                                id: catRow
                                anchors.centerIn: parent
                                spacing: 4
                                Text {
                                    text: modelData
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 11
                                    font.weight: isSelected ? Font.DemiBold : Font.Normal
                                    color: isSelected ? Theme.accentLight : Theme.textSecondary
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderSubtle
                }

                // Widget List (Grid or Column)
                GridLayout {
                    id: widgetCatalogGrid
                    Layout.fillWidth: true
                    columns: desktopBuilderRoot.width > 860 ? 2 : 1
                    columnSpacing: Theme.spaceMd
                    rowSpacing: Theme.spaceMd

                    readonly property var currentList: desktopBuilderRoot.getFilteredWidgets()

                    Repeater {
                        model: widgetCatalogGrid.currentList

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: widgetItemCol.implicitHeight + 20
                            radius: Theme.radiusSm
                            color: Theme.surface
                            border.color: Theme.borderSubtle
                            border.width: 1

                            ColumnLayout {
                                id: widgetItemCol
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spaceSm

                                    Rectangle {
                                        width: 26
                                        height: 26
                                        radius: Theme.radiusSm
                                        color: modelData.source === "user_installed" ? Qt.rgba(0.96, 0.62, 0.04, 0.15) : Qt.rgba(0.08, 0.72, 0.65, 0.12)
                                        border.color: modelData.source === "user_installed" ? Theme.warning : Theme.borderSubtle
                                        border.width: 1
                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.name ? modelData.name.charAt(0).toUpperCase() : "W"
                                            font.pixelSize: 12
                                            font.weight: Font.Bold
                                            color: modelData.source === "user_installed" ? Theme.warning : Theme.accentLight
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1

                                        Text {
                                            text: modelData.name
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontSizeSm
                                            font.weight: Font.DemiBold
                                            color: Theme.textPrimary
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }

                                        Text {
                                            text: modelData.plugin_id
                                            font.family: Theme.fontMono
                                            font.pixelSize: 10
                                            color: Theme.textMuted
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }
                                    }

                                    PFBadge {
                                        text: modelData.source === "user_installed" ? "User Plasmoid" : "System"
                                        variant: modelData.source === "user_installed" ? "warning" : "neutral"
                                        size: "xs"
                                    }
                                }

                                Text {
                                    text: modelData.description || "No description provided."
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeXs
                                    color: Theme.textSecondary
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spaceSm

                                    PFBadge {
                                        text: modelData.category || "Utilities"
                                        variant: "neutral"
                                        size: "xs"
                                    }

                                    Item { Layout.fillWidth: true }

                                    PFButton {
                                        text: "+ Add to Panel"
                                        size: "xs"
                                        variant: "secondary"
                                        visible: Boolean(modelData.suitable_for && modelData.suitable_for.indexOf("panel") !== -1)
                                        onClicked: {
                                            DesktopCtrl.addAppletToDraft(DesktopCtrl.selectedPanelId, modelData.plugin_id)
                                            AppCtrl.showToast("Added " + modelData.name + " to selected panel", "success")
                                        }
                                    }

                                    PFButton {
                                        text: "+ Add to Desktop"
                                        size: "xs"
                                        variant: "outline"
                                        visible: Boolean(modelData.suitable_for && modelData.suitable_for.indexOf("desktop") !== -1)
                                        onClicked: {
                                            DesktopCtrl.addDesktopWidgetToDraft(modelData.plugin_id)
                                            AppCtrl.showToast("Added " + modelData.name + " to desktop", "success")
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Empty state if filtered results are empty
                Rectangle {
                    visible: widgetCatalogGrid.currentList.length === 0
                    Layout.fillWidth: true
                    height: 100
                    radius: Theme.radiusSm
                    color: Qt.rgba(1, 1, 1, 0.02)
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 6
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: DesktopCtrl.isCatalogLoading ? "Discovering installed widgets..." : "No widgets matched your search."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textSecondary
                        }
                        PFButton {
                            visible: !DesktopCtrl.isCatalogLoading && (desktopBuilderRoot.widgetSearchQuery.length > 0 || desktopBuilderRoot.selectedCategory !== "All")
                            Layout.alignment: Qt.AlignHCenter
                            text: "Reset Search Filters"
                            size: "xs"
                            variant: "secondary"
                            onClicked: {
                                searchWidgetField.text = ""
                                desktopBuilderRoot.widgetSearchQuery = ""
                                desktopBuilderRoot.selectedCategory = "All"
                                desktopBuilderRoot.selectedTargetFilter = "all"
                            }
                        }
                    }
                }
            }
        }

        // Workbench Controls: 2-Column Responsive Layout
        GridLayout {
            Layout.fillWidth: true
            columns: desktopBuilderRoot.width > 740 ? 2 : 1
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
                            PFBadge { text: "Preview Only"; variant: "neutral"; size: "xs" }
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
            implicitHeight: desktopWidgetsCardCol.implicitHeight + (Theme.spaceLg * 2)

            ColumnLayout {
                id: desktopWidgetsCardCol
                anchors.fill: parent
                anchors.margins: Theme.spaceLg
                spacing: Theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
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
                                text: "Desktop Widgets Layer (" + DesktopCtrl.desktopWidgets.length + " Staged)"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                            }
                            PFBadge {
                                text: "Freeform Coordinates Simulated"
                                variant: "neutral"
                                size: "xs"
                            }
                        }
                        Text {
                            text: "Renders Nothing-inspired clock, system telemetry, and custom plasmoids on the desktop canvas"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textSecondary
                        }
                    }

                    PFButton {
                        text: DesktopCtrl.showWidgets ? "Hide Widget Layer" : "Show Widget Layer"
                        variant: DesktopCtrl.showWidgets ? "primary" : "secondary"
                        size: "sm"
                        onClicked: DesktopCtrl.setShowWidgets(!DesktopCtrl.showWidgets)
                    }
                }

                // Staged desktop widgets chips
                Flow {
                    visible: DesktopCtrl.desktopWidgets.length > 0
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Repeater {
                        model: DesktopCtrl.desktopWidgets

                        delegate: Rectangle {
                            height: 30
                            implicitWidth: dChipRow.implicitWidth + 18
                            radius: Theme.radiusSm
                            color: Qt.rgba(1, 1, 1, 0.04)
                            border.color: Theme.borderSubtle
                            border.width: 1

                            RowLayout {
                                id: dChipRow
                                anchors.centerIn: parent
                                spacing: 6

                                Text {
                                    text: "🧩"
                                    font.pixelSize: 10
                                }

                                Text {
                                    text: modelData.replace("org.kde.plasma.", "").replace("com.github.", "")
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeXs
                                    font.weight: Font.DemiBold
                                    color: Theme.textPrimary
                                }

                                Rectangle {
                                    width: 16
                                    height: 16
                                    radius: 8
                                    color: Qt.rgba(0.94, 0.27, 0.27, 0.15)
                                    Text {
                                        anchors.centerIn: parent
                                        text: "✕"
                                        font.pixelSize: 9
                                        color: "#f87171"
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: DesktopCtrl.removeDesktopWidgetFromDraft(index)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Item { height: Theme.spaceXl; Layout.fillWidth: true }
            }
        }
    }

    // Slide-out Drawer for Diff Preview
    Drawer {
        id: diffDrawer
        width: Math.min(desktopBuilderRoot.width * 0.85, 780)
        height: desktopBuilderRoot.height
        edge: Qt.RightEdge
        dim: true

        background: Rectangle {
            color: Theme.bg
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

                        RowLayout {
                            spacing: Theme.spaceSm
                            Text {
                                text: AppCtrl.safeMode ? "Safe Mode Simulation:" : "Live Desktop Configuration Modification:"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                font.weight: Font.DemiBold
                                color: AppCtrl.safeMode ? Theme.accentLight : Theme.warning
                            }
                            PFBadge {
                                text: DesktopCtrl.isLiveEditingSupported ? "Live D-Bus Enabled" : "Session Reload Only"
                                variant: DesktopCtrl.isLiveEditingSupported ? "accent" : "neutral"
                                size: "xs"
                            }
                        }

                        Text {
                            text: AppCtrl.safeMode
                                ? "Safe Mode is active. A simulated dry-run will create a test snapshot and generate unified diffs without modifying your live configuration."
                                : "A verified cryptographic SHA256 snapshot will be captured before modifying files. Panel position, thickness, and visibility will be applied to disk and live via Plasma 6 D-Bus (qdbus6 evaluateScript). Verification confirms both on-disk and live D-Bus properties. On any verification failure, changes are rolled back automatically. Plasmashell will NOT be terminated."
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
                        Text { anchors.centerIn: parent; text: "3. Live & Disk Apply"; font.pixelSize: 10; font.weight: Font.DemiBold; color: Theme.textMuted }
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

                // Actions & Loading Status
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    Text {
                        visible: DesktopCtrl.isApplying
                        text: "Applying transactionally..."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeSm
                        color: Theme.accentLight
                    }

                    Item { Layout.fillWidth: true }

                    PFButton {
                        text: "Cancel"
                        variant: "secondary"
                        size: "md"
                        enabled: !DesktopCtrl.isApplying
                        onClicked: DesktopCtrl.cancelApply()
                    }

                    PFButton {
                        text: DesktopCtrl.isApplying ? "Applying..." : (AppCtrl.safeMode ? "Confirm Simulation" : "Apply Layout to KDE")
                        iconText: DesktopCtrl.isApplying ? "⏳" : (AppCtrl.safeMode ? "🛡" : "✓")
                        variant: "primary"
                        size: "md"
                        enabled: !DesktopCtrl.isApplying
                        onClicked: DesktopCtrl.confirmApplyDraft()
                    }
                }
                }
            }
        }
    }

    // Save Preset Modal Overlay
    Rectangle {
        id: savePresetOverlay
        visible: desktopBuilderRoot.showSavePresetDialog
        anchors.fill: parent
        color: Qt.rgba(0.04, 0.05, 0.07, 0.78)
        z: 9999

        MouseArea {
            anchors.fill: parent
            onClicked: desktopBuilderRoot.showSavePresetDialog = false
        }

        Rectangle {
            id: savePresetModalCard
            width: Math.min(desktopBuilderRoot.width - 48, 520)
            implicitHeight: savePresetCol.implicitHeight + (Theme.spaceXl * 2)
            anchors.centerIn: parent
            radius: Theme.radiusLg
            color: Theme.card
            border.color: Theme.accent
            border.width: 1

            MouseArea {
                anchors.fill: parent
                // prevent click-through
            }

            ColumnLayout {
                id: savePresetCol
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                spacing: Theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Rectangle {
                        width: 32
                        height: 32
                        radius: Theme.radiusSm
                        color: Qt.rgba(0.08, 0.72, 0.65, 0.15)
                        border.color: Theme.accent
                        border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "💾"
                            font.pixelSize: 16
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: "Save Draft as Layout Preset"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeLg
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                        }
                        Text {
                            text: "Save configured panels, applets, and desktop widgets into a reusable preset"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderSubtle
                }

                // Preset Name input
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "Preset Name"; font.pixelSize: Theme.fontSizeXs; font.weight: Font.DemiBold; color: Theme.textSecondary }
                    Rectangle {
                        Layout.fillWidth: true
                        height: 36
                        radius: Theme.radiusSm
                        color: Theme.surface
                        border.color: presetNameInput.activeFocus ? Theme.accent : Theme.borderSubtle
                        border.width: 1

                        TextInput {
                            id: presetNameInput
                            anchors.fill: parent
                            anchors.margins: 8
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textPrimary
                            selectByMouse: true
                            text: "My Custom Preset"
                        }
                    }
                }

                // Preset Description input
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "Description"; font.pixelSize: Theme.fontSizeXs; font.weight: Font.DemiBold; color: Theme.textSecondary }
                    Rectangle {
                        Layout.fillWidth: true
                        height: 54
                        radius: Theme.radiusSm
                        color: Theme.surface
                        border.color: presetDescInput.activeFocus ? Theme.accent : Theme.borderSubtle
                        border.width: 1

                        TextInput {
                            id: presetDescInput
                            anchors.fill: parent
                            anchors.margins: 8
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textPrimary
                            selectByMouse: true
                            text: "Personal layout with customized panels and widget arrangement."
                        }
                    }
                }

                // Summary
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: summaryCol.implicitHeight + 16
                    radius: Theme.radiusSm
                    color: Qt.rgba(1, 1, 1, 0.03)
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        id: summaryCol
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 4

                        Text {
                            text: "Included in Preset:"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            font.weight: Font.DemiBold
                            color: Theme.accentLight
                        }
                        Text {
                            text: "• Top Panel: " + DesktopCtrl.panelPosition + " (" + DesktopCtrl.panelThickness + "px, " + DesktopCtrl.selectedPanelApplets.length + " applets)\n• Dock: " + DesktopCtrl.dockPosition + " (" + DesktopCtrl.dockThickness + "px)\n• Desktop Widgets: " + DesktopCtrl.desktopWidgets.length + " widget(s)"
                            font.family: Theme.fontMono
                            font.pixelSize: 11
                            color: Theme.textSecondary
                        }
                    }
                }

                Item { height: Theme.spaceSm }

                // Actions
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    Item { Layout.fillWidth: true }

                    PFButton {
                        text: "Cancel"
                        variant: "secondary"
                        size: "md"
                        onClicked: desktopBuilderRoot.showSavePresetDialog = false
                    }

                    PFButton {
                        text: "Save Preset"
                        iconText: "💾"
                        variant: "primary"
                        size: "md"
                        enabled: presetNameInput.text.trim().length > 0
                        onClicked: {
                            var ok = DesktopCtrl.saveDraftAsPreset("", presetNameInput.text.trim(), presetDescInput.text.trim())
                            if (ok) {
                                AppCtrl.showToast("Saved custom preset: " + presetNameInput.text.trim(), "success")
                                desktopBuilderRoot.showSavePresetDialog = false
                            } else {
                                AppCtrl.showToast("Failed to save preset.", "error")
                            }
                        }
                    }
                }
            }
        }
    }
}
