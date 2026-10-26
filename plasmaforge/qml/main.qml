import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import PlasmaForge.Controllers 1.0
import plasmaforge.qml.theme 1.0
import plasmaforge.qml.components 1.0
import plasmaforge.qml.views 1.0

ApplicationWindow {
    id: appWindow
    visible: true
    width: 1100
    height: 720
    minimumWidth: 800
    minimumHeight: 560
    title: "PlasmaForge - KDE Plasma 6 Customization Studio"
    color: Theme.bg

    // Navigation sections definition
    readonly property var navSections: [
        { name: "Overview", icon: "⊞", desc: "System status & workspace summary" },
        { name: "Theme Studio", icon: "🎨", desc: "Color schemes, plasma styles & palettes" },
        { name: "Desktop Builder", icon: "📐", desc: "Panel geometry & widget workspace" },
        { name: "Setup Gallery", icon: "✨", desc: "Curated desktop presets & recipes" },
        { name: "Global Themes", icon: "🌐", desc: "KDE Store catalog & safe installation" },
        { name: "Backups & Restore", icon: "🛡", desc: "Safe configuration snapshots & diffs" },
        { name: "Settings", icon: "⚙", desc: "Runtime preferences & diagnostics" }
    ]

    Connections {
        target: AppCtrl
        function onStatusToastRequested(message, level) {
            toastNotification.show(message, level)
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ==========================================
        // PERSISTENT NAVIGATION SIDEBAR
        // ==========================================
        Rectangle {
            id: sidebar
            Layout.preferredWidth: appWindow.width < 960 ? 200 : 236
            Layout.fillHeight: true
            color: Theme.surface
            border.color: Theme.borderSubtle
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // App Branding Header
                Rectangle {
                    Layout.fillWidth: true
                    height: 68
                    color: "transparent"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spaceLg
                        anchors.rightMargin: Theme.spaceLg
                        spacing: Theme.spaceMd

                        // Brand geometric icon
                        Rectangle {
                            width: 32
                            height: 32
                            radius: Theme.radiusMd
                            color: Qt.rgba(0.08, 0.72, 0.65, 0.15)
                            border.color: Theme.accentBorder
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "✦"
                                font.pixelSize: 16
                                color: Theme.accentLight
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1

                            RowLayout {
                                spacing: 6
                                Text {
                                    text: "PlasmaForge"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSizeMd
                                    font.weight: Font.Bold
                                    color: Theme.textPrimary
                                }
                                PFBadge {
                                    text: "v" + AppCtrl.appVersion
                                    variant: "neutral"
                                    size: "xs"
                                }
                            }

                            Text {
                                text: "KDE Plasma 6 Studio"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeXs
                                color: Theme.textMuted
                            }
                        }
                    }

                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 1
                        color: Theme.borderSubtle
                    }
                }

                Item { height: Theme.spaceMd }

                // Navigation Items List
                ListView {
                    id: navList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: appWindow.navSections
                    clip: true
                    spacing: 2

                    delegate: Rectangle {
                        width: navList.width
                        height: 40
                        color: {
                            var isSelected = AppCtrl.activeSection === modelData.name
                            if (isSelected) return Qt.rgba(0.08, 0.72, 0.65, 0.12)
                            if (itemMouse.containsMouse) return Theme.cardHover
                            return "transparent"
                        }

                        Behavior on color { ColorAnimation { duration: Theme.animDurationFast } }

                        // Left active indicator strip
                        Rectangle {
                            visible: AppCtrl.activeSection === modelData.name
                            width: 3
                            height: parent.height - 8
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 2
                            radius: 1.5
                            color: Theme.accent
                        }

                        MouseArea {
                            id: itemMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: AppCtrl.navigateTo(modelData.name)
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.spaceLg
                            anchors.rightMargin: Theme.spaceMd
                            spacing: Theme.spaceMd

                            Text {
                                text: modelData.icon
                                font.pixelSize: 14
                                color: AppCtrl.activeSection === modelData.name ? Theme.accentLight : Theme.textSecondary
                            }

                            Text {
                                text: modelData.name
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeBase
                                font.weight: AppCtrl.activeSection === modelData.name ? Font.DemiBold : Font.Normal
                                color: AppCtrl.activeSection === modelData.name ? Theme.textPrimary : Theme.textSecondary
                                Layout.fillWidth: true
                            }
                        }
                    }
                }

                // Bottom Sidebar Status Box
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 76
                    color: Theme.inputBg
                    border.color: Theme.borderSubtle
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spaceMd
                        spacing: 4

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            Rectangle {
                                width: 8
                                height: 8
                                radius: 4
                                color: AppCtrl.safeMode ? Theme.success : Theme.warning
                            }

                            Text {
                                text: AppCtrl.safeMode ? "Safe Sandbox Active" : "Live Mode Active"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSizeSm
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                                Layout.fillWidth: true
                            }
                        }

                        Text {
                            text: "KDE " + SystemCtrl.plasmaVersion + " • " + SystemCtrl.sessionType
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textMuted
                        }
                    }
                }
            }
        }

        // ==========================================
        // MAIN WORKSPACE AREA
        // ==========================================
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // Topbar
            Rectangle {
                Layout.fillWidth: true
                height: 54
                color: Theme.surface
                border.color: Theme.borderSubtle
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spaceXl
                    anchors.rightMargin: Theme.spaceXl
                    spacing: Theme.spaceMd

                    Text {
                        text: AppCtrl.activeSection
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeLg
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                    }

                    Rectangle {
                        width: 1
                        height: 16
                        color: Theme.borderSubtle
                    }

                    Text {
                        text: {
                            for (var i = 0; i < appWindow.navSections.length; i++) {
                                if (appWindow.navSections[i].name === AppCtrl.activeSection) {
                                    return appWindow.navSections[i].desc
                                }
                            }
                            return ""
                        }
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeSm
                        color: Theme.textMuted
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    PFBadge {
                        text: AppCtrl.safeMode ? "Safe Mode" : "Live Mode"
                        variant: AppCtrl.safeMode ? "accent" : "warning"
                        size: "sm"
                    }

                    PFBadge {
                        text: SystemCtrl.distribution
                        variant: "neutral"
                        size: "sm"
                        visible: appWindow.width > 900
                    }
                }
            }

            // Central View Container
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                StackLayout {
                    id: viewStack
                    anchors.fill: parent
                    currentIndex: {
                        if (AppCtrl.activeSection === "Overview") return 0
                        if (AppCtrl.activeSection === "Theme Studio") return 1
                        if (AppCtrl.activeSection === "Desktop Builder") return 2
                        if (AppCtrl.activeSection === "Setup Gallery") return 3
                        if (AppCtrl.activeSection === "Global Themes") return 4
                        if (AppCtrl.activeSection === "Backups & Restore") return 5
                        if (AppCtrl.activeSection === "Settings") return 6
                        return 0
                    }

                    OverviewView {}
                    ThemeStudioView {}
                    DesktopBuilderView {}
                    SetupGalleryView {}
                    GlobalThemesView {}
                    BackupRestoreView {}
                    SettingsView {}
                }

                // Floating Non-intrusive Toast Notification
                PFToast {
                    id: toastNotification
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
        }
    }
}
