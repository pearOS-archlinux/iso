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
import org.kde.plasma.plasmoid 2.0
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.plasma.components 2.0 as PlasmaComponents
import org.kde.plasma.extras 2.0 as PlasmaExtras

Item {
    id: root

    property var currentMetadata: mpris2Source.data[mpris2Source.current] ? mpris2Source.data[mpris2Source.current].Metadata : undefined
    property string track: {
        if (!currentMetadata) {
            return ""
        }
        var xesamTitle = currentMetadata["xesam:title"]
        if (xesamTitle) {
            return xesamTitle
        }
        // if no track title is given, print out the file name
        var xesamUrl = currentMetadata["xesam:url"] ? currentMetadata["xesam:url"].toString() : ""
        if (!xesamUrl) {
            return ""
        }
        var lastSlashPos = xesamUrl.lastIndexOf('/')
        if (lastSlashPos < 0) {
            return ""
        }
        var lastUrlPart = xesamUrl.substring(lastSlashPos + 1)
        return decodeURIComponent(lastUrlPart)
    }
    property string artist: currentMetadata ? currentMetadata["xesam:artist"] || "" : ""
    property string playerIcon: ""

    property bool noPlayer: mpris2Source.sources.length <= 1

    Plasmoid.switchWidth: units.gridUnit * 14
    Plasmoid.switchHeight: units.gridUnit * 10
    Plasmoid.toolTipMainText: i18n("No media playing")
    Plasmoid.status: PlasmaCore.Types.ActiveStatus

    // HACK Some players like Amarok take quite a while to load the next track
    // this avoids having the plasmoid jump between popup and panel
    onStateChanged: {
        if (state != "") {
            plasmoid.status = PlasmaCore.Types.ActiveStatus
        } else {
            updatePlasmoidStatusTimer.restart()
        }
    }

    Timer {
        id: updatePlasmoidStatusTimer
        interval: 250
        onTriggered: {
            if (state != "") {
                plasmoid.status = PlasmaCore.Types.ActiveStatus
            } else {
                plasmoid.status = PlasmaCore.Types.PassiveStatus
            }
        }
    }

    Plasmoid.fullRepresentation: ExpandedRepresentation {}

    Plasmoid.compactRepresentation: ExpandedRepresentation {}

    PlasmaCore.DataSource {
        id: executeSource
        engine: "executable"
        connectedSources: []

        onNewData: {
            //we get new data when the process finished, so we can remove it
            disconnectSource(sourceName)
        }
    }
    function exec(cmd) {
        //Note: we assume that 'cmd' is executed quickly so that a previous call
        //with the same 'cmd' has already finished (otherwise no new cmd will be
        //added because it is already in the list)
        executeSource.connectSource(cmd)
    }


    PlasmaCore.DataSource {
        id: mpris2Source
        engine: "mpris2"
        connectedSources: current

        property string current: "@multiplex"

        onDataChanged: updateOpenPlayerAction()
    }

    function updateOpenPlayerAction() {
        if (!root.noPlayer && mpris2Source.data[mpris2Source.current].CanRaise) {
            plasmoid.setAction("openplayer", i18nc("Bring the window of player %1 to the front", "Open %1", mpris2Source.data[mpris2Source.current].Identity))
        } else {
            plasmoid.removeAction("openplayer")
        }
    }

    function action_openplayer() {
        serviceOp(mpris2Source.current, "Raise");
    }
    function volumeUp() {
        exec(plasmoid.configuration.volumeUpCmd)
    }
    function volumeDown() {
        exec(plasmoid.configuration.volumeDownCmd)
    }

    function playPause() {
        serviceOp(mpris2Source.current, "PlayPause");
    }

    function previous() {
        serviceOp(mpris2Source.current, "Previous");
    }

    function next() {
        serviceOp(mpris2Source.current, "Next");
    }

    function serviceOp(src, op) {
        var service = mpris2Source.serviceForSource(src);
        var operation = service.operationDescription(op);
        return service.startOperationCall(operation);
    }

    states: [
        State {
            name: "playing"
            when: !root.noPlayer && mpris2Source.data[mpris2Source.current].PlaybackStatus == "Playing"

            PropertyChanges {
                target: plasmoid
                toolTipMainText: track
                toolTipSubText: artist ? i18nc("Artist of the song", "by %1", artist) : ""
            }
        },
        State {
            name: "paused"
            when: !root.noPlayer && mpris2Source.data[mpris2Source.current].PlaybackStatus == "Paused"

            PropertyChanges {
                target: plasmoid
                toolTipMainText: track
                toolTipSubText: artist ? i18nc("Artist of the song", "by %1 (paused)", artist) : i18n("Paused")
            }
        }
    ]
}
