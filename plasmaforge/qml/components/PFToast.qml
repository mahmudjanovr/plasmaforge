import QtQuick
import QtQuick.Layouts
import plasmaforge.qml.theme 1.0

Rectangle {
    id: toastRoot

    property string message: ""
    property string level: "info" // "info", "success", "warning", "error"
    property bool showing: false

    function show(msg, lvl) {
        toastRoot.message = msg
        toastRoot.level = lvl || "info"
        toastRoot.showing = true
        hideTimer.restart()
    }

    implicitWidth: Math.min(toastRow.implicitWidth + 32, 600)
    implicitHeight: 40
    radius: Theme.radiusMd

    color: Theme.surfaceElevated
    border.color: {
        if (level === "success") return Theme.success
        if (level === "warning") return Theme.warning
        if (level === "error") return Theme.danger
        return Theme.accent
    }
    border.width: 1

    opacity: showing ? 1.0 : 0.0
    visible: opacity > 0.0
    y: showing ? parent.height - height - Theme.spaceLg : parent.height

    Behavior on opacity {
        NumberAnimation { duration: Theme.animDurationNormal }
    }
    Behavior on y {
        NumberAnimation { duration: Theme.animDurationNormal; easing.type: Easing.OutCubic }
    }

    RowLayout {
        id: toastRow
        anchors.centerIn: parent
        spacing: Theme.spaceSm

        Text {
            text: {
                if (toastRoot.level === "success") return "✓"
                if (toastRoot.level === "warning") return "⚠"
                if (toastRoot.level === "error") return "✕"
                return "ℹ"
            }
            font.pixelSize: Theme.fontSizeSm
            color: {
                if (toastRoot.level === "success") return Theme.success
                if (toastRoot.level === "warning") return Theme.warning
                if (toastRoot.level === "error") return Theme.danger
                return Theme.accentLight
            }
        }

        Text {
            text: toastRoot.message
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSizeSm
            color: Theme.textPrimary
            elide: Text.ElideRight
            Layout.maximumWidth: 500
        }
    }

    Timer {
        id: hideTimer
        interval: 3800
        repeat: false
        onTriggered: toastRoot.showing = false
    }
}
