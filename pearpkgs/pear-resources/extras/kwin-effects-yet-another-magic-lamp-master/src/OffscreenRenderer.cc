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

// Own
#include "OffscreenRenderer.h"

// std
#include <cmath>

using namespace KWin;

/**
    \class OffscreenRenderer
    \brief Helper class to render windows into offscreen textures.
*/

/*!
    Constructs a OffscreenRenderer object with the given \p parent.
*/
OffscreenRenderer::OffscreenRenderer(QObject *parent)
    : QObject(parent)
{
    connect(effects, &EffectsHandler::windowGeometryShapeChanged,
            this, &OffscreenRenderer::slotWindowGeometryShapeChanged);
    connect(effects, &EffectsHandler::windowDeleted,
            this, &OffscreenRenderer::slotWindowDeleted);
    connect(effects, &EffectsHandler::windowDamaged,
            this, &OffscreenRenderer::slotWindowDamaged);
}

/*!
    Destructs the OffscreenRenderer object.
*/
OffscreenRenderer::~OffscreenRenderer()
{
    unregisterAllWindows();
}

/*!
    Allocates necessary rendering resources.
*/
void OffscreenRenderer::registerWindow(EffectWindow *window)
{
    if (m_renderResources.contains(window))
        return;

    RenderResources resources = allocateRenderResources(window);
    if (resources.isValid())
        m_renderResources[window] = resources;
}

/*!
    Frees rendering resources.
*/
void OffscreenRenderer::unregisterWindow(EffectWindow *window)
{
    auto it = m_renderResources.find(window);
    if (it == m_renderResources.end())
        return;

    freeRenderResources(*it);
    m_renderResources.erase(it);
}

/*!
    Frees rendering resources for all windows.
*/
void OffscreenRenderer::unregisterAllWindows()
{
    const auto windows = m_renderResources.keys();
    for (EffectWindow *window : windows)
        unregisterWindow(window);
}

/*!
    Renders the given window into an offscreen texture.
*/
GLTexture *OffscreenRenderer::render(EffectWindow *window)
{
    auto it = m_renderResources.find(window);
    if (it == m_renderResources.end())
        return nullptr;

    if (!it->isDirty)
        return it->texture;

    GLRenderTarget::pushRenderTarget(it->renderTarget);

    glClearColor(0.0, 0.0, 0.0, 0.0);
    glClear(GL_COLOR_BUFFER_BIT);

    const int mask = Effect::PAINT_WINDOW_TRANSFORMED | Effect::PAINT_WINDOW_TRANSLUCENT;

    WindowPaintData data(window);

    QMatrix4x4 projectionMatrix;
    projectionMatrix.ortho(QRect(0, 0, it->texture->width(), it->texture->height()));
    data.setProjectionMatrix(projectionMatrix);

    data.setXTranslation(-window->expandedGeometry().x());
    data.setYTranslation(-window->expandedGeometry().y());

    effects->drawWindow(window, mask, infiniteRegion(), data);

    GLRenderTarget::popRenderTarget();

    it->isDirty = false;

    return it->texture;
}

void OffscreenRenderer::slotWindowGeometryShapeChanged(EffectWindow *window, const QRect &old)
{
    if (window->size() == old.size())
        return;

    auto it = m_renderResources.find(window);
    if (it == m_renderResources.end())
        return;

    effects->makeOpenGLContextCurrent();
    freeRenderResources(*it);
    RenderResources resources = allocateRenderResources(window);
    if (resources.isValid())
        *it = resources;
    else
        m_renderResources.erase(it);
    effects->doneOpenGLContextCurrent();
}

void OffscreenRenderer::slotWindowDeleted(EffectWindow *window)
{
    effects->makeOpenGLContextCurrent();
    unregisterWindow(window);
    effects->doneOpenGLContextCurrent();
}

void OffscreenRenderer::slotWindowDamaged(EffectWindow *window)
{
    auto it = m_renderResources.find(window);
    if (it != m_renderResources.end())
        it->isDirty = true;
}

OffscreenRenderer::RenderResources
OffscreenRenderer::allocateRenderResources(EffectWindow *window)
{
    effects->makeOpenGLContextCurrent();
    const QRect geometry = window->expandedGeometry();

    const int levels = std::floor(std::log2(std::min(geometry.width(), geometry.height()))) + 1;
    QScopedPointer<GLTexture> texture;
    texture.reset(new GLTexture(GL_RGBA8, geometry.width(), geometry.height(), levels));
    texture->setFilter(GL_LINEAR_MIPMAP_LINEAR);
    texture->setWrapMode(GL_CLAMP_TO_EDGE);

    QScopedPointer<GLRenderTarget> renderTarget;
    renderTarget.reset(new GLRenderTarget(*texture));

    if (!renderTarget->valid())
        return {};

    RenderResources resources = {};
    resources.texture = texture.take();
    resources.renderTarget = renderTarget.take();
    resources.isDirty = true;

    return resources;
}

void OffscreenRenderer::freeRenderResources(RenderResources &resources)
{
    delete resources.renderTarget;
    delete resources.texture;
}
