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
#include "WindowMeshRenderer.h"

// kwineffects
#include <kwinglutils.h>

#if defined(__GNUC__)
#define KWIN_ALIGN(n) __attribute((aligned(n)))
#if defined(__SSE2__)
#define HAVE_SSE2
#endif
#elif defined(__INTEL_COMPILER)
#define KWIN_ALIGN(n) __declspec(align(n))
#define HAVE_SSE2
#else
#define KWIN_ALIGN(n)
#endif

#ifdef HAVE_SSE2
#include <emmintrin.h>
#endif

/*!
    Constructs a WindowMeshRenderer object with the given \p parent.
*/
WindowMeshRenderer::WindowMeshRenderer(QObject *parent)
    : QObject(parent)
{
}

QVector<WindowQuad> WindowMeshRenderer::makeGrid(const KWin::EffectWindow *window, int gridResolution)
{
    QVector<WindowQuad> quads;
    quads.reserve(gridResolution * gridResolution);

    const QRectF geometry = window->geometry();
    const QRectF expandedGeometry = window->expandedGeometry();

    const qreal initialX = expandedGeometry.x() - geometry.x();
    const qreal initialY = expandedGeometry.y() - geometry.y();
    const qreal initialU = 0.0;
    const qreal initialV = 0.0;

    const qreal dx = static_cast<qreal>(window->expandedGeometry().width()) / gridResolution;
    const qreal dy = static_cast<qreal>(window->expandedGeometry().height()) / gridResolution;
    const qreal du = 1.0 / gridResolution;
    const qreal dv = 1.0 / gridResolution;

    qreal y = initialY;
    qreal v = initialV;
    for (int i = 0; i < gridResolution; ++i) {
        qreal x = initialX;
        qreal u = initialU;
        for (int j = 0; j < gridResolution; ++j) {
            WindowQuad quad;

            quad[0].setX(x);
            quad[0].setY(y);
            quad[0].setU(u);
            quad[0].setV(v);

            quad[1].setX(x + dx);
            quad[1].setY(y);
            quad[1].setU(u + du);
            quad[1].setV(v);

            quad[2].setX(x + dx);
            quad[2].setY(y + dy);
            quad[2].setU(u + du);
            quad[2].setV(v + dv);

            quad[3].setX(x);
            quad[3].setY(y + dy);
            quad[3].setU(u);
            quad[3].setV(v + dv);

            quads.append(quad);
            x += dx;
            u += du;
        }
        y += dy;
        v += dv;
    }

    return quads;
}

