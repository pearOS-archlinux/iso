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
#include "WindowQuad.h"

// kwineffects
#include <kwineffects.h>
#include <kwingltexture.h>

// Qt
#include <QVector>

class WindowMeshRenderer : public QObject
{
    Q_OBJECT

public:
    explicit WindowMeshRenderer(QObject *parent = nullptr);

    QVector<WindowQuad> makeGrid(const KWin::EffectWindow *window, int blockSize);

    void render(KWin::EffectWindow *window, const QVector<WindowQuad> &quads,
                KWin::GLTexture *texture, const QRegion &clipRegion) const;
};
