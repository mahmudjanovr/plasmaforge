import QtQuick
import plasmaforge.qml.theme 1.0

Rectangle {
    id: badgeRoot

    property string text: ""
    property string variant: "neutral" // "accent", "success", "warning", "danger", "neutral"
    property string size: "sm" // "xs", "sm", "md"

    implicitWidth: textLabel.implicitWidth + (size === "xs" ? 10 : size === "md" ? 16 : 12)
    implicitHeight: size === "xs" ? 18 : size === "md" ? 24 : 20
    radius: Theme.radiusFull

    color: {
        if (variant === "accent") return Qt.rgba(0.08, 0.72, 0.65, 0.15)
        if (variant === "success") return Qt.rgba(0.06, 0.73, 0.51, 0.15)
        if (variant === "warning") return Qt.rgba(0.96, 0.62, 0.04, 0.15)
        if (variant === "danger") return Qt.rgba(0.94, 0.27, 0.27, 0.15)
        return Qt.rgba(1, 1, 1, 0.06)
    }

    border.color: {
        if (variant === "accent") return Qt.rgba(0.08, 0.72, 0.65, 0.35)
        if (variant === "success") return Qt.rgba(0.06, 0.73, 0.51, 0.35)
        if (variant === "warning") return Qt.rgba(0.96, 0.62, 0.04, 0.35)
        if (variant === "danger") return Qt.rgba(0.94, 0.27, 0.27, 0.35)
        return Theme.borderSubtle
    }
    border.width: 1

    Text {
        id: textLabel
        anchors.centerIn: parent
        text: badgeRoot.text
        font.family: Theme.fontFamily
        font.pixelSize: badgeRoot.size === "xs" ? Theme.fontSizeXs : (badgeRoot.size === "md" ? Theme.fontSizeBase : Theme.fontSizeSm)
        font.weight: Font.DemiBold
        color: {
            if (badgeRoot.variant === "accent") return Theme.accentLight
            if (badgeRoot.variant === "success") return Theme.success
            if (badgeRoot.variant === "warning") return Theme.warning
            if (badgeRoot.variant === "danger") return Theme.danger
            return Theme.textSecondary
        }
    }
}
