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
#include "common.h"

// kwineffects
#include <kwineffects.h>

#if KWIN_EFFECT_API_VERSION < KWIN_EFFECT_API_MAKE_VERSION(0, 226)
#include "hacks/TimeLine.h"
#endif

class WindowQuad;

/**
 * Model for the magic lamp animation.
 **/
class Model {
public:
    struct Parameters {
        // The duration of the squash stage.
        std::chrono::milliseconds squashDuration;

        // The duration of the stretch stage.
        std::chrono::milliseconds stretchDuration;

        // How long it takes to raise the window.
        std::chrono::milliseconds bumpDuration;

        // Defines shape of transformed windows.
        QEasingCurve shapeCurve;

        // The blend factor between Squash and Stretch stage.
        qreal shapeFactor;

        // How much the transformed window should be raised.
        int bumpDistance;
    };

    explicit Model(KWin::EffectWindow* window = nullptr);

    /**
     * This enum type is used to specify kind of the current animation.
     **/
    enum class AnimationKind {
        Minimize,
        Unminimize
    };

    /**
     * Starts animation with the given kind.
     *
     * @param kind Kind of the animation (minimize or unminimize).
     **/
    void start(AnimationKind kind);

    /**
     * Updates the model by @p delta milliseconds.
     **/
    void step(std::chrono::milliseconds delta);

    /**
     * Returns whether the animation is complete.
     **/
    bool done() const;

    /**
     * Applies the current state of the model to the given list of
     * window quads.
     *
     * @param quadds The list of window quads to be transformed.
     **/
    void apply(QVector<WindowQuad>& quads) const;

    /**
     * Returns the parameters of the model.
     **/
    Parameters parameters() const;

    /**
     * Sets parameters of the model.
     *
     * @param parameters The new paramaters.
     **/
    void setParameters(const Parameters& parameters);

    /**
     * Returns the associated window.
     **/
    KWin::EffectWindow* window() const;

    /**
     * Sets the associated window.
     *
     * @param window The window associated with this model.
     **/
    void setWindow(KWin::EffectWindow* window);

    /**
     * Returns whether the painted result has to be clipped.
     *
     * @see clipRegion
     **/
    bool needsClip() const;

    /**
     * Returns the clip region.
     *
     * @see needsClip
     **/
    QRegion clipRegion() const;

private:
    void applyBump(QVector<WindowQuad>& quads) const;
    void applyStretch1(QVector<WindowQuad>& quads) const;
    void applyStretch2(QVector<WindowQuad>& quads) const;
    void applySquash(QVector<WindowQuad>& quads) const;

    void updateMinimizeStage();
    void updateUnminimizeStage();

    int computeBumpDistance() const;
    qreal computeShapeFactor() const;

    Parameters m_parameters;

    enum class AnimationStage {
        Bump,
        Stretch1,
        Stretch2,
        Squash
    };

    KWin::EffectWindow* m_window;
    AnimationKind m_kind;
    AnimationStage m_stage;
    KWin::TimeLine m_timeLine;
    Direction m_direction;
    int m_bumpDistance;
    qreal m_shapeFactor;
    bool m_clip;
    bool m_done = false;
};
