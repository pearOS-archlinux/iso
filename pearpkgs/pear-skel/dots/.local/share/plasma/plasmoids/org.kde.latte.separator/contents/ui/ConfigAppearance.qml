/*
*  Copyright 2019  Michail Vourlakos <mvourlakos@gmail.com>
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
import QtQuick.Controls 1.0
import QtQuick.Layouts 1.0
import QtGraphicalEffects 1.0

import org.kde.plasma.core 2.0 as PlasmaCore

Item {
    id: root

    property alias cfg_lengthMargin: lengthMargin.value
    property alias cfg_thickMargin: thickMargin.value

    // used from the ui
    readonly property real centerFactor: 0.3
    readonly property int minimumWidth: 220

    ColumnLayout {
        spacing: units.largeSpacing
        Layout.fillWidth: true

        GridLayout{
            columns: 2
            Label {
                Layout.minimumWidth: Math.max(centerFactor * root.width, minimumWidth)
                text: i18n("Length margin:")
                horizontalAlignment: Text.AlignRight
            }

            SpinBox{
                id: lengthMargin

                minimumValue: 0
                maximumValue: 64
                stepSize: 1
                suffix: " " + i18nc("pixels","px.")
            }

            Label {
                Layout.minimumWidth: Math.max(centerFactor * root.width, minimumWidth)
                text: i18n("Thickness margin:")
                horizontalAlignment: Text.AlignRight
            }

            SpinBox{
                id: thickMargin

                minimumValue: 0
                maximumValue: 64
                stepSize: 1
                suffix: " " + i18nc("pixels","px.")
            }
        }

    }
}
