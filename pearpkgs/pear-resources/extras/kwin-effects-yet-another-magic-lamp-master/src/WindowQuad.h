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

// Qt
#include <QPointF>

class WindowVertex {
public:
    WindowVertex() = default;
    WindowVertex(const QPointF& position, const QPointF& texcoord)
        : m_x(position.x())
        , m_y(position.y())
        , m_u(texcoord.x())
        , m_v(texcoord.y())
    {
    }

    WindowVertex(const WindowVertex& other) = default;
    WindowVertex(WindowVertex&& other) = default;
    WindowVertex& operator=(const WindowVertex& other) = default;
    WindowVertex& operator=(WindowVertex&& other) = default;

    qreal x() const { return m_x; }
    void setX(qreal x) { m_x = x; }

    qreal y() const { return m_y; }
    void setY(qreal y) { m_y = y; }

    qreal u() const { return m_u; }
    void setU(qreal u) { m_u = u; }

    qreal v() const { return m_v; }
    void setV(qreal v) { m_v = v; }

private:
    qreal m_x = 0.0;
    qreal m_y = 0.0;
    qreal m_u = 0.0;
    qreal m_v = 0.0;
};

class WindowQuad {
public:
    // Compiler generated constructors are fine.

    WindowVertex& operator[](int index)
    {
        return m_vertices[index];
    }

    const WindowVertex& operator[](int index) const
    {
        return m_vertices[index];
    }

private:
    WindowVertex m_vertices[4];
};
