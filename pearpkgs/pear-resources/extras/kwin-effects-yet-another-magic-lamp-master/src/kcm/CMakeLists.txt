set(kcm_SRCS
    YetAnotherMagicLampEffectKCM.cc
    plugin.cc
)

kconfig_add_kcfg_files(kcm_SRCS
    ../YetAnotherMagicLampConfig.kcfgc
)

qt5_wrap_ui(kcm_SRCS YetAnotherMagicLampEffectKCM.ui)

qt5_add_dbus_interface(kcm_SRCS ${KWIN_EFFECTS_INTERFACE} kwineffects_interface)

add_library(kwin_yetanothermagiclamp_config MODULE ${kcm_SRCS})

target_link_libraries(kwin_yetanothermagiclamp_config
    Qt5::Core
    Qt5::DBus
    Qt5::Gui
    KF5::ConfigCore
    KF5::ConfigGui
    KF5::ConfigWidgets
)

install(
    TARGETS
        kwin_yetanothermagiclamp_config

    DESTINATION
        ${PLUGIN_INSTALL_DIR}/kwin/effects/configs
)
