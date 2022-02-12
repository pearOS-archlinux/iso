/*
 *   Copyright 2012-2013 Daniel Nicoletti <dantti12@gmail.com>
 *   Copyright 2013, 2015 Kai Uwe Broulik <kde@privat.broulik.de>
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU Library General Public License as
 *   published by the Free Software Foundation; either version 2 or
 *   (at your option) any later version.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details
 *
 *   You should have received a copy of the GNU Library General Public
 *   License along with this program; if not, write to the
 *   Free Software Foundation, Inc.,
 *   51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */

import QtQuick 2.0
import QtQuick.Layouts 1.1
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.plasma.components 2.0 as Components
import org.kde.kquickcontrolsaddons 2.0

Column {
    property alias enabled: pmCheckBox.checked

    spacing: 0

    RowLayout {
        width: parent.width
        spacing: units.gridUnit

        MouseArea {
            Layout.fillWidth: true
            height: childrenRect.height
            onClicked: {
                pmCheckBox.forceActiveFocus()
                pmCheckBox.checked = !pmCheckBox.checked
            }

            PlasmaCore.ToolTipArea {
                anchors.fill: parent
                subText: i18n("Disabling power management will prevent your screen and computer from turning off automatically.\n\nMost applications will automatically suppress power management when they don't want to have you interrupted.")
            }

            RowLayout {
                width: parent.width
                spacing: units.gridUnit

                Item {
                    width: units.iconSizes.medium
                    height: width

                    Components.CheckBox {
                        id: pmCheckBox
                        anchors.centerIn: parent
                        checked: true
                        // we don't want to mess with the checked state but still reflect that changing it might not yield the desired result
                        opacity: inhibitions.length > 0 ? 0.5 : 1
                        Behavior on opacity {
                            NumberAnimation { duration: units.longDuration }
                        }
                    }
                }

                Components.Label {
                    Layout.fillWidth: true
                    text: i18n("Enable Power Management")
                }
            }
        }

        Components.ToolButton {
            iconSource: "configure"
            onClicked: batterywidget.action_powerdevilkcm()
            tooltip: i18n("Configure Power Saving...")
            visible: batterywidget.kcmsAuthorized
        }
    }

    Column {
        anchors {
            left: parent.left
            leftMargin: units.iconSizes.medium + units.gridUnit
            right: parent.right
        }
        spacing: units.smallSpacing

        InhibitionHint {
            width: parent.width
            visible: pmSource.data["PowerDevil"] && pmSource.data["PowerDevil"]["Is Lid Present"] && !pmSource.data["PowerDevil"]["Triggers Lid Action"] ? true : false
            iconSource: "computer-laptop"
            text: i18n("Your notebook is configured not to suspend when closing the lid while an external monitor is connected.")
        }

        InhibitionHint {
            width: parent.width
            visible: inhibitions.length > 0
            iconSource: inhibitions.length > 0 ? inhibitions[0].Icon || "" : ""
            text: {
                if (inhibitions.length > 1) {
                    return i18ncp("Some Application and n others are currently suppressing PM",
                                  "%2 and %1 other application are currently suppressing power management.",
                                  "%2 and %1 other applications are currently suppressing power management.",
                                  inhibitions.length - 1, inhibitions[0].Name) // plural only works on %1
                } else if (inhibitions.length === 1) {
                    if (!inhibitions[0].Reason) {
                        return i18nc("Some Application is suppressing PM",
                                     "%1 is currently suppressing power management.", inhibitions[0].Name)
                    } else {
                        return i18nc("Some Application is suppressing PM: Reason provided by the app",
                                     "%1 is currently suppressing power management: %2", inhibitions[0].Name, inhibitions[0].Reason)
                    }
                } else {
                    return ""
                }
            }
        }
    }
}