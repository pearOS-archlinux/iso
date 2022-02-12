/*
 *  Copyright 2020 Kpple <info.kpple@gmail.com>
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  2.010-1301, USA.
 */

import QtQuick 2.2
import QtQuick.Layouts 1.1

import org.kde.plasma.plasmoid 2.0
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.plasma.components 2.0 as PlasmaComponents

Item {
    id: item

    signal clicked

    property Item highlight
    property alias text: label.text

    Layout.fillWidth: true
    height: row.height

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        onClicked: item.clicked()
        // detect the mouse on the item
        onContainsMouseChanged: {
            
            if (!highlight) {
                return
            }
            
            if (area.containsMouse) {
                highlight.parent = item
                highlight.width = item.width
                highlight.height = item.height
            }
            // if the mouse is in the area, the condition will return a bool "true" to >> highlight.visible
            highlight.visible = area.containsMouse
        }
    }

    RowLayout {
        id: row

        // set space before the text item with a empty icon
        Item {
            id: emptySpace
            Layout.minimumWidth: 1 * units.gridUnit
            Layout.maximumWidth: 1 * units.gridUnit
        }

        Item {
            height: 24
            PlasmaComponents.Label {
                id: label
                anchors.fill: parent
            }
        }
    }
}
 
