import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import PlasmaForge.Controllers 1.0
import plasmaforge.qml.theme 1.0
import plasmaforge.qml.components 1.0

Item {
    id: storeRoot

    Component.onCompleted: {
        // Load catalog on first display if empty
        if (StoreCtrl.catalog.length === 0 && !StoreCtrl.isLoading) {
            StoreCtrl.loadCatalog()
        }
    }

    property bool showInstalledOnly: false
    property string localSearchFilter: ""

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ==========================================
        // MAIN CATALOG BROWSER (LEFT / CENTER)
        // ==========================================
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // Header & Search Toolbar
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 64
                color: Theme.surface
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spaceLg
                    anchors.rightMargin: Theme.spaceLg
                    spacing: Theme.spaceMd

                    // Search Input Field
                    Rectangle {
                        Layout.preferredWidth: Math.min(320, parent.width * 0.35)
                        implicitHeight: 36
                        color: Theme.inputBg
                        border.color: searchTextInput.activeFocus ? Theme.accent : Theme.border
                        border.width: 1
                        radius: Theme.radiusMd

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.spaceSm
                            anchors.rightMargin: Theme.spaceSm
                            spacing: Theme.spaceSm

                            Text {
                                text: "🔍"
                                font.pixelSize: 12
                                color: Theme.textMuted
                            }

                            TextInput {
                                id: searchTextInput
                                Layout.fillWidth: true
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.textPrimary
                                clip: true
                                selectByMouse: true
                                text: StoreCtrl.searchQuery

                                Text {
                                    visible: !searchTextInput.text && !searchTextInput.activeFocus
                                    text: "Search online global themes..."
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeSm
                                    color: Theme.textMuted
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                onAccepted: {
                                    StoreCtrl.search(searchTextInput.text)
                                }
                            }

                            Text {
                                visible: searchTextInput.text.length > 0
                                text: "✕"
                                font.pixelSize: 11
                                color: Theme.textMuted
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        searchTextInput.text = ""
                                        StoreCtrl.search("")
                                    }
                                }
                            }
                        }
                    }

                    PFButton {
                        text: "Search"
                        variant: "secondary"
                        size: "sm"
                        onClicked: StoreCtrl.search(searchTextInput.text)
                    }

                    Rectangle {
                        width: 1
                        height: 20
                        color: Theme.borderSubtle
                    }

                    // Sort selector buttons
                    RowLayout {
                        spacing: 2

                        PFButton {
                            text: "Popular"
                            size: "sm"
                            variant: StoreCtrl.sortMode === "down" ? "primary" : "subtle"
                            onClicked: StoreCtrl.setSortMode("down")
                        }

                        PFButton {
                            text: "Newest"
                            size: "sm"
                            variant: StoreCtrl.sortMode === "new" ? "primary" : "subtle"
                            onClicked: StoreCtrl.setSortMode("new")
                        }

                        PFButton {
                            text: "Rating"
                            size: "sm"
                            variant: StoreCtrl.sortMode === "high" ? "primary" : "subtle"
                            onClicked: StoreCtrl.setSortMode("high")
                        }
                    }

                    Item { Layout.fillWidth: true }

                    // Installed Only Toggle
                    PFButton {
                        text: storeRoot.showInstalledOnly ? "Showing Installed" : "All Themes"
                        iconText: storeRoot.showInstalledOnly ? "✓" : "📁"
                        variant: storeRoot.showInstalledOnly ? "outline" : "subtle"
                        size: "sm"
                        onClicked: {
                            storeRoot.showInstalledOnly = !storeRoot.showInstalledOnly
                            if (storeRoot.showInstalledOnly) {
                                StoreCtrl.refreshInstalledThemes()
                            }
                        }
                    }

                    // Refresh Button
                    PFButton {
                        iconText: "↻"
                        text: ""
                        variant: "secondary"
                        size: "sm"
                        enabled: !StoreCtrl.isLoading
                        onClicked: {
                            StoreCtrl.refreshInstalledThemes()
                            StoreCtrl.loadCatalog()
                        }
                    }
                }
            }

            // Status Bar / Result counter
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 32
                color: Theme.surfaceElevated
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spaceLg
                    anchors.rightMargin: Theme.spaceLg
                    spacing: Theme.spaceMd

                    Text {
                        text: {
                            if (storeRoot.showInstalledOnly) {
                                return "Installed Themes (" + StoreCtrl.installedThemes.length + ")"
                            }
                            if (StoreCtrl.isLoading) {
                                return "Querying KDE Store catalog..."
                            }
                            return "KDE Store: " + StoreCtrl.totalItems + " themes available (Page " + StoreCtrl.currentPage + ")"
                        }
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeXs
                        color: Theme.textSecondary
                    }

                    Item { Layout.fillWidth: true }

                    // Pagination Controls (visible when browsing store catalog)
                    RowLayout {
                        visible: !storeRoot.showInstalledOnly && StoreCtrl.catalog.length > 0
                        spacing: 4

                        PFButton {
                            text: "‹ Prev"
                            size: "sm"
                            variant: "subtle"
                            enabled: StoreCtrl.currentPage > 1 && !StoreCtrl.isLoading
                            onClicked: StoreCtrl.previousPage()
                        }

                        Text {
                            text: "Page " + StoreCtrl.currentPage
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textPrimary
                        }

                        PFButton {
                            text: "Next ›"
                            size: "sm"
                            variant: "subtle"
                            enabled: StoreCtrl.hasMore && !StoreCtrl.isLoading
                            onClicked: StoreCtrl.nextPage()
                        }
                    }
                }
            }

            // Download Progress Banner (visible during active download)
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: StoreCtrl.isDownloading ? 50 : 0
                visible: StoreCtrl.isDownloading
                clip: true
                color: Qt.rgba(0.08, 0.72, 0.65, 0.12)
                border.color: Theme.accentBorder
                border.width: 1

                Behavior on implicitHeight { NumberAnimation { duration: Theme.animDurationNormal } }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spaceLg
                    anchors.rightMargin: Theme.spaceLg
                    spacing: Theme.spaceMd

                    Text {
                        text: "⬇"
                        font.pixelSize: 16
                        color: Theme.accentLight
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: StoreCtrl.downloadStatus
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            Text {
                                text: Math.round(StoreCtrl.downloadPercent) + "%"
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.accentLight
                            }
                        }

                        // Progress Bar Track
                        Rectangle {
                            Layout.fillWidth: true
                            height: 4
                            radius: 2
                            color: Theme.card

                            Rectangle {
                                width: parent.width * (Math.max(0, Math.min(100, StoreCtrl.downloadPercent)) / 100.0)
                                height: parent.height
                                radius: 2
                                color: Theme.accent
                            }
                        }
                    }

                    PFButton {
                        text: "Cancel"
                        variant: "danger"
                        size: "sm"
                        onClicked: StoreCtrl.cancelDownload()
                    }
                }
            }

            // Content Area: Grid / Empty / Loading / Error
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                // 1. Loading State
                ColumnLayout {
                    anchors.centerIn: parent
                    visible: StoreCtrl.isLoading && StoreCtrl.catalog.length === 0
                    spacing: Theme.spaceMd

                    ProgressBar {
                        indeterminate: true
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: 200
                    }

                    Text {
                        text: "Loading KDE Global Themes catalog..."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeSm
                        color: Theme.textSecondary
                        Layout.alignment: Qt.AlignHCenter
                    }
                }

                // 2. Error / Offline State
                PFEmptyState {
                    anchors.centerIn: parent
                    visible: StoreCtrl.errorMessage.length > 0 && !StoreCtrl.isLoading && StoreCtrl.catalog.length === 0
                    title: "Could Not Reach KDE Store"
                    description: StoreCtrl.errorMessage + "\n\nPlease check your internet connection or try again."
                    statusTag: "Network Offline"
                    iconSymbol: "⚠"

                    PFButton {
                        text: "Retry Connection"
                        iconText: "↻"
                        variant: "primary"
                        size: "md"
                        onClicked: StoreCtrl.loadCatalog()
                    }
                }

                // 3. Empty Search Results
                PFEmptyState {
                    anchors.centerIn: parent
                    visible: !StoreCtrl.isLoading && StoreCtrl.errorMessage.length === 0 && (
                        (!storeRoot.showInstalledOnly && StoreCtrl.catalog.length === 0) ||
                        (storeRoot.showInstalledOnly && StoreCtrl.installedThemes.length === 0)
                    )
                    title: storeRoot.showInstalledOnly ? "No Installed Global Themes" : "No Matching Themes"
                    description: storeRoot.showInstalledOnly
                        ? "You have no custom Look and Feel packages installed in ~/.local/share/plasma/look-and-feel."
                        : "No themes matched your search query. Try different keywords or reset search."
                    statusTag: storeRoot.showInstalledOnly ? "Clean Environment" : "0 Results"
                    iconSymbol: "🔍"

                    PFButton {
                        visible: StoreCtrl.searchQuery.length > 0
                        text: "Clear Search"
                        variant: "secondary"
                        size: "md"
                        onClicked: {
                            searchTextInput.text = ""
                            StoreCtrl.search("")
                        }
                    }
                }

                // 4. Grid of Themes (Online or Installed)
                ScrollView {
                    id: catalogScrollView
                    anchors.fill: parent
                    visible: (storeRoot.showInstalledOnly ? StoreCtrl.installedThemes.length > 0 : StoreCtrl.catalog.length > 0)
                    contentWidth: availableWidth
                    clip: true

                    GridView {
                        id: themeGrid
                        anchors.fill: parent
                        anchors.margins: Theme.spaceLg
                        cellWidth: Math.max(240, Math.floor((width - Theme.spaceLg * 2) / Math.max(1, Math.floor((width - Theme.spaceLg * 2) / 250))))
                        cellHeight: 250
                        clip: true

                        model: storeRoot.showInstalledOnly ? StoreCtrl.installedThemes : StoreCtrl.catalog

                        delegate: Item {
                            width: themeGrid.cellWidth
                            height: themeGrid.cellHeight

                            PFCard {
                                anchors.fill: parent
                                anchors.margins: Theme.spaceSm
                                hoverable: true
                                interactive: true
                                active: {
                                    if (storeRoot.showInstalledOnly) {
                                        return StoreCtrl.selectedTheme && StoreCtrl.selectedTheme.id === modelData.id
                                    }
                                    return StoreCtrl.selectedIndex === index
                                }

                                onClicked: {
                                    if (storeRoot.showInstalledOnly) {
                                        StoreCtrl.requestApplyTheme(modelData.id)
                                    } else {
                                        StoreCtrl.selectTheme(index)
                                    }
                                }

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: Theme.spaceMd
                                    spacing: Theme.spaceSm

                                    // Thumbnail Container
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 120
                                        radius: Theme.radiusMd
                                        color: Theme.surfaceElevated
                                        clip: true

                                        Image {
                                            anchors.fill: parent
                                            source: modelData.preview_url ? modelData.preview_url : ""
                                            fillMode: Image.PreserveAspectCrop
                                            asynchronous: true
                                            visible: status === Image.Ready

                                            Rectangle {
                                                anchors.fill: parent
                                                color: Qt.rgba(0, 0, 0, 0.15)
                                            }
                                        }

                                        // Fallback icon placeholder if image loading or unavailable
                                        ColumnLayout {
                                            anchors.centerIn: parent
                                            spacing: 4
                                            visible: !modelData.preview_url || imgLoader.status !== Image.Ready

                                            Text {
                                                Layout.alignment: Qt.AlignHCenter
                                                text: "🎨"
                                                font.pixelSize: 28
                                                color: Theme.accentLight
                                            }
                                            Text {
                                                Layout.alignment: Qt.AlignHCenter
                                                text: "Global Theme"
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontSizeXs
                                                color: Theme.textMuted
                                            }
                                        }

                                        Image {
                                            id: imgLoader
                                            source: modelData.preview_url || ""
                                            visible: false
                                        }

                                        // Floating Status Badges
                                        RowLayout {
                                            anchors.top: parent.top
                                            anchors.right: parent.right
                                            anchors.margins: 6
                                            spacing: 4

                                            PFBadge {
                                                visible: Boolean(modelData.is_active)
                                                text: "Active"
                                                variant: "accent"
                                                size: "xs"
                                            }

                                            PFBadge {
                                                visible: Boolean(modelData.is_installed) && !modelData.is_active
                                                text: "Installed"
                                                variant: "success"
                                                size: "xs"
                                            }

                                            PFBadge {
                                                visible: Boolean(modelData.has_update)
                                                text: "Update"
                                                variant: "warning"
                                                size: "xs"
                                            }
                                        }
                                    }

                                    // Title & Author
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1

                                        Text {
                                            text: modelData.name || modelData.id
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontSizeSm
                                            font.weight: Font.DemiBold
                                            color: Theme.textPrimary
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }

                                        Text {
                                            text: "by " + (modelData.author || "KDE Community") + (modelData.version ? " • v" + modelData.version : "")
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontSizeXs
                                            color: Theme.textSecondary
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }
                                    }

                                    Item { Layout.fillHeight: true }

                                    // Card Footer: Stats & Action
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: Theme.spaceSm

                                        Text {
                                            visible: Boolean(modelData.downloads)
                                            text: "⬇ " + modelData.downloads
                                            font.family: Theme.fontMono
                                            font.pixelSize: Theme.fontSizeXs
                                            color: Theme.textMuted
                                        }

                                        Text {
                                            visible: Boolean(modelData.score)
                                            text: "★ " + modelData.score + "%"
                                            font.family: Theme.fontMono
                                            font.pixelSize: Theme.fontSizeXs
                                            color: Theme.accentLight
                                        }

                                        Item { Layout.fillWidth: true }

                                        // Quick Action Button
                                        PFButton {
                                            text: {
                                                if (modelData.is_installed) return "Apply"
                                                return "Install"
                                            }
                                            variant: modelData.is_installed ? "primary" : "secondary"
                                            size: "sm"
                                            onClicked: {
                                                if (modelData.is_installed) {
                                                    StoreCtrl.requestApplyTheme(modelData.id)
                                                } else {
                                                    StoreCtrl.startInstallTheme(modelData.id)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // ==========================================
        // DETAIL INSPECTOR SIDEBAR (RIGHT)
        // ==========================================
        Rectangle {
            id: detailPane
            Layout.preferredWidth: storeRoot.width < 960 ? 280 : 360
            Layout.fillHeight: true
            color: Theme.surface
            border.color: Theme.borderSubtle
            border.width: 1

            ScrollView {
                anchors.fill: parent
                contentWidth: availableWidth
                clip: true

                ColumnLayout {
                    width: detailPane.width - (Theme.spaceLg * 2)
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: Theme.spaceLg
                    spacing: Theme.spaceLg

                    // Header: Selected Theme Title & Version
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceXs

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm

                            Text {
                                text: StoreCtrl.selectedTheme.name || "Select a Theme"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeLg
                                font.weight: Font.Bold
                                color: Theme.textPrimary
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            PFBadge {
                                visible: Boolean(StoreCtrl.selectedTheme.is_active)
                                text: "Active"
                                variant: "accent"
                                size: "xs"
                            }
                            PFBadge {
                                visible: Boolean(StoreCtrl.selectedTheme.is_installed) && !StoreCtrl.selectedTheme.is_active
                                text: "Installed"
                                variant: "success"
                                size: "xs"
                            }
                        }

                        Text {
                            text: "Author: " + (StoreCtrl.selectedTheme.author || "KDE Community") +
                                  (StoreCtrl.selectedTheme.version ? " • Version: " + StoreCtrl.selectedTheme.version : "")
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }
                    }

                    // Preview Hero Image
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 180
                        radius: Theme.radiusMd
                        color: Theme.surfaceElevated
                        clip: true

                        Image {
                            anchors.fill: parent
                            source: StoreCtrl.selectedTheme.preview_url || ""
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                            visible: status === Image.Ready
                        }

                        Text {
                            anchors.centerIn: parent
                            text: "No Preview Available"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textMuted
                            visible: !StoreCtrl.selectedTheme.preview_url
                        }
                    }

                    // Primary Action Buttons
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        PFButton {
                            Layout.fillWidth: true
                            visible: Boolean(StoreCtrl.selectedTheme.is_installed)
                            text: "Apply Global Theme"
                            iconText: "✦"
                            variant: "primary"
                            size: "md"
                            enabled: !StoreCtrl.isApplying
                            onClicked: {
                                StoreCtrl.requestApplyTheme(StoreCtrl.selectedTheme.installed_id || StoreCtrl.selectedTheme.id)
                            }
                        }

                        PFButton {
                            Layout.fillWidth: true
                            visible: !StoreCtrl.selectedTheme.is_installed && Boolean(StoreCtrl.selectedTheme.id)
                            text: "Download & Install"
                            iconText: "⬇"
                            variant: "primary"
                            size: "md"
                            enabled: !StoreCtrl.isDownloading
                            onClicked: {
                                StoreCtrl.startInstallTheme(StoreCtrl.selectedTheme.id)
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm

                            PFButton {
                                Layout.fillWidth: true
                                visible: Boolean(StoreCtrl.selectedTheme.is_installed)
                                text: "Reinstall"
                                iconText: "↻"
                                variant: "secondary"
                                size: "sm"
                                enabled: !StoreCtrl.isDownloading
                                onClicked: {
                                    StoreCtrl.startInstallTheme(StoreCtrl.selectedTheme.id)
                                }
                            }

                            PFButton {
                                Layout.fillWidth: true
                                visible: Boolean(StoreCtrl.selectedTheme.is_installed) && Boolean(StoreCtrl.selectedTheme.installed_id)
                                text: "Uninstall"
                                iconText: "🗑"
                                variant: "danger"
                                size: "sm"
                                onClicked: {
                                    StoreCtrl.uninstallTheme(StoreCtrl.selectedTheme.installed_id)
                                }
                            }
                        }
                    }

                    // Theme Metadata Stats
                    PFCard {
                        Layout.fillWidth: true
                        implicitHeight: metaGrid.implicitHeight + (Theme.spaceMd * 2)

                        GridLayout {
                            id: metaGrid
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
                            columns: 2
                            columnSpacing: Theme.spaceMd
                            rowSpacing: Theme.spaceSm

                            Text { text: "KDE Store ID:"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                            Text { text: StoreCtrl.selectedTheme.id || "N/A"; font.pixelSize: Theme.fontSizeXs; color: Theme.textPrimary; font.family: Theme.fontMono }

                            Text { text: "Downloads:"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                            Text { text: StoreCtrl.selectedTheme.downloads ? StoreCtrl.selectedTheme.downloads.toLocaleString() : "N/A"; font.pixelSize: Theme.fontSizeXs; color: Theme.textPrimary }

                            Text { text: "User Rating:"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                            Text { text: StoreCtrl.selectedTheme.score ? StoreCtrl.selectedTheme.score + "%" : "N/A"; font.pixelSize: Theme.fontSizeXs; color: Theme.accentLight }

                            Text { text: "Download Size:"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                            Text { text: StoreCtrl.selectedTheme.primary_download_size_kb ? StoreCtrl.selectedTheme.primary_download_size_kb + " KB" : "N/A"; font.pixelSize: Theme.fontSizeXs; color: Theme.textPrimary }

                            Text { text: "KDE Store Page:"; font.pixelSize: Theme.fontSizeXs; color: Theme.textMuted }
                            Text {
                                text: "store.kde.org ↗"
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.info
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (StoreCtrl.selectedTheme.detail_url) {
                                            Qt.openUrlExternally(StoreCtrl.selectedTheme.detail_url)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Theme Description
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceXs

                        Text {
                            text: "Description"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                        }

                        Text {
                            Layout.fillWidth: true
                            text: StoreCtrl.selectedTheme.description || StoreCtrl.selectedTheme.summary || "No description provided."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textSecondary
                            wrapMode: Text.WordWrap
                            lineHeight: 1.3
                        }
                    }

                    // Affected Components (Parsed from defaults)
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceXs
                        visible: Boolean(StoreCtrl.selectedTheme && StoreCtrl.selectedTheme.components && Object.keys(StoreCtrl.selectedTheme.components).length > 0)

                        Text {
                            text: "Packaged Components"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeSm
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                        }

                        Repeater {
                            model: (StoreCtrl.selectedTheme && StoreCtrl.selectedTheme.components) ? Object.keys(StoreCtrl.selectedTheme.components) : []

                            delegate: RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spaceSm

                                Text {
                                    text: "• " + modelData + ":"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeXs
                                    color: Theme.textMuted
                                    Layout.preferredWidth: 120
                                }

                                Text {
                                    text: StoreCtrl.selectedTheme.components[modelData]
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSizeXs
                                    color: Theme.textPrimary
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }

                    Item { height: Theme.spaceXl; Layout.fillWidth: true }
                }
            }
        }
    }

    // ==========================================
    // TRANSACTIONAL APPLY CONFIRMATION MODAL
    // ==========================================
    Rectangle {
        id: applyConfirmModal
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.7)
        visible: StoreCtrl.showApplyConfirmDialog
        z: 99

        MouseArea {
            anchors.fill: parent
            // Prevent clicking through
        }

        PFCard {
            anchors.centerIn: parent
            width: Math.min(parent.width - 64, 620)
            implicitHeight: modalCol.implicitHeight + (Theme.spaceXl * 2)

            ColumnLayout {
                id: modalCol
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                spacing: Theme.spaceMd

                // Modal Header
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    Rectangle {
                        width: 36
                        height: 36
                        radius: Theme.radiusMd
                        color: Qt.rgba(0.08, 0.72, 0.65, 0.15)
                        border.color: Theme.accentBorder
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "✦"
                            font.pixelSize: 18
                            color: Theme.accentLight
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            text: "Apply Global Theme Confirmation"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeMd
                            font.weight: Font.Bold
                            color: Theme.textPrimary
                        }

                        Text {
                            text: "Target Package: " + StoreCtrl.confirmThemeName + " (" + StoreCtrl.confirmThemeId + ")"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textSecondary
                        }
                    }

                    PFBadge {
                        text: AppCtrl.safeMode ? "Safe Mode Simulation" : "Live Modification"
                        variant: AppCtrl.safeMode ? "accent" : "warning"
                        size: "sm"
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderSubtle
                }

                // Safety Assurance Notice
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: safetyNoticeCol.implicitHeight + (Theme.spaceMd * 2)
                    color: Qt.rgba(0.06, 0.72, 0.5, 0.08)
                    border.color: Theme.successMuted
                    border.width: 1
                    radius: Theme.radiusMd

                    ColumnLayout {
                        id: safetyNoticeCol
                        anchors.fill: parent
                        anchors.margins: Theme.spaceMd
                        spacing: 4

                        RowLayout {
                            spacing: 6
                            Text { text: "🛡"; font.pixelSize: 14; color: Theme.success }
                            Text {
                                text: "Transactional Safety Engine Active"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                            }
                        }

                        Text {
                            text: AppCtrl.safeMode
                                ? "Safe Mode is active. A verified snapshot simulation will be run without modifying live configuration files."
                                : "An automatic pre-apply cryptographic snapshot of all affected KDE files will be created before modifying any configuration. If application or verification fails, your previous configuration will be automatically rolled back."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textSecondary
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                // Warnings section (if any third-party dependencies are unverified)
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    visible: StoreCtrl.confirmWarnings.length > 0

                    Text {
                        text: "Notices & Dependency Notes:"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeXs
                        font.weight: Font.DemiBold
                        color: Theme.warning
                    }

                    Repeater {
                        model: StoreCtrl.confirmWarnings
                        delegate: Text {
                            text: "• " + modelData
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textSecondary
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                // Affected Configuration Files
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: "Affected KDE Configuration Files:"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeXs
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                    }

                    RowLayout {
                        spacing: 6
                        Repeater {
                            model: StoreCtrl.confirmAffectedFiles
                            delegate: PFBadge {
                                text: "~/.config/" + modelData
                                variant: "neutral"
                                size: "xs"
                            }
                        }
                    }
                }

                // Diff / Impact preview preview box
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 120
                    color: Theme.inputBg
                    border.color: Theme.borderSubtle
                    border.width: 1
                    radius: Theme.radiusMd
                    clip: true

                    ScrollView {
                        anchors.fill: parent
                        anchors.margins: Theme.spaceSm

                        Text {
                            width: parent.width
                            text: StoreCtrl.currentDiffPreview
                            font.family: Theme.fontMono
                            font.pixelSize: 11
                            color: Theme.textSecondary
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                }

                // Modal Actions
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    Item { Layout.fillWidth: true }

                    PFButton {
                        text: "Cancel"
                        variant: "subtle"
                        size: "md"
                        onClicked: StoreCtrl.cancelApplyTheme()
                    }

                    PFButton {
                        text: AppCtrl.safeMode ? "Simulate Apply (Safe Mode)" : "Confirm & Apply Live"
                        iconText: "✦"
                        variant: "primary"
                        size: "md"
                        onClicked: StoreCtrl.confirmApplyTheme()
                    }
                }
            }
        }
    }
}
