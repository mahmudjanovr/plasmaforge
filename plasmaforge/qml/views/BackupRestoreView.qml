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
        width: Math.min(backupRoot.width - (Theme.spaceXxl * 2), 1140)
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Theme.spaceXl

        Item { height: Theme.spaceXs; Layout.fillWidth: true }

        PFSectionHeader {
            title: "Backups & Restore"
            subtitle: "Create cryptographic snapshots of KDE 6 configurations, audit diffs, and safely restore or purge backups"

            RowLayout {
                spacing: Theme.spaceSm

                PFButton {
                    text: "Refresh Snapshots"
                    iconText: "↻"
                    variant: "secondary"
                    size: "sm"
                    onClicked: {
                        BackupCtrl.refreshSnapshots()
                        AppCtrl.showToast("Snapshot registry refreshed.", "info")
                    }
                }
            }
        }

        // Snapshot Creation Card
        PFCard {
            Layout.fillWidth: true
            implicitHeight: createLayout.implicitHeight + (Theme.spaceLg * 2)

            GridLayout {
                id: createLayout
                anchors.fill: parent
                anchors.margins: Theme.spaceLg
                columns: backupRoot.width > 760 ? 3 : 1
                columnSpacing: Theme.spaceMd
                rowSpacing: Theme.spaceSm

                ColumnLayout {
                    spacing: 2
                    Layout.preferredWidth: backupRoot.width > 760 ? 240 : -1
                    Layout.fillWidth: backupRoot.width <= 760

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
                        elide: Text.ElideRight
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
                    Layout.alignment: backupRoot.width > 760 ? Qt.AlignRight : Qt.AlignLeft
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

        // Responsive Two-column Layout: Snapshots on left, Detail/Diff on right
        GridLayout {
            Layout.fillWidth: true
            columns: backupRoot.width > 900 ? 2 : 1
            columnSpacing: Theme.spaceLg
            rowSpacing: Theme.spaceLg

            // Left: Snapshots List Card
            PFCard {
                Layout.fillWidth: true
                Layout.preferredWidth: backupRoot.width > 900 ? 420 : 1
                implicitHeight: 520

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.spaceMd

                    // Header row with count badges
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        Text {
                            text: "STORED SNAPSHOTS"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            font.weight: Font.DemiBold
                            color: Theme.textMuted
                            Layout.fillWidth: true
                        }

                        PFBadge {
                            text: BackupCtrl.totalSnapshotCount + " Total"
                            variant: "neutral"
                            size: "xs"
                        }

                        PFBadge {
                            visible: BackupCtrl.searchQuery.length > 0
                            text: BackupCtrl.snapshotCount + " Found"
                            variant: "accent"
                            size: "xs"
                        }
                    }

                    // Search filter bar
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 32
                        radius: Theme.radiusMd
                        color: Theme.inputBg
                        border.color: snapSearchInput.activeFocus ? Theme.borderActive : Theme.borderSubtle
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
                                id: snapSearchInput
                                Layout.fillWidth: true
                                text: BackupCtrl.searchQuery
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.textPrimary
                                selectByMouse: true
                                verticalAlignment: TextInput.AlignVCenter
                                onTextChanged: BackupCtrl.setSearchQuery(text)

                                Text {
                                    text: "Filter snapshots by ID or note..."
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeSm
                                    color: Theme.textMuted
                                    visible: !snapSearchInput.text && !snapSearchInput.activeFocus
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            Text {
                                text: "✕"
                                font.pixelSize: 11
                                color: clearSnapSearch.containsMouse ? Theme.textPrimary : Theme.textMuted
                                visible: snapSearchInput.text.length > 0

                                MouseArea {
                                    id: clearSnapSearch
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        snapSearchInput.text = ""
                                        BackupCtrl.setSearchQuery("")
                                    }
                                }
                            }
                        }
                    }

                    // Snapshots Scrollable ListView
                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        ListView {
                            id: snapsList
                            anchors.fill: parent
                            clip: true
                            spacing: Theme.spaceSm
                            model: BackupCtrl.snapshots

                            ScrollBar.vertical: ScrollBar {
                                active: true
                                policy: ScrollBar.AsNeeded
                            }

                            delegate: Rectangle {
                                width: snapsList.width - (snapsList.contentHeight > snapsList.height ? 12 : 0)
                                height: 68
                                radius: Theme.radiusMd
                                color: BackupCtrl.selectedSnapshotId === modelData.id
                                    ? Qt.rgba(0.08, 0.72, 0.65, 0.12)
                                    : (snapMouse.containsMouse ? Theme.cardHover : Theme.surface)
                                border.color: BackupCtrl.selectedSnapshotId === modelData.id
                                    ? Theme.accent
                                    : Theme.borderSubtle
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
                                            text: (modelData.file_count || 0) + " files • " + Math.round((modelData.total_size_bytes || 0) / 1024) + " KB"
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontSizeXs
                                            color: Theme.textMuted
                                        }
                                    }

                                    // Quick Delete Icon Button on Item
                                    PFButton {
                                        iconText: "🗑"
                                        variant: "subtle"
                                        size: "sm"
                                        onClicked: BackupCtrl.requestDeleteSnapshot(modelData.id)
                                    }
                                }
                            }

                            // Empty state when no snapshots exist or match filter
                            Item {
                                visible: BackupCtrl.snapshotCount === 0
                                anchors.fill: parent

                                ColumnLayout {
                                    anchors.centerIn: parent
                                    spacing: Theme.spaceSm

                                    Text {
                                        text: BackupCtrl.totalSnapshotCount === 0 ? "No Snapshots Stored" : "No Matching Snapshots"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeBase
                                        font.weight: Font.DemiBold
                                        color: Theme.textMuted
                                        Layout.alignment: Qt.AlignHCenter
                                    }
                                    Text {
                                        text: BackupCtrl.totalSnapshotCount === 0
                                            ? "Click 'Create Snapshot' above to safely back up your KDE Plasma configuration."
                                            : "Try adjusting your search filter."
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
            }

            // Right: Selected Snapshot Detail & Dry-Run Diff Card
            PFCard {
                Layout.fillWidth: true
                implicitHeight: 520

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceXl
                    spacing: Theme.spaceMd

                    // Detail Header & Metadata
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
                                text: BackupCtrl.selectedSnapshot.description
                                    ? (BackupCtrl.selectedSnapshot.description + " • Created " + BackupCtrl.selectedSnapshot.created_at)
                                    : "No snapshot currently active."
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.textSecondary
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }
                    }

                    // Action Buttons Bar: Verify, Diff, Restore, and Delete
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

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

                        Item { Layout.fillWidth: true }

                        PFButton {
                            text: "Restore Snapshot"
                            iconText: "↩"
                            variant: "primary"
                            size: "sm"
                            enabled: BackupCtrl.selectedSnapshotId !== "" && !BackupCtrl.isRestoring
                            onClicked: BackupCtrl.requestRestoreSnapshot(BackupCtrl.selectedSnapshotId)
                        }

                        PFButton {
                            text: "Delete"
                            iconText: "🗑"
                            variant: "danger"
                            size: "sm"
                            enabled: BackupCtrl.selectedSnapshotId !== "" && !BackupCtrl.isRestoring && !BackupCtrl.isDeleting
                            onClicked: BackupCtrl.requestDeleteSnapshot(BackupCtrl.selectedSnapshotId)
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
                        text: "🛡️ Safety Guarantee: PlasmaForge Phase 3 transactional safety creates a pre-restore backup, verifies SHA256 integrity manifests, and performs post-restore verification before committing any changes."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeXs
                        color: Theme.textMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }
        }

        Item { height: Theme.spaceXxxl; Layout.fillWidth: true }
    }

    // ==========================================
    // RESTORE CONFIRMATION DIALOG MODAL OVERLAY
    // ==========================================
    Rectangle {
        id: restoreConfirmOverlay
        visible: BackupCtrl.showRestoreConfirmDialog
        anchors.fill: parent
        color: Qt.rgba(0.04, 0.05, 0.07, 0.78)
        z: 9999

        MouseArea {
            anchors.fill: parent
            onClicked: BackupCtrl.cancelRestore()
        }

        PFCard {
            id: restoreModalCard
            width: Math.min(backupRoot.width - 48, 560)
            height: Math.min(backupRoot.height - 48, 420)
            anchors.centerIn: parent
            border.color: AppCtrl.safeMode ? Theme.accent : Theme.warning
            border.width: 1

            MouseArea {
                anchors.fill: parent
                // absorb clicks inside card
            }

            ScrollView {
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                clip: true

                ColumnLayout {
                    width: restoreModalCard.width - (Theme.spaceXl * 2) - 16
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
                                text: AppCtrl.safeMode ? "🛡" : "↩"
                                font.pixelSize: 18
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                text: "Confirm Snapshot Restoration"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeLg
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                            }

                            Text {
                                text: "Target Snapshot: " + BackupCtrl.restoreTargetSnapshotId
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

                    // Warning / Info Note
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: restoreNoteCol.implicitHeight + 16
                        radius: Theme.radiusMd
                        color: AppCtrl.safeMode ? Qt.rgba(0.08, 0.72, 0.65, 0.1) : Qt.rgba(0.96, 0.62, 0.04, 0.1)
                        border.color: AppCtrl.safeMode ? Qt.rgba(0.08, 0.72, 0.65, 0.25) : Qt.rgba(0.96, 0.62, 0.04, 0.25)
                        border.width: 1

                        ColumnLayout {
                            id: restoreNoteCol
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 4

                            Text {
                                text: AppCtrl.safeMode ? "Safe Mode Simulation:" : "Live Desktop Configuration Restore:"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                font.weight: Font.DemiBold
                                color: AppCtrl.safeMode ? Theme.accentLight : Theme.warning
                            }
                            Text {
                                text: AppCtrl.safeMode
                                    ? "Safe Mode is active. A simulated restore will verify SHA256 integrity and generate diffs without modifying live files."
                                    : "PlasmaForge will automatically create a pre-restore safety snapshot before replacing live files. Post-restore SHA256 verification will confirm data integrity."
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.textSecondary
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }

                    // Metadata details
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Text {
                            text: "Description: " + BackupCtrl.restoreTargetDescription
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textPrimary
                        }
                        Text {
                            text: "Files in bundle: " + BackupCtrl.restoreTargetFileCount + " allowlisted configuration files"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }
                    }

                    Item { height: Theme.spaceSm; Layout.fillWidth: true }

                    // Modal action buttons
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceMd

                        Item { Layout.fillWidth: true }

                        PFButton {
                            text: "Cancel"
                            variant: "outline"
                            size: "md"
                            onClicked: BackupCtrl.cancelRestore()
                        }

                        PFButton {
                            text: AppCtrl.safeMode ? "Simulate Restore" : "Confirm Restore"
                            iconText: AppCtrl.safeMode ? "🛡" : "↩"
                            variant: "primary"
                            size: "md"
                            onClicked: BackupCtrl.confirmRestore()
                        }
                    }
                }
            }
        }
    }

    // ==========================================
    // DELETE CONFIRMATION DIALOG MODAL OVERLAY
    // ==========================================
    Rectangle {
        id: deleteConfirmOverlay
        visible: BackupCtrl.showDeleteConfirmDialog
        anchors.fill: parent
        color: Qt.rgba(0.04, 0.05, 0.07, 0.82)
        z: 9999

        MouseArea {
            anchors.fill: parent
            onClicked: BackupCtrl.cancelDelete()
        }

        PFCard {
            id: deleteModalCard
            width: Math.min(backupRoot.width - 48, 540)
            height: Math.min(backupRoot.height - 48, 420)
            anchors.centerIn: parent
            border.color: Theme.danger
            border.width: 1

            MouseArea {
                anchors.fill: parent
                // absorb clicks inside card
            }

            ScrollView {
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                clip: true

                ColumnLayout {
                    width: deleteModalCard.width - (Theme.spaceXl * 2) - 16
                    spacing: Theme.spaceMd

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceMd

                        Rectangle {
                            width: 36
                            height: 36
                            radius: Theme.radiusMd
                            color: Qt.rgba(0.93, 0.27, 0.27, 0.15)
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
                                text: "Permanently Delete Snapshot?"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeLg
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                            }

                            Text {
                                text: "Target: " + BackupCtrl.deleteTargetSnapshotId
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.danger
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.borderSubtle
                    }

                    // Warning Box
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: deleteWarningCol.implicitHeight + 16
                        radius: Theme.radiusMd
                        color: Qt.rgba(0.93, 0.27, 0.27, 0.1)
                        border.color: Qt.rgba(0.93, 0.27, 0.27, 0.25)
                        border.width: 1

                        ColumnLayout {
                            id: deleteWarningCol
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 4

                            Text {
                                text: "Irreversible Deletion:"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                font.weight: Font.DemiBold
                                color: Theme.danger
                            }
                            Text {
                                text: "This will permanently remove the snapshot directory, files, and manifest from ~/.local/share/plasmaforge/snapshots. This action cannot be undone."
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.textSecondary
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }

                    // Snapshot summary metadata
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Text {
                            text: "Description: " + (BackupCtrl.deleteTargetDescription || "Safe Snapshot")
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textPrimary
                        }
                        Text {
                            text: "Created: " + (BackupCtrl.deleteTargetCreatedAt || "Unknown")
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }
                        Text {
                            text: "Contents: " + BackupCtrl.deleteTargetFileCount + " files • " + BackupCtrl.deleteTargetSizeKb + " KB"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }
                    }

                    Item { height: Theme.spaceSm; Layout.fillWidth: true }

                    // Modal action buttons
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceMd

                        Item { Layout.fillWidth: true }

                        PFButton {
                            text: "Cancel"
                            variant: "outline"
                            size: "md"
                            onClicked: BackupCtrl.cancelDelete()
                        }

                        PFButton {
                            text: "Permanently Delete"
                            iconText: "🗑"
                            variant: "danger"
                            size: "md"
                            onClicked: BackupCtrl.confirmDelete()
                        }
                    }
                }
            }
        }
    }
}
