"""A GTK3 recreation of Cubic's compression-selection widget: a diagonal
grid of radio buttons over a gradient triangle, with axis labels for
Compression / Size / Speed trade-offs. Cubic draws this from a static SVG
(compression-grid.svg) sitting under 5 GtkRadioButtons in a 7x7 GtkGrid;
this recreates the same layout with Cairo instead of shipping the asset,
so it scales cleanly and needs no extra file.
"""

from __future__ import annotations

import math

import cairo
from gi.repository import Gtk


class CompressionTriangle(Gtk.Overlay):
    """options: ordered list of (key, label, tooltip) from fastest/biggest
    to slowest/smallest -- placed on the diagonal top-left to bottom-right,
    exactly like Cubic's lz4 -> lzo -> gzip -> zstd -> xz row.
    """

    SIZE = 360

    def __init__(self, options):
        super().__init__()
        self.options = options
        n = len(options)

        self.canvas = Gtk.DrawingArea()
        self.canvas.set_size_request(self.SIZE, self.SIZE)
        self.canvas.connect("draw", self._on_draw)
        self.add(self.canvas)

        grid = Gtk.Grid(row_homogeneous=True, column_homogeneous=True)
        grid.set_size_request(self.SIZE, self.SIZE)

        # Outer ring (row/col 0 and n+1) is reserved for axis labels, same
        # as Cubic's 7x7 grid around its 5x5 diagonal.
        top = Gtk.Label(label="⊲  Lower Compression", xalign=0.5)
        grid.attach(top, 0, 0, n + 2, 1)
        bottom = Gtk.Label(label="Higher Compression  ⊳", xalign=0.5)
        grid.attach(bottom, 0, n + 1, n + 2, 1)

        left = Gtk.Label(label="Larger Size  ⊳", angle=90)
        grid.attach(left, 0, 0, 1, n + 2)
        right = Gtk.Label(label="Smaller Size  ⊳", angle=270)
        grid.attach(right, n + 1, 0, 1, n + 2)

        faster = Gtk.Label(label="Faster", angle=45)
        faster.set_opacity(0.5)
        faster.set_size_request(1, 1)
        grid.attach(faster, 1, 1, 2, 2)
        slower = Gtk.Label(label="Slower", angle=45)
        slower.set_opacity(0.5)
        slower.set_size_request(1, 1)
        grid.attach(slower, n - 1, n - 1, 2, 2)

        self.radios = {}
        first = None
        for i, (key, label, tooltip) in enumerate(options):
            radio = Gtk.RadioButton.new_with_label_from_widget(first, label)
            if first is None:
                first = radio
                radio.set_active(True)
            radio.set_tooltip_text(tooltip)
            radio.set_halign(Gtk.Align.START)
            radio.set_valign(Gtk.Align.CENTER)
            grid.attach(radio, 1 + i, 1 + i, 2, 1)
            self.radios[key] = radio
            radio.connect("toggled", lambda _b: self.canvas.queue_draw())

        self.add_overlay(grid)
        self.set_overlay_pass_through(grid, False)

    def get_active_key(self):
        for key, radio in self.radios.items():
            if radio.get_active():
                return key
        return None

    def set_active_key(self, key):
        radio = self.radios.get(key)
        if radio is not None:
            radio.set_active(True)

    def _on_draw(self, _widget, cr):
        w = self.canvas.get_allocated_width()
        h = self.canvas.get_allocated_height()
        n = len(self.options)
        margin = min(w, h) * 0.12
        size = min(w, h) - 2 * margin

        # Gradient triangle, same idea as Cubic's rounded corner-cut shape:
        # darker toward the "faster/bigger" corner, lighter toward
        # "slower/smaller".
        pat = cairo.LinearGradient(margin, margin, margin + size, margin + size)
        pat.add_color_stop_rgba(0.0, 0.36, 0.36, 0.35, 0.35)
        pat.add_color_stop_rgba(1.0, 0.92, 0.91, 0.90, 0.45)

        # Rounded square with the top-right corner chamfered off (a
        # straight diagonal cut, not rounded) -- that missing corner is
        # what reads as a triangle, same trick Cubic's SVG uses. Corners
        # go clockwise from top-left: round, chamfer (top-right), round,
        # round.
        r = size * 0.10
        chamfer = size * 0.28
        x0, y0 = margin, margin
        x1, y1 = margin + size, margin + size
        cr.new_path()
        cr.move_to(x0 + r, y0)
        cr.line_to(x1 - chamfer, y0)
        cr.line_to(x1, y0 + chamfer)
        cr.line_to(x1, y1 - r)
        cr.arc(x1 - r, y1 - r, r, 0, math.pi / 2)
        cr.line_to(x0 + r, y1)
        cr.arc(x0 + r, y1 - r, r, math.pi / 2, math.pi)
        cr.line_to(x0, y0 + r)
        cr.arc(x0 + r, y0 + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.set_source(pat)
        cr.fill()

        # Dashed grid lines, one per diagonal step (matches Cubic's 5 lines
        # in each direction).
        cr.set_source_rgba(0.68, 0.65, 0.62, 0.6)
        cr.set_line_width(1)
        cr.set_dash([1, 4])
        step = size / n
        for i in range(1, n + 1):
            pos = margin + step * i - step / 2
            cr.move_to(margin, pos)
            cr.line_to(margin + size, pos)
            cr.move_to(pos, margin)
            cr.line_to(pos, margin + size)
        cr.stroke()
        cr.set_dash([])
