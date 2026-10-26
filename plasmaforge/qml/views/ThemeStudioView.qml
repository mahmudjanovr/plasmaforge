import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import PlasmaForge.Controllers 1.0
import plasmaforge.qml.theme 1.0
import plasmaforge.qml.components 1.0

Item {
    id: themeStudioRoot

    // Active sub-tab: 0 = Reactive Theme Editor, 1 = KDE System Palettes & Styles
    property int activeTab: 0

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
                spacing: Theme.spaceLg

                Item { height: Theme.spaceXs; Layout.fillWidth: true }

                // Main Section Header
                PFSectionHeader {
                    title: "Theme Studio"
                    subtitle: "Reactive desktop theme engine, instant live preview, preset library, and KDE color management"

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
                            visible: themeStudioRoot.activeTab === 1
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

                // Studio Navigation Tabs & Preset Status Bar
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    // Tab Selector Pills
                    RowLayout {
                        spacing: 4

                        Rectangle {
                            height: 36
                            implicitWidth: tab1Row.implicitWidth + 24
                            radius: Theme.radiusMd
                            color: themeStudioRoot.activeTab === 0 ? Qt.rgba(0.08, 0.72, 0.65, 0.16) : (tab1Mouse.containsMouse ? Theme.cardHover : Theme.surface)
                            border.color: themeStudioRoot.activeTab === 0 ? Theme.accent : Theme.borderSubtle
                            border.width: 1

                            MouseArea {
                                id: tab1Mouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: themeStudioRoot.activeTab = 0
                            }

                            RowLayout {
                                id: tab1Row
                                anchors.centerIn: parent
                                spacing: 6

                                Text {
                                    text: "🎨"
                                    font.pixelSize: 13
                                }
                                Text {
                                    text: "Live Theme Editor"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeSm
                                    font.weight: themeStudioRoot.activeTab === 0 ? Font.DemiBold : Font.Normal
                                    color: themeStudioRoot.activeTab === 0 ? Theme.textPrimary : Theme.textSecondary
                                }
                            }
                        }

                        Rectangle {
                            height: 36
                            implicitWidth: tab2Row.implicitWidth + 24
                            radius: Theme.radiusMd
                            color: themeStudioRoot.activeTab === 1 ? Qt.rgba(0.08, 0.72, 0.65, 0.16) : (tab2Mouse.containsMouse ? Theme.cardHover : Theme.surface)
                            border.color: themeStudioRoot.activeTab === 1 ? Theme.accent : Theme.borderSubtle
                            border.width: 1

                            MouseArea {
                                id: tab2Mouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: themeStudioRoot.activeTab = 1
                            }

                            RowLayout {
                                id: tab2Row
                                anchors.centerIn: parent
                                spacing: 6

                                Text {
                                    text: "🖥"
                                    font.pixelSize: 13
                                }
                                Text {
                                    text: "KDE System Palettes (" + ThemeCtrl.colorSchemes.length + ")"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeSm
                                    font.weight: themeStudioRoot.activeTab === 1 ? Font.DemiBold : Font.Normal
                                    color: themeStudioRoot.activeTab === 1 ? Theme.textPrimary : Theme.textSecondary
                                }
                            }
                        }
                    }

                    Item { Layout.fillWidth: true }

                    // Draft status indicator in tab 0
                    PFBadge {
                        visible: themeStudioRoot.activeTab === 0
                        text: ThemeCtrl.isDraftModified ? "Draft: Modified" : "Active: " + ThemeCtrl.currentPresetName
                        variant: ThemeCtrl.isDraftModified ? "accent" : "neutral"
                        size: "sm"
                    }
                }

                // ==============================================================
                // TAB 0: REACTIVE THEME EDITOR & INSTANT LIVE PREVIEW
                // ==============================================================
                ColumnLayout {
                    visible: themeStudioRoot.activeTab === 0
                    Layout.fillWidth: true
                    spacing: Theme.spaceLg

                    // Presets Carousel & Actions Strip
                    PFCard {
                        Layout.fillWidth: true
                        implicitHeight: presetsCol.implicitHeight + (Theme.spaceMd * 2)

                        ColumnLayout {
                            id: presetsCol
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
                            spacing: Theme.spaceSm

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spaceMd

                                Text {
                                    text: "THEME PRESETS"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeXs
                                    font.weight: Font.DemiBold
                                    color: Theme.textMuted
                                    Layout.fillWidth: true
                                }

                                RowLayout {
                                    spacing: Theme.spaceSm

                                    PFButton {
                                        text: "Save Preset"
                                        iconText: "💾"
                                        size: "sm"
                                        variant: "primary"
                                        onClicked: ThemeCtrl.requestSavePreset()
                                    }

                                    PFButton {
                                        visible: !ThemeCtrl.isCurrentPresetBuiltin
                                        text: "Update Preset"
                                        iconText: "✓"
                                        size: "sm"
                                        variant: "outline"
                                        onClicked: ThemeCtrl.requestOverwritePreset(ThemeCtrl.currentPresetId)
                                    }

                                    PFButton {
                                        visible: !ThemeCtrl.isCurrentPresetBuiltin
                                        text: "Delete Preset"
                                        iconText: "✕"
                                        size: "sm"
                                        variant: "danger"
                                        onClicked: ThemeCtrl.requestDeletePreset(ThemeCtrl.currentPresetId)
                                    }

                                    PFButton {
                                        text: "Restore Default"
                                        iconText: "↺"
                                        size: "sm"
                                        variant: "secondary"
                                        onClicked: {
                                            ThemeCtrl.restoreDefaultTheme()
                                            AppCtrl.showToast("Restored default PlasmaForge theme.", "info")
                                        }
                                    }
                                }
                            }

                            // Presets List
                            ScrollView {
                                Layout.fillWidth: true
                                implicitHeight: 64
                                clip: true
                                contentHeight: 64

                                RowLayout {
                                    spacing: Theme.spaceSm

                                    Repeater {
                                        model: ThemeCtrl.themePresets

                                        delegate: Rectangle {
                                            implicitWidth: 180
                                            height: 52
                                            radius: Theme.radiusMd
                                            color: ThemeCtrl.currentPresetId === modelData.id ? Qt.rgba(0.08, 0.72, 0.65, 0.12) : (presetCardMouse.containsMouse ? Theme.cardHover : Theme.surface)
                                            border.color: ThemeCtrl.currentPresetId === modelData.id ? Theme.accent : Theme.borderSubtle
                                            border.width: 1

                                            Behavior on color { ColorAnimation { duration: Theme.animDurationFast } }

                                            MouseArea {
                                                id: presetCardMouse
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: ThemeCtrl.loadPreset(modelData.id)
                                            }

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.margins: Theme.spaceSm
                                                spacing: Theme.spaceSm

                                                // Swatch pill preview
                                                ColumnLayout {
                                                    spacing: 2
                                                    Row {
                                                        spacing: 2
                                                        Rectangle { width: 8; height: 16; radius: 2; color: (modelData.colors && modelData.colors.primary) || "#14b8a6" }
                                                        Rectangle { width: 8; height: 16; radius: 2; color: (modelData.colors && modelData.colors.background) || "#131518"; border.color: Theme.border; border.width: 1 }
                                                        Rectangle { width: 8; height: 16; radius: 2; color: (modelData.colors && modelData.colors.surface) || "#181b20" }
                                                    }
                                                }

                                                ColumnLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 1

                                                    Text {
                                                        text: modelData.name
                                                        font.family: Theme.fontFamily
                                                        font.pixelSize: Theme.fontSizeSm
                                                        font.weight: ThemeCtrl.currentPresetId === modelData.id ? Font.DemiBold : Font.Normal
                                                        color: ThemeCtrl.currentPresetId === modelData.id ? Theme.textPrimary : Theme.textSecondary
                                                        elide: Text.ElideRight
                                                        Layout.fillWidth: true
                                                    }

                                                    Text {
                                                        text: modelData.is_builtin ? "Curated Preset" : "User Preset"
                                                        font.family: Theme.fontFamily
                                                        font.pixelSize: 9
                                                        color: Theme.textMuted
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Main Editor & Live Preview 2-Column Responsive Layout
                    GridLayout {
                        Layout.fillWidth: true
                        columns: themeStudioRoot.width > 780 ? 2 : 1
                        columnSpacing: Theme.spaceLg
                        rowSpacing: Theme.spaceLg

                        // Left Column: Reactive Theme Controls
                        PFCard {
                            Layout.fillWidth: true
                            Layout.preferredWidth: themeStudioRoot.width > 780 ? 460 : -1
                            implicitHeight: controlsCol.implicitHeight + (Theme.spaceLg * 2)

                            ColumnLayout {
                                id: controlsCol
                                anchors.fill: parent
                                anchors.margins: Theme.spaceLg
                                spacing: Theme.spaceLg

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text {
                                        text: "THEME PARAMETERS"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeXs
                                        font.weight: Font.DemiBold
                                        color: Theme.accentLight
                                        Layout.fillWidth: true
                                    }

                                    PFButton {
                                        text: "Import KDE Palette"
                                        iconText: "📥"
                                        size: "sm"
                                        variant: "outline"
                                        onClicked: ThemeCtrl.applyCurrentKdeSchemeToEditor()
                                    }
                                }

                                // ------------------------------------
                                // 1. Colors Controls
                                // ------------------------------------
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spaceMd

                                    Text {
                                        text: "COLOR PALETTE"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 10
                                        font.weight: Font.DemiBold
                                        color: Theme.textMuted
                                    }

                                    // A. Primary / Accent Color
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Primary / Accent"; font.pixelSize: Theme.fontSizeXs; font.weight: Font.DemiBold; color: Theme.textPrimary }
                                            Item { Layout.fillWidth: true }
                                            Rectangle { width: 14; height: 14; radius: 3; color: ThemeCtrl.primaryColor; border.color: Theme.border; border.width: 1 }
                                            Rectangle {
                                                width: 76
                                                height: 20
                                                radius: Theme.radiusSm
                                                color: Theme.inputBg
                                                border.color: primaryHexInput.activeFocus ? Theme.accent : Theme.borderSubtle
                                                border.width: 1
                                                TextInput {
                                                    id: primaryHexInput
                                                    anchors.fill: parent
                                                    anchors.leftMargin: 6
                                                    anchors.rightMargin: 6
                                                    verticalAlignment: TextInput.AlignVCenter
                                                    font.family: Theme.fontMono
                                                    font.pixelSize: Theme.fontSizeXs
                                                    color: Theme.accentLight
                                                    text: ThemeCtrl.primaryColor
                                                    selectByMouse: true
                                                    onEditingFinished: ThemeCtrl.setPrimaryColor(text)
                                                }
                                            }
                                        }

                                        Flow {
                                            Layout.fillWidth: true
                                            spacing: 6

                                            Repeater {
                                                model: ["#14b8a6", "#06b6d4", "#3b82f6", "#6366f1", "#a855f7", "#f59e0b", "#f43f5e", "#10b981"]
                                                delegate: Rectangle {
                                                    width: 24
                                                    height: 24
                                                    radius: 4
                                                    color: modelData
                                                    border.color: ThemeCtrl.primaryColor.toLowerCase() === modelData.toLowerCase() ? "#ffffff" : Theme.border
                                                    border.width: ThemeCtrl.primaryColor.toLowerCase() === modelData.toLowerCase() ? 2 : 1
                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: ThemeCtrl.setPrimaryColor(modelData)
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    // B. Background Color
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Background"; font.pixelSize: Theme.fontSizeXs; font.weight: Font.DemiBold; color: Theme.textPrimary }
                                            Item { Layout.fillWidth: true }
                                            Rectangle { width: 14; height: 14; radius: 3; color: ThemeCtrl.backgroundColor; border.color: Theme.border; border.width: 1 }
                                            Rectangle {
                                                width: 76
                                                height: 20
                                                radius: Theme.radiusSm
                                                color: Theme.inputBg
                                                border.color: bgHexInput.activeFocus ? Theme.accent : Theme.borderSubtle
                                                border.width: 1
                                                TextInput {
                                                    id: bgHexInput
                                                    anchors.fill: parent
                                                    anchors.leftMargin: 6
                                                    anchors.rightMargin: 6
                                                    verticalAlignment: TextInput.AlignVCenter
                                                    font.family: Theme.fontMono
                                                    font.pixelSize: Theme.fontSizeXs
                                                    color: Theme.textSecondary
                                                    text: ThemeCtrl.backgroundColor
                                                    selectByMouse: true
                                                    onEditingFinished: ThemeCtrl.setBackgroundColor(text)
                                                }
                                            }
                                        }

                                        Flow {
                                            Layout.fillWidth: true
                                            spacing: 6

                                            Repeater {
                                                model: ["#131518", "#0a0c10", "#242933", "#1e1d1b", "#121417", "#000000", "#eff0f1"]
                                                delegate: Rectangle {
                                                    width: 24
                                                    height: 24
                                                    radius: 4
                                                    color: modelData
                                                    border.color: ThemeCtrl.backgroundColor.toLowerCase() === modelData.toLowerCase() ? Theme.accent : Theme.border
                                                    border.width: ThemeCtrl.backgroundColor.toLowerCase() === modelData.toLowerCase() ? 2 : 1
                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: ThemeCtrl.setBackgroundColor(modelData)
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    // C. Surface Color
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Surface / Cards"; font.pixelSize: Theme.fontSizeXs; font.weight: Font.DemiBold; color: Theme.textPrimary }
                                            Item { Layout.fillWidth: true }
                                            Rectangle { width: 14; height: 14; radius: 3; color: ThemeCtrl.surfaceColor; border.color: Theme.border; border.width: 1 }
                                            Rectangle {
                                                width: 76
                                                height: 20
                                                radius: Theme.radiusSm
                                                color: Theme.inputBg
                                                border.color: surfaceHexInput.activeFocus ? Theme.accent : Theme.borderSubtle
                                                border.width: 1
                                                TextInput {
                                                    id: surfaceHexInput
                                                    anchors.fill: parent
                                                    anchors.leftMargin: 6
                                                    anchors.rightMargin: 6
                                                    verticalAlignment: TextInput.AlignVCenter
                                                    font.family: Theme.fontMono
                                                    font.pixelSize: Theme.fontSizeXs
                                                    color: Theme.textSecondary
                                                    text: ThemeCtrl.surfaceColor
                                                    selectByMouse: true
                                                    onEditingFinished: ThemeCtrl.setSurfaceColor(text)
                                                }
                                            }
                                        }

                                        Flow {
                                            Layout.fillWidth: true
                                            spacing: 6

                                            Repeater {
                                                model: ["#181b20", "#1f2228", "#2e3440", "#2a2825", "#1c1f24", "#22252c", "#ffffff"]
                                                delegate: Rectangle {
                                                    width: 24
                                                    height: 24
                                                    radius: 4
                                                    color: modelData
                                                    border.color: ThemeCtrl.surfaceColor.toLowerCase() === modelData.toLowerCase() ? Theme.accent : Theme.border
                                                    border.width: ThemeCtrl.surfaceColor.toLowerCase() === modelData.toLowerCase() ? 2 : 1
                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: ThemeCtrl.setSurfaceColor(modelData)
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    // D. Text Color
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Text Primary"; font.pixelSize: Theme.fontSizeXs; font.weight: Font.DemiBold; color: Theme.textPrimary }
                                            Item { Layout.fillWidth: true }
                                            Rectangle { width: 14; height: 14; radius: 3; color: ThemeCtrl.textColor; border.color: Theme.border; border.width: 1 }
                                            Rectangle {
                                                width: 76
                                                height: 20
                                                radius: Theme.radiusSm
                                                color: Theme.inputBg
                                                border.color: textHexInput.activeFocus ? Theme.accent : Theme.borderSubtle
                                                border.width: 1
                                                TextInput {
                                                    id: textHexInput
                                                    anchors.fill: parent
                                                    anchors.leftMargin: 6
                                                    anchors.rightMargin: 6
                                                    verticalAlignment: TextInput.AlignVCenter
                                                    font.family: Theme.fontMono
                                                    font.pixelSize: Theme.fontSizeXs
                                                    color: Theme.textSecondary
                                                    text: ThemeCtrl.textColor
                                                    selectByMouse: true
                                                    onEditingFinished: ThemeCtrl.setTextColor(text)
                                                }
                                            }
                                        }

                                        Flow {
                                            Layout.fillWidth: true
                                            spacing: 6

                                            Repeater {
                                                model: ["#f3f4f6", "#ffffff", "#eceff4", "#e7e5e4", "#f5f5f5", "#1f2937"]
                                                delegate: Rectangle {
                                                    width: 24
                                                    height: 24
                                                    radius: 4
                                                    color: modelData
                                                    border.color: ThemeCtrl.textColor.toLowerCase() === modelData.toLowerCase() ? Theme.accent : Theme.border
                                                    border.width: ThemeCtrl.textColor.toLowerCase() === modelData.toLowerCase() ? 2 : 1
                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: ThemeCtrl.setTextColor(modelData)
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    // E. Secondary Text Color
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Secondary Text"; font.pixelSize: Theme.fontSizeXs; font.weight: Font.DemiBold; color: Theme.textPrimary }
                                            Item { Layout.fillWidth: true }
                                            Rectangle { width: 14; height: 14; radius: 3; color: ThemeCtrl.secondaryTextColor; border.color: Theme.border; border.width: 1 }
                                            Rectangle {
                                                width: 76
                                                height: 20
                                                radius: Theme.radiusSm
                                                color: Theme.inputBg
                                                border.color: secHexInput.activeFocus ? Theme.accent : Theme.borderSubtle
                                                border.width: 1
                                                TextInput {
                                                    id: secHexInput
                                                    anchors.fill: parent
                                                    anchors.leftMargin: 6
                                                    anchors.rightMargin: 6
                                                    verticalAlignment: TextInput.AlignVCenter
                                                    font.family: Theme.fontMono
                                                    font.pixelSize: Theme.fontSizeXs
                                                    color: Theme.textSecondary
                                                    text: ThemeCtrl.secondaryTextColor
                                                    selectByMouse: true
                                                    onEditingFinished: ThemeCtrl.setSecondaryTextColor(text)
                                                }
                                            }
                                        }

                                        Flow {
                                            Layout.fillWidth: true
                                            spacing: 6

                                            Repeater {
                                                model: ["#9ca3af", "#6b7280", "#d8dee9", "#a8a29e", "#8b949e", "#4b5563"]
                                                delegate: Rectangle {
                                                    width: 24
                                                    height: 24
                                                    radius: 4
                                                    color: modelData
                                                    border.color: ThemeCtrl.secondaryTextColor.toLowerCase() === modelData.toLowerCase() ? Theme.accent : Theme.border
                                                    border.width: ThemeCtrl.secondaryTextColor.toLowerCase() === modelData.toLowerCase() ? 2 : 1
                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: ThemeCtrl.setSecondaryTextColor(modelData)
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

                                // ------------------------------------
                                // 2. Typography Controls
                                // ------------------------------------
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spaceSm

                                    Text {
                                        text: "TYPOGRAPHY"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 10
                                        font.weight: Font.DemiBold
                                        color: Theme.textMuted
                                    }

                                    // Font Family Selection
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4

                                        Text { text: "Font Family"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }

                                        Flow {
                                            Layout.fillWidth: true
                                            spacing: 6

                                            Repeater {
                                                model: ThemeCtrl.availableFontFamilies

                                                delegate: PFButton {
                                                    text: modelData
                                                    size: "sm"
                                                    variant: ThemeCtrl.fontFamily === modelData ? "primary" : "secondary"
                                                    onClicked: ThemeCtrl.setFontFamily(modelData)
                                                }
                                            }
                                        }
                                    }

                                    // Font Base Size Selection
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Base Size"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                                            Item { Layout.fillWidth: true }
                                            Text { text: ThemeCtrl.fontSize + " pt"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeXs; color: Theme.accentLight }
                                        }

                                        RowLayout {
                                            spacing: 6

                                            Repeater {
                                                model: ThemeCtrl.availableFontSizes

                                                delegate: PFButton {
                                                    text: modelData + "pt"
                                                    size: "sm"
                                                    variant: ThemeCtrl.fontSize === modelData ? "primary" : "secondary"
                                                    onClicked: ThemeCtrl.setFontSize(modelData)
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

                                // ------------------------------------
                                // 3. Border Radius & Spacing Controls
                                // ------------------------------------
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.spaceSm

                                    Text {
                                        text: "GEOMETRY & SPACING"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 10
                                        font.weight: Font.DemiBold
                                        color: Theme.textMuted
                                    }

                                    // Border Radius
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Border Radius"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                                            Item { Layout.fillWidth: true }
                                            Text { text: ThemeCtrl.borderRadius + " px"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeXs; color: Theme.accentLight }
                                        }

                                        Flow {
                                            Layout.fillWidth: true
                                            spacing: 6

                                            Repeater {
                                                model: ThemeCtrl.availableRadiusOptions

                                                delegate: PFButton {
                                                    text: modelData === 0 ? "0px (Square)" : (modelData + "px")
                                                    size: "sm"
                                                    variant: ThemeCtrl.borderRadius === modelData ? "primary" : "secondary"
                                                    onClicked: ThemeCtrl.setBorderRadius(modelData)
                                                }
                                            }
                                        }
                                    }

                                    // Spacing Scale
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Spacing Scale"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                                            Item { Layout.fillWidth: true }
                                            Text { text: ThemeCtrl.spacingScale + "x (" + ThemeCtrl.spacingMd + "px base)"; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeXs; color: Theme.accentLight }
                                        }

                                        Flow {
                                            Layout.fillWidth: true
                                            spacing: 6

                                            Repeater {
                                                model: ThemeCtrl.availableSpacingOptions

                                                delegate: PFButton {
                                                    text: modelData + "x"
                                                    size: "sm"
                                                    variant: Math.abs(ThemeCtrl.spacingScale - modelData) < 0.01 ? "primary" : "secondary"
                                                    onClicked: ThemeCtrl.setSpacingScale(modelData)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Right Column: INSTANT LIVE PREVIEW CANVAS
                        PFCard {
                            Layout.fillWidth: true
                            implicitHeight: previewContainerCol.implicitHeight + (Theme.spaceLg * 2)

                            ColumnLayout {
                                id: previewContainerCol
                                anchors.fill: parent
                                anchors.margins: Theme.spaceLg
                                spacing: Theme.spaceMd

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text {
                                        text: "INSTANT LIVE PREVIEW"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeXs
                                        font.weight: Font.DemiBold
                                        color: Theme.accentLight
                                        Layout.fillWidth: true
                                    }
                                    PFBadge {
                                        text: "100% Reactive State"
                                        variant: "accent"
                                        size: "xs"
                                    }
                                }

                                // Simulated Application Window Canvas (uses actual reactive theme variables)
                                Rectangle {
                                    id: livePreviewWindow
                                    Layout.fillWidth: true
                                    implicitHeight: 380
                                    radius: ThemeCtrl.radiusLg
                                    color: ThemeCtrl.backgroundColor
                                    border.color: Theme.border
                                    border.width: 1
                                    clip: true

                                    ColumnLayout {
                                        anchors.fill: parent
                                        spacing: 0

                                        // Mock Window Header Bar
                                        Rectangle {
                                            Layout.fillWidth: true
                                            height: 38
                                            color: Qt.rgba(0, 0, 0, 0.2)
                                            border.color: Qt.rgba(1, 1, 1, 0.05)
                                            border.width: 1

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: ThemeCtrl.spacingMd
                                                anchors.rightMargin: ThemeCtrl.spacingMd
                                                spacing: 6

                                                Rectangle { width: 10; height: 10; radius: 5; color: "#ff5f56" }
                                                Rectangle { width: 10; height: 10; radius: 5; color: "#ffbd2e" }
                                                Rectangle { width: 10; height: 10; radius: 5; color: "#27c93f" }

                                                Item { width: ThemeCtrl.spacingSm }

                                                Text {
                                                    text: "PlasmaForge Theme Studio — " + ThemeCtrl.currentPresetName
                                                    font.family: ThemeCtrl.fontFamily
                                                    font.pixelSize: ThemeCtrl.fontSize
                                                    font.weight: Font.DemiBold
                                                    color: ThemeCtrl.textColor
                                                    elide: Text.ElideRight
                                                    Layout.fillWidth: true
                                                }

                                                Rectangle {
                                                    height: 20
                                                    radius: ThemeCtrl.radiusSm
                                                    color: Qt.rgba(0.08, 0.72, 0.65, 0.15)
                                                    implicitWidth: fontBadgeText.implicitWidth + 12

                                                    Text {
                                                        id: fontBadgeText
                                                        anchors.centerIn: parent
                                                        text: ThemeCtrl.fontFamily + " " + ThemeCtrl.fontSize + "pt"
                                                        font.family: ThemeCtrl.fontFamily
                                                        font.pixelSize: Math.max(9, ThemeCtrl.fontSize - 3)
                                                        font.weight: Font.DemiBold
                                                        color: ThemeCtrl.primaryColor
                                                    }
                                                }
                                            }
                                        }

                                        // Window Content Area
                                        Item {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true

                                            ColumnLayout {
                                                anchors.fill: parent
                                                anchors.margins: ThemeCtrl.spacingLg
                                                spacing: ThemeCtrl.spacingMd

                                                // Top Simulation Tabs
                                                RowLayout {
                                                    spacing: ThemeCtrl.spacingSm

                                                    Rectangle {
                                                        height: 26
                                                        radius: ThemeCtrl.radiusSm
                                                        color: ThemeCtrl.primaryColor
                                                        implicitWidth: activeTabText.implicitWidth + (ThemeCtrl.spacingMd * 2)

                                                        Text {
                                                            id: activeTabText
                                                            anchors.centerIn: parent
                                                            text: "Active View"
                                                            font.family: ThemeCtrl.fontFamily
                                                            font.pixelSize: Math.max(10, ThemeCtrl.fontSize - 2)
                                                            font.weight: Font.DemiBold
                                                            color: "#ffffff"
                                                        }
                                                    }

                                                    Rectangle {
                                                        height: 26
                                                        radius: ThemeCtrl.radiusSm
                                                        color: Qt.rgba(1, 1, 1, 0.06)
                                                        implicitWidth: inactiveTabText.implicitWidth + (ThemeCtrl.spacingMd * 2)

                                                        Text {
                                                            id: inactiveTabText
                                                            anchors.centerIn: parent
                                                            text: "Components"
                                                            font.family: ThemeCtrl.fontFamily
                                                            font.pixelSize: Math.max(10, ThemeCtrl.fontSize - 2)
                                                            color: ThemeCtrl.secondaryTextColor
                                                        }
                                                    }

                                                    Item { Layout.fillWidth: true }
                                                }

                                                // Simulated Surface Card
                                                Rectangle {
                                                    Layout.fillWidth: true
                                                    Layout.fillHeight: true
                                                    radius: ThemeCtrl.radiusMd
                                                    color: ThemeCtrl.surfaceColor
                                                    border.color: Qt.rgba(1, 1, 1, 0.08)
                                                    border.width: 1

                                                    ColumnLayout {
                                                        anchors.fill: parent
                                                        anchors.margins: ThemeCtrl.spacingMd
                                                        spacing: ThemeCtrl.spacingMd

                                                        // Typography Section
                                                        ColumnLayout {
                                                            Layout.fillWidth: true
                                                            spacing: 2

                                                            Text {
                                                                text: "Reactive Typography Heading"
                                                                font.family: ThemeCtrl.fontFamily
                                                                font.pixelSize: ThemeCtrl.fontSize + 4
                                                                font.weight: Font.Bold
                                                                color: ThemeCtrl.textColor
                                                            }

                                                            Text {
                                                                text: "Body text rendered with " + ThemeCtrl.fontFamily + " at " + ThemeCtrl.fontSize + "pt with " + ThemeCtrl.secondaryTextColor + " secondary tone."
                                                                font.family: ThemeCtrl.fontFamily
                                                                font.pixelSize: ThemeCtrl.fontSize
                                                                color: ThemeCtrl.secondaryTextColor
                                                                wrapMode: Text.WordWrap
                                                                Layout.fillWidth: true
                                                            }
                                                        }

                                                        // Interactive Buttons Preview Row
                                                        RowLayout {
                                                            Layout.fillWidth: true
                                                            spacing: ThemeCtrl.spacingSm

                                                            // Primary button
                                                            Rectangle {
                                                                height: 32
                                                                radius: ThemeCtrl.radiusSm
                                                                color: ThemeCtrl.primaryColor
                                                                implicitWidth: 100

                                                                Text {
                                                                    anchors.centerIn: parent
                                                                    text: "Primary Action"
                                                                    font.family: ThemeCtrl.fontFamily
                                                                    font.pixelSize: Math.max(10, ThemeCtrl.fontSize - 1)
                                                                    font.weight: Font.DemiBold
                                                                    color: "#ffffff"
                                                                }
                                                            }

                                                            // Surface / Outline button
                                                            Rectangle {
                                                                height: 32
                                                                radius: ThemeCtrl.radiusSm
                                                                color: "transparent"
                                                                border.color: ThemeCtrl.primaryColor
                                                                border.width: 1
                                                                implicitWidth: 80

                                                                Text {
                                                                    anchors.centerIn: parent
                                                                    text: "Outline"
                                                                    font.family: ThemeCtrl.fontFamily
                                                                    font.pixelSize: Math.max(10, ThemeCtrl.fontSize - 1)
                                                                    color: ThemeCtrl.primaryColor
                                                                }
                                                            }

                                                            // Secondary Button
                                                            Rectangle {
                                                                height: 32
                                                                radius: ThemeCtrl.radiusSm
                                                                color: Qt.rgba(1, 1, 1, 0.08)
                                                                implicitWidth: 80

                                                                Text {
                                                                    anchors.centerIn: parent
                                                                    text: "Secondary"
                                                                    font.family: ThemeCtrl.fontFamily
                                                                    font.pixelSize: Math.max(10, ThemeCtrl.fontSize - 1)
                                                                    color: ThemeCtrl.textColor
                                                                }
                                                            }

                                                            Item { Layout.fillWidth: true }
                                                        }

                                                        // Simulated Input Field & Status Bar
                                                        RowLayout {
                                                            Layout.fillWidth: true
                                                            spacing: ThemeCtrl.spacingSm

                                                            Rectangle {
                                                                Layout.fillWidth: true
                                                                height: 30
                                                                radius: ThemeCtrl.radiusSm
                                                                color: Qt.rgba(0, 0, 0, 0.25)
                                                                border.color: Qt.rgba(1, 1, 1, 0.12)
                                                                border.width: 1

                                                                RowLayout {
                                                                    anchors.fill: parent
                                                                    anchors.leftMargin: 8
                                                                    anchors.rightMargin: 8

                                                                    Text {
                                                                        text: "🔍 Search plasma workspace..."
                                                                        font.family: ThemeCtrl.fontFamily
                                                                        font.pixelSize: Math.max(9, ThemeCtrl.fontSize - 2)
                                                                        color: ThemeCtrl.secondaryTextColor
                                                                        Layout.fillWidth: true
                                                                    }
                                                                }
                                                            }

                                                            // Accent Status Metric Pill
                                                            Rectangle {
                                                                height: 30
                                                                radius: ThemeCtrl.radiusSm
                                                                color: Qt.rgba(0.08, 0.72, 0.65, 0.15)
                                                                border.color: ThemeCtrl.primaryColor
                                                                border.width: 1
                                                                implicitWidth: 84

                                                                Text {
                                                                    anchors.centerIn: parent
                                                                    text: "Live 100%"
                                                                    font.family: ThemeCtrl.fontFamily
                                                                    font.pixelSize: Math.max(10, ThemeCtrl.fontSize - 1)
                                                                    font.weight: Font.DemiBold
                                                                    color: ThemeCtrl.primaryColor
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                // Hex Tokens Bar
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: Theme.spaceMd

                                    Repeater {
                                        model: [
                                            { label: "Accent", val: ThemeCtrl.primaryColor },
                                            { label: "Background", val: ThemeCtrl.backgroundColor },
                                            { label: "Surface", val: ThemeCtrl.surfaceColor },
                                            { label: "Text", val: ThemeCtrl.textColor },
                                            { label: "Secondary", val: ThemeCtrl.secondaryTextColor }
                                        ]
                                        delegate: RowLayout {
                                            spacing: 6
                                            Rectangle { width: 14; height: 14; radius: 3; color: modelData.val; border.color: Theme.border; border.width: 1 }
                                            Text {
                                                text: modelData.label + ": " + modelData.val
                                                font.family: Theme.fontMono
                                                font.pixelSize: Theme.fontSizeXs
                                                color: Theme.textSecondary
                                            }
                                        }
                                    }

                                    RowLayout {
                                        spacing: 6
                                        Text {
                                            text: "• Radius: " + ThemeCtrl.borderRadius + "px"
                                            font.family: Theme.fontMono
                                            font.pixelSize: Theme.fontSizeXs
                                            color: Theme.textMuted
                                        }
                                        Text {
                                            text: "• Spacing: " + ThemeCtrl.spacingScale + "x"
                                            font.family: Theme.fontMono
                                            font.pixelSize: Theme.fontSizeXs
                                            color: Theme.textMuted
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // ==============================================================
                // TAB 1: INSTALLED KDE SCHEMES, INSPECTOR & SAFE DESKTOP APPLY
                // ==============================================================
                ColumnLayout {
                    visible: themeStudioRoot.activeTab === 1
                    Layout.fillWidth: true
                    spacing: Theme.spaceLg

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
                                        text: "Load Into Theme Editor"
                                        iconText: "🎨"
                                        variant: "outline"
                                        size: "md"
                                        onClicked: {
                                            ThemeCtrl.applyCurrentKdeSchemeToEditor()
                                            themeStudioRoot.activeTab = 0
                                        }
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
                }

                Item { height: Theme.spaceXl; Layout.fillWidth: true }
            }
        }
    }

    // ==========================================
    // SAVE / OVERWRITE PRESET MODAL OVERLAY
    // ==========================================
    Rectangle {
        id: presetSaveModalOverlay
        anchors.fill: parent
        visible: ThemeCtrl.showPresetSaveDialog
        color: Qt.rgba(0, 0, 0, 0.65)
        z: 98

        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }

        PFCard {
            id: presetSaveCard
            anchors.centerIn: parent
            width: Math.min(presetSaveModalOverlay.width - 48, 480)
            height: Math.min(presetSaveCol.implicitHeight + (Theme.spaceXl * 2), presetSaveModalOverlay.height - 48)

            MouseArea {
                anchors.fill: parent
            }

            ScrollView {
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                clip: true

                ColumnLayout {
                    id: presetSaveCol
                    width: presetSaveCard.width - (Theme.spaceXl * 2) - 16
                    spacing: Theme.spaceMd

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceMd

                        Rectangle {
                            width: 36
                            height: 36
                            radius: Theme.radiusMd
                            color: Qt.rgba(0.08, 0.72, 0.65, 0.15)
                            border.color: Theme.accent
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "💾"
                                font.pixelSize: 18
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                text: ThemeCtrl.presetSaveDialogMode === "overwrite" ? "Update Theme Preset" : "Save New Theme Preset"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeLg
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                            }

                            Text {
                                text: ThemeCtrl.presetSaveDialogMode === "overwrite"
                                    ? "Confirm updating preset '" + ThemeCtrl.currentPresetName + "' with current draft values."
                                    : "Enter a unique name for your custom theme preset."
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.textSecondary
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.borderSubtle
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Text {
                            text: "Preset Name:"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            font.weight: Font.DemiBold
                            color: Theme.textMuted
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 38
                            radius: Theme.radiusMd
                            color: Theme.inputBg
                            border.color: presetNameInput.activeFocus ? Theme.accent : Theme.border
                            border.width: 1

                            TextInput {
                                id: presetNameInput
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                verticalAlignment: TextInput.AlignVCenter
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeBase
                                color: Theme.textPrimary
                                text: ThemeCtrl.presetSaveDialogMode === "overwrite" ? ThemeCtrl.currentPresetName : (ThemeCtrl.isDraftModified ? ThemeCtrl.currentPresetName + " Copy" : "")
                                selectByMouse: true
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
                            onClicked: ThemeCtrl.cancelSavePreset()
                        }

                        PFButton {
                            text: ThemeCtrl.presetSaveDialogMode === "overwrite" ? "Confirm Update" : "Save Preset"
                            variant: "primary"
                            size: "md"
                            onClicked: {
                                var isOverwrite = ThemeCtrl.presetSaveDialogMode === "overwrite"
                                ThemeCtrl.confirmSavePreset(presetNameInput.text, isOverwrite)
                            }
                        }
                    }
                }
            }
        }
    }

    // ==========================================
    // DELETE PRESET CONFIRMATION MODAL OVERLAY
    // ==========================================
    Rectangle {
        id: presetDeleteModalOverlay
        anchors.fill: parent
        visible: ThemeCtrl.showPresetDeleteDialog
        color: Qt.rgba(0, 0, 0, 0.65)
        z: 98

        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }

        PFCard {
            id: presetDeleteCard
            anchors.centerIn: parent
            width: Math.min(presetDeleteModalOverlay.width - 48, 480)
            height: Math.min(presetDeleteCol.implicitHeight + (Theme.spaceXl * 2), presetDeleteModalOverlay.height - 48)

            MouseArea {
                anchors.fill: parent
            }

            ScrollView {
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                clip: true

                ColumnLayout {
                    id: presetDeleteCol
                    width: presetDeleteCard.width - (Theme.spaceXl * 2) - 16
                    spacing: Theme.spaceMd

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceMd

                        Rectangle {
                            width: 36
                            height: 36
                            radius: Theme.radiusMd
                            color: Qt.rgba(0.94, 0.27, 0.27, 0.15)
                            border.color: Theme.danger
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "🗑"
                                font.pixelSize: 18
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                text: "Delete Theme Preset"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeLg
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                            }

                            Text {
                                text: "Are you sure you want to permanently delete preset '" + ThemeCtrl.deleteTargetPresetName + "'? This action cannot be undone."
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.textSecondary
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.borderSubtle
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: Theme.spaceSm
                        spacing: Theme.spaceMd

                        Item { Layout.fillWidth: true }

                        PFButton {
                            text: "Cancel"
                            variant: "secondary"
                            size: "md"
                            onClicked: ThemeCtrl.cancelDeletePreset()
                        }

                        PFButton {
                            text: "Delete Preset"
                            variant: "danger"
                            size: "md"
                            onClicked: ThemeCtrl.confirmDeletePreset()
                        }
                    }
                }
            }
        }
    }

    // ==========================================
    // CONFIRMATION DIALOG MODAL OVERLAY (KDE APPLY)
    // ==========================================
    Rectangle {
        id: confirmModalOverlay
        anchors.fill: parent
        visible: ThemeCtrl.showConfirmDialog
        color: Qt.rgba(0, 0, 0, 0.65)
        z: 99

        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }

        PFCard {
            id: confirmCard
            anchors.centerIn: parent
            width: Math.min(confirmModalOverlay.width - 48, 560)
            height: Math.min(modalContentCol.implicitHeight + (Theme.spaceXl * 2), confirmModalOverlay.height - 48)

            MouseArea {
                anchors.fill: parent
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
