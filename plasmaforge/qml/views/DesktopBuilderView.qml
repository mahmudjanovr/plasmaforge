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
        width: Math.min(desktopBuilderRoot.width - (Theme.spaceXxl * 2), 1100)
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Theme.spaceXl

        Item { height: Theme.spaceXs; Layout.fillWidth: true }

        PFSectionHeader {
            title: "Desktop Builder"
            subtitle: "Panel geometry, widget orchestration, and multi-monitor layout blueprints"
        }

        // Blueprint Schematic Preview Card
        PFCard {
            Layout.fillWidth: true
            implicitHeight: 320

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                spacing: Theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Text {
                        text: "ACTIVE DISPLAY BLUEPRINT"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeXs
                        font.weight: Font.DemiBold
                        color: Theme.textMuted
                    }

                    Item { Layout.fillWidth: true }

                    PFBadge {
                        text: "Wayland Output: Primary"
                        variant: "neutral"
                        size: "xs"
                    }
                    PFBadge {
                        text: "Floating Panel Detected"
                        variant: "accent"
                        size: "xs"
                    }
                }

                // Schematic Canvas / Canvas Rectangle
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: Theme.radiusMd
                    color: "#0f1115"
                    border.color: Theme.borderSubtle
                    border.width: 1

                    // Screen frame representation
                    Rectangle {
                        anchors.centerIn: parent
                        width: Math.min(parent.width - 48, 640)
                        height: Math.min(parent.height - 32, 210)
                        radius: Theme.radiusSm
                        color: "#181a20"
                        border.color: Theme.borderActive
                        border.width: 1

                        // Wallpaper subtle grid
                        Grid {
                            anchors.centerIn: parent
                            columns: 4
                            spacing: 24
                            opacity: 0.15
                            Repeater {
                                model: 8
                                delegate: Rectangle {
                                    width: 48
                                    height: 32
                                    color: "transparent"
                                    border.color: Theme.accentLight
                                    border.width: 1
                                    radius: 2
                                }
                            }
                        }

                        // Floating Plasma 6 Panel Representation
                        Rectangle {
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 10
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: parent.width * 0.72
                            height: 28
                            radius: 14
                            color: Qt.rgba(0.12, 0.14, 0.18, 0.95)
                            border.color: Qt.rgba(0.08, 0.72, 0.65, 0.4)
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 8

                                // App launcher icon
                                Rectangle {
                                    width: 16
                                    height: 16
                                    radius: 8
                                    color: Theme.accent
                                }

                                Text {
                                    text: "Kickoff"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    color: Theme.textMuted
                                }

                                Item { width: 12 }

                                // Taskbar icons
                                Repeater {
                                    model: 4
                                    delegate: Rectangle {
                                        width: 16
                                        height: 16
                                        radius: 4
                                        color: Qt.rgba(1, 1, 1, 0.15)
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                // System Tray icons
                                Repeater {
                                    model: 3
                                    delegate: Rectangle {
                                        width: 12
                                        height: 12
                                        radius: 2
                                        color: Qt.rgba(1, 1, 1, 0.2)
                                    }
                                }

                                Text {
                                    text: "21:05"
                                    font.family: Theme.fontMono
                                    font.pixelSize: 10
                                    color: Theme.textSecondary
                                }
                            }
                        }
                    }
                }
            }
        }

        // Realistic Staging / Empty State Component
        PFEmptyState {
            Layout.fillWidth: true
            title: "Desktop Builder Workbench (Staging)"
            description: "Phase 1 provides architecture verification, safe backup isolation, and read-only plasma inspection. Panel injection, widget orchestrations, and dock templates will be fully operational in Phase 2 once the KDE configuration adapter achieves certified stability."
            statusTag: "Phase 1 Blueprint Mode"
            iconSymbol: "📐"

            PFButton {
                text: "View Setup Presets"
                variant: "primary"
                onClicked: AppCtrl.navigateTo("Setup Gallery")
            }

            PFButton {
                text: "Create Layout Backup"
                variant: "outline"
                onClicked: {
                    BackupCtrl.createSnapshot("Desktop Layout Backup")
                }
            }
        }

        Item { height: Theme.spaceXl; Layout.fillWidth: true }
    }
}
