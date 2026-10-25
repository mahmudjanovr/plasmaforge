import QtQuick
import QtQuick.Layouts
import plasmaforge.qml.theme 1.0

PFCard {
    id: metricRoot

    property string label: ""
    property string value: ""
    property string subvalue: ""
    property string badgeText: ""
    property string badgeVariant: "neutral"

    implicitWidth: 200
    implicitHeight: 90
    hoverable: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceLg
        spacing: Theme.spaceXs

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            Text {
                text: metricRoot.label.toUpperCase()
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSizeXs
                font.weight: Font.DemiBold
                color: Theme.textMuted
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            PFBadge {
                visible: metricRoot.badgeText !== ""
                text: metricRoot.badgeText
                variant: metricRoot.badgeVariant
                size: "xs"
            }
        }

        Text {
            text: metricRoot.value
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSizeLg
            font.weight: Font.Bold
            color: Theme.textPrimary
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        Text {
            visible: metricRoot.subvalue !== ""
            text: metricRoot.subvalue
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSizeSm
            color: Theme.textSecondary
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
    }
}
