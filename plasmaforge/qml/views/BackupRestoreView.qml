import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import PlasmaForge.Controllers 1.0
import plasmaforge.qml.theme 1.0
import plasmaforge.qml.components 1.0

ScrollView {
    id: backupRoot
    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        width: Math.min(backupRoot.width - (Theme.spaceXxl * 2), 1100)
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Theme.spaceXl

        Item { height: Theme.spaceXs; Layout.fillWidth: true }

        PFSectionHeader {
            title: "Backups & Restore"
            subtitle: "Create cryptographic snapshots of KDE 6 configurations and perform dry-run audits"

            PFButton {
                text: "Refresh Snapshots"
                iconText: "↻"
                size: "sm"
                onClicked: {
                    BackupCtrl.refreshSnapshots()
                    AppCtrl.showToast("Snapshot registry refreshed.", "info")
                }
            }
        }

        // Snapshot Creation Card
        PFCard {
            Layout.fillWidth: true
            implicitHeight: createLayout.implicitHeight + (Theme.spaceLg * 2)

            RowLayout {
                id: createLayout
                anchors.fill: parent
                anchors.margins: Theme.spaceLg
                spacing: Theme.spaceMd

                ColumnLayout {
                    spacing: 2
                    Text {
                        text: "Create Safe Snapshot"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeBase
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                    }
                    Text {
                        text: "Copies live ~/.config plasma files with SHA256 hashes"
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
                    border.color: descInput.activeFocus ? Theme.borderActive : Theme.border
                    border.width: 1

                    TextInput {
                        id: descInput
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        verticalAlignment: TextInput.AlignVCenter
                        text: "Manual Pre-Customization Snapshot"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeSm
                        color: Theme.textPrimary
                        selectByMouse: true
                    }
                }

                PFButton {
                    text: "Create Snapshot"
                    iconText: "🛡"
                    variant: "primary"
                    size: "md"
                    onClicked: {
                        var ok = BackupCtrl.createSnapshot(descInput.text)
                        if (ok) {
                            AppCtrl.showToast("Snapshot created successfully with SHA256 manifest.", "success")
                        } else {
                            AppCtrl.showToast("Snapshot creation failed.", "error")
                        }
                    }
                }
            }
        }

        // Two-column layout: Snapshots on left, Detail/Diff on right
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceLg

            // Left: Snapshots List
            PFCard {
                Layout.preferredWidth: 380
                Layout.fillHeight: true
                implicitHeight: 460

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.spaceMd

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "STORED SNAPSHOTS"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            font.weight: Font.DemiBold
                            color: Theme.textMuted
                            Layout.fillWidth: true
                        }
                        PFBadge {
                            text: BackupCtrl.snapshotCount + " Total"
                            variant: "neutral"
                            size: "xs"
                        }
                    }

                    ListView {
                        id: snapsList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: Theme.spaceSm
                        model: BackupCtrl.snapshots

                        delegate: Rectangle {
                            width: snapsList.width
                            height: 64
                            radius: Theme.radiusMd
                            color: BackupCtrl.selectedSnapshotId === modelData.id ? Qt.rgba(0.08, 0.72, 0.65, 0.12) : (snapMouse.containsMouse ? Theme.cardHover : Theme.surface)
                            border.color: BackupCtrl.selectedSnapshotId === modelData.id ? Theme.accent : Theme.borderSubtle
                            border.width: 1

                            Behavior on color { ColorAnimation { duration: Theme.animDurationFast } }

                            MouseArea {
                                id: snapMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: BackupCtrl.selectSnapshot(modelData.id)
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: Theme.spaceMd
                                spacing: Theme.spaceSm

                                Rectangle {
                                    width: 32
                                    height: 32
                                    radius: Theme.radiusSm
                                    color: Qt.rgba(1, 1, 1, 0.05)
                                    border.color: Theme.borderSubtle
                                    border.width: 1

                                    Text {
                                        anchors.centerIn: parent
                                        text: "🛡"
                                        font.pixelSize: 14
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1

                                    Text {
                                        text: modelData.id
                                        font.family: Theme.fontMono
                                        font.pixelSize: Theme.fontSizeSm
                                        font.weight: BackupCtrl.selectedSnapshotId === modelData.id ? Font.DemiBold : Font.Normal
                                        color: BackupCtrl.selectedSnapshotId === modelData.id ? Theme.accentLight : Theme.textPrimary
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }

                                    Text {
                                        text: modelData.description || "Safe Snapshot"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeXs
                                        color: Theme.textSecondary
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }

                                    Text {
                                        text: modelData.file_count + " files • " + Math.round(modelData.total_size_bytes / 1024) + " KB"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeXs
                                        color: Theme.textMuted
                                    }
                                }
                            }
                        }

                        // Empty notice when no snapshots exist
                        Item {
                            visible: BackupCtrl.snapshotCount === 0
                            anchors.fill: parent

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: Theme.spaceSm

                                Text {
                                    text: "No Snapshots Yet"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeBase
                                    font.weight: Font.DemiBold
                                    color: Theme.textMuted
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Text {
                                    text: "Click 'Create Snapshot' above to safely back up your KDE configuration."
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeXs
                                    color: Theme.textMuted
                                    horizontalAlignment: Text.AlignHCenter
                                    wrapMode: Text.WordWrap
                                    Layout.maximumWidth: 260
                                    Layout.alignment: Qt.AlignHCenter
                                }
                            }
                        }
                    }
                }
            }

            // Right: Selected Snapshot Detail & Dry-Run Diff
            PFCard {
                Layout.fillWidth: true
                implicitHeight: 460

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceXl
                    spacing: Theme.spaceMd

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceMd

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                text: BackupCtrl.selectedSnapshotId ? ("Snapshot: " + BackupCtrl.selectedSnapshotId) : "Select a Snapshot"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeLg
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                            }

                            Text {
                                text: BackupCtrl.selectedSnapshot.description ? (BackupCtrl.selectedSnapshot.description + " • Created " + BackupCtrl.selectedSnapshot.created_at) : "No snapshot currently active."
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.textSecondary
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }

                        PFButton {
                            text: "Verify Integrity"
                            iconText: "🔍"
                            size: "sm"
                            enabled: BackupCtrl.selectedSnapshotId !== ""
                            onClicked: {
                                BackupCtrl.verifySnapshot(BackupCtrl.selectedSnapshotId)
                                AppCtrl.showToast("Cryptographic checksum verification complete.", "info")
                            }
                        }

                        PFButton {
                            text: "Dry-Run Diff"
                            iconText: "⚡"
                            variant: "outline"
                            size: "sm"
                            enabled: BackupCtrl.selectedSnapshotId !== ""
                            onClicked: {
                                BackupCtrl.dryRunRestore(BackupCtrl.selectedSnapshotId)
                                AppCtrl.showToast("Dry-run comparison against live files updated.", "info")
                            }
                        }
                    }

                    // Integrity Status Pill
                    RowLayout {
                        Layout.fillWidth: true
                        visible: BackupCtrl.integrityStatus !== ""
                        spacing: Theme.spaceSm

                        Text {
                            text: "Integrity Status:"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            font.weight: Font.DemiBold
                            color: Theme.textMuted
                        }
                        Text {
                            text: BackupCtrl.integrityStatus
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.success
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.borderSubtle
                    }

                    Text {
                        text: "LIVE CONFIGURATION COMPARISON (DRY-RUN)"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeXs
                        font.weight: Font.DemiBold
                        color: Theme.textMuted
                    }

                    // Diff view
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: Theme.radiusMd
                        color: "#0f1115"
                        border.color: Theme.borderSubtle
                        border.width: 1

                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
                            clip: true

                            Text {
                                text: BackupCtrl.diffReport || "Select a snapshot on the left to inspect differences against your live ~/.config environment."
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.textSecondary
                                wrapMode: Text.NoWrap
                            }
                        }
                    }

                    Text {
                        text: "🛡️ Safety Guarantee: Phase 1 strictly forbids destructive overwrites. Restoring configurations operates purely in dry-run comparison mode."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeXs
                        color: Theme.textMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }
        }

        Item { height: Theme.spaceXl; Layout.fillWidth: true }
    }
}
