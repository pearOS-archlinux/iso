/*
 * Copyright (C) 2018 Vlad Zagorodniy <vladzzag@gmail.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */

#pragma once

// Own
#include "Model.h"
#include "common.h"

// kwineffects
#include <kwineffects.h>

class OffscreenRenderer;
class WindowMeshRenderer;

class YetAnotherMagicLampEffect : public KWin::Effect {
    Q_OBJECT

public:
    YetAnotherMagicLampEffect();
    ~YetAnotherMagicLampEffect() override;

    void reconfigure(ReconfigureFlags flags) override;

    void prePaintScreen(KWin::ScreenPrePaintData& data, int time) override;
    void postPaintScreen() override;

    void prePaintWindow(KWin::EffectWindow* w, KWin::WindowPrePaintData& data, int time) override;

#if KWIN_EFFECT_API_VERSION <= KWIN_EFFECT_API_MAKE_VERSION(0, 228)
    void drawWindow(KWin::EffectWindow* w, int mask, QRegion region, KWin::WindowPaintData& data) override;
#else
    void drawWindow(KWin::EffectWindow* w, int mask, const QRegion& region, KWin::WindowPaintData& data) override;
#endif

    bool isActive() const override;
    int requestedEffectChainPosition() const override;

    static bool supported();

private Q_SLOTS:
    void slotWindowMinimized(KWin::EffectWindow* w);
    void slotWindowUnminimized(KWin::EffectWindow* w);
    void slotWindowDeleted(KWin::EffectWindow* w);
    void slotActiveFullScreenEffectChanged();

private:
    Model::Parameters m_modelParameters;
    int m_gridResolution;

    QMap<KWin::EffectWindow*, Model> m_models;
    OffscreenRenderer* m_offscreenRenderer;
    WindowMeshRenderer* m_meshRenderer;
};

inline int YetAnotherMagicLampEffect::requestedEffectChainPosition() const
{
    return 50;
}
