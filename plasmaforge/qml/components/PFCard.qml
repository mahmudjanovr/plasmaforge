import QtQuick
import plasmaforge.qml.theme 1.0

Rectangle {
    id: cardRoot

    property bool hoverable: false
    property bool interactive: false
    property bool active: false
    property alias hovered: mouseArea.containsMouse
    signal clicked()

    color: {
        if (active) return Qt.lighter(Theme.card, 1.1)
        if (hoverable && mouseArea.containsMouse) return Theme.cardHover
        return Theme.card
    }

    border.color: {
        if (active) return Theme.accent
        if (hoverable && mouseArea.containsMouse) return Theme.borderActive
        return Theme.border
    }
    border.width: 1
    radius: Theme.radiusLg

    Behavior on color {
        ColorAnimation { duration: Theme.animDurationFast }
    }
    Behavior on border.color {
        ColorAnimation { duration: Theme.animDurationFast }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: cardRoot.interactive || cardRoot.hoverable
        hoverEnabled: cardRoot.hoverable
        cursorShape: cardRoot.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: cardRoot.clicked()
    }
}
