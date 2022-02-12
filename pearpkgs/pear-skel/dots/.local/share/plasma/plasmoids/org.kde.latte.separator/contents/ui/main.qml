/*
 * Copyright 2019 Michail Vourlakos <mvourlakos@gmail.com>
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of
 * the License or (at your option) version 3 or any later version
 * accepted by the membership of KDE e.V. (or its successor approved
 * by the membership of KDE e.V.), which shall act as a proxy
 * defined in Section 14 of version 3 of the license.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>
 */

import QtQuick 2.4
import QtQuick.Layouts 1.0
import org.kde.plasma.plasmoid 2.0
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.plasma.extras 2.0 as PlasmaExtras
Item {
    id: root
    readonly property bool horizontal: plasmoid.formFactor === PlasmaCore.Types.Horizontal
    readonly property bool planar: plasmoid.formFactor === PlasmaCore.Types.Planar

    Layout.fillWidth: horizontal ? false : true
    Layout.fillHeight: horizontal ? true : false

    Layout.minimumWidth:   horizontal ? length : -1
    Layout.preferredWidth: Layout.minimumWidth
    Layout.maximumWidth:   Layout.minimumWidth

    Layout.minimumHeight: !horizontal ? length : -1
    Layout.preferredHeight: Layout.minimumHeight
    Layout.maximumHeight: Layout.minimumHeight

    Plasmoid.preferredRepresentation: plasmoid.fullRepresentation
    Plasmoid.backgroundHints: planar ? PlasmaCore.Types.StandardBackground : PlasmaCore.Types.NoBackground

    readonly property int length: latteBridge && latteBridge.inEditMode ? Math.max(10, totalLength) : totalLength
    readonly property int totalLength: 2*plasmoid.configuration.lengthMargin+1

    readonly property int fullThickness: {
        if (!parent) {
            return 36;
        }

        return plasmoid.formFactor === PlasmaCore.Types.Vertical ? parent.width : parent.height
    }
    readonly property int thickness: (latteBridge ? latteBridge.iconSize - (2*thickMargin) : fullThickness - (2*thickMargin))

    readonly property int thickMargin: plasmoid.configuration.thickMargin
    readonly property int lengthMargn: plasmoid.configuration.lengthMargin

    function increaseLength() {
        plasmoid.configuration.lengthMargin = plasmoid.configuration.lengthMargin + 4;
    }

    function decreaseLength() {
        plasmoid.configuration.lengthMargin = Math.max(0,plasmoid.configuration.lengthMargin - 4);
    }

    //BEGIN Latte Dock Communicator
    property QtObject latteBridge: null // current Latte v0.9 API

    onLatteBridgeChanged: {
        if (latteBridge) {
            latteBridge.actions.setProperty(plasmoid.id, "latteSideColoringEnabled", false);
        }
    }
    //END  Latte Dock Communicator
    //BEGIN Latte based properties
    readonly property bool enforceLattePalette: latteBridge && latteBridge.applyPalette && latteBridge.palette
    readonly property bool latteInEditMode: latteBridge && latteBridge.inEditMode
    //END Latte based properties

    Rectangle {
        id: sep
        anchors.centerIn: parent

        width: horizontal ? 1 : thickness
        height: !horizontal ? 1 : thickness

        color: enforceLattePalette ? latteBridge.palette.textColor : theme.textColor
        opacity: 0.4
        visible: !planar
    }
}
