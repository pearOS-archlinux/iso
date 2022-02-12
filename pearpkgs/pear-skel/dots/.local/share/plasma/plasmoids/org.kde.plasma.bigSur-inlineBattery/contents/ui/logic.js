/*
 *   Copyright 2011 Sebastian Kügler <sebas@kde.org>
 *   Copyright 2012 Viranch Mehta <viranch.mehta@gmail.com>
 *   Copyright 2014-2016 Kai Uwe Broulik <kde@privat.broulik.de>
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

function stringForBatteryState(batteryData) {
    if (batteryData["Plugged in"]) {
        switch(batteryData["State"]) {
            case "Discharging": return i18n("Discharging");
            case "FullyCharged": return i18n("Fully Charged");
            case "Charging": return i18n("Charging");
            // when in doubt we're not charging
            default: return i18n("Not Charging");
        }
    } else {
        return i18nc("Battery is currently not present in the bay","Not present");
    }
}

function batteryDetails(batteryData, remainingTime) {
    var data = []

    if (remainingTime > 0 && batteryData["Is Power Supply"] && (batteryData["State"] == "Discharging" || batteryData["State"] == "Charging")) {
        data.push({label: (batteryData["State"] == "Charging" ? i18n("Time To Full:") : i18n("Time To Empty:")) })
        data.push({value: KCoreAddons.Format.formatDuration(remainingTime, KCoreAddons.FormatTypes.HideSeconds) })
    }

    if (batteryData["Is Power Supply"] && batteryData["Capacity"] != "" && typeof batteryData["Capacity"] == "number") {
        data.push({label: i18n("Capacity:") })
        data.push({value: i18nc("Placeholder is battery capacity", "%1%", batteryData["Capacity"]) })
    }

    // Non-powersupply batteries have a name consisting of the vendor and model already
    if (batteryData["Is Power Supply"]) {
        if (batteryData["Vendor"] != "" && typeof batteryData["Vendor"] == "string") {
            data.push({label: i18n("Vendor:") })
            data.push({value: batteryData["Vendor"] })
        }

        if (batteryData["Product"] != "" && typeof batteryData["Product"] == "string") {
            data.push({label: i18n("Model:") })
            data.push({value: batteryData["Product"] })
        }
    }

    return data
}

function updateBrightness(rootItem, source) {
    if (!source.data["PowerDevil"]) {
        return;
    }

    // we don't want passive brightness change send setBrightness call
    rootItem.disableBrightnessUpdate = true;

    if (typeof source.data["PowerDevil"]["Screen Brightness"] === 'number') {
        rootItem.screenBrightness = source.data["PowerDevil"]["Screen Brightness"];
    }
    if (typeof source.data["PowerDevil"]["Keyboard Brightness"] === 'number') {
        rootItem.keyboardBrightness = source.data["PowerDevil"]["Keyboard Brightness"];
    }
    rootItem.disableBrightnessUpdate = false;
}

function updateInhibitions(rootItem, source) {
    var inhibitions = [];

    if (source.data["Inhibitions"]) {
        for(var key in pmSource.data["Inhibitions"]) {
            if (key === "plasmashell" || key === "plasmoidviewer") { // ignore our own inhibition
                continue
            }

            inhibitions.push(pmSource.data["Inhibitions"][key])
        }
    }

    rootItem.inhibitions = inhibitions
}
