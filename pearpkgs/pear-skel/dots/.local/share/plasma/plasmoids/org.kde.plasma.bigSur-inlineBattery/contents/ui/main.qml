import QtQuick 2.1
import QtQuick.Layouts 1.3
import org.kde.plasma.plasmoid 2.0
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.plasma.components 2.0 as PlasmaComponent
import org.kde.kcoreaddons 1.0 as KCoreAddons

import org.kde.kquickcontrolsaddons 2.0
import "logic.js" as Logic

Item {
	id: batterywidget

	AppletConfig { id: config }

	// https://github.com/KDE/plasma-workspace/blob/master/dataengines/powermanagement/powermanagementengine.h
	// https://github.com/KDE/plasma-workspace/blob/master/dataengines/powermanagement/powermanagementengine.cpp

    Plasmoid.status: {
        if (powermanagementDisabled) {
            return PlasmaCore.Types.ActiveStatus
        }

        if (pmSource.data.Battery["Has Cumulative"]) {
            if (pmSource.data.Battery.State !== "Charging" && pmSource.data.Battery.Percent <= 5) {
                return PlasmaCore.Types.NeedsAttentionStatus
            } else if (pmSource.data["Battery"]["State"] !== "FullyCharged") {
                return PlasmaCore.Types.ActiveStatus
            }
        }

        return PlasmaCore.Types.PassiveStatus
    }

     Plasmoid.toolTipMainText: {
        if (batteries.count === 0) {
            return i18n("No Batteries Available");
        } else if (!pmSource.data["Battery"]["Has Cumulative"]) {
            // Bug 362924: Distinguish between no batteries and no power supply batteries
            // just show the generic applet title in the latter case
            return i18n("Battery and Brightness")
        } else if (pmSource.data["Battery"]["State"] === "FullyCharged") {
            return i18n("Fully Charged");
        } else if (pmSource.data["AC Adapter"] && pmSource.data["AC Adapter"]["Plugged in"]) {
            var percent = pmSource.data.Battery.Percent
            var state = pmSource.data.Battery.State
            if (state === "Charging") {
                return i18n("%1%. Charging", percent)
            } else if (state === "NoCharge") {
                return i18n("%1%. Plugged in, not Charging", percent)
            } else {
                return i18n("%1%. Plugged in", percent)
            }
        } else {
            if (remainingTime > 0) {
                return i18nc("%1 is remaining time, %2 is percentage", "%1 Remaining (%2%)",
                             KCoreAddons.Format.formatDuration(remainingTime, KCoreAddons.FormatTypes.HideSeconds),
                             pmSource.data["Battery"]["Percent"])
            } else {
                return i18n("%1% Battery Remaining", pmSource.data["Battery"]["Percent"]);
            }
        }
    }

    Plasmoid.toolTipSubText: powermanagementDisabled ? i18n("Power management is disabled") : ""

    property bool disableBrightnessUpdate: true
    property int screenBrightness
    readonly property int maximumScreenBrightness: pmSource.data["PowerDevil"] ? pmSource.data["PowerDevil"]["Maximum Screen Brightness"] || 0 : 0

    property int keyboardBrightness
    readonly property int maximumKeyboardBrightness: pmSource.data["PowerDevil"] ? pmSource.data["PowerDevil"]["Maximum Keyboard Brightness"] || 0 : 0

    readonly property int remainingTime: Number(pmSource.data["Battery"]["Remaining msec"])

    property bool powermanagementDisabled: false

    property var inhibitions: []

    readonly property var kcms: ["powerdevilprofilesconfig.desktop",
                                 "powerdevilactivitiesconfig.desktop",
                                 "powerdevilglobalconfig.desktop"]

    readonly property bool kcmsAuthorized: KCMShell.authorize(batterywidget.kcms).length > 0

    onScreenBrightnessChanged: {
        if (disableBrightnessUpdate) {
            return;
        }
        var service = pmSource.serviceForSource("PowerDevil");
        var operation = service.operationDescription("setBrightness");
        operation.brightness = screenBrightness;
        // show OSD only when the plasmoid isn't expanded since the moving slider is feedback enough
        operation.silent = plasmoid.expanded
        service.startOperationCall(operation);
    }

    onKeyboardBrightnessChanged: {
        if (disableBrightnessUpdate) {
            return;
        }
        var service = pmSource.serviceForSource("PowerDevil");
        var operation = service.operationDescription("setKeyboardBrightness");
        operation.brightness = keyboardBrightness;
        operation.silent = plasmoid.expanded
        service.startOperationCall(operation);
    }

    function action_powerdevilkcm() {
        KCMShell.open(batterywidget.kcms);
    }

    Component.onCompleted: {
        Logic.updateBrightness(batterywidget, pmSource);
        Logic.updateInhibitions(batterywidget, pmSource)

        if (batterywidget.kcmsAuthorized) {
            plasmoid.setAction("powerdevilkcm", i18n("&Configure Power Saving..."), "preferences-system-power-management");
        }
    }

    property QtObject batteries: PlasmaCore.SortFilterModel {
        id: batteries
        filterRole: "Is Power Supply"
        sortOrder: Qt.DescendingOrder
        sourceModel: PlasmaCore.SortFilterModel {
            sortRole: "Pretty Name"
            sortOrder: Qt.AscendingOrder
            sortCaseSensitivity: Qt.CaseInsensitive
            sourceModel: PlasmaCore.DataModel {
                dataSource: pmSource
                sourceFilter: "Battery[0-9]+"
            }
        }
    }

	  // PlasmaCore.DataSource {
    property QtObject pmSource: PlasmaCore.DataSource {
		    id: pmSource
		    engine: "powermanagement"
		    connectedSources: sources
		    onSourceAdded: {
			      // console.log('onSourceAdded', source)
			      disconnectSource(source)
			      connectSource(source)
		    }
		    onSourceRemoved: {
			      disconnectSource(source)
		    }

        onDataChanged: {
            Logic.updateBrightness(batterywidget, pmSource)
            Logic.updateInhibitions(batterywidget, pmSource)
        }

	  }


	function getData(sourceName, key, def) {
		var source = pmSource.data[sourceName]
		if (typeof source === 'undefined') {
			return def;
		} else {
			var value = source[key]
			if (typeof value === 'undefined') {
				return def;
			} else {
				return value;
			}
		}
	}

	  property string currentBatteryName: 'Battery'
	  property string currentBatteryState: getData(currentBatteryName, 'State', false)
	  property int currentBatteryPercent: getData(currentBatteryName, 'Percent', 100)
	  property bool currentBatteryLowPower: currentBatteryPercent <= config.lowBatteryPercent
	  property color currentTextColor: {
		    if (currentBatteryLowPower) {
			      return config.lowBatteryColor
		    } else {
			      return config.normalColor
		    }
	  }


	  Plasmoid.compactRepresentation: Item {
		    id: panelItem

        MouseArea {
            id: desktopMouseArea
            anchors.fill: parent

            onClicked:
            {
                plasmoid.expanded = !plasmoid.expanded
            }
        }

		    Layout.minimumWidth: gridLayout.implicitWidth
		    Layout.preferredWidth: gridLayout.implicitWidth

		    Layout.minimumHeight: gridLayout.implicitHeight
		    Layout.preferredHeight: gridLayout.implicitHeight

		    // property int textHeight: Math.max(6, Math.min(panelItem.height, 16 * units.devicePixelRatio))
		    property int textHeight: 12 * units.devicePixelRatio
		    // onTextHeightChanged: console.log('textHeight', textHeight)

		    GridLayout {
			      id: gridLayout
			      anchors.fill: parent

			      // The rect around the Text items in the vertical layout should provide 2 pixels above
			      // and below. Adding extra space will make the space between the percentage and time left
			      // labels look bigger than the space between the icon and the percentage.
			      // So for vertical layouts, we'll add the spacing to just the icon.
			      property int spacing: 4 * units.devicePixelRatio
			      columnSpacing: spacing
			      rowSpacing: 0

			      PlasmaComponent.Label {
				        id: percentTextLeft
				        visible: plasmoid.configuration.showPercentage && !!plasmoid.configuration.alignLeft
				        anchors.right: batteryIconContainer.left
				        anchors.rightMargin: config.padding
				        text: {
					          if (currentBatteryPercent > 0) {
						            return '' + currentBatteryPercent + '%'
					          } else {
						            return '100%';
					          }
				        }
				        font.pixelSize: config.fontSize
				        fontSizeMode: Text.Fit
				        horizontalAlignment: Text.AlignHCenter
				        verticalAlignment: Text.AlignVCenter
				        color: currentTextColor
			      }

			      Item {
				        id: batteryIconContainer
				        visible: plasmoid.configuration.showBatteryIcon
				        width: config.iconWidth * units.devicePixelRatio
				        height: config.iconHeight * units.devicePixelRatio
				        anchors.verticalCenter: parent.verticalCenter

				        MacBatteryIcon {
					          id: batteryIcon
					          width: Math.min(parent.width, config.iconWidth * units.devicePixelRatio)
					          height: Math.min(parent.height, config.iconHeight * units.devicePixelRatio)
					          anchors.centerIn: parent
					          charging: currentBatteryState == "Charging"
					          charge: currentBatteryPercent
					          normalColor: config.normalColor
					          chargingColor: config.chargingColor
					          lowBatteryColor: config.lowBatteryColor
					          lowBatteryPercent: plasmoid.configuration.lowBatteryPercent
				        }
			      }

			      PlasmaComponent.Label {
				        id: percentTextRight
				        visible: plasmoid.configuration.showPercentage && !plasmoid.configuration.alignLeft
				        anchors.left: batteryIconContainer.right
				        anchors.leftMargin: config.padding
				        text: {
					          if (currentBatteryPercent > 0) {
						            return '' + currentBatteryPercent + '%'
					          } else {
						            return '100%';
					          }
				        }
				        font.pixelSize: config.fontSize
				        fontSizeMode: Text.Fit
				        horizontalAlignment: Text.AlignHCenter
				        verticalAlignment: Text.AlignVCenter
				        color: currentTextColor
			      }
		    }
	  }

    Plasmoid.fullRepresentation: PopupDialog {
        id: dialogItem
        Layout.minimumWidth: units.iconSizes.medium * 9
        Layout.minimumHeight: units.gridUnit * 15
        // TODO Probably needs a sensible preferredHeight too

        model: plasmoid.expanded ? batteries : null
        anchors.fill: parent
        focus: true

        isBrightnessAvailable: pmSource.data["PowerDevil"] && pmSource.data["PowerDevil"]["Screen Brightness Available"] ? true : false
        isKeyboardBrightnessAvailable: pmSource.data["PowerDevil"] && pmSource.data["PowerDevil"]["Keyboard Brightness Available"] ? true : false

        pluggedIn: pmSource.data["AC Adapter"] != undefined && pmSource.data["AC Adapter"]["Plugged in"]

        property int cookie1: -1
        property int cookie2: -1
        onPowermanagementChanged: {
            var service = pmSource.serviceForSource("PowerDevil");
            if (checked) {
                var op1 = service.operationDescription("stopSuppressingSleep");
                op1.cookie = cookie1;
                var op2 = service.operationDescription("stopSuppressingScreenPowerManagement");
                op2.cookie = cookie2;

                var job1 = service.startOperationCall(op1);
                job1.finished.connect(function(job) {
                    cookie1 = -1;
                });

                var job2 = service.startOperationCall(op2);
                job2.finished.connect(function(job) {
                    cookie2 = -1;
                });
            } else {
                var reason = i18n("The battery applet has enabled system-wide inhibition");
                var op1 = service.operationDescription("beginSuppressingSleep");
                op1.reason = reason;
                var op2 = service.operationDescription("beginSuppressingScreenPowerManagement");
                op2.reason = reason;

                var job1 = service.startOperationCall(op1);
                job1.finished.connect(function(job) {
                    cookie1 = job.result;
                });

                var job2 = service.startOperationCall(op2);
                job2.finished.connect(function(job) {
                    cookie2 = job.result;
                });
            }

            batterywidget.powermanagementDisabled = !checked
        }
    }
}
