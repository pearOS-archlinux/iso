/***************************************************************************
 *   Copyright (C) 2016 Kai Uwe Broulik <kde@privat.broulik.de>            *
 *   Copyright (C) 2016 Marco Martin <mart@kde.org>                            *
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 *   This program is distributed in the hope that it will be useful,       *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
 *   GNU General Public License for more details.                          *
 *                                                                         *
 *   You should have received a copy of the GNU General Public License     *
 *   along with this program; if not, write to the                         *
 *   Free Software Foundation, Inc.,                                       *
 *   51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA .        *
 ***************************************************************************/

import QtQuick 2.4
import QtGraphicalEffects 1.0
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.plasma.components 2.0 as PlasmaComponents

Item {
    property alias text: label.text
    property Item icon

    Rectangle {
        id: badgeRect
        anchors {
            right: parent.right
            bottom: parent.bottom
        }
        color: PlasmaCore.ColorScope.backgroundColor
        width: Math.max(units.gridUnit, label.width + units.devicePixelRatio * 2)
        height: label.height
        radius: units.devicePixelRatio * 3
        opacity: 0.9
    }

    PlasmaComponents.Label {
        id: label
        anchors.centerIn: badgeRect
        height: paintedHeight
        font.pixelSize: Math.max(icon.height/4, theme.smallestFont.pixelSize*0.8)
    }

    layer.enabled: true
    layer.effect: DropShadow {
        horizontalOffset: 0
        verticalOffset: 0
        radius: units.devicePixelRatio * 2
        samples: radius*2
        color: Qt.rgba(0, 0, 0, 0.5)
    }
}
