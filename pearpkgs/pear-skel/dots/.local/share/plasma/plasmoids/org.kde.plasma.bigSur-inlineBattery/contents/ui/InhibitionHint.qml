/*
 *   Copyright 2015 Kai Uwe Broulik <kde@privat.broulik.de>
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

RowLayout {
    property alias iconSource: iconItem.source
    property alias text: label.text

    spacing: units.smallSpacing

    PlasmaCore.IconItem {
        id: iconItem
        Layout.preferredWidth: units.iconSizes.medium
        Layout.preferredHeight: units.iconSizes.medium
        visible: valid
    }

    Components.Label {
        id: label
        Layout.fillWidth: true
        height: implicitHeight
        font.pointSize: theme.smallestFont.pointSize
        wrapMode: Text.WordWrap
        elide: Text.ElideRight
        maximumLineCount: 3
    }
}