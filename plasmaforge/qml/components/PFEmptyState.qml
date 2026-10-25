import QtQuick
import QtQuick.Layouts
import plasmaforge.qml.theme 1.0

PFCard {
    id: emptyRoot

    property string title: "Feature Staging"
    property string description: "This module is staged for Phase 2 implementation."
    property string statusTag: "Read-Only Preview"
    property string iconSymbol: "◫"
    default property alias actions: actionArea.children

    implicitWidth: 500
    implicitHeight: 280

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 64, 460)
        spacing: Theme.spaceMd

        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            width: 48
            height: 48
            radius: Theme.radiusLg
            color: Qt.rgba(0.08, 0.72, 0.65, 0.1)
            border.color: Qt.rgba(0.08, 0.72, 0.65, 0.25)
            border.width: 1

            Text {
                anchors.centerIn: parent
                text: emptyRoot.iconSymbol
                font.pixelSize: 22
                color: Theme.accentLight
            }
        }

        PFBadge {
            Layout.alignment: Qt.AlignHCenter
            text: emptyRoot.statusTag
            variant: "accent"
            size: "xs"
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: emptyRoot.title
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSizeLg
            font.weight: Font.DemiBold
            color: Theme.textPrimary
            horizontalAlignment: Text.AlignHCenter
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            text: emptyRoot.description
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSizeBase
            color: Theme.textSecondary
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            lineHeight: 1.3
        }

        Item {
            height: Theme.spaceXs
            Layout.fillWidth: true
        }

        RowLayout {
            id: actionArea
            Layout.alignment: Qt.AlignHCenter
            spacing: Theme.spaceMd
        }
    }
}
