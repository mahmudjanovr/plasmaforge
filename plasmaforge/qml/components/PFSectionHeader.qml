import QtQuick
import QtQuick.Layouts
import plasmaforge.qml.theme 1.0

Item {
    id: headerRoot

    property string title: ""
    property string subtitle: ""
    default property alias actions: actionContainer.children

    Layout.fillWidth: true
    implicitHeight: headerLayout.implicitHeight

    GridLayout {
        id: headerLayout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        columns: headerRoot.width > 760 ? 2 : 1
        columnSpacing: Theme.spaceLg
        rowSpacing: Theme.spaceSm

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            Text {
                text: headerRoot.title
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSizeLg
                font.weight: Font.DemiBold
                color: Theme.textPrimary
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            Text {
                visible: headerRoot.subtitle !== ""
                text: headerRoot.subtitle
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSizeSm
                color: Theme.textSecondary
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
        }

        Flow {
            id: actionContainer
            spacing: Theme.spaceSm
            Layout.fillWidth: headerRoot.width <= 760
            Layout.alignment: headerRoot.width > 760 ? (Qt.AlignRight | Qt.AlignVCenter) : Qt.AlignLeft
        }
    }
}
