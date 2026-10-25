import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import PlasmaForge.Controllers 1.0
import plasmaforge.qml.theme 1.0
import plasmaforge.qml.components 1.0

ScrollView {
    id: overviewRoot
    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        width: Math.min(overviewRoot.width - (Theme.spaceXxl * 2), 1100)
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Theme.spaceXl

        Item { height: Theme.spaceXs; Layout.fillWidth: true }

        // Hero System Status Card
        PFCard {
            Layout.fillWidth: true
            implicitHeight: heroLayout.implicitHeight + (Theme.spaceXl * 2)

            ColumnLayout {
                id: heroLayout
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                spacing: Theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    Rectangle {
                        width: 44
                        height: 44
                        radius: Theme.radiusMd
                        color: Qt.rgba(0.08, 0.72, 0.65, 0.12)
                        border.color: Theme.accentBorder
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "✦"
                            font.pixelSize: 20
                            color: Theme.accentLight
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        RowLayout {
                            spacing: Theme.spaceSm

                            Text {
                                text: "KDE Plasma 6 Customization Studio"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeLg
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                            }

                            PFBadge {
                                text: "Phase 1 Shell"
                                variant: "accent"
                                size: "xs"
                            }
                        }

                        Text {
                            text: SystemCtrl.distribution + " • Plasma " + SystemCtrl.plasmaVersion + " • " + SystemCtrl.sessionType
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textSecondary
                        }
                    }

                    PFButton {
                        text: "Create Snapshot"
                        iconText: "🛡"
                        variant: "primary"
                        size: "sm"
                        onClicked: {
                            BackupCtrl.createSnapshot("Overview Quick Snapshot")
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderSubtle
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    RowLayout {
                        spacing: 4
                        Text {
                            text: "Active Theme: "
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textMuted
                        }
                        Text {
                            text: SystemCtrl.activeLookAndFeel
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            font.weight: Font.DemiBold
                            color: Theme.accentLight
                        }
                    }

                    RowLayout {
                        spacing: 4
                        Text {
                            text: "•   UI Font: "
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textMuted
                        }
                        Text {
                            text: SystemCtrl.activeFont
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textPrimary
                        }
                    }

                    RowLayout {
                        spacing: 4
                        Text {
                            text: "•   Monospace: "
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textMuted
                        }
                        Text {
                            text: SystemCtrl.activeFixedFont
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textSecondary
                        }
                    }
                }
            }
        }

        // Metrics Grid
        GridLayout {
            Layout.fillWidth: true
            columns: overviewRoot.width > 800 ? 3 : (overviewRoot.width > 540 ? 2 : 1)
            columnSpacing: Theme.spaceLg
            rowSpacing: Theme.spaceLg

            PFMetricCard {
                Layout.fillWidth: true
                label: "Desktop Environment"
                value: "Plasma " + SystemCtrl.plasmaVersion
                subvalue: "Qt " + SystemCtrl.qtVersion + " SceneGraph"
                badgeText: SystemCtrl.sessionType
                badgeVariant: "neutral"
            }

            PFMetricCard {
                Layout.fillWidth: true
                label: "Safety Sandbox"
                value: "Active & Enforced"
                subvalue: "Zero direct writes to live configs"
                badgeText: "Safe Mode"
                badgeVariant: "success"
            }

            PFMetricCard {
                Layout.fillWidth: true
                label: "Safety Snapshots"
                value: BackupCtrl.snapshotCount + " Stored"
                subvalue: "Integrity checksum verified"
                badgeText: BackupCtrl.snapshotCount > 0 ? "Protected" : "No backups"
                badgeVariant: BackupCtrl.snapshotCount > 0 ? "accent" : "warning"
            }
        }

        // Section: Studio Modules
        PFSectionHeader {
            title: "Studio Modules"
            subtitle: "Select a module to inspect, design, or verify desktop configurations"
        }

        GridLayout {
            Layout.fillWidth: true
            columns: overviewRoot.width > 780 ? 3 : 1
            columnSpacing: Theme.spaceLg
            rowSpacing: Theme.spaceLg

            PFCard {
                Layout.fillWidth: true
                implicitHeight: 130
                hoverable: true
                interactive: true
                onClicked: AppCtrl.navigateTo("Theme Studio")

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.spaceSm

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "🎨 Theme Studio"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeMd
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                            Layout.fillWidth: true
                        }
                        PFBadge {
                            text: ThemeCtrl.colorSchemes.length + " Schemes"
                            variant: "neutral"
                            size: "xs"
                        }
                    }

                    Text {
                        text: "Inspect installed color schemes, plasma styles, and palette definitions safely."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeSm
                        color: Theme.textSecondary
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            PFCard {
                Layout.fillWidth: true
                implicitHeight: 130
                hoverable: true
                interactive: true
                onClicked: AppCtrl.navigateTo("Desktop Builder")

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.spaceSm

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "📐 Desktop Builder"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeMd
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                            Layout.fillWidth: true
                        }
                        PFBadge {
                            text: "Staging"
                            variant: "warning"
                            size: "xs"
                        }
                    }

                    Text {
                        text: "Panel layouts, floating docks, and widget arrangement workbench preview."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeSm
                        color: Theme.textSecondary
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            PFCard {
                Layout.fillWidth: true
                implicitHeight: 130
                hoverable: true
                interactive: true
                onClicked: AppCtrl.navigateTo("Setup Gallery")

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.spaceSm

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "✨ Setup Gallery"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeMd
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                            Layout.fillWidth: true
                        }
                        PFBadge {
                            text: PresetCtrl.presets.length + " Presets"
                            variant: "accent"
                            size: "xs"
                        }
                    }

                    Text {
                        text: "Curated native presets with dry-run changeset inspection and diff analysis."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeSm
                        color: Theme.textSecondary
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }
        }

        // KDE Tools Diagnostics
        PFCard {
            Layout.fillWidth: true
            implicitHeight: toolsRow.implicitHeight + (Theme.spaceLg * 2)

            Flow {
                id: toolsRow
                anchors.fill: parent
                anchors.margins: Theme.spaceLg
                spacing: Theme.spaceLg

                Text {
                    text: "KDE 6 System Binaries:"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSizeSm
                    font.weight: Font.DemiBold
                    color: Theme.textMuted
                }

                Repeater {
                    model: ["plasmashell", "kwriteconfig6", "kreadconfig6", "qdbus6"]
                    delegate: RowLayout {
                        spacing: 6
                        Rectangle {
                            width: 8
                            height: 8
                            radius: 4
                            color: SystemCtrl.toolsAvailable[modelData] ? Theme.success : Theme.warning
                        }
                        Text {
                            text: modelData
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textSecondary
                        }
                    }
                }

                Text {
                    text: "•   Arch Linux Kernel " + SystemCtrl.kernelVersion
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSizeXs
                    color: Theme.textMuted
                }
            }
        }

        Item { height: Theme.spaceXl; Layout.fillWidth: true }
    }
}
