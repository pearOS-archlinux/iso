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
#include <QEasingCurve>

// std
#include <chrono>

namespace KWin {

class TimeLine {
public:
    enum Direction {
        Forward,
        Backward
    };

    explicit TimeLine(std::chrono::milliseconds duration = std::chrono::milliseconds(1000),
        Direction direction = Forward)
        : m_duration(duration)
        , m_direction(direction)
    {
    }

    qreal progress() const
    {
        return static_cast<qreal>(m_elapsed.count()) / m_duration.count();
    }

    qreal value() const
    {
        const qreal t = progress();
        return m_easingCurve.valueForProgress(m_direction == Backward ? 1.0 - t : t);
    }

    void update(std::chrono::milliseconds delta)
    {
        Q_ASSERT(delta >= std::chrono::milliseconds::zero());
        if (m_done) {
            return;
        }
        m_elapsed += delta;
        if (m_elapsed >= m_duration) {
            m_done = true;
            m_elapsed = m_duration;
        }
    }

    std::chrono::milliseconds elapsed() const
    {
        return m_elapsed;
    }

    void setElapsed(std::chrono::milliseconds elapsed)
    {
        Q_ASSERT(elapsed >= std::chrono::milliseconds::zero());
        if (elapsed == m_elapsed) {
            return;
        }
        reset();
        update(elapsed);
    }

    std::chrono::milliseconds duration() const
    {
        return m_duration;
    }

    void setDuration(std::chrono::milliseconds duration)
    {
        Q_ASSERT(duration > std::chrono::milliseconds::zero());
        if (duration == m_duration) {
            return;
        }
        m_elapsed = std::chrono::milliseconds(qRound(progress() * duration.count()));
        m_duration = duration;
        if (m_elapsed == m_duration) {
            m_done = true;
        }
    }

    Direction direction() const
    {
        return m_direction;
    }

    void setDirection(Direction direction)
    {
        if (m_direction == direction) {
            return;
        }
        if (m_elapsed > std::chrono::milliseconds::zero()) {
            m_elapsed = m_duration - m_elapsed;
        }
        m_direction = direction;
    }

    void toggleDirection()
    {
        setDirection(m_direction == Forward ? Backward : Forward);
    }

    QEasingCurve easingCurve() const
    {
        return m_easingCurve;
    }

    void setEasingCurve(const QEasingCurve& easingCurve)
    {
        m_easingCurve = easingCurve;
    }

    void setEasingCurve(QEasingCurve::Type type)
    {
        m_easingCurve.setType(type);
    }

    bool running() const
    {
        return m_elapsed != std::chrono::milliseconds::zero()
            && m_elapsed != m_duration;
    }

    bool done() const
    {
        return m_done;
    }

    void reset()
    {
        m_elapsed = std::chrono::milliseconds::zero();
        m_done = false;
    }

private:
    std::chrono::milliseconds m_duration;
    Direction m_direction;
    QEasingCurve m_easingCurve;

    std::chrono::milliseconds m_elapsed = std::chrono::milliseconds::zero();
    bool m_done = false;
};

} // namespace KWin
