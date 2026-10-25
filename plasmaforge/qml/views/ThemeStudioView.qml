import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import PlasmaForge.Controllers 1.0
import plasmaforge.qml.theme 1.0
import plasmaforge.qml.components 1.0

ScrollView {
    id: themeStudioRoot
    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        width: Math.min(themeStudioRoot.width - (Theme.spaceXxl * 2), 1100)
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Theme.spaceXl

        Item { height: Theme.spaceXs; Layout.fillWidth: true }

        PFSectionHeader {
            title: "Theme Studio"
            subtitle: "Safe read-only inspection of installed KDE color schemes and Plasma desktop styles"

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

        // Two-column layout: Schemes list on left, Palette detail on right
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceLg

            // Left: Color Schemes list
            PFCard {
                Layout.preferredWidth: 340
                Layout.fillHeight: true
                implicitHeight: 460

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.spaceMd

                    Text {
                        text: "INSTALLED COLOR SCHEMES"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeXs
                        font.weight: Font.DemiBold
                        color: Theme.textMuted
                    }

                    ListView {
                        id: schemesList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: Theme.spaceSm
                        model: ThemeCtrl.colorSchemes

                        delegate: Rectangle {
                            width: schemesList.width
                            height: 52
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
                                    Rectangle { width: 12; height: 24; radius: 2; color: modelData.window_bg; border.color: Theme.border; border.width: 1 }
                                    Rectangle { width: 12; height: 24; radius: 2; color: modelData.selection_bg }
                                    Rectangle { width: 12; height: 24; radius: 2; color: modelData.button_bg; border.color: Theme.border; border.width: 1 }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1

                                    Text {
                                        text: modelData.name
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeBase
                                        font.weight: ThemeCtrl.selectedSchemeIndex === index ? Font.DemiBold : Font.Normal
                                        color: ThemeCtrl.selectedSchemeIndex === index ? Theme.textPrimary : Theme.textSecondary
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }

                                    Text {
                                        text: modelData.is_user_scheme ? "User Palette (~/.local)" : "System Palette (/usr)"
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

            // Right: Selected Scheme Palette Inspector
            PFCard {
                Layout.fillWidth: true
                implicitHeight: 460

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceXl
                    spacing: Theme.spaceLg

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceMd

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                text: ThemeCtrl.selectedScheme.name || "Select a Scheme"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeLg
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
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
                        height: 140
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
                                        height: 32
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
                                        width: 100
                                        height: 32
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

                    // Realistic Safety Notice
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceMd

                        Rectangle {
                            width: 6
                            Layout.fillHeight: true
                            radius: 3
                            color: Theme.accent
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                text: "Read-Only Palette Inspection Mode"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                            }
                            Text {
                                text: "Phase 1 protects your active KDE color settings from accidental modifications. Full interactive palette editing and color-scheme authoring are scheduled for Phase 2."
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
        }

        // Plasma Styles Row
        PFSectionHeader {
            title: "Plasma Styles (Desktop Themes)"
            subtitle: "Detected desktop themes governing panels, widgets, and Plasma overlays"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceLg

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
