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

import QtQuick 2.0
import QtQuick.Layouts 1.1
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.plasma.plasmoid 2.0

Item{
    id: root

    Plasmoid.preferredRepresentation: Plasmoid.fullRepresentation

    Layout.fillWidth: horizontal && plasmoid.configuration.lengthType===2 || /*Expanded OR vertical Percentage*/
                      !horizontal && plasmoid.configuration.lengthType===2 ? true : false
    Layout.fillHeight: !horizontal && plasmoid.configuration.lengthType===2 || /*Expanded OR horizontal Percentage*/
                       horizontal && plasmoid.configuration.lengthType===2 ? true : false

    property bool horizontal: plasmoid.formFactor !== PlasmaCore.Types.Vertical
    property int lengthType: plasmoid.configuration.lengthType

    property int pixelStep: 10
    property int percentageStep: 20

    readonly property int thickness: horizontal ? root.height : root.width

    property int length: {
        //this is calculated in pixels
        if (lengthType===0) { /*Pixels*/
            return plasmoid.configuration.lengthPixels;
        } else if (lengthType===1) { /*Percentage*/
            return thickness * (plasmoid.configuration.lengthPercentage / 100);
        } else if (lengthType === 3 && latteBridge) {
            return -1; /*default Latte behavior - Square layout*/
        }

        return Infinity;
    }

    //BEGIN Latte Dock Communicator
    property QtObject latteBridge: null // current Latte v0.9 API

    onLatteBridgeChanged: {
        if (latteBridge) {
            plasmoid.configuration.containmentType = 2; /*Latte containment with new API*/
            latteBridge.actions.setProperty(plasmoid.id, "latteSideColoringEnabled", false);
            latteBridge.actions.setProperty(plasmoid.id, "lengthMarginsEnabled", latteBridge.parabolicEffectEnabled);
            updateValues();
        }
    }

    Connections {
        target: latteBridge
        onParabolicEffectEnabledChanged: {
            latteBridge.actions.setProperty(plasmoid.id, "lengthMarginsEnabled", latteBridge.parabolicEffectEnabled);
        }
    }
    //END  Latte Dock Communicator

    //BEGIN Latte based properties
    readonly property bool enforceLattePalette: latteBridge && latteBridge.applyPalette && latteBridge.palette
    readonly property bool latteInEditMode: latteBridge && latteBridge.inEditMode
    //END Latte based properties

    onLengthChanged: updateValues();
    onLengthTypeChanged: updateValues();
    Component.onCompleted: {
        containmentIdentifierTimer.start();
        updateValues();
    }

    function updateValues() {
        if (lengthType !== 2) { /* !Expanded */
            if (horizontal) {
                Layout.minimumWidth = length;
                Layout.preferredWidth = length;
                Layout.maximumWidth = length;
                Layout.minimumHeight = -1;
                Layout.preferredHeight = -1;
                Layout.maximumHeight = -1;
            } else {
                Layout.minimumHeight = length;
                Layout.preferredHeight = length;
                Layout.maximumHeight = length;
                Layout.minimumWidth = -1;
                Layout.preferredWidth = -1;
                Layout.maximumWidth = -1;
            }
        } else {
            Layout.minimumWidth = -1;
            Layout.preferredWidth = -1;
            Layout.maximumWidth = -1;
            Layout.minimumHeight = -1;
            Layout.preferredHeight = -1;
            Layout.maximumHeight = -1;
        }
    }

    function increaseLength() {
        if (lengthType === 0) { /*Pixels*/
            plasmoid.configuration.lengthPixels = plasmoid.configuration.lengthPixels + pixelStep;
        } else if (lengthType === 1) { /*Percentage*/
            plasmoid.configuration.lengthPercentage = plasmoid.configuration.lengthPercentage + percentageStep;
        }
    }

    function decreaseLength() {
        if (lengthType === 0) { /*Pixels*/
            plasmoid.configuration.lengthPixels = Math.max(5, plasmoid.configuration.lengthPixels - pixelStep);
        } else if (lengthType === 1) { /*Percentage*/
            plasmoid.configuration.lengthPercentage = Math.max(10, plasmoid.configuration.lengthPercentage - percentageStep);
        }
    }

    Loader{
        active: latteInEditMode
        anchors.fill: parent

        sourceComponent: Rectangle{
            anchors.fill: parent
            border.width: 1
            border.color: theme.highlightColor
            color: alphaBackColor

            property color alphaBackColor: Qt.rgba(theme.highlightColor.r, theme.highlightColor.g, theme.highlightColor.b, 0.5)
        }
    }

    //! this timer is used in order to identify in which containment the applet is in
    //! it should be called only the first time an applet is created and loaded because
    //! afterwards the applet has no way to move between different processes such
    //! as Plasma and Latte
    Timer{
        id: containmentIdentifierTimer
        interval: 5000
        onTriggered: {
            if (latteBridge) {
                plasmoid.configuration.containmentType = 2; /*Latte containment with new API*/
            } else {
                plasmoid.configuration.containmentType = 1; /*Plasma containment or Latte with old API*/
            }

            updateValues();
        }
    }
}
