"""
FRIDAY AI — Orange Sci-Fi Core Visualizer v1.2.0
Matches reference image:
  - Concentric metallic dark rings with glowing orange segmented arcs & radial notches
  - Glowing FRIDAY diamond emblem with inner sci-fi chevron
  - Bold futuristic "FRIDAY" text in amber/orange glow
  - Symmetrical audio waveform spectrum bars inside lower half of the reactor core
"""

import math
import sys
from pathlib import Path

_root_dir = str(Path(__file__).resolve().parent.parent)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

# Orange Sci-Fi palette tokens
_ORANGE      = QColor(0xFF, 0x79, 0x00)
_AMBER       = QColor(0xFF, 0xAA, 0x33)
_PALE        = QColor(0xFF, 0xD0, 0x8A)
_BG_DARK     = QColor(0x0A, 0x0A, 0x0C)
_CHARCOAL    = QColor(0x14, 0x14, 0x18)
_METALLIC    = QColor(0x22, 0x22, 0x28)
_RED         = QColor(0xEF, 0x44, 0x44)
_GREEN       = QColor(0x22, 0xC5, 0x5E)


def _alpha(c: QColor, a: int) -> QColor:
    nc = QColor(c)
    nc.setAlpha(min(255, max(0, a)))
    return nc


class CoreVisualizerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)

        self._angle_outer  = 0.0
        self._angle_mid    = 0.0
        self._angle_inner  = 0.0
        self._pulse_val    = 0.0
        self._pulse_dir    = 1
        self._wave_phase   = 0.0
        self._state        = "IDLE"

        # 60 FPS animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def set_state(self, state: str):
        self._state = state.upper()
        self.update()

    # ─── animation tick ────────────────────────────────────────────────────────

    def _tick(self):
        sf = 1.0
        if self._state in ("PROCESSING", "EXECUTING"):
            sf = 2.8
        elif self._state in ("LISTENING", "SPEAKING"):
            sf = 2.0
        elif self._state == "STOPPED":
            sf = 0.1

        self._angle_outer  = (self._angle_outer  + 0.40 * sf) % 360
        self._angle_mid    = (self._angle_mid    - 0.65 * sf) % 360
        self._angle_inner  = (self._angle_inner  + 0.90 * sf) % 360
        self._wave_phase  += 0.09 * sf

        self._pulse_val += 0.02 * self._pulse_dir * sf
        if self._pulse_val >= 1.0:
            self._pulse_val, self._pulse_dir = 1.0, -1
        elif self._pulse_val <= 0.0:
            self._pulse_val, self._pulse_dir = 0.0, 1

        self.update()

    # ─── painting ─────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        w, h = self.width(), self.height()
        size = min(w, h)
        cx, cy = w / 2.0, h / 2.0
        center = QPointF(cx, cy)
        R = size / 2.0 - 18

        # Colors by state
        if self._state == "STOPPED":
            pri, sec = _RED, QColor(255, 120, 120)
        elif self._state == "LISTENING":
            pri, sec = _AMBER, _PALE
        elif self._state in ("PROCESSING", "EXECUTING"):
            pri, sec = _ORANGE, _AMBER
        elif self._state == "SPEAKING":
            pri, sec = _GREEN, _AMBER
        else:
            pri, sec = _ORANGE, _AMBER

        # ── 1. Outer Deep Atmospheric Glow ────────────────────────────────
        halo = QRadialGradient(center, R + 28)
        halo.setColorAt(0.0, _alpha(pri, 40))
        halo.setColorAt(0.55, _alpha(pri, 14))
        halo.setColorAt(1.0, _alpha(pri, 0))
        painter.setBrush(QBrush(halo))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, R + 28, R + 28)

        # ── 2. Outer Heavy Metallic Ring Chassis ──────────────────────────
        outer_rim = QRadialGradient(center, R)
        outer_rim.setColorAt(0.70, _CHARCOAL)
        outer_rim.setColorAt(0.88, _METALLIC)
        outer_rim.setColorAt(0.96, QColor(0x10, 0x10, 0x14))
        outer_rim.setColorAt(1.0, _BG_DARK)
        painter.setBrush(QBrush(outer_rim))
        painter.setPen(QPen(_alpha(pri, 60), 1.5))
        painter.drawEllipse(center, R, R)

        # ── 3. Outer Segmented Glowing Arcs (4 thick arcs) ────────────────
        self._draw_thick_arcs(painter, center, R - 6, 4, 62, 5.0, pri, self._angle_outer)

        # ── 4. Intermediate Groove & Notch Ring ───────────────────────────
        self._draw_groove_ring(painter, center, R * 0.82, R * 0.74, pri, self._angle_mid)

        # ── 5. Inner Core Base Floor ──────────────────────────────────────
        inner_r = R * 0.65
        core_grad = QRadialGradient(center, inner_r)
        core_grad.setColorAt(0.0, QColor(0x1C, 0x0E, 0x02))
        core_grad.setColorAt(0.60, QColor(0x12, 0x08, 0x01))
        core_grad.setColorAt(0.92, QColor(0x0C, 0x0A, 0x0E))
        core_grad.setColorAt(1.0, _alpha(pri, 80))
        painter.setBrush(QBrush(core_grad))
        painter.setPen(QPen(pri, 2.0))
        painter.drawEllipse(center, inner_r, inner_r)

        # Inner ring subtle pulse circle
        pulse_r = inner_r * 0.95 + self._pulse_val * 2
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(_alpha(sec, int(70 + self._pulse_val * 45)), 1.2))
        painter.drawEllipse(center, pulse_r, pulse_r)

        # ── 6. Diamond Logo (positioned in upper half of core) ────────────
        logo_y = cy - inner_r * 0.28
        logo_center = QPointF(cx, logo_y)
        logo_size = inner_r * 0.36 + self._pulse_val * 3
        self._draw_diamond_emblem(painter, logo_center, logo_size, pri, sec)

        # ── 7. Text "FRIDAY" below Diamond ────────────────────────────────
        text_y = logo_y + logo_size * 0.78
        self._draw_friday_text(painter, cx, text_y, inner_r * 0.30, pri, sec)

        # ── 8. Audio Waveform Spectrum inside lower half of reactor ───────
        wave_y = cy + inner_r * 0.44
        self._draw_inner_waveform(painter, cx, wave_y, inner_r * 1.35, pri, sec)

    # ── Arc segments ──────────────────────────────────────────────────────────

    def _draw_thick_arcs(self, painter, center, r, n_segs, span_deg, pen_w, col, angle):
        painter.save()
        painter.translate(center)
        painter.rotate(angle)

        pen = QPen(col, pen_w)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        rect = QRectF(-r, -r, r * 2, r * 2)
        gap = (360.0 - n_segs * span_deg) / n_segs

        for i in range(n_segs):
            start = int((i * (span_deg + gap) + 4) * 16)
            painter.drawArc(rect, start, int(span_deg * 16))

        # Radial notches on the outer edge
        notch_pen = QPen(_alpha(col, 120), 1.5)
        painter.setPen(notch_pen)
        for d in range(0, 360, 15):
            rd = math.radians(d)
            x1 = (r - 2) * math.cos(rd)
            y1 = (r - 2) * math.sin(rd)
            x2 = (r + 4) * math.cos(rd)
            y2 = (r + 4) * math.sin(rd)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        painter.restore()

    def _draw_groove_ring(self, painter, center, r_outer, r_inner, col, angle):
        painter.save()
        painter.translate(center)
        painter.rotate(angle)

        # Thin circular guide rails
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(_alpha(col, 45), 1.0))
        painter.drawEllipse(QPointF(0, 0), r_outer, r_outer)
        painter.drawEllipse(QPointF(0, 0), r_inner, r_inner)

        # 8 smaller luminous arc segments
        seg_pen = QPen(_alpha(col, 170), 2.5)
        seg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(seg_pen)
        rect = QRectF(-r_inner, -r_inner, r_inner * 2, r_inner * 2)
        for i in range(8):
            start = int((i * 45 + 5) * 16)
            painter.drawArc(rect, start, int(28 * 16))

        painter.restore()

    # ── Diamond emblem matching reference image ──────────────────────────────

    def _draw_diamond_emblem(self, painter, center, size, pri, sec):
        cx, cy = center.x(), center.y()
        s = size

        # Outer diamond path
        diamond = QPainterPath()
        diamond.moveTo(cx, cy - s)
        diamond.lineTo(cx + s * 0.95, cy)
        diamond.lineTo(cx, cy + s)
        diamond.lineTo(cx - s * 0.95, cy)
        diamond.closeSubpath()

        # Dark core fill with orange glow
        fill_grad = QRadialGradient(center, s)
        fill_grad.setColorAt(0.0, QColor(0x35, 0x1A, 0x02))
        fill_grad.setColorAt(0.70, QColor(0x1A, 0x0C, 0x02))
        fill_grad.setColorAt(1.0, QColor(0x0C, 0x06, 0x01))
        painter.setBrush(QBrush(fill_grad))
        painter.setPen(QPen(pri, 2.5))
        painter.drawPath(diamond)

        # Inner beveled diamond border
        s2 = s * 0.72
        inner = QPainterPath()
        inner.moveTo(cx, cy - s2)
        inner.lineTo(cx + s2 * 0.95, cy)
        inner.lineTo(cx, cy + s2)
        inner.lineTo(cx - s2 * 0.95, cy)
        inner.closeSubpath()
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(_alpha(sec, 120), 1.2))
        painter.drawPath(inner)

        # Stylized Inverted Chevron / "7" symbol inside
        # (Matches the distinct futuristic AI glyph from the reference image)
        glyph = QPainterPath()
        gx = s * 0.38
        gy = s * 0.42
        glyph.moveTo(cx - gx, cy - gy)          # top left
        glyph.lineTo(cx + gx, cy - gy)          # top right
        glyph.lineTo(cx + gx * 0.15, cy + gy)   # bottom point
        glyph.lineTo(cx - gx * 0.25, cy + gy)   # bottom left
        glyph.lineTo(cx + gx * 0.35, cy - gy * 0.45) # inner diagonal
        glyph.lineTo(cx - gx, cy - gy * 0.45)   # inner horizontal
        glyph.closeSubpath()

        glyph_grad = QLinearGradient(cx, cy - gy, cx, cy + gy)
        glyph_grad.setColorAt(0.0, QColor(255, 255, 255, 245))
        glyph_grad.setColorAt(0.4, _alpha(sec, 250))
        glyph_grad.setColorAt(1.0, _alpha(pri, 240))
        painter.setBrush(QBrush(glyph_grad))
        painter.setPen(Qt.NoPen)
        painter.drawPath(glyph)

        # Second parallel accent blade
        blade = QPainterPath()
        bx = gx * 0.65
        blade.moveTo(cx + gx * 0.45, cy - gy * 0.20)
        blade.lineTo(cx + gx * 0.85, cy - gy * 0.20)
        blade.lineTo(cx + gx * 0.40, cy + gy * 0.80)
        blade.lineTo(cx + gx * 0.10, cy + gy * 0.80)
        blade.closeSubpath()
        painter.setBrush(QBrush(_alpha(sec, 220)))
        painter.drawPath(blade)

    # ── Bold "FRIDAY" text ────────────────────────────────────────────────────

    def _draw_friday_text(self, painter, cx, cy, font_size, pri, sec):
        font = QFont("Segoe UI", max(9, int(font_size * 0.52)), QFont.Bold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 3.5)
        painter.setFont(font)

        # Subtle text glow
        glow_col = _alpha(pri, 60)
        painter.setPen(QPen(glow_col))
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            painter.drawText(QRectF(cx - 80 + dx, cy + dy, 160, 26), Qt.AlignCenter, "FRIDAY")

        # Sharp main text
        painter.setPen(QPen(sec))
        painter.drawText(QRectF(cx - 80, cy, 160, 26), Qt.AlignCenter, "FRIDAY")

    # ── Inner Waveform Spectrum inside lower half of circle ────────────────────

    def _draw_inner_waveform(self, painter, cx, cy, total_w, pri, sec):
        """
        Draws symmetrical glowing audio spectrum bars directly inside the
        lower half of the Arc Reactor core, matching the reference image.
        """
        n_bars = 27
        bar_w = 3.0
        gap = 2.2
        span = n_bars * (bar_w + gap)
        start_x = cx - span / 2.0
        mid_idx = (n_bars - 1) / 2.0

        for i in range(n_bars):
            # Symmetrical gaussian envelope: tallest in center, tapering to sides
            dist = abs(i - mid_idx) / mid_idx
            env = math.exp(-2.2 * dist * dist)

            if self._state in ("LISTENING", "SPEAKING"):
                base_h = 24.0 * env
                wave = abs(math.sin(i * 0.45 + self._wave_phase)) * 14.0 * env
            elif self._state in ("PROCESSING", "EXECUTING"):
                base_h = 16.0 * env
                wave = abs(math.sin(i * 0.35 + self._wave_phase * 1.5)) * 9.0 * env
            else:
                base_h = 8.0 * env
                wave = abs(math.sin(i * 0.25 + self._pulse_val * 3.0)) * 4.0 * env

            h = max(2.5, base_h + wave)
            bx = start_x + i * (bar_w + gap)
            by = cy - h / 2.0

            # Gradient bar with rounded tip
            bar_grad = QLinearGradient(bx, by, bx, by + h)
            bar_grad.setColorAt(0.0, _alpha(sec, int(200 + env * 55)))
            bar_grad.setColorAt(0.5, _alpha(pri, 240))
            bar_grad.setColorAt(1.0, _alpha(sec, int(150 + env * 80)))

            painter.setBrush(QBrush(bar_grad))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(bx, by, bar_w, h), 1.5, 1.5)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QVBoxLayout
    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("FRIDAY Core Visualizer Preview")
    win.resize(460, 460)
    win.setStyleSheet("background: #0A0A0C;")
    lay = QVBoxLayout(win)
    viz = CoreVisualizerWidget()
    lay.addWidget(viz, 1)
    btn_lay = QHBoxLayout()
    for st in ["IDLE", "LISTENING", "PROCESSING", "SPEAKING", "STOPPED"]:
        b = QPushButton(st)
        b.setStyleSheet("color: #FF7900; border: 1px solid #FF7900; padding: 4px 10px; border-radius: 4px; background: #1a0a00;")
        b.clicked.connect(lambda _, s=st: viz.set_state(s))
        btn_lay.addWidget(b)
    lay.addLayout(btn_lay)
    win.show()
    sys.exit(app.exec())
