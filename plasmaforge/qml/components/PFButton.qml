import QtQuick
import QtQuick.Templates as T
import plasmaforge.qml.theme 1.0

T.Button {
    id: control

    property string variant: "secondary" // "primary", "secondary", "outline", "subtle", "ghost", "danger"
    property string size: "md" // "sm", "md", "lg"
    property string iconText: ""

    readonly property bool _isIconOnly: control.text.length <= 2 && control.iconText === ""
    implicitWidth: _isIconOnly ? implicitHeight : Math.max(contentRow.implicitWidth + (size === "sm" ? 16 : size === "lg" ? 28 : 22), 48)
    implicitHeight: size === "sm" ? 28 : size === "lg" ? 40 : 34

    HoverHandler {
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    contentItem: Row {
        id: contentRow
        anchors.centerIn: parent
        spacing: 6

        Text {
            visible: control.iconText !== ""
            text: control.iconText
            font.pixelSize: control.size === "sm" ? Theme.fontSizeSm : Theme.fontSizeBase
            color: control._textColor
            verticalAlignment: Text.AlignVCenter
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            visible: control.text !== ""
            text: control.text
            font.family: Theme.fontFamily
            font.pixelSize: control.size === "sm" ? Theme.fontSizeSm : (control.size === "lg" ? Theme.fontSizeMd : Theme.fontSizeBase)
            font.weight: control.variant === "primary" ? Font.DemiBold : Font.Normal
            color: control._textColor
            verticalAlignment: Text.AlignVCenter
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    readonly property color _textColor: {
        if (!control.enabled) return Theme.textMuted
        if (control.variant === "primary") return Theme.textOnAccent
        if (control.variant === "danger") return Theme.danger
        return Theme.textPrimary
    }

    background: Rectangle {
        implicitWidth: control.implicitWidth
        implicitHeight: control.implicitHeight
        radius: control._isIconOnly ? Theme.radiusSm : Theme.radiusMd

        color: {
            if (!control.enabled) return Theme.surfaceElevated
            if (control.variant === "primary") {
                if (control.down) return Theme.accentPressed
                if (control.hovered) return Theme.accentHover
                return Theme.accent
            }
            if (control.variant === "outline" || control.variant === "subtle" || control.variant === "ghost") {
                if (control.down) return Qt.rgba(1, 1, 1, 0.08)
                if (control.hovered) return Qt.rgba(1, 1, 1, 0.05)
                return "transparent"
            }
            if (control.variant === "danger") {
                if (control.down) return Qt.rgba(0.93, 0.27, 0.27, 0.25)
                if (control.hovered) return Qt.rgba(0.93, 0.27, 0.27, 0.15)
                return Qt.rgba(0.93, 0.27, 0.27, 0.08)
            }
            // Default "secondary"
            if (control.down) return Qt.darker(Theme.cardHover, 1.1)
            if (control.hovered) return Theme.cardHover
            return Theme.card
        }

        border.color: {
            if (!control.enabled) return Theme.borderSubtle
            if (control.variant === "primary") return "transparent"
            if (control.variant === "outline") return control.hovered ? Theme.accent : Theme.border
            if (control.variant === "subtle" || control.variant === "ghost") return "transparent"
            if (control.variant === "danger") return control.hovered ? Theme.danger : Theme.dangerMuted
            return control.hovered ? Theme.borderActive : Theme.border
        }
        border.width: 1

        Behavior on color {
            ColorAnimation { duration: Theme.animDurationFast }
        }
        Behavior on border.color {
            ColorAnimation { duration: Theme.animDurationFast }
        }
    }
}