// Copied from libkwineffects.
static void uploadQuads(GLenum primitiveType, const QVector<WindowQuad> &quads,
                        const QMatrix4x4 &textureMatrix, KWin::GLVertex2D *out)
{
    // Since we know that the texture matrix just scales and translates
    // we can use this information to optimize the transformation.
    const QVector2D scale(textureMatrix(0, 0), textureMatrix(1, 1));
    const QVector2D shift(textureMatrix(0, 3), textureMatrix(1, 3));

    switch (primitiveType) {
    case GL_QUADS:
#ifdef HAVE_SSE2
        if (!(intptr_t(out) & 0xf)) {
            for (int i = 0; i < quads.count(); i++) {
                const WindowQuad &quad = quads[i];
                KWIN_ALIGN(16)
                KWin::GLVertex2D v[4];

                for (int j = 0; j < 4; j++) {
                    const WindowVertex &wv = quad[j];

                    v[j].position = QVector2D(wv.x(), wv.y());
                    v[j].texcoord = QVector2D(wv.u(), wv.v()) * scale + shift;
                }

                const __m128i *srcP = (const __m128i *)&v;
                __m128i *dstP = (__m128i *)out;

                _mm_stream_si128(&dstP[0], _mm_load_si128(&srcP[0])); // Top-left
                _mm_stream_si128(&dstP[1], _mm_load_si128(&srcP[1])); // Top-right
                _mm_stream_si128(&dstP[2], _mm_load_si128(&srcP[2])); // Bottom-right
                _mm_stream_si128(&dstP[3], _mm_load_si128(&srcP[3])); // Bottom-left

                out += 4;
            }
        } else
#endif // HAVE_SSE2
        {
            for (int i = 0; i < quads.count(); i++) {
                const WindowQuad &quad = quads[i];

                for (int j = 0; j < 4; j++) {
                    const WindowVertex &wv = quad[j];

                    KWin::GLVertex2D v;
                    v.position = QVector2D(wv.x(), wv.y());
                    v.texcoord = QVector2D(wv.u(), wv.v()) * scale + shift;

                    *(out++) = v;
                }
            }
        }
        break;

    case GL_TRIANGLES:
#ifdef HAVE_SSE2
        if (!(intptr_t(out) & 0xf)) {
            for (int i = 0; i < quads.count(); i++) {
                const WindowQuad &quad = quads[i];
                KWIN_ALIGN(16) KWin::GLVertex2D v[4];

                for (int j = 0; j < 4; j++) {
                    const WindowVertex &wv = quad[j];

                    v[j].position = QVector2D(wv.x(), wv.y());
                    v[j].texcoord = QVector2D(wv.u(), wv.v()) * scale + shift;
                }

                const __m128i *srcP = (const __m128i *)&v;
                __m128i *dstP = (__m128i *)out;

                __m128i src[4];
                src[0] = _mm_load_si128(&srcP[0]); // Top-left
                src[1] = _mm_load_si128(&srcP[1]); // Top-right
                src[2] = _mm_load_si128(&srcP[2]); // Bottom-right
                src[3] = _mm_load_si128(&srcP[3]); // Bottom-left

                // First triangle
                _mm_stream_si128(&dstP[0], src[1]); // Top-right
                _mm_stream_si128(&dstP[1], src[0]); // Top-left
                _mm_stream_si128(&dstP[2], src[3]); // Bottom-left

                // Second triangle
                _mm_stream_si128(&dstP[3], src[3]); // Bottom-left
                _mm_stream_si128(&dstP[4], src[2]); // Bottom-right
                _mm_stream_si128(&dstP[5], src[1]); // Top-right

                out += 6;
            }
        } else
#endif // HAVE_SSE2
        {
            for (int i = 0; i < quads.count(); i++) {
                const WindowQuad &quad = quads[i];
                KWin::GLVertex2D v[4]; // Four unique vertices / quad

                for (int j = 0; j < 4; j++) {
                    const WindowVertex &wv = quad[j];

                    v[j].position = QVector2D(wv.x(), wv.y());
                    v[j].texcoord = QVector2D(wv.u(), wv.v()) * scale + shift;
                }

                // First triangle
                *(out++) = v[1]; // Top-right
                *(out++) = v[0]; // Top-left
                *(out++) = v[3]; // Bottom-left

                // Second triangle
                *(out++) = v[3]; // Bottom-left
                *(out++) = v[2]; // Bottom-right
                *(out++) = v[1]; // Top-right
            }
        }
        break;

    default:
        break;
    }
}

void WindowMeshRenderer::render(KWin::EffectWindow *window, const QVector<WindowQuad> &quads,
                                KWin::GLTexture *texture, const QRegion &clipRegion) const
{
    KWin::GLShader *shader = KWin::ShaderManager::instance()->pushShader(KWin::ShaderTrait::MapTexture);

    QMatrix4x4 modelViewProjection;
    const QRect screenRect = KWin::effects->virtualScreenGeometry();
    modelViewProjection.ortho(0, screenRect.width(), screenRect.height(), 0, 0, 65535);
    modelViewProjection.translate(window->x(), window->y());
    shader->setUniform(KWin::GLShader::ModelViewProjectionMatrix, modelViewProjection);

    const GLenum primitiveType = KWin::GLVertexBuffer::supportsIndexedQuads() ? GL_QUADS : GL_TRIANGLES;
    const int verticesPerQuad = primitiveType == GL_QUADS ? 4 : 6;
    const size_t vboSize = verticesPerQuad * quads.count() * sizeof(KWin::GLVertex2D);

    KWin::GLVertexBuffer *vbo = KWin::GLVertexBuffer::streamingBuffer();
    auto map = static_cast<KWin::GLVertex2D *>(vbo->map(vboSize));
    uploadQuads(primitiveType, quads, texture->matrix(KWin::NormalizedCoordinates), map);
    vbo->unmap();

    vbo->bindArrays();

    glEnable(GL_SCISSOR_TEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA);

    texture->bind();
    texture->generateMipmaps();
    vbo->draw(clipRegion, primitiveType, 0, verticesPerQuad * quads.count(), true);
    texture->unbind();

    glDisable(GL_BLEND);
    glDisable(GL_SCISSOR_TEST);

    vbo->unbindArrays();

    KWin::ShaderManager::instance()->popShader();
}
