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

RowLayout {
    property alias icon: brightnessIcon.source
    property alias label: brightnessLabel.text
    property alias value: brightnessSlider.value
    property alias maximumValue: brightnessSlider.maximumValue

    spacing: units.gridUnit

    PlasmaCore.IconItem {
        id: brightnessIcon
        Layout.alignment: Qt.AlignTop
        Layout.preferredWidth: units.iconSizes.medium
        Layout.preferredHeight: width
    }

    Column {
        id: brightnessColumn
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignTop
        spacing: 0

        Components.Label {
            id: brightnessLabel
            width: parent.width
            height: paintedHeight
        }

        Components.Slider {
            id: brightnessSlider
            width: parent.width
            // Don't allow the slider to turn off the screen
            // Please see https://git.reviewboard.kde.org/r/122505/ for more information
            minimumValue: maximumValue > 100 ? 1 : 0
            stepSize: 1
        }
    }
}