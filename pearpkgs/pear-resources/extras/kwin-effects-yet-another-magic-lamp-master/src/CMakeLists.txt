add_subdirectory(kcm)

set(effect_SRCS
    Model.cc
    OffscreenRenderer.cc
    WindowMeshRenderer.cc
    YetAnotherMagicLampEffect.cc
    plugin.cc
)

kconfig_add_kcfg_files(effect_SRCS
    YetAnotherMagicLampConfig.kcfgc
)

include_directories(${epoxy_INCLUDE_DIR})
add_library(kwin4_effect_yetanothermagiclamp SHARED ${effect_SRCS})

target_link_libraries(kwin4_effect_yetanothermagiclamp
    Qt5::Core
    Qt5::Gui
    KF5::ConfigCore
    KF5::ConfigGui
    KF5::CoreAddons
    KF5::WindowSystem
    kwineffects::kwineffects
    kwineffects::kwinglutils
    ${epoxy_LIBRARY}
)

install(
    TARGETS
        kwin4_effect_yetanothermagiclamp

    DESTINATION
        ${PLUGIN_INSTALL_DIR}/kwin/effects/plugins/
)
