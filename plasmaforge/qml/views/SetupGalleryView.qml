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

    property bool showImportModal: false
    property int importTab: 0 // 0: File Path, 1: JSON Text

    ColumnLayout {
        width: Math.min(galleryRoot.width - (Theme.spaceXxl * 2), 1140)
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Theme.spaceXl

        Item { height: Theme.spaceXs; Layout.fillWidth: true }

        // Section Header
        PFSectionHeader {
            title: "Setup Gallery"
            subtitle: "Curated desktop profiles combining verified KDE color schemes and layout blueprints"

            RowLayout {
                spacing: Theme.spaceSm

                PFButton {
                    text: "Import Profile"
                    iconText: "📥"
                    variant: "secondary"
                    size: "sm"
                    onClicked: galleryRoot.showImportModal = true
                }

                PFButton {
                    text: "Export Profile"
                    iconText: "💾"
                    variant: "outline"
                    size: "sm"
                    enabled: PresetCtrl.profiles.length > 0
                    onClicked: {
                        var ok = PresetCtrl.exportProfile("", "")
                    }
                }
            }
        }

        // Status & Safety Strip
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceMd

            PFBadge {
                text: AppCtrl.safeMode ? "Safe Mode: Stage & Draft Only" : "Live Mode"
                variant: AppCtrl.safeMode ? "accent" : "warning"
                size: "sm"
            }

            PFBadge {
                text: PresetCtrl.profiles.length + (PresetCtrl.profiles.length === 1 ? " Profile" : " Profiles")
                variant: "neutral"
                size: "sm"
            }

            PFBadge {
                text: "Schema v1 Validated"
                variant: "success"
                size: "sm"
            }

            Item { Layout.fillWidth: true }

            Text {
                text: "Profiles stage color schemes in Theme Studio and layouts in Desktop Builder without unsafe direct mutation."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSizeXs
                color: Theme.textMuted
                elide: Text.ElideRight
                Layout.maximumWidth: 500
            }
        }

        // Filters and Search Bar Card
        PFCard {
            Layout.fillWidth: true
            implicitHeight: filterCol.implicitHeight + (Theme.spaceMd * 2)

            ColumnLayout {
                id: filterCol
                anchors.fill: parent
                anchors.margins: Theme.spaceMd
                spacing: Theme.spaceMd

                GridLayout {
                    Layout.fillWidth: true
                    columns: galleryRoot.width > 760 ? 2 : 1
                    columnSpacing: Theme.spaceLg
                    rowSpacing: Theme.spaceMd

                    // Category Filter Pills
                    Flow {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm

                        Repeater {
                            model: PresetCtrl.categories
                            delegate: Rectangle {
                                id: catChip
                                implicitHeight: 28
                                implicitWidth: catText.implicitWidth + 20
                                radius: Theme.radiusFull
                                color: PresetCtrl.selectedCategory === modelData
                                    ? Qt.rgba(0.08, 0.72, 0.65, 0.18)
                                    : (catMouse.containsMouse ? Theme.cardHover : Theme.surface)
                                border.color: PresetCtrl.selectedCategory === modelData
                                    ? Theme.accent
                                    : Theme.borderSubtle
                                border.width: 1

                                Behavior on color { ColorAnimation { duration: Theme.animDurationFast } }

                                MouseArea {
                                    id: catMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: PresetCtrl.setCategory(modelData)
                                }

                                Text {
                                    id: catText
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeSm
                                    font.weight: PresetCtrl.selectedCategory === modelData ? Font.DemiBold : Font.Normal
                                    color: PresetCtrl.selectedCategory === modelData ? Theme.accentLight : Theme.textSecondary
                                }
                            }
                        }
                    }

                    // Search input field
                    Rectangle {
                        Layout.fillWidth: galleryRoot.width <= 760
                        Layout.alignment: galleryRoot.width > 760 ? Qt.AlignRight : Qt.AlignLeft
                        implicitWidth: galleryRoot.width > 760 ? 260 : -1
                        implicitHeight: 32
                        radius: Theme.radiusMd
                        color: Theme.inputBg
                        border.color: searchInput.activeFocus ? Theme.borderActive : Theme.borderSubtle
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
                                id: searchInput
                                Layout.fillWidth: true
                                text: PresetCtrl.searchQuery
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.textPrimary
                                selectByMouse: true
                                verticalAlignment: TextInput.AlignVCenter
                                onTextChanged: PresetCtrl.setSearchQuery(text)

                                Text {
                                    text: "Search profiles..."
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeSm
                                    color: Theme.textMuted
                                    visible: !searchInput.text && !searchInput.activeFocus
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            Text {
                                text: "✕"
                                font.pixelSize: 11
                                color: clearMouse.containsMouse ? Theme.textPrimary : Theme.textMuted
                                visible: searchInput.text.length > 0

                                MouseArea {
                                    id: clearMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        searchInput.text = ""
                                        PresetCtrl.setSearchQuery("")
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // Empty state when search or filter matches nothing
        PFEmptyState {
            Layout.fillWidth: true
            visible: PresetCtrl.profiles.length === 0
            title: "No Profiles Found"
            description: "No setup profiles match '" + PresetCtrl.selectedCategory + "' category or search query '" + PresetCtrl.searchQuery + "'."
            statusTag: "Filter Empty"
            iconSymbol: "🔍"

            PFButton {
                text: "Reset Filters"
                variant: "secondary"
                size: "sm"
                onClicked: {
                    PresetCtrl.setCategory("All")
                    PresetCtrl.setSearchQuery("")
                    searchInput.text = ""
                }
            }
        }

        // Split Layout: Cards Grid / List (Left) and Blueprint Detail (Right)
        GridLayout {
            Layout.fillWidth: true
            columns: galleryRoot.width > 900 ? 2 : 1
            columnSpacing: Theme.spaceLg
            rowSpacing: Theme.spaceLg
            visible: PresetCtrl.profiles.length > 0
            Layout.alignment: Qt.AlignTop

            // Left Column: Profile Cards List
            ColumnLayout {
                Layout.preferredWidth: galleryRoot.width > 900 ? 400 : -1
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: Theme.spaceMd

                Repeater {
                    model: PresetCtrl.profiles
                    delegate: PFCard {
                        Layout.fillWidth: true
                        implicitHeight: cardContent.implicitHeight + (Theme.spaceLg * 2)
                        hoverable: true
                        interactive: true
                        active: PresetCtrl.selectedIndex === index
                        onClicked: PresetCtrl.selectProfile(index)

                        ColumnLayout {
                            id: cardContent
                            anchors.fill: parent
                            anchors.margins: Theme.spaceLg
                            spacing: Theme.spaceSm

                            // Title & Badges
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spaceSm

                                Text {
                                    text: modelData.name || ""
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeMd
                                    font.weight: Font.DemiBold
                                    color: Theme.textPrimary
                                    Layout.fillWidth: true
                                }

                                PFBadge {
                                    text: modelData.category || "General"
                                    variant: "neutral"
                                    size: "xs"
                                }

                                PFBadge {
                                    visible: modelData.is_user_imported === true
                                    text: "Imported"
                                    variant: "accent"
                                    size: "xs"
                                }
                            }

                            // Tagline
                            Text {
                                text: modelData.tagline || ""
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.textSecondary
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            // Palette Swatch Row & Layout Pill
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spaceMd

                                // Swatch boxes
                                Row {
                                    spacing: 4
                                    Rectangle {
                                        width: 14; height: 14; radius: 3
                                        color: (modelData.color_scheme && modelData.color_scheme.preview_colors) ? modelData.color_scheme.preview_colors.bg : "#101214"
                                        border.color: Theme.border; border.width: 1
                                    }
                                    Rectangle {
                                        width: 14; height: 14; radius: 3
                                        color: (modelData.color_scheme && modelData.color_scheme.preview_colors) ? modelData.color_scheme.preview_colors.surface : "#181a1f"
                                        border.color: Theme.border; border.width: 1
                                    }
                                    Rectangle {
                                        width: 14; height: 14; radius: 3
                                        color: (modelData.color_scheme && modelData.color_scheme.preview_colors) ? modelData.color_scheme.preview_colors.accent : Theme.accent
                                    }
                                    Rectangle {
                                        width: 14; height: 14; radius: 3
                                        color: (modelData.color_scheme && modelData.color_scheme.preview_colors) ? modelData.color_scheme.preview_colors.text : "#f3f4f6"
                                        border.color: Theme.border; border.width: 1
                                    }
                                }

                                Text {
                                    text: (modelData.color_scheme ? modelData.color_scheme.name : "")
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeXs
                                    color: Theme.textMuted
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }

                            // Desktop Layout Badge info
                            Rectangle {
                                Layout.fillWidth: true
                                height: 22
                                radius: Theme.radiusSm
                                color: Qt.rgba(1, 1, 1, 0.03)
                                border.color: Theme.borderSubtle
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 8
                                    spacing: 6

                                    Text {
                                        text: "📐"
                                        font.pixelSize: 10
                                    }

                                    Text {
                                        text: {
                                            if (!modelData.desktop_layout) return "No layout"
                                            var dl = modelData.desktop_layout
                                            var tp = dl.top_panel ? (dl.top_panel.position + " panel (" + dl.top_panel.thickness + "px)") : "No panel"
                                            var dk = dl.dock ? (dl.dock.position + " dock (" + dl.dock.icon_size + "px)") : "No dock"
                                            return tp + " • " + dk
                                        }
                                        font.family: Theme.fontMono
                                        font.pixelSize: Theme.fontSizeXs
                                        color: Theme.textSecondary
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                }
                            }

                            // Tags Row
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                Repeater {
                                    model: modelData.tags || []
                                    delegate: PFBadge {
                                        text: modelData
                                        variant: "neutral"
                                        size: "xs"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                Text {
                                    text: PresetCtrl.selectedIndex === index ? "Selected ✓" : "View Blueprint →"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeXs
                                    font.weight: Font.DemiBold
                                    color: PresetCtrl.selectedIndex === index ? Theme.accentLight : Theme.textMuted
                                }
                            }
                        }
                    }
                }
            }

            // Right Column: Detailed Profile Blueprint & Workbench Transfer
            PFCard {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                implicitHeight: rightColContent.implicitHeight + (Theme.spaceXl * 2)

                ColumnLayout {
                    id: rightColContent
                    anchors.fill: parent
                    anchors.margins: Theme.spaceXl
                    spacing: Theme.spaceLg

                    // Blueprint Header
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceMd

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceXs

                            RowLayout {
                                spacing: Theme.spaceSm
                                Text {
                                    text: (PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.name) || "Select Profile"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeXl
                                    font.weight: Font.Bold
                                    color: Theme.textPrimary
                                }
                                PFBadge {
                                    text: "v" + ((PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.version) || "1.0.0")
                                    variant: "neutral"
                                    size: "xs"
                                }
                                PFBadge {
                                    text: (PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.category) || ""
                                    variant: "accent"
                                    size: "xs"
                                }
                            }

                            Text {
                                text: (PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.tagline) || ""
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.accentLight
                            }

                            Text {
                                text: (PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.description) || ""
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.textSecondary
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }

                    // Metadata author & tags
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceMd

                        Text {
                            text: "Author: " + ((PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.author) || "PlasmaForge")
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }

                        Item { Layout.fillWidth: true }

                        Repeater {
                            model: (PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.tags) || []
                            delegate: PFBadge {
                                text: "#" + modelData
                                variant: "neutral"
                                size: "xs"
                            }
                        }
                    }

                    // Section Divider
                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.borderSubtle
                    }

                    // Action Buttons Bar
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceMd

                        PFButton {
                            text: "Stage in Theme Studio"
                            iconText: "🎨"
                            variant: "primary"
                            size: "md"
                            onClicked: PresetCtrl.applyColorSchemeViaThemeStudio()
                        }

                        PFButton {
                            text: "Load into Desktop Builder"
                            iconText: "📐"
                            variant: "secondary"
                            size: "md"
                            onClicked: PresetCtrl.loadLayoutIntoDesktopBuilder()
                        }

                        Item { Layout.fillWidth: true }

                        PFButton {
                            text: "Export JSON"
                            iconText: "💾"
                            variant: "outline"
                            size: "sm"
                            onClicked: PresetCtrl.exportProfile("", "")
                        }
                    }

                    // SECTION 1: KDE Color Scheme Blueprint (Real Live Feature)
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: colorSchemeCol.implicitHeight + (Theme.spaceMd * 2)
                        radius: Theme.radiusMd
                        color: Theme.surface
                        border.color: Theme.borderSubtle
                        border.width: 1

                        ColumnLayout {
                            id: colorSchemeCol
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
                            spacing: Theme.spaceSm

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "1. KDE COLOR SCHEME (LIVE FEATURE)"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeXs
                                    font.weight: Font.DemiBold
                                    color: Theme.accentLight
                                    Layout.fillWidth: true
                                }
                                PFBadge {
                                    text: "Live Applicable"
                                    variant: "success"
                                    size: "xs"
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spaceMd

                                ColumnLayout {
                                    spacing: 2
                                    Text {
                                        text: (PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.color_scheme)
                                            ? PresetCtrl.selectedProfile.color_scheme.name
                                            : "Default Scheme"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeMd
                                        font.weight: Font.DemiBold
                                        color: Theme.textPrimary
                                    }
                                    Text {
                                        text: "Scheme ID: " + ((PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.color_scheme)
                                            ? PresetCtrl.selectedProfile.color_scheme.scheme_id
                                            : "default")
                                        font.family: Theme.fontMono
                                        font.pixelSize: Theme.fontSizeXs
                                        color: Theme.textMuted
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                // 4 color swatches with labels
                                RowLayout {
                                    spacing: Theme.spaceSm

                                    Repeater {
                                        model: [
                                            { label: "Background", color: (PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.color_scheme && PresetCtrl.selectedProfile.color_scheme.preview_colors) ? PresetCtrl.selectedProfile.color_scheme.preview_colors.bg : "#101214" },
                                            { label: "Surface", color: (PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.color_scheme && PresetCtrl.selectedProfile.color_scheme.preview_colors) ? PresetCtrl.selectedProfile.color_scheme.preview_colors.surface : "#181a1f" },
                                            { label: "Accent", color: (PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.color_scheme && PresetCtrl.selectedProfile.color_scheme.preview_colors) ? PresetCtrl.selectedProfile.color_scheme.preview_colors.accent : Theme.accent },
                                            { label: "Text", color: (PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.color_scheme && PresetCtrl.selectedProfile.color_scheme.preview_colors) ? PresetCtrl.selectedProfile.color_scheme.preview_colors.text : "#f3f4f6" }
                                        ]
                                        delegate: ColumnLayout {
                                            spacing: 2
                                            Layout.alignment: Qt.AlignHCenter

                                            Rectangle {
                                                width: 38
                                                height: 24
                                                radius: Theme.radiusSm
                                                color: modelData.color
                                                border.color: Theme.border
                                                border.width: 1
                                            }
                                            Text {
                                                text: modelData.label
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fontSizeXs
                                                color: Theme.textMuted
                                                horizontalAlignment: Text.AlignHCenter
                                            }
                                            Text {
                                                text: modelData.color
                                                font.family: Theme.fontMono
                                                font.pixelSize: 9
                                                color: Theme.textSecondary
                                                horizontalAlignment: Text.AlignHCenter
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // SECTION 2: Desktop Layout Blueprint (Live Feature via Builder)
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: layoutCol.implicitHeight + (Theme.spaceMd * 2)
                        radius: Theme.radiusMd
                        color: Theme.surface
                        border.color: Theme.borderSubtle
                        border.width: 1

                        ColumnLayout {
                            id: layoutCol
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
                            spacing: Theme.spaceSm

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "2. DESKTOP LAYOUT BLUEPRINT (LIVE FEATURE)"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeXs
                                    font.weight: Font.DemiBold
                                    color: Theme.accentLight
                                    Layout.fillWidth: true
                                }
                                PFBadge {
                                    text: "Live Applicable"
                                    variant: "success"
                                    size: "xs"
                                }
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 2
                                rowSpacing: Theme.spaceSm
                                columnSpacing: Theme.spaceLg

                                // Top Panel Summary Card
                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: 64
                                    radius: Theme.radiusSm
                                    color: Qt.rgba(1, 1, 1, 0.02)
                                    border.color: Theme.borderSubtle
                                    border.width: 1

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: Theme.spaceSm
                                        spacing: 2

                                        Text {
                                            text: "Top Panel Configuration"
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontSizeSm
                                            font.weight: Font.DemiBold
                                            color: Theme.textPrimary
                                        }
                                        Text {
                                            text: {
                                                if (!PresetCtrl.selectedProfile || !PresetCtrl.selectedProfile.desktop_layout) return "None"
                                                var tp = PresetCtrl.selectedProfile.desktop_layout.top_panel
                                                if (!tp) return "None"
                                                return "Position: " + tp.position + " | Height: " + tp.thickness + "px | " + tp.visibility
                                            }
                                            font.family: Theme.fontMono
                                            font.pixelSize: Theme.fontSizeXs
                                            color: Theme.textSecondary
                                        }
                                    }
                                }

                                // Dock Summary Card
                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: 64
                                    radius: Theme.radiusSm
                                    color: Qt.rgba(1, 1, 1, 0.02)
                                    border.color: Theme.borderSubtle
                                    border.width: 1

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: Theme.spaceSm
                                        spacing: 2

                                        Text {
                                            text: "Bottom Dock Configuration"
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fontSizeSm
                                            font.weight: Font.DemiBold
                                            color: Theme.textPrimary
                                        }
                                        Text {
                                            text: {
                                                if (!PresetCtrl.selectedProfile || !PresetCtrl.selectedProfile.desktop_layout) return "None"
                                                var dk = PresetCtrl.selectedProfile.desktop_layout.dock
                                                if (!dk) return "None"
                                                return "Position: " + dk.position + " | Icon: " + dk.icon_size + "px | " + dk.visibility
                                            }
                                            font.family: Theme.fontMono
                                            font.pixelSize: Theme.fontSizeXs
                                            color: Theme.textSecondary
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // SECTION 3: Simulated Features (Honest Simulation Badge)
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: simCol.implicitHeight + (Theme.spaceMd * 2)
                        radius: Theme.radiusMd
                        color: Theme.surface
                        border.color: Theme.borderSubtle
                        border.width: 1

                        ColumnLayout {
                            id: simCol
                            anchors.fill: parent
                            anchors.margins: Theme.spaceMd
                            spacing: Theme.spaceSm

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "3. ENVIRONMENT & VISUAL REFERENCE"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeXs
                                    font.weight: Font.DemiBold
                                    color: Theme.textMuted
                                    Layout.fillWidth: true
                                }
                                PFBadge {
                                    text: "Preview Only (Non-Destructive)"
                                    variant: "neutral"
                                    size: "xs"
                                }
                            }

                            Text {
                                text: "The following visual attributes provide contextual reference for this profile. PlasmaForge does not alter wallpapers, fonts, or external third-party icons to maintain system stability."
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.textMuted
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 2
                                rowSpacing: Theme.spaceSm
                                columnSpacing: Theme.spaceLg

                                ColumnLayout {
                                    spacing: 2
                                    Text {
                                        text: "Typography Reference:"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeXs
                                        color: Theme.textMuted
                                    }
                                    Text {
                                        text: (PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.simulated_features)
                                            ? (PresetCtrl.selectedProfile.simulated_features.font_family || "System Default")
                                            : "System Default"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeSm
                                        color: Theme.textSecondary
                                    }
                                }

                                ColumnLayout {
                                    spacing: 2
                                    Text {
                                        text: "Wallpaper Reference:"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeXs
                                        color: Theme.textMuted
                                    }
                                    Text {
                                        text: (PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.simulated_features)
                                            ? (PresetCtrl.selectedProfile.simulated_features.wallpaper || "Default")
                                            : "Default"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeSm
                                        color: Theme.textSecondary
                                    }
                                }

                                ColumnLayout {
                                    spacing: 2
                                    Text {
                                        text: "Widget Simulation:"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeXs
                                        color: Theme.textMuted
                                    }
                                    Text {
                                        text: (PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.simulated_features)
                                            ? (PresetCtrl.selectedProfile.simulated_features.widget_style || "Standard")
                                            : "Standard"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeSm
                                        color: Theme.textSecondary
                                    }
                                }

                                ColumnLayout {
                                    spacing: 2
                                    Text {
                                        text: "Simulation Notes:"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontSizeXs
                                        color: Theme.textMuted
                                    }
                                    Text {
                                        text: (PresetCtrl.selectedProfile && PresetCtrl.selectedProfile.simulated_features)
                                            ? (PresetCtrl.selectedProfile.simulated_features.notes || "None")
                                            : "None"
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
            }
        }

        Item { height: Theme.spaceXl; Layout.fillWidth: true }
    }

    // ==========================================
    // IMPORT PROFILE MODAL OVERLAY
    // ==========================================
    Rectangle {
        id: importModalOverlay
        anchors.fill: parent
        visible: galleryRoot.showImportModal
        color: Qt.rgba(0, 0, 0, 0.70)
        z: 99

        MouseArea {
            anchors.fill: parent
            // Prevent clicks through modal
            onClicked: {}
        }

        PFCard {
            id: importDialogCard
            anchors.centerIn: parent
            width: Math.min(galleryRoot.width - 48, 580)
            height: Math.min(importContentCol.implicitHeight + (Theme.spaceXl * 2), galleryRoot.height - 48)

            MouseArea {
                anchors.fill: parent
                // absorb clicks inside modal card
            }

            ScrollView {
                anchors.fill: parent
                anchors.margins: Theme.spaceXl
                clip: true

                ColumnLayout {
                    id: importContentCol
                    width: importDialogCard.width - (Theme.spaceXl * 2) - 16
                    spacing: Theme.spaceMd

                // Modal Header
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    Rectangle {
                        width: 32
                        height: 32
                        radius: Theme.radiusMd
                        color: Qt.rgba(0.08, 0.72, 0.65, 0.15)
                        border.color: Theme.accent
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "📥"
                            font.pixelSize: 16
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1

                        Text {
                            text: "Import Setup Profile"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeLg
                            font.weight: Font.DemiBold
                            color: Theme.textPrimary
                        }

                        Text {
                            text: "Load a verified JSON profile blueprint (schema version 1)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textSecondary
                        }
                    }

                    PFButton {
                        text: "✕"
                        variant: "ghost"
                        size: "sm"
                        onClicked: galleryRoot.showImportModal = false
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.borderSubtle
                }

                // Import Tabs
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm

                    PFButton {
                        text: "Import from File Path"
                        variant: galleryRoot.importTab === 0 ? "secondary" : "outline"
                        size: "sm"
                        onClicked: galleryRoot.importTab = 0
                    }

                    PFButton {
                        text: "Paste Raw JSON"
                        variant: galleryRoot.importTab === 1 ? "secondary" : "outline"
                        size: "sm"
                        onClicked: galleryRoot.importTab = 1
                    }
                }

                // Tab 0: File Path Input
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm
                    visible: galleryRoot.importTab === 0

                    Text {
                        text: "JSON Profile File Path:"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeSm
                        color: Theme.textSecondary
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 38
                        radius: Theme.radiusMd
                        color: Theme.inputBg
                        border.color: pathInput.activeFocus ? Theme.borderActive : Theme.borderSubtle
                        border.width: 1

                        TextInput {
                            id: pathInput
                            anchors.fill: parent
                            anchors.margins: Theme.spaceSm
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textPrimary
                            selectByMouse: true
                            verticalAlignment: TextInput.AlignVCenter
                            text: ""

                            Text {
                                text: "/path/to/profile.json"
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.textMuted
                                visible: !pathInput.text && !pathInput.activeFocus
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }
                }

                // Tab 1: Paste JSON Text
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm
                    visible: galleryRoot.importTab === 1

                    Text {
                        text: "Paste Profile JSON:"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeSm
                        color: Theme.textSecondary
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 140
                        radius: Theme.radiusMd
                        color: Theme.inputBg
                        border.color: jsonArea.activeFocus ? Theme.borderActive : Theme.borderSubtle
                        border.width: 1

                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: Theme.spaceSm
                            clip: true

                            TextArea {
                                id: jsonArea
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.textPrimary
                                selectByMouse: true
                                wrapMode: TextEdit.Wrap
                                placeholderText: '{\n  "schema_version": 1,\n  "id": "my_profile",\n  ...\n}'
                                placeholderTextColor: Theme.textMuted
                                background: null
                            }
                        }
                    }
                }

                // Security Note
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 38
                    radius: Theme.radiusSm
                    color: Qt.rgba(0.08, 0.72, 0.65, 0.08)
                    border.color: Qt.rgba(0.08, 0.72, 0.65, 0.2)
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spaceSm
                        spacing: Theme.spaceSm

                        Text {
                            text: "🛡️"
                            font.pixelSize: 12
                        }

                        Text {
                            text: "Files are strictly schema-validated. Shell commands, scripts, and executable keys are rejected."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.accentLight
                            Layout.fillWidth: true
                        }
                    }
                }

                // Dialog Buttons
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceMd

                    Item { Layout.fillWidth: true }

                    PFButton {
                        text: "Cancel"
                        variant: "outline"
                        size: "md"
                        onClicked: galleryRoot.showImportModal = false
                    }

                    PFButton {
                        text: "Import Profile"
                        iconText: "✓"
                        variant: "primary"
                        size: "md"
                        onClicked: {
                            var ok = false
                            if (galleryRoot.importTab === 0) {
                                if (pathInput.text.trim().length > 0) {
                                    ok = PresetCtrl.importProfileFile(pathInput.text.trim())
                                } else {
                                    AppCtrl.showToast("Please provide a valid file path.", "error")
                                    return
                                }
                            } else {
                                if (jsonArea.text.trim().length > 0) {
                                    ok = PresetCtrl.importProfileJson(jsonArea.text.trim())
                                } else {
                                    AppCtrl.showToast("Please paste profile JSON content.", "error")
                                    return
                                }
                            }
                            if (ok) {
                                galleryRoot.showImportModal = false
                                pathInput.text = ""
                                jsonArea.text = ""
                            }
                        }
                    }
                }
            }
        }
    }
}
}
