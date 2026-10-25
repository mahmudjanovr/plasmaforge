import QtQuick
import QtQuick.Layouts
import plasmaforge.qml.theme 1.0

Item {
    id: headerRoot

    property string title: ""
    property string subtitle: ""
    default property alias actions: actionContainer.children

    implicitWidth: parent ? parent.width : 400
    implicitHeight: 48

    RowLayout {
        anchors.fill: parent
        spacing: Theme.spaceLg

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            Text {
                text: headerRoot.title
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSizeLg
                font.weight: Font.DemiBold
                color: Theme.textPrimary
            }

            Text {
                visible: headerRoot.subtitle !== ""
                text: headerRoot.subtitle
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSizeSm
                color: Theme.textSecondary
            }
        }

        RowLayout {
            id: actionContainer
            spacing: Theme.spaceSm
        }
    }
}
