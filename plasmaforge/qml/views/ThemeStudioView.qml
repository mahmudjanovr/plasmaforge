import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import PlasmaForge.Controllers 1.0
import plasmaforge.qml.theme 1.0
import plasmaforge.qml.components 1.0

Item {
    id: themeStudioRoot

    Connections {
        target: ThemeCtrl
        function onApplyFinished(success, message, isDryRun) {
            var level = success ? (isDryRun ? "info" : "success") : "error"
            AppCtrl.showToast(message, level)
        }
        function onRestoreFinished(success, message) {
            AppCtrl.showToast(message, success ? "success" : "error")
        }
    }

    ScrollView {
        id: scrollView
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        Item {
            width: scrollView.availableWidth
            implicitHeight: themeMainCol.implicitHeight + (Theme.spaceXl * 2)

            ColumnLayout {
                id: themeMainCol
                width: Math.min(parent.width - (Theme.spaceXxl * 2), 1140)
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: Theme.spaceLg
                spacing: Theme.spaceXl

            Item { height: Theme.spaceXs; Layout.fillWidth: true }

            PFSectionHeader {
                title: "Theme Studio"
                subtitle: "Browse installed KDE color schemes, inspect palettes, preview diffs, and apply safely"

                RowLayout {
                    spacing: Theme.spaceSm

                    PFBadge {
                        text: AppCtrl.safeMode ? "🛡️ Safe Mode: Active" : "⚡ Live Desktop Mode"
                        variant: AppCtrl.safeMode ? "neutral" : "warning"
                        size: "sm"
                    }

                    PFButton {
                        visible: ThemeCtrl.canRestorePrevious
                        text: "Restore " + ThemeCtrl.previousSchemeId
                        iconText: "↺"
                        variant: "outline"
                        size: "sm"
                        onClicked: ThemeCtrl.restorePreviousScheme()
                    }

                    PFButton {
                        text: "Refresh Palettes"
                        iconText: "↻"
                        size: "sm"
                        onClicked: {
                            ThemeCtrl.refresh()
                            AppCtrl.showToast("Refreshed color schemes and desktop styles.", "info")
                        }
                    }
                }
            }

            // Responsive Two-column layout: Schemes list on left, Palette detail on right
            GridLayout {
                Layout.fillWidth: true
                columns: themeStudioRoot.width > 760 ? 2 : 1
                columnSpacing: Theme.spaceLg
                rowSpacing: Theme.spaceLg

                // Left: Color Schemes list
                PFCard {
                    Layout.preferredWidth: themeStudioRoot.width > 760 ? 360 : -1
                    Layout.maximumWidth: themeStudioRoot.width > 760 ? 400 : -1
                    Layout.fillWidth: themeStudioRoot.width <= 760
                    implicitHeight: themeStudioRoot.width > 760 ? 520 : 380

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spaceLg
                        spacing: Theme.spaceMd

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "INSTALLED COLOR SCHEMES"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                font.weight: Font.DemiBold
                                color: Theme.textMuted
                                Layout.fillWidth: true
                            }
                            PFBadge {
                                text: ThemeCtrl.colorSchemes.length + " Available"
                                variant: "neutral"
                                size: "xs"
                            }
                        }

                        ListView {
                            id: schemesList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: Theme.spaceSm
                            model: ThemeCtrl.colorSchemes

                            ScrollBar.vertical: ScrollBar {
                                active: true
                                policy: ScrollBar.AsNeeded
                            }

                            delegate: Rectangle {
                                width: schemesList.width
                                height: 56
                                radius: Theme.radiusMd
                                color: ThemeCtrl.selectedSchemeIndex === index ? Qt.rgba(0.08, 0.72, 0.65, 0.12) : (schemeMouse.containsMouse ? Theme.cardHover : Theme.surface)
                                border.color: ThemeCtrl.selectedSchemeIndex === index ? Theme.accent : Theme.borderSubtle
                                border.width: 1

                                Behavior on color { ColorAnimation { duration: Theme.animDurationFast } }

                                MouseArea {
                                    id: schemeMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: ThemeCtrl.selectScheme(index)
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: Theme.spaceMd
                                    spacing: Theme.spaceSm

                                    // Palette swatch preview
                                    Row {
                                        spacing: 2
                                        Rectangle { width: 12; height: 26; radius: 2; color: modelData.window_bg; border.color: Theme.border; border.width: 1 }
                                        Rectangle { width: 12; height: 26; radius: 2; color: modelData.selection_bg }
                                        Rectangle { width: 12; height: 26; radius: 2; color: modelData.button_bg; border.color: Theme.border; border.width: 1 }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 4

                                            Text {
                                                text: modelData.name
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontSizeBase
                                                font.weight: ThemeCtrl.selectedSchemeIndex === index ? Font.DemiBold : Font.Normal
                                                color: ThemeCtrl.selectedSchemeIndex === index ? Theme.textPrimary : Theme.textSecondary
                                                elide: Text.ElideRight
                                                Layout.fillWidth: true
                                            }

                                            PFBadge {
                                                visible: modelData.is_active === true
                                                text: "Active"
                                                variant: "success"
                                                size: "xs"
                                            }
                                        }

                                        Text {
                                            text: modelData.is_user_scheme ? "User Scheme (~/.local)" : "System Scheme (/usr)"
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontSizeXs
                                            color: Theme.textMuted
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Right: Selected Scheme Palette Inspector & Action Center
                PFCard {
                    Layout.fillWidth: true
                    Layout.minimumWidth: themeStudioRoot.width > 760 ? 340 : -1
                    implicitHeight: themeStudioRoot.width > 760 ? Math.max(520, rightCardCol.implicitHeight + (Theme.spaceXl * 2)) : (rightCardCol.implicitHeight + (Theme.spaceXl * 2))

                    ColumnLayout {
                        id: rightCardCol
                        anchors.fill: parent
                        anchors.margins: Theme.spaceXl
                        spacing: Theme.spaceMd

                        // Header with selected info
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceMd

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                RowLayout {
                                    spacing: Theme.spaceSm
                                    Text {
                                        text: ThemeCtrl.selectedScheme.name || "Select a Scheme"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeLg
                                        font.weight: Font.DemiBold
                                        color: Theme.textPrimary
                                    }

                                    PFBadge {
                                        visible: ThemeCtrl.selectedScheme.is_active === true
                                        text: "Currently Active in Plasma"
                                        variant: "success"
                                        size: "xs"
                                    }
                                }

                                Text {
                                    text: ThemeCtrl.selectedScheme.file_path || ""
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeSm
                                    color: Theme.textMuted
                                    elide: Text.ElideMiddle
                                    Layout.fillWidth: true
                                }
                            }

                            PFBadge {
                                text: ThemeCtrl.selectedScheme.is_user_scheme ? "User Scheme" : "System Protected"
                                variant: ThemeCtrl.selectedScheme.is_user_scheme ? "accent" : "neutral"
                                size: "xs"
                            }
                        }

                        // Action Buttons Bar
                        Flow {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm

                            PFButton {
                                text: ThemeCtrl.selectedScheme.is_active ? "Currently Active" : (AppCtrl.safeMode ? "Simulate Apply (Safe Mode)" : "Apply Color Scheme")
                                iconText: ThemeCtrl.selectedScheme.is_active ? "✓" : "⚡"
                                variant: ThemeCtrl.selectedScheme.is_active ? "secondary" : "primary"
                                size: "md"
                                enabled: !ThemeCtrl.selectedScheme.is_active && !ThemeCtrl.isApplying
                                onClicked: ThemeCtrl.requestApplySelected()
                            }

                            PFButton {
                                text: "Preview Changes (Diff)"
                                iconText: "🔍"
                                variant: "outline"
                                size: "md"
                                onClicked: {
                                    ThemeCtrl.requestDiffPreview(ThemeCtrl.selectedSchemeIndex)
                                    diffDrawer.visible = true
                                }
                            }

                            PFButton {
                                visible: ThemeCtrl.canRestorePrevious
                                text: "Restore Previous Scheme"
                                iconText: "↺"
                                variant: "danger"
                                size: "md"
                                onClicked: ThemeCtrl.restorePreviousScheme()
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.borderSubtle
                        }

                        Text {
                            text: "PALETTE ROLES & MOCK PREVIEW"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            font.weight: Font.DemiBold
                            color: Theme.textMuted
                        }

                        // Simulated Window / View Preview Box
                        Rectangle {
                            Layout.fillWidth: true
                            height: 130
                            radius: Theme.radiusMd
                            color: ThemeCtrl.selectedScheme.window_bg || "#202326"
                            border.color: Theme.border
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: Theme.spaceMd
                                spacing: Theme.spaceSm

                                // Mock Window Header
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 6

                                    Rectangle { width: 10; height: 10; radius: 5; color: "#ff5f56" }
                                    Rectangle { width: 10; height: 10; radius: 5; color: "#ffbd2e" }
                                    Rectangle { width: 10; height: 10; radius: 5; color: "#27c93f" }

                                    Text {
                                        text: "Plasma Window Preview (" + (ThemeCtrl.selectedScheme.name || "") + ")"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeSm
                                        color: ThemeCtrl.selectedScheme.window_fg || "#ffffff"
                                        Layout.fillWidth: true
                                        Layout.leftMargin: 8
                                    }
                                }

                                // Mock View content
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    radius: Theme.radiusSm
                                    color: ThemeCtrl.selectedScheme.view_bg || "#181a1d"
                                    border.color: Qt.rgba(1, 1, 1, 0.08)
                                    border.width: 1

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: Theme.spaceSm
                                        spacing: Theme.spaceSm

                                        Rectangle {
                                            width: 120
                                            height: 30
                                            radius: Theme.radiusSm
                                            color: ThemeCtrl.selectedScheme.selection_bg || "#14b8a6"

                                            Text {
                                                anchors.centerIn: parent
                                                text: "Selected Item"
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontSizeSm
                                                font.weight: Font.DemiBold
                                                color: ThemeCtrl.selectedScheme.selection_fg || "#ffffff"
                                            }
                                        }

                                        Rectangle {
                                            width: 90
                                            height: 30
                                            radius: Theme.radiusSm
                                            color: ThemeCtrl.selectedScheme.button_bg || "#2d3136"
                                            border.color: Qt.rgba(1, 1, 1, 0.1)
                                            border.width: 1

                                            Text {
                                                anchors.centerIn: parent
                                                text: "Button"
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontSizeSm
                                                color: ThemeCtrl.selectedScheme.button_fg || "#ffffff"
                                            }
                                        }

                                        Text {
                                            text: "Normal text item inside view"
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontSizeSm
                                            color: ThemeCtrl.selectedScheme.view_fg || "#f0f2f5"
                                            Layout.fillWidth: true
                                            Layout.leftMargin: 8
                                        }
                                    }
                                }
                            }
                        }

                        // Color Hex Tokens Row
                        Flow {
                            Layout.fillWidth: true
                            spacing: Theme.spaceMd

                            Repeater {
                                model: [
                                    { label: "Window BG", val: ThemeCtrl.selectedScheme.window_bg },
                                    { label: "View BG", val: ThemeCtrl.selectedScheme.view_bg },
                                    { label: "Selection", val: ThemeCtrl.selectedScheme.selection_bg },
                                    { label: "Button BG", val: ThemeCtrl.selectedScheme.button_bg }
                                ]
                                delegate: RowLayout {
                                    spacing: 6
                                    Rectangle { width: 14; height: 14; radius: 3; color: modelData.val || "#000000"; border.color: Theme.border; border.width: 1 }
                                    Text {
                                        text: modelData.label + ": " + (modelData.val || "N/A")
                                        font.family: Theme.fontMono
                                        font.pixelSize: Theme.fontSizeXs
                                        color: Theme.textSecondary
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Expandable Diff Preview Drawer
            PFCard {
                id: diffDrawer
                visible: false
                Layout.fillWidth: true
                implicitHeight: diffLayout.implicitHeight + (Theme.spaceLg * 2)

                ColumnLayout {
                    id: diffLayout
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.spaceSm

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "CONFIGURATION DIFF PREVIEW (DRY-RUN AUDIT)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            font.weight: Font.DemiBold
                            color: Theme.textMuted
                            Layout.fillWidth: true
                        }
                        PFButton {
                            text: "Close Preview"
                            size: "sm"
                            onClicked: diffDrawer.visible = false
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 180
                        radius: Theme.radiusMd
                        color: "#0f1115"
                        border.color: Theme.borderSubtle
                        border.width: 1

                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
                            clip: true

                            Text {
                                text: ThemeCtrl.currentDiffPreview || "Click 'Preview Changes (Diff)' to inspect changes."
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.textSecondary
                                wrapMode: Text.NoWrap
                            }
                        }
                    }
                }
            }

            // Plasma Styles Row
            PFSectionHeader {
                title: "Plasma Styles (Desktop Themes)"
                subtitle: "Detected desktop themes governing panels, widgets, and Plasma overlays"
            }

            GridLayout {
                Layout.fillWidth: true
                columns: themeStudioRoot.width > 800 ? Math.min(Math.max(ThemeCtrl.plasmaStyles.length, 1), 3) : 1
                columnSpacing: Theme.spaceLg
                rowSpacing: Theme.spaceLg

                Repeater {
                    model: ThemeCtrl.plasmaStyles
                    delegate: PFCard {
                        Layout.fillWidth: true
                        implicitHeight: 90
                        hoverable: true

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.spaceLg
                            spacing: Theme.spaceXs

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: modelData.name
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeBase
                                    font.weight: Font.DemiBold
                                    color: Theme.textPrimary
                                    Layout.fillWidth: true
                                }
                                PFBadge {
                                    text: modelData.is_user_style ? "User" : "System"
                                    variant: "neutral"
                                    size: "xs"
                                }
                            }

                            Text {
                                text: modelData.comment
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.textSecondary
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            Text {
                                text: "Author: " + modelData.author
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.textMuted
                            }
                        }
                    }
                }
            }

            Item { height: Theme.spaceXl; Layout.fillWidth: true }
        }
    }
    }

    // ==========================================
    // CONFIRMATION DIALOG MODAL OVERLAY
    // ==========================================
    Rectangle {
        id: confirmModalOverlay
        anchors.fill: parent
        visible: ThemeCtrl.showConfirmDialog
        color: Qt.rgba(0, 0, 0, 0.65)
        z: 99

        MouseArea {
            anchors.fill: parent
            // Eat clicks outside dialog
            onClicked: {}
        }

        PFCard {
            id: confirmCard
            anchors.centerIn: parent
            width: Math.min(confirmModalOverlay.width - 48, 560)
            height: Math.min(modalContentCol.implicitHeight + (Theme.spaceXl * 2), confirmModalOverlay.height - 48)

            MouseArea {
                anchors.fill: parent
                // absorb clicks inside card
            }

            ScrollView {
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                clip: true

                ColumnLayout {
                    id: modalContentCol
                    width: confirmCard.width - (Theme.spaceXl * 2) - 16
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
                                text: "Confirm Color Scheme Application"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeLg
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                            }

                            Text {
                                text: "Selected: " + ThemeCtrl.confirmSchemeName + " (Active: " + ThemeCtrl.activeSchemeId + ")"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
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
                        implicitHeight: safetyNoteCol.implicitHeight + 16
                        radius: Theme.radiusMd
                        color: AppCtrl.safeMode ? Qt.rgba(0.08, 0.72, 0.65, 0.1) : Qt.rgba(0.96, 0.62, 0.04, 0.1)
                        border.color: AppCtrl.safeMode ? Qt.rgba(0.08, 0.72, 0.65, 0.25) : Qt.rgba(0.96, 0.62, 0.04, 0.25)
                        border.width: 1

                        ColumnLayout {
                            id: safetyNoteCol
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 4

                            Text {
                                text: AppCtrl.safeMode ? "Safe Mode Simulation:" : "Live Session Update:"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                font.weight: Font.DemiBold
                                color: AppCtrl.safeMode ? Theme.accentLight : Theme.warning
                            }
                            Text {
                                text: AppCtrl.safeMode
                                    ? "Safe Mode is currently ON. A simulated dry-run will verify the backup engine and generate diffs without modifying your active desktop session."
                                    : "A verified cryptographic snapshot of ~/.config/kdeglobals will be created automatically before applying. Running KDE apps will re-theme immediately."
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.textSecondary
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }

                    // Transactional Pipeline Steps
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

                            Text {
                                anchors.centerIn: parent
                                text: "1. Preview Diff"
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                font.weight: Font.DemiBold
                                color: Theme.textMuted
                            }
                        }

                        Rectangle {
                            height: 22
                            radius: Theme.radiusSm
                            color: Qt.rgba(0.08, 0.72, 0.65, 0.1)
                            border.color: Qt.rgba(0.08, 0.72, 0.65, 0.25)
                            border.width: 1
                            Layout.fillWidth: true

                            Text {
                                anchors.centerIn: parent
                                text: "2. SHA256 Backup"
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                font.weight: Font.DemiBold
                                color: Theme.accentLight
                            }
                        }

                        Rectangle {
                            height: 22
                            radius: Theme.radiusSm
                            color: Qt.rgba(1, 1, 1, 0.04)
                            border.color: Theme.borderSubtle
                            border.width: 1
                            Layout.fillWidth: true

                            Text {
                                anchors.centerIn: parent
                                text: "3. Apply (shell=False)"
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                font.weight: Font.DemiBold
                                color: Theme.textMuted
                            }
                        }

                        Rectangle {
                            height: 22
                            radius: Theme.radiusSm
                            color: Qt.rgba(0.08, 0.72, 0.65, 0.1)
                            border.color: Qt.rgba(0.08, 0.72, 0.65, 0.25)
                            border.width: 1
                            Layout.fillWidth: true

                            Text {
                                anchors.centerIn: parent
                                text: "4. Verify & Rollback"
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                font.weight: Font.DemiBold
                                color: Theme.accentLight
                            }
                        }
                    }

                    // Diff preview block
                    Text {
                        text: "INTENDED CONFIGURATION CHANGES (TARGET: ~/.config/kdeglobals)"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeXs
                        font.weight: Font.DemiBold
                        color: Theme.textMuted
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 130
                        radius: Theme.radiusMd
                        color: "#0f1115"
                        border.color: Theme.borderSubtle
                        border.width: 1

                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
                            clip: true

                            Text {
                                text: ThemeCtrl.currentDiffPreview
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.textSecondary
                                wrapMode: Text.NoWrap
                            }
                        }
                    }

                    // Modal Actions
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: Theme.spaceSm
                        spacing: Theme.spaceMd

                        Item { Layout.fillWidth: true }

                        PFButton {
                            text: "Cancel"
                            variant: "secondary"
                            size: "md"
                            onClicked: ThemeCtrl.cancelApply()
                        }

                        PFButton {
                            text: AppCtrl.safeMode ? "Confirm Simulation" : "Apply to KDE Session"
                            iconText: AppCtrl.safeMode ? "🛡" : "⚡"
                            variant: "primary"
                            size: "md"
                            onClicked: ThemeCtrl.confirmApplySelected()
                        }
                    }
                }
            }
        }
    }
}
