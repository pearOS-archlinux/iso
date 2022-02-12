import QtQuick 2.0

QtObject {
	readonly property color defaultNormalColor: theme.textColor
	readonly property color normalColor: plasmoid.configuration.normalColor || defaultNormalColor

	readonly property color defaultChargingColor: '#1e1'
	readonly property color chargingColor: plasmoid.configuration.chargingColor || defaultChargingColor

	readonly property color defaultLowBatteryColor: '#e33'
	readonly property color lowBatteryColor: plasmoid.configuration.lowBatteryColor || defaultLowBatteryColor

	readonly property int defaultFontSize: 16
	readonly property int fontSize: plasmoid.configuration.fontSize || defaultFontSize

	readonly property int defaultPadding: 8
	readonly property int padding: plasmoid.configuration.padding || defaultPadding

	readonly property int defaultIconWidth: 26
	readonly property int iconWidth: plasmoid.configuration.iconWidth || defaultIconWidth

	readonly property int defaultIconHeight: 15
	readonly property int iconHeight: plasmoid.configuration.iconHeight || defaultIconHeight
}
