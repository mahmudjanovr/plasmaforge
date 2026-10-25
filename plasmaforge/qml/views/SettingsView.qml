import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import PlasmaForge.Controllers 1.0
import plasmaforge.qml.theme 1.0
import plasmaforge.qml.components 1.0

ScrollView {
    id: settingsRoot
    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        width: Math.min(settingsRoot.width - (Theme.spaceXxl * 2), 1100)
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Theme.spaceXl

        Item { height: Theme.spaceXs; Layout.fillWidth: true }

        PFSectionHeader {
            title: "Settings & Architecture Diagnostics"
            subtitle: "Manage PlasmaForge runtime parameters, safety constraints, and KDE 6 environment diagnostics"
        }

        // Safety Foundation Card
        PFCard {
            Layout.fillWidth: true
            implicitHeight: safetyCol.implicitHeight + (Theme.spaceXl * 2)

            ColumnLayout {
                id: safetyCol
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                spacing: Theme.spaceMd

                GridLayout {
                    Layout.fillWidth: true
                    columns: settingsRoot.width > 740 ? 3 : 1
                    columnSpacing: Theme.spaceMd
                    rowSpacing: Theme.spaceMd

                    Rectangle {
                        width: 36
                        height: 36
                        radius: Theme.radiusMd
                        color: SettingsCtrl.safeMode ? Qt.rgba(0.06, 0.73, 0.51, 0.15) : Qt.rgba(0.96, 0.62, 0.04, 0.15)
                        border.color: SettingsCtrl.safeMode ? Theme.success : Theme.warning
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: SettingsCtrl.safeMode ? "🛡" : "⚡"
                            font.pixelSize: 18
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        RowLayout {
                            spacing: Theme.spaceSm
                            Text {
                                text: SettingsCtrl.safeMode ? "Safe Mode (Simulation Only)" : "Live Mode (KDE Desktop Customization)"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeMd
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                            }
                            PFBadge {
                                text: SettingsCtrl.safeMode ? "PROTECTED" : "LIVE CUSTOMIZATION"
                                variant: SettingsCtrl.safeMode ? "success" : "warning"
                                size: "xs"
                            }
                        }

                        Text {
                            text: SettingsCtrl.safeMode
                                ? "All theme applications and changesets are simulated. No live ~/.config files are mutated."
                                : "Color scheme changes will be applied directly to your active KDE Plasma 6 desktop session. Automatic pre-apply backups are always created before any modification."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textSecondary
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    PFButton {
                        text: SettingsCtrl.safeMode ? "Switch to Live Mode" : "Switch to Safe Mode"
                        variant: SettingsCtrl.safeMode ? "warning" : "primary"
                        size: "md"
                        Layout.alignment: settingsRoot.width > 740 ? Qt.AlignRight : Qt.AlignLeft
                        onClicked: {
                            SettingsCtrl.setSafeMode(!SettingsCtrl.safeMode)
                        }
                    }
                }
            }
        }

        // Application Preferences Card
        PFCard {
            Layout.fillWidth: true
            implicitHeight: prefCol.implicitHeight + (Theme.spaceXl * 2)

            ColumnLayout {
                id: prefCol
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                spacing: Theme.spaceLg

                Text {
                    text: "APPLICATION PREFERENCES"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSizeXs
                    font.weight: Font.DemiBold
                    color: Theme.textMuted
                }

                // Backup Directory Row
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceLg

                    ColumnLayout {
                        Layout.preferredWidth: 260
                        spacing: 2
                        Text {
                            text: "Snapshot Storage Location"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeBase
                            color: Theme.textPrimary
                        }
                        Text {
                            text: "XDG-compliant local storage folder"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 34
                        radius: Theme.radiusMd
                        color: Theme.inputBg
                        border.color: backupDirInput.activeFocus ? Theme.borderActive : Theme.border
                        border.width: 1

                        TextInput {
                            id: backupDirInput
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            verticalAlignment: TextInput.AlignVCenter
                            text: SettingsCtrl.backupDir
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textPrimary
                            selectByMouse: true
                            onEditingFinished: SettingsCtrl.setBackupDir(text)
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                // Theme Mode Row
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceLg

                    ColumnLayout {
                        Layout.preferredWidth: 260
                        spacing: 2
                        Text {
                            text: "Studio Appearance"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeBase
                            color: Theme.textPrimary
                        }
                        Text {
                            text: "Dark-first styling with teal accents"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }
                    }

                    RowLayout {
                        spacing: Theme.spaceSm

                        PFButton {
                            text: "Dark (Default)"
                            variant: SettingsCtrl.themeMode === "dark" ? "primary" : "outline"
                            size: "sm"
                            onClicked: SettingsCtrl.setThemeMode("dark")
                        }
                        PFButton {
                            text: "System Sync"
                            variant: SettingsCtrl.themeMode === "system" ? "primary" : "outline"
                            size: "sm"
                            onClicked: SettingsCtrl.setThemeMode("system")
                        }
                    }

                    Item { Layout.fillWidth: true }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderSubtle }

                // Animations Toggle Row
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceLg

                    ColumnLayout {
                        Layout.preferredWidth: 260
                        spacing: 2
                        Text {
                            text: "UI Animations & Transitions"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeBase
                            color: Theme.textPrimary
                        }
                        Text {
                            text: "Smooth transitions for low-latency integrated GPUs"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }
                    }

                    PFButton {
                        text: SettingsCtrl.enableAnimations ? "Enabled (Smooth)" : "Reduced Motion"
                        variant: SettingsCtrl.enableAnimations ? "primary" : "outline"
                        size: "sm"
                        onClicked: SettingsCtrl.setEnableAnimations(!SettingsCtrl.enableAnimations)
                    }

                    Item { Layout.fillWidth: true }
                }
            }
        }

        // Diagnostics Card
        PFCard {
            Layout.fillWidth: true
            implicitHeight: diagCol.implicitHeight + (Theme.spaceXl * 2)

            ColumnLayout {
                id: diagCol
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                spacing: Theme.spaceMd

                Text {
                    text: "ENVIRONMENT DIAGNOSTICS & ADAPTER READINESS"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSizeXs
                    font.weight: Font.DemiBold
                    color: Theme.textMuted
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: settingsRoot.width > 680 ? 2 : 1
                    columnSpacing: Theme.spaceXl
                    rowSpacing: Theme.spaceSm

                    Text { text: "Distribution:"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSizeSm; color: Theme.textMuted }
                    Text { text: SystemCtrl.distribution; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSizeSm; color: Theme.textPrimary }

                    Text { text: "Plasma Version:"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSizeSm; color: Theme.textMuted }
                    Text { text: SystemCtrl.plasmaVersion + " (KDE 6)"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSizeSm; color: Theme.textPrimary }

                    Text { text: "Session Protocol:"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSizeSm; color: Theme.textMuted }
                    Text { text: SystemCtrl.sessionType; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSizeSm; color: Theme.accentLight }

                    Text { text: "Kernel Release:"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSizeSm; color: Theme.textMuted }
                    Text { text: SystemCtrl.kernelVersion; font.family: Theme.fontMono; font.pixelSize: Theme.fontSizeSm; color: Theme.textSecondary }

                    Text { text: "Active Look & Feel:"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSizeSm; color: Theme.textMuted }
                    Text { text: SystemCtrl.activeLookAndFeel; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSizeSm; color: Theme.textPrimary }

                    Text { text: "Hardware Graphics Target:"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSizeSm; color: Theme.textMuted }
                    Text { text: "Intel Integrated Graphics / 8 GB RAM (Optimized SceneGraph)"; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSizeSm; color: Theme.textSecondary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
            }
        }

        Item { height: Theme.spaceXl; Layout.fillWidth: true }
    }
}
