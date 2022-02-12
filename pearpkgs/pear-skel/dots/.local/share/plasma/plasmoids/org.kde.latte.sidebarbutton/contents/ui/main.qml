/*
 * Copyright 2020 Michail Vourlakos <mvourlakos@gmail.com>
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
import QtQuick.Window 2.2
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.plasma.plasmoid 2.0

import "icons" as Icons

Item{
    id: root

    Plasmoid.preferredRepresentation: Plasmoid.fullRepresentation

    Layout.fillWidth: !isHorizontal
    Layout.fillHeight: isHorizontal

    Layout.minimumWidth: -1
    Layout.minimumHeight: -1
    Layout.preferredWidth: {
        if (isInLatte) {
            return Math.min(latteBridge.iconSize, plasmoid.configuration.maximumIconSize);
        }

        return isHorizontal ? Math.min(height, plasmoid.configuration.maximumIconSize) : height;
    }

    Layout.preferredHeight: {
        if (isInLatte) {
            return Math.min(latteBridge.iconSize, plasmoid.configuration.maximumIconSize);
        }

        return isHorizontal ? width : Math.min(width, plasmoid.configuration.maximumIconSize);
    }

    Layout.maximumWidth: Layout.preferredWidth
    Layout.maximumHeight: Layout.preferredHeight

    readonly property bool isHorizontal: plasmoid.formFactor === PlasmaCore.Types.Horizontal

    Plasmoid.onActivated: toggle();

    readonly property string iconSource: plasmoid.configuration.iconSource === "" ? Plasmoid.icon : plasmoid.configuration.iconSource
    readonly property string screenName: plasmoid.configuration.screenName === "" ? Screen.name : plasmoid.configuration.screenName

    //BEGIN Latte Dock Communicator
    property QtObject latteBridge: null // current Latte v0.9 API
    //END  Latte Dock Communicator

    //BEGIN Latte based properties
    readonly property bool enforceLattePalette: latteBridge && latteBridge.applyPalette && latteBridge.palette
    readonly property bool isInLatte: latteBridge !== null
    readonly property bool latteInEditMode: latteBridge && latteBridge.inEditMode
    //END Latte based properties

    PlasmaCore.DataSource {
        id: executable
        engine: "executable"
        connectedSources: []
        onNewData: disconnectSource(sourceName)

        function exec(cmd) {
            executable.connectSource(cmd)
        }
    }

    function toggle() {
        var command = 'dbus-send --type=method_call --dest=org.kde.lattedock /Latte org.kde.LatteDock.toggleHiddenState ';
        var options = 'string:"' + plasmoid.configuration.layoutName + '" ';
        options = options + 'string:"' + root.screenName + '" ';
        options = options + 'int32:' + plasmoid.configuration.screenEdge;
        command = command + options;

        executable.exec(command);
    }


    Icons.GeneralIcon{
        id: icon
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height)
        height: width
    }

    MouseArea {
        anchors.fill: parent
        onClicked: toggle();
    }
}
