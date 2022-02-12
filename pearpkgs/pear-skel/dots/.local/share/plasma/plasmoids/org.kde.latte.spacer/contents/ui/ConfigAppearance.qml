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

    property bool vertical: (plasmoid.formFactor === PlasmaCore.Types.Vertical)

    property alias cfg_lengthType: root.lengthType
    property alias cfg_lengthPixels: lengthPixels.value
    property alias cfg_lengthPercentage: lengthPercentage.value

    // used from the ui
    readonly property real centerFactor: 0.3
    readonly property int minimumWidth: 220
    property int lengthType: 0

    ColumnLayout {
        spacing: units.largeSpacing
        Layout.fillWidth: true

        GridLayout{
            columns: 2
            Label {
                Layout.minimumWidth: Math.max(centerFactor * root.width, minimumWidth)
                text: i18n("Length:")
                horizontalAlignment: Text.AlignRight
            }

            ExclusiveGroup {
                id: lengthTypeGroup
                onCurrentChanged: {
                    root.lengthType = current.type;
                }
            }

            RowLayout {
                RadioButton {
                    id: usePixels
                    checked: root.lengthType === type
                    exclusiveGroup: lengthTypeGroup

                    readonly property int type: 0 /*Pixels*/
                }

                SpinBox{
                    id: lengthPixels
                    Layout.minimumWidth: Math.max(lengthPixels.implicitWidth, lengthPercentage.implicitWidth)

                    minimumValue: 0
                    maximumValue: 1024
                    stepSize: 10
                    suffix: " " + i18nc("pixels","px.")
                }
            }

            Label {}

            RowLayout {
                RadioButton {
                    id: usePercentage
                    checked: root.lengthType === type
                    exclusiveGroup: lengthTypeGroup

                    readonly property int type: 1 /*Percentage*/
                }

                SpinBox {
                    id: lengthPercentage
                    Layout.minimumWidth: Math.max(lengthPixels.implicitWidth, lengthPercentage.implicitWidth)

                    minimumValue: 0
                    maximumValue: 1000
                    stepSize: 20
                    suffix: " %"
                }

                Label {
                    height: lengthPercentage.height
                    text: " " + i18n(" of panel thickness")
                }
            }

            Label {visible: plasmoid.configuration.containmentType === 2} /*Latte containmnent*/

            RowLayout {
                visible: plasmoid.configuration.containmentType === 2 /*Latte containmnent*/

                RadioButton {
                    id: latteIcon
                    checked: root.lengthType === type
                    exclusiveGroup: lengthTypeGroup

                    readonly property int type: 3 /*Latte Icon*/
                }

                Label {
                    height: lengthPercentage.height
                    Layout.leftMargin: 4
                    text: i18n("use Latte icon size")
                }
            }

            Label {}

            RowLayout {
                RadioButton {
                    id: useExpanded
                    checked: root.lengthType === type
                    exclusiveGroup: lengthTypeGroup

                    readonly property int type: 2 /*Exclusive*/
                }

                Label {
                    height: lengthPercentage.height
                    Layout.leftMargin: 4
                    text: i18n("fill available space")
                }

                SpinBox {
                    opacity: 0
                }
            }
        }
    }
}
