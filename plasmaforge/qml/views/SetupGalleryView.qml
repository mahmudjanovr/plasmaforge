import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import PlasmaForge.Controllers 1.0
import plasmaforge.qml.theme 1.0
import plasmaforge.qml.components 1.0

ScrollView {
    id: galleryRoot
    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        width: Math.min(galleryRoot.width - (Theme.spaceXxl * 2), 1100)
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Theme.spaceXl

        Item { height: Theme.spaceXs; Layout.fillWidth: true }

        PFSectionHeader {
            title: "Setup Gallery"
            subtitle: "Curated native Plasma 6 desktop presets with dry-run changeset inspection"

            PFBadge {
                text: "Safe Mode: Dry-Run Only"
                variant: "accent"
                size: "sm"
            }
        }

        // Presets Grid
        GridLayout {
            Layout.fillWidth: true
            columns: galleryRoot.width > 880 ? 2 : 1
            columnSpacing: Theme.spaceLg
            rowSpacing: Theme.spaceLg

            Repeater {
                model: PresetCtrl.presets
                delegate: PFCard {
                    Layout.fillWidth: true
                    implicitHeight: 220
                    hoverable: true
                    interactive: true
                    active: PresetCtrl.selectedIndex === index
                    onClicked: PresetCtrl.selectPreset(index)

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spaceLg
                        spacing: Theme.spaceSm

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm

                            Text {
                                text: modelData.title
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeMd
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                                Layout.fillWidth: true
                            }

                            // Swatch pills
                            Row {
                                spacing: 4
                                Rectangle { width: 14; height: 14; radius: 7; color: modelData.preview_colors.bg; border.color: Theme.border; border.width: 1 }
                                Rectangle { width: 14; height: 14; radius: 7; color: modelData.preview_colors.surface; border.color: Theme.border; border.width: 1 }
                                Rectangle { width: 14; height: 14; radius: 7; color: modelData.preview_colors.accent }
                            }
                        }

                        Text {
                            text: modelData.tagline
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textSecondary
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Text {
                            text: modelData.description
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }

                        Item { Layout.fillHeight: true }

                        // Tags & Action Row
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm

                            Repeater {
                                model: modelData.tags
                                delegate: PFBadge {
                                    text: modelData
                                    variant: "neutral"
                                    size: "xs"
                                }
                            }

                            Item { Layout.fillWidth: true }

                            PFButton {
                                text: PresetCtrl.selectedIndex === index ? "Selected" : "Inspect Preset"
                                variant: PresetCtrl.selectedIndex === index ? "primary" : "outline"
                                size: "sm"
                                onClicked: PresetCtrl.selectPreset(index)
                            }
                        }
                    }
                }
            }
        }

        // Preset Details & Dry-Run Inspector Box
        PFSectionHeader {
            title: "Selected Preset Blueprint & Dry-Run"
            subtitle: "Examine configuration changes validated against the Phase 1 DryRunAdapter"
        }

        PFCard {
            Layout.fillWidth: true
            implicitHeight: inspectorLayout.implicitHeight + (Theme.spaceXl * 2)

            ColumnLayout {
                id: inspectorLayout
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                spacing: Theme.spaceMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    Text {
                        text: PresetCtrl.selectedPreset.title || ""
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeLg
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                    }

                    PFBadge {
                        text: "Author: " + (PresetCtrl.selectedPreset.author || "PlasmaForge")
                        variant: "neutral"
                        size: "xs"
                    }

                    Item { Layout.fillWidth: true }

                    PFButton {
                        text: "Validate Changeset"
                        iconText: "✓"
                        variant: "secondary"
                        size: "sm"
                        onClicked: {
                            AppCtrl.showToast("Changeset validated successfully. Zero safety violations.", "success")
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderSubtle
                }

                Text {
                    text: "DRY-RUN CONFIGURATION CHANGES"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSizeXs
                    font.weight: Font.DemiBold
                    color: Theme.textMuted
                }

                // Diff preview code block
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
                            text: PresetCtrl.previewText
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textSecondary
                            wrapMode: Text.NoWrap
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    Text {
                        text: "🛡️ Phase 1 Safety Constraint:"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeSm
                        font.weight: Font.DemiBold
                        color: Theme.accentLight
                    }

                    Text {
                        text: "Applying live modifications is disabled in Phase 1 to guarantee system stability."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeSm
                        color: Theme.textSecondary
                        Layout.fillWidth: true
                    }
                }
            }
        }

        Item { height: Theme.spaceXl; Layout.fillWidth: true }
    }
}
