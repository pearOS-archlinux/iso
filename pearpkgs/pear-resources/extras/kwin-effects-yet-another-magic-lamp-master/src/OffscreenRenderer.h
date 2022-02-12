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

// kwineffects
#include <kwineffects.h>
#include <kwingltexture.h>
#include <kwinglutils.h>

// Qt
#include <QMap>
#include <QObject>

class OffscreenRenderer : public QObject
{
    Q_OBJECT

public:
    explicit OffscreenRenderer(QObject *parent = nullptr);
    ~OffscreenRenderer() override;

    void registerWindow(KWin::EffectWindow *window);
    void unregisterWindow(KWin::EffectWindow *window);
    void unregisterAllWindows();

    KWin::GLTexture *render(KWin::EffectWindow *window);

private Q_SLOTS:
    void slotWindowGeometryShapeChanged(KWin::EffectWindow *window, const QRect& old);
    void slotWindowDeleted(KWin::EffectWindow *window);
    void slotWindowDamaged(KWin::EffectWindow *window);

private:
    struct RenderResources
    {
        bool isValid() const
        {
            return texture && renderTarget;
        }

        KWin::GLTexture *texture = nullptr;
        KWin::GLRenderTarget *renderTarget = nullptr;
        bool isDirty = false;
    };

    RenderResources allocateRenderResources(KWin::EffectWindow *window);
    void freeRenderResources(RenderResources &resources);

    QMap<KWin::EffectWindow *, RenderResources> m_renderResources;

    Q_DISABLE_COPY(OffscreenRenderer)
};
