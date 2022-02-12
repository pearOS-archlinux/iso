/***************************************************************************
 *   Copyright 2013 Sebastian Kügler <sebas@kde.org>                       *
 *   Copyright 2014 Kai Uwe Broulik <kde@privat.broulik.de>                *
 *   Copyright 2015 Beat Küng <beat-kueng@gmx.net>                         *
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU Library General Public License as       *
 *   published by the Free Software Foundation; either version 2 of the    *
 *   License, or (at your option) any later version.                       *
 *                                                                         *
 *   This program is distributed in the hope that it will be useful,       *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
 *   GNU Library General Public License for more details.                  *
 *                                                                         *
 *   You should have received a copy of the GNU Library General Public     *
 *   License along with this program; if not, write to the                 *
 *   Free Software Foundation, Inc.,                                       *
 *   51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA .        *
 ***************************************************************************/

import QtQuick 2.0
import QtQuick.Layouts 1.1
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.plasma.components 2.0 as PlasmaComponents
import org.kde.plasma.extras 2.0 as PlasmaExtras

MouseArea {
    id: expandedRepresentation
    anchors.fill: parent

    Layout.minimumWidth: root.noPlayer ? height : plasmoid.configuration.widgetWidth
    Layout.preferredWidth: Layout.minimumWidth
    Layout.fillHeight: true

    readonly property int controlSize: height

    property bool isExpanded: plasmoid.expanded
    property var iconWidth: expandedRepresentation.controlSize * 0.8

    acceptedButtons: Qt.MidButton

    onReleased: {
        if (mouse.button == Qt.MidButton) {
            root.action_openplayer()
        }
    }

    onWheel: {
         if (wheel.angleDelta.y > 0) {
             root.volumeUp()
         } else if (wheel.angleDelta.y < 0) {
             root.volumeDown()
         }
    }

    Column {
        id: playbackItems
        width: parent.width
        height: parent.height
        Layout.fillHeight: true
        Layout.fillWidth: true
        spacing: 0

        RowLayout {
            width: parent.width
            height: parent.height

            Column {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: !root.noPlayer

                PlasmaComponents.Label {
                    id: song
                    width: parent.width
                    opacity: 0.9
                    height: parent.height / 2

                    elide: Text.ElideRight
                    text: root.track ? root.track : i18n("No media playing")
                }

                PlasmaComponents.Label {
                    id: artist
                    width: parent.width
                    opacity: 0.7
                    height: parent.height / 2

                    elide: Text.ElideRight
                    text: root.artist ? root.artist : ""
                }
            }

            Column {
                id: playerControls
                property bool enabled: !root.noPlayer && mpris2Source.data[mpris2Source.current].CanControl
                visible: !root.noPlayer

                PlasmaCore.IconItem {
                    source: "media-skip-backward"
                    width: expandedRepresentation.iconWidth
                    height: width
                    enabled: playerControls.enabled
                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.LeftButton
                        onClicked: {
                            root.previous()
                        }
                    }
                }
            }
            Column {
                visible: !root.noPlayer
                PlasmaCore.IconItem {
                    source: root.state == "playing" ? "media-playback-pause" : "media-playback-start"
                    width: expandedRepresentation.iconWidth
                    height: width
                    enabled: playerControls.enabled
                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.LeftButton
                        onClicked: {
                            root.playPause()
                        }
                    }
                }
            }
            Column {
                visible: !root.noPlayer
                PlasmaCore.IconItem {
                    source: "media-skip-forward"
                    width: expandedRepresentation.iconWidth
                    height: width
                    enabled: playerControls.enabled
                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.LeftButton
                        onClicked: {
                            root.next()
                        }
                    }
                }
            }
            Column {
                visible: root.noPlayer
                PlasmaCore.IconItem {
                    source: "media-playback-start"
                    width: expandedRepresentation.iconWidth
                    height: width
                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.LeftButton
                        onClicked: {
                            root.exec(plasmoid.configuration.startPlayerCmd+"&")
                        }
                    }
                }
            }
        }
    }

}
