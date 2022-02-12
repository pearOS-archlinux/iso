/*
*  Copyright 2020 Michail Vourlakos <mvourlakos@gmail.com>
*
*  This file is part of Latte-Dock
*
*  Latte-Dock is free software; you can redistribute it and/or
*  modify it under the terms of the GNU General Public License as
*  published by the Free Software Foundation; either version 2 of
*  the License, or (at your option) any later version.
*
*  Latte-Dock is distributed in the hope that it will be useful,
*  but WITHOUT ANY WARRANTY; without even the implied warranty of
*  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
*  GNU General Public License for more details.
*
*  You should have received a copy of the GNU General Public License
*  along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

import QtQuick 2.0
import QtQuick.Layouts 1.0
import QtQuick.Controls 1.0 as QtControls

import org.kde.plasma.plasmoid 2.0
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.plasma.components 2.0 as PlasmaComponents
import org.kde.kirigami 2.5 as Kirigami

import org.kde.kquickcontrolsaddons 2.0

Item {
    id: generalPage

    width: childrenRect.width
    height: childrenRect.height
    implicitWidth: pageColumn.implicitWidth
    implicitHeight: pageColumn.implicitHeight

    property alias cfg_iconSource: generalPage.currentIconSource
    property alias cfg_layoutName: layoutNameTxt.text
    property alias cfg_maximumIconSize: iconMaxSizeSpn.value
    property alias cfg_screenEdge: generalPage.screenEdgeCurrentValue
    property alias cfg_screenName: screenNameTxt.text

    property bool vertical: (plasmoid.formFactor === PlasmaCore.Types.Vertical)

    property int screenEdgeCurrentValue: 5 /*Left*/
    property string currentIconSource: ""

    Component.onCompleted: currentIconSource = plasmoid.configuration.iconSource

    IconDialog {
        id: iconDialog
        onIconNameChanged: currentIconSource = iconName;
    }

    PlasmaComponents.ContextMenu {
        id: iconMenu
        visualParent: iconButton

        PlasmaComponents.MenuItem {
            text: i18nc("@item:inmenu Open icon chooser dialog", "Choose...")
            icon: "document-open-folder"
            onClicked: iconDialog.open()
        }

        PlasmaComponents.MenuItem {
            text: i18nc("@item:inmenu Reset icon to default", "Clear Icon")
            icon: "edit-clear"
            onClicked: generalPage.currentIconSource = "";
        }
    }

    Kirigami.FormLayout {
        id: pageColumn
        anchors {
            left: parent.left
            right: parent.right
        }

        QtControls.Button {
            id: iconButton
            Layout.minimumWidth: units.iconSizes.large + units.smallSpacing * 2
            Layout.maximumWidth: Layout.minimumWidth
            Layout.minimumHeight: Layout.minimumWidth
            Layout.maximumHeight: Layout.minimumWidth
            height: Layout.minimumWidth

            Kirigami.FormData.label: i18n("Icon:")

            onClicked: {
                checked = Qt.binding(function() {
                    return iconMenu.status === PlasmaComponents.DialogStatus.Open;
                })

                iconMenu.open(0, height);
            }

            PlasmaCore.IconItem {
                anchors.centerIn: parent
                width: units.iconSizes.large
                height: width
                source: currentIconSource === "" ? plasmoid.icon : currentIconSource
            }
        }

        RowLayout{
            spacing: units.smallSpacing

            QtControls.SpinBox{
                id: iconMaxSizeSpn
                minimumValue: 16
                maximumValue: 256
                suffix: " " + i18nc("pixels","px.")
            }

            QtControls.Label {
                Layout.leftMargin: units.smallSpacing
                text: "maximum"
            }
        }

        Item {
            Kirigami.FormData.isSection: true
        }

        QtControls.ComboBox {
            id: iconSizeCmb
            model: [i18n("Top"),
                    i18n("Bottom"),
                    i18n("Left"),
                    i18n("Right")]

            currentIndex: plasmoid.configuration.screenEdge - screenEdgeFirstValue
            onCurrentIndexChanged: generalPage.screenEdgeCurrentValue = currentIndex + screenEdgeFirstValue

            readonly property int screenEdgeFirstValue: 3

            Kirigami.FormData.label: i18n("On Demand SideBar:")
        }

        RowLayout {
            spacing: units.smallSpacing

            QtControls.TextField {
                id: screenNameTxt
                text: plasmoid.configuration.screenName
                placeholderText: i18n("optional")
            }

            QtControls.Label {
                Layout.leftMargin: units.smallSpacing
                text: "screen name"
            }
        }

        RowLayout {
            spacing: units.smallSpacing

            QtControls.TextField {
                id: layoutNameTxt
                text: plasmoid.configuration.layoutName
                placeholderText: i18n("optional")
            }

            QtControls.Label {
                Layout.leftMargin: units.smallSpacing
                text: "layout"
            }
        }
    }


}

