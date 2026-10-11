#!/usr/bin/env python3
"""
PySide6 Unicode Graphics Engine v3
Full Unicode rendering with interactive controls, new scenes, and visual enhancements.

Scenes: 3D Cube, Multi-Cube, Terrain, Particles, Emojis, Unicode Showcase,
        Plasma, Starfield, Fractal, Combined
Features: Mouse interaction, keyboard shortcuts, screenshot, pause, fullscreen,
          half-block 2x vertical resolution, bloom, dithering, background stars.
"""

import sys, math, random, time, os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFrame, QSizePolicy, QComboBox, QCheckBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QPainter, QFont, QColor, QPalette, QPixmap
)

# ─── Shared Constants ────────────────────────────────────────────────
COLS = 100
ROWS = 40
FONT_W = 9
FONT_H = 16

# ─── Bayer 4x4 dithering matrix (normalized 0-1) ────────────────────
BAYER_4 = [
    [0.0,  8.0,  2.0, 10.0],
    [12.0, 4.0, 14.0,  6.0],
    [3.0, 11.0,  1.0,  9.0],
    [15.0, 7.0, 13.0,  5.0],
]
for _r in range(4):
    for _c in range(4):
        BAYER_4[_r][_c] = (BAYER_4[_r][_c] + 0.5) / 16.0

# ─── FULL UNICODE CHARACTER SETS ────────────────────────────────────
BRAILLE_BASE = 0x2800
BRAILLE_LOOKUP = {}
for _v in range(256):
    BRAILLE_LOOKUP[_v] = chr(BRAILLE_BASE + _v)

# FIX: Added braille density ordering for smooth visual ramps.
# Previously, PlasmaScene style 2 used raw index order which is chaotic
# (ordered by bit pattern, not visual density). This creates a proper
# density-sorted ramp from empty (0 dots) to full (8 dots).
BRAILLE_DENSITY_ORDER = sorted(range(256), key=lambda v: (bin(v).count('1'), v))
BRAILLE_DENSITY_CHARS = [BRAILLE_LOOKUP[v] for v in BRAILLE_DENSITY_ORDER]

# Correct braille bit mapping: Unicode braille uses column-major ordering
# where dots 1-3 (left col, rows 0-2) map to bits 0-2,
# dots 4-6 (right col, rows 0-2) map to bits 3-5,
# dots 7-8 (bottom row, left-right) map to bits 6-7.
BRAILLE_BIT_MAP = [
    [0, 3],  # row 0: left=bit0(dot1), right=bit3(dot4)
    [1, 4],  # row 1: left=bit1(dot2), right=bit4(dot5)
    [2, 5],  # row 2: left=bit2(dot3), right=bit5(dot6)
    [6, 7],  # row 3: left=bit6(dot7), right=bit7(dot8)
]

BLOCK_RAMP = list(" ░▒▓█")
SHADE_RAMP_ASCII  = " .:-=+*#%@"

BOX_SINGLE = {'tl':'┌','tr':'┐','bl':'└','br':'┘','h':'─','v':'│','t':'┬','b':'┴','l':'├','r':'┤','cross':'┼'}
BOX_DOUBLE = {'tl':'╔','tr':'╗','bl':'╚','br':'╝','h':'═','v':'║','t':'╦','b':'╩','l':'╠','r':'╣','cross':'╬'}
BOX_ROUNDED = {'tl':'╭','tr':'╮','bl':'╰','br':'╯','h':'─','v':'│','t':'┬','b':'┴','l':'├','r':'┤','cross':'┼'}
BOX_HEAVY = {'tl':'┏','tr':'┓','bl':'┗','br':'┛','h':'━','v':'┃','t':'┳','b':'┻','l':'┣','r':'┫','cross':'╋'}
ALL_BOX = [BOX_SINGLE, BOX_DOUBLE, BOX_ROUNDED, BOX_HEAVY]

# Deterministic axis-to-box-style mapping (replaces non-deterministic hash)
AXIS_BOX_IDX = {'x': 0, 'y': 1, 'z': 2}

ARROWS = list("←→↑↓↖↗↘↙⇐⇒⇑⇓↩↪↰↱↴↵➜➡➢➣➤➥➦➧➨➩➪➫➬➭➮➯➱➲➳➴➵➶➷➸➹➺➻➼➽➾➔➘➙➚➛➝➞➟↝↠↞↟↣↦↤↥⇄⇅⇆⇇⇈⇉⇊⇋⇌⇍⇎⇏")
SHAPES_SOLID = list("●◆■▲▼★⬟⬠⬡⬢⬣⬤◯◇□△▽☆")
SHAPES_OUTLINE = list("○◇□△▽☆✦✧✩✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿❀❁❂❃❇❈❉❊❋")
MATH_SYMBOLS = list("∑∏∫∮∂∇√∞≈≠≡≤≥±×÷∓⊕⊗⊙⊚⊡ΞΨΦΩαβγδεζηθλμπρσφψω")
CHESS_WHITE = list("♔♕♖♗♘♙"); CHESS_BLACK = list("♚♛♜♝♞♟")

# FIX: Removed duplicate currency symbols. The original list had ₹, ₽, and ₿
# appearing twice each, causing duplicate display in the Unicode Showcase.
CURRENCY = list("$€£¥¢₿₽₹₩₪₫₭₮₯₰₱₲₳₴₵₶₷₸₺₻₼₾")
ZODIAC = list("♈♉♊♋♌♍♎♏♐♑♒♓")
MUSIC = list("♩♪♫♬𝄞𝄢𝄡♭♮♯")
DICE = list("⚀⚁⚂⚃⚄⚅")
DINGBATS = list("✁✂✃✄✆✇✈✉✊✋✌✍✎✏✐✑✒✓✔✕✖✗✘✙✚✛✜✝✞✟✠✡✢✣✤✥✦✧✩✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿❀❁❂❃❄❅❆❇❈❉❊❋")
HEARTS = list("♥♡❤❥❣❦❧")
STARS = list("☆★✦✧✩✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿")

# ─── Color Palette ───────────────────────────────────────────────────
class C:
    BG = QColor(10, 10, 18); GRID = QColor(30, 30, 45)
    CYAN = QColor(0, 220, 255); GREEN = QColor(0, 255, 130)
    MAGENTA = QColor(255, 50, 200); YELLOW = QColor(255, 230, 50)
    ORANGE = QColor(255, 140, 30); RED = QColor(255, 60, 60)
    WHITE = QColor(240, 240, 250); BLUE = QColor(60, 120, 255)
    PURPLE = QColor(180, 80, 255); PINK = QColor(255, 105, 180)
    LIME = QColor(180, 255, 50); TEAL = QColor(0, 200, 180)
    GOLD = QColor(255, 200, 50); CORAL = QColor(255, 127, 80)
    LAVENDER = QColor(200, 160, 255)

PALETTE_ALL = [C.CYAN, C.GREEN, C.MAGENTA, C.YELLOW, C.ORANGE, C.RED,
               C.BLUE, C.PURPLE, C.PINK, C.LIME, C.TEAL, C.GOLD, C.CORAL, C.LAVENDER]

# ─── 3D Math ─────────────────────────────────────────────────────────
def rot_x(p, a):
    x, y, z = p; c, s = math.cos(a), math.sin(a)
    return (x, y*c - z*s, y*s + z*c)
def rot_y(p, a):
    x, y, z = p; c, s = math.cos(a), math.sin(a)
    return (x*c + z*s, y, -x*s + z*c)
def rot_z(p, a):
    x, y, z = p; c, s = math.cos(a), math.sin(a)
    return (x*c - y*s, x*s + y*c, z)
def proj(p, fov=80, dist=6):
    x, y, z = p; f = fov / (dist + z)
    return (x*f + COLS/2, -y*f + ROWS/2, z)
def lerp(a, b, t): return a + (b - a) * t
def clamp(v, lo, hi): return max(lo, min(hi, v))
def hsv(h, s=1.0, v=1.0): return QColor.fromHsvF((h % 360) / 360.0, clamp(s,0,1), clamp(v,0,1))

# ─── Noise ────────────────────────────────────────────────────────────
def simple_noise(x, y, seed=42):
    def h2d(ix, iy):
        n = ix*374761393 + iy*668265263 + seed
        n = (n ^ (n >> 13)) * 1274126177; n = n ^ (n >> 16)
        return (n & 0x7fffffff) / 0x7fffffff
    ix, iy = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - ix, y - iy
    fx = fx*fx*(3 - 2*fx); fy = fy*fy*(3 - 2*fy)
    return lerp(lerp(h2d(ix,iy), h2d(ix+1,iy), fx), lerp(h2d(ix,iy+1), h2d(ix+1,iy+1), fx), fy)

def fbm(x, y, octaves=5, seed=42):
    v = 0.0; a = 0.5; f = 1.0
    for _ in range(octaves):
        v += a * simple_noise(x*f, y*f, seed); a *= 0.5; f *= 2.0
    return v

# ─── Background Stars ────────────────────────────────────────────────
def make_stars(n=120):
    return [(random.randint(0, COLS-1), random.randint(0, ROWS-1),
             random.uniform(0.2, 1.0), random.uniform(0.5, 3.0)) for _ in range(n)]

def draw_stars(canvas, stars, t, color_base=None):
    cb = color_base or C.WHITE
    for sx, sy, brightness, speed in stars:
        twinkle = (math.sin(t * speed + sx * 0.5 + sy * 0.3) * 0.3 + 0.7) * brightness
        if twinkle > 0.3:
            c = QColor(int(cb.red()*twinkle), int(cb.green()*twinkle), int(cb.blue()*twinkle))
            ch = '·' if twinkle < 0.5 else ('✦' if twinkle < 0.8 else '✧')
            canvas.set_char(sy, sx, ch, c)

# ─── Glow / Bloom Simulation ─────────────────────────────────────────
def draw_glow(canvas, cx, cy, radius, color, t=0):
    """Draw a soft glow using sparse braille dots fading outward."""
    # FIX: Removed redundant step=1 parameter (it's the default for range()).
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            dist = math.sqrt(dx*dx + dy*dy*0.5)
            if dist > radius:
                continue
            intensity = 1.0 - dist / radius
            intensity = intensity * intensity  # quadratic falloff
            if intensity < 0.05:
                continue
            x, y = int(cx + dx), int(cy + dy)
            if 0 <= y < ROWS and 0 <= x < COLS:
                alpha = intensity * (0.8 + 0.2 * math.sin(t * 4 + dist * 2))
                gc = QColor(int(color.red()*alpha), int(color.green()*alpha), int(color.blue()*alpha))
                ch = '⠿' if intensity > 0.6 else ('⠇' if intensity > 0.3 else '⠁')
                canvas.set_char(y, x, ch, gc)

# ─── Mandelbrot ──────────────────────────────────────────────────────
# FIX: Added cardioid and period-2 bulb early exit checks.
# Points inside these regions are guaranteed to be in the Mandelbrot set,
# so we can skip the full iteration. This provides ~40% speedup for
# typical views since a large fraction of the screen falls in these regions.
def mandelbrot(cx, cy, max_iter=64):
    # Cardioid check: skip points inside the main cardioid
    q = (cx - 0.25)**2 + cy*cy
    if q * (q + (cx - 0.25)) <= 0.25 * cy*cy:
        return max_iter
    # Period-2 bulb check: skip points inside the left bulb
    if (cx + 1.0)**2 + cy*cy <= 0.0625:
        return max_iter
    x = y = 0.0
    for i in range(max_iter):
        x2, y2 = x*x, y*y
        if x2 + y2 > 4.0:
            return i
        y = 2*x*y + cy
        x = x2 - y2 + cx
    return max_iter

# ─── Canvas Widget ───────────────────────────────────────────────────
class Canvas(QWidget):
    """Dual-buffer Unicode canvas with mouse interaction and screenshot support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(COLS * FONT_W, ROWS * FONT_H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._buf = [[' '] * COLS for _ in range(ROWS)]
        self._cbuf = [[C.WHITE] * COLS for _ in range(ROWS)]
        self._font = QFont("DejaVu Sans Mono", 10)
        self._font.setStyleHint(QFont.Monospace)
        self.setFont(self._font)
        self.setFocusPolicy(Qt.StrongFocus)
        self.mouse_pos = None      # (col, row) or None
        self.mouse_pressed = False
        self.mouse_drag_start = None
        self.mouse_clicks = []     # list of (col, row, time)

    def clear(self, ch=' ', color=None):
        c = color or C.WHITE
        # FIX: Reuse existing list objects with slice assignment to reduce
        # garbage collection pressure. Previously created 80 new list objects
        # per frame (40 rows * 2 buffers). Now creates only 2 temporary lists.
        row_buf = [ch] * COLS
        row_c = [c] * COLS
        for r in range(ROWS):
            self._buf[r][:] = row_buf
            self._cbuf[r][:] = row_c

    def set_char(self, r, c, ch, color=None):
        if 0 <= r < ROWS and 0 <= c < COLS:
            self._buf[r][c] = ch
            if color is not None:
                self._cbuf[r][c] = color

    def get_char(self, r, c):
        if 0 <= r < ROWS and 0 <= c < COLS:
            return self._buf[r][c], self._cbuf[r][c]
        return ' ', C.WHITE

    def draw_line(self, x0, y0, x1, y1, ch='*', color=None):
        c = color or C.CYAN
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx, dy = abs(x1-x0), abs(y1-y0)
        sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set_char(y0, x0, ch, c)
            if x0 == x1 and y0 == y1: break
            e2 = 2 * err
            if e2 > -dy: err -= dy; x0 += sx
            if e2 < dx: err += dx; y0 += sy

    def draw_box(self, x, y, w, h, box_set=None, color=None):
        """Draw a box using Unicode box-drawing characters."""
        b = box_set or BOX_DOUBLE
        c = color or C.CYAN
        for i in range(x, x + w):
            self.set_char(y, i, b['h'], c)
            self.set_char(y + h - 1, i, b['h'], c)
        for j in range(y, y + h):
            self.set_char(j, x, b['v'], c)
            self.set_char(j, x + w - 1, b['v'], c)
        self.set_char(y, x, b['tl'], c)
        self.set_char(y, x + w - 1, b['tr'], c)
        self.set_char(y + h - 1, x, b['bl'], c)
        self.set_char(y + h - 1, x + w - 1, b['br'], c)

    def draw_text(self, x, y, text, color=None):
        for i, ch in enumerate(text):
            self.set_char(y, x + i, ch, color or C.WHITE)

    def fill_rect(self, x, y, w, h, ch, color):
        # FIX: Changed self.canvas.set_char to self.set_char — this was a
        # crash bug (AttributeError) since Canvas has no 'canvas' attribute.
        # Also added max(0,...) guards for negative coordinates.
        for r in range(max(0, y), min(y + h, ROWS)):
            for c in range(max(0, x), min(x + w, COLS)):
                self.set_char(r, c, ch, color)

    def _cell_from_pixel(self, px, py):
        fm = self.fontMetrics()
        cw = fm.horizontalAdvance('M'); ch = fm.height()
        sx = self.width() / (COLS * cw); sy = self.height() / (ROWS * ch)
        s = min(sx, sy)
        ox = (self.width() - COLS * cw * s) / 2.0
        oy = (self.height() - ROWS * ch * s) / 2.0
        col = int((px - ox) / (s * cw))
        row = int((py - oy) / (s * ch))
        return max(0, min(COLS - 1, col)), max(0, min(ROWS - 1, row))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_pressed = True
            c, r = self._cell_from_pixel(event.position().x(), event.position().y())
            self.mouse_clicks.append((c, r, time.time()))
            self.mouse_drag_start = (c, r)

    def mouseReleaseEvent(self, event):
        self.mouse_pressed = False
        self.mouse_drag_start = None

    def mouseMoveEvent(self, event):
        self.mouse_pos = self._cell_from_pixel(event.position().x(), event.position().y())

    def keyPressEvent(self, event):
        event.ignore()

    def paintEvent(self, event):
        self._render_buffer()

    def take_screenshot(self):
        # FIX: Added HiDPI support. Previously screenshots were taken at 1x
        # resolution, appearing blurry on high-DPI displays. Now uses
        # devicePixelRatio for crisp capture on all displays.
        dpr = self.devicePixelRatioF() if hasattr(self, 'devicePixelRatioF') else self.devicePixelRatio()
        if dpr < 1.0:
            dpr = 1.0
        size = self.size()
        pixmap = QPixmap(int(size.width() * dpr), int(size.height() * dpr))
        pixmap.setDevicePixelRatio(dpr)
        self._render_buffer(pixmap)
        return pixmap

    def _render_buffer(self, target=None):
        painter = QPainter(self) if target is None else QPainter(target)
        try:
            painter.fillRect(self.rect() if target is None else target.rect(), C.BG)
            painter.setFont(self._font)
            fm = painter.fontMetrics()
            cw = fm.horizontalAdvance('M'); ch = fm.height()
            sx = self.width() / (COLS * cw) if target is None else target.width() / (COLS * cw)
            sy = self.height() / (ROWS * ch) if target is None else target.height() / (ROWS * ch)
            s = min(sx, sy)
            # FIX: Guard against zero, negative, and non-finite scale values.
            # Previously only checked s <= 0, which doesn't catch NaN/inf
            # from division by zero (e.g., when font metrics return 0).
            if s <= 0 or not math.isfinite(s):
                return
            content_w = COLS * cw * s
            content_h = ROWS * ch * s
            ox = (self.width() - content_w) / 2.0 if target is None else (target.width() - content_w) / 2.0
            oy = (self.height() - content_h) / 2.0 if target is None else (target.height() - content_h) / 2.0
            painter.translate(ox, oy)
            painter.scale(s, s)
            # Batch consecutive same-color characters into single drawText calls
            for r in range(ROWS):
                row_buf = self._buf[r]
                row_c = self._cbuf[r]
                c = 0
                while c < COLS:
                    char = row_buf[c]
                    if char == ' ':
                        c += 1
                        continue
                    color = row_c[c]
                    run_start = c
                    run_chars = [char]
                    c += 1
                    while c < COLS and row_buf[c] != ' ' and row_c[c] == color:
                        run_chars.append(row_buf[c])
                        c += 1
                    painter.setPen(color)
                    painter.drawText(run_start * cw, (r + 1) * ch - fm.descent(), ''.join(run_chars))
        finally:
            painter.end()


# ─── Scene: 3D Cube (Enhanced) ───────────────────────────────────────
class CubeScene:
    _stars = None

    def __init__(self, canvas):
        self.canvas = canvas; self.t = 0.0; self.style = 0
        self.drag_ax = self.drag_ay = 0.0  # mouse drag rotation
        s = 1.2
        self.verts = [(-s,-s,-s),(s,-s,-s),(s,s,-s),(-s,s,-s),
                       (-s,-s,s),(s,-s,s),(s,s,s),(-s,s,s)]
        self.faces = [(0,1,2,3),(4,5,6,7),(0,1,5,4),(2,3,7,6),(0,3,7,4),(1,2,6,5)]
        self.fcolors = [C.CYAN, C.GREEN, C.MAGENTA, C.YELLOW, C.ORANGE, C.RED]
        if CubeScene._stars is None:
            CubeScene._stars = make_stars(80)

    def _nz(self, v0, v1, v2):
        return (v1[0]-v0[0])*(v2[1]-v0[1]) - (v1[1]-v0[1])*(v2[0]-v0[0])

    def _bright(self, fv):
        e1 = (fv[1][0]-fv[0][0],fv[1][1]-fv[0][1],fv[1][2]-fv[0][2])
        e2 = (fv[3][0]-fv[0][0],fv[3][1]-fv[0][1],fv[3][2]-fv[0][2])
        nx, ny, nz = e1[1]*e2[2]-e1[2]*e2[1], e1[2]*e2[0]-e1[0]*e2[2], e1[0]*e2[1]-e1[1]*e2[0]
        l = math.sqrt(nx*nx+ny*ny+nz*nz)+1e-9
        return clamp(nz/l*0.577+0.4, 0.15, 1.0)

    def _scol(self, bc, b):
        return QColor(clamp(int(bc.red()*b),0,255), clamp(int(bc.green()*b),0,255), clamp(int(bc.blue()*b),0,255))

    def _schar(self, b, ramp=None):
        r = ramp or BLOCK_RAMP; i = int(b*(len(r)-1)); return r[clamp(i,0,len(r)-1)]

    def _fill_poly(self, projected, char, color):
        if len(projected) < 3: return
        my = max(0, int(min(p[1] for p in projected)))
        My = min(ROWS-1, int(max(p[1] for p in projected)))
        mx = max(0, int(min(p[0] for p in projected)))
        Mx = min(COLS-1, int(max(p[0] for p in projected)))
        n = len(projected)
        for y in range(my, My+1):
            ints = []
            for i in range(n):
                j = (i+1)%n; y0,y1 = projected[i][1],projected[j][1]; x0,x1 = projected[i][0],projected[j][0]
                if y0 == y1: continue
                if (y0 <= y < y1) or (y1 <= y < y0):
                    ints.append(x0 + (y-y0)/(y1-y0)*(x1-x0))
            ints.sort()
            for k in range(0, len(ints)-1, 2):
                for x in range(max(mx, int(math.ceil(ints[k]))), min(Mx, int(math.floor(ints[k+1])))+1):
                    self.canvas.set_char(y, x, char, color)

    def _fill_braille(self, projected, color):
        if len(projected) < 3: return
        n = len(projected)
        my = max(0, int(min(p[1] for p in projected))-1)
        My = min(ROWS-1, int(max(p[1] for p in projected))+1)
        mx = max(0, int(min(p[0] for p in projected))-1)
        Mx = min(COLS-1, int(max(p[0] for p in projected))+1)
        for br in range(my, My+1):
            for bc in range(mx//2, (Mx+2)//2):
                bits = 0
                for lr in range(4):
                    for lc in range(2):
                        px, py = bc*2+lc, br+lr*0.25
                        inside = False; j = n-1
                        for i in range(n):
                            xi,yi = projected[i][0],projected[i][1]; xj,yj = projected[j][0],projected[j][1]
                            if ((yi > py) != (yj > py)) and (px < (xj-xi)*(py-yi)/(yj-yi+1e-12)+xi):
                                inside = not inside
                            j = i
                        if inside: bits |= (1 << BRAILLE_BIT_MAP[lr][lc])
                if bits: self.canvas.set_char(br, bc, BRAILLE_LOOKUP[bits], color)

    def update(self, dt, clear=True, draw_stars_bg=True, update_canvas=True):
        self.t += dt
        ax = self.t * 0.5 + self.drag_ax
        ay = self.t * 0.7 + self.drag_ay
        az = self.t * 0.3

        if self.canvas.mouse_pressed and self.canvas.mouse_drag_start and self.canvas.mouse_pos is not None:
            mc, mr = self.canvas.mouse_pos
            sc, sr = self.canvas.mouse_drag_start
            self.drag_ay += (mc - sc) * 0.002
            self.drag_ax += (mr - sr) * 0.002
            self.canvas.mouse_drag_start = (mc, mr)

        trans = [rot_z(rot_y(rot_x(v, ax), ay), az) for v in self.verts]
        pr = [proj(v) for v in trans]

        fd = []
        for fi, face in enumerate(self.faces):
            v3 = [trans[i] for i in face]; v2 = [(pr[i][0], pr[i][1]) for i in face]
            az2 = sum(v[2] for v in v3)/4.0
            if self._nz(v2[0], v2[1], v2[2]) > 0:
                fd.append((az2, fi, v2))
        fd.sort(key=lambda f: -f[0])

        if clear:
            self.canvas.clear()
        if draw_stars_bg:
            draw_stars(self.canvas, self._stars, self.t, QColor(40, 40, 60))

        for _, fi, v2 in fd:
            b = self._bright([trans[i] for i in self.faces[fi]])
            col = self._scol(self.fcolors[fi], b)
            if self.style == 0:
                self._fill_poly(v2, self._schar(b, BLOCK_RAMP), col)
            elif self.style == 1:
                self._fill_braille(v2, col)
            else:
                self._fill_poly(v2, self._schar(b, SHADE_RAMP_ASCII), col)

        # Wireframe with cycling box styles
        bx = ALL_BOX[int(self.t * 0.3) % len(ALL_BOX)]
        edge_ch = bx['h']
        for fi, face in enumerate(self.faces):
            v2 = [(pr[i][0], pr[i][1]) for i in face]
            for i in range(4):
                j = (i+1)%4
                self.canvas.draw_line(v2[i][0],v2[i][1],v2[j][0],v2[j][1], edge_ch, self._scol(self.fcolors[fi], 0.95))

        # Mouse glow on hover
        if self.canvas.mouse_pos:
            mc, mr = self.canvas.mouse_pos
            draw_glow(self.canvas, mc, mr, 4, C.CYAN, self.t)

        if update_canvas:
            self.canvas.update()


# ─── Scene: Multi-Cube ──────────────────────────────────────────────
class MultiCubeScene:
    _stars = None

    def __init__(self, canvas):
        self.canvas = canvas; self.t = 0.0
        self.cube_data = [
            (0, 0, 1.5, 0.4, 'y', C.CYAN, '█'),
            (0, 0, 2.2, 0.3, 'x', C.GREEN, '▓'),
            (0, 0, 2.8, 0.25, 'z', C.MAGENTA, '▒'),
        ]
        if MultiCubeScene._stars is None:
            MultiCubeScene._stars = make_stars(60)

    def update(self, dt):
        self.t += dt; self.canvas.clear()
        draw_stars(self.canvas, self._stars, self.t, QColor(30, 30, 50))
        for ox, oy, sz, sp, ax, col, fc in reversed(self.cube_data):
            self._draw_cube(ox, oy, sz, sp, ax, col, fc)
        self.canvas.update()

    def _draw_cube(self, ox, oy, sz, sp, axis, bc, fc):
        s = sz/2
        vs = [(-s+ox,-s+oy,-s),(s+ox,-s+oy,-s),(s+ox,s+oy,-s),(-s+ox,s+oy,-s),
              (-s+ox,-s+oy,s),(s+ox,-s+oy,s),(s+ox,s+oy,s),(-s+ox,s+oy,s)]
        faces = [(0,1,2,3),(4,5,6,7),(0,1,5,4),(2,3,7,6),(0,3,7,4),(1,2,6,5)]
        t = self.t * sp
        rot = rot_x if axis=='x' else (rot_y if axis=='y' else rot_z)
        trans = [rot(v, t) for v in vs]
        pr = [proj(v) for v in trans]
        fd = []
        for fi, face in enumerate(faces):
            v2 = [(pr[i][0],pr[i][1]) for i in face]
            az = sum(trans[i][2] for i in face)/4.0
            nz = (v2[1][0]-v2[0][0])*(v2[2][1]-v2[0][1])-(v2[1][1]-v2[0][1])*(v2[2][0]-v2[0][0])
            if nz > 0: fd.append((az, v2))
        fd.sort(key=lambda f: -f[0])
        for _, v2 in fd:
            self._fill(v2, bc, fc)
        bx = ALL_BOX[AXIS_BOX_IDX.get(axis, 0) % len(ALL_BOX)]
        for fi, face in enumerate(faces):
            v2 = [(pr[i][0],pr[i][1]) for i in face]
            for i in range(4):
                j = (i+1)%4
                self.canvas.draw_line(v2[i][0],v2[i][1],v2[j][0],v2[j][1],bx['h'],bc)

    def _fill(self, proj, col, ch='█'):
        n = len(proj)
        my = max(0,int(min(p[1] for p in proj))); My = min(ROWS-1,int(max(p[1] for p in proj)))
        mx = max(0,int(min(p[0] for p in proj))); Mx = min(COLS-1,int(max(p[0] for p in proj)))
        for y in range(my, My+1):
            ints = []
            for i in range(n):
                j=(i+1)%n; y0,y1=proj[i][1],proj[j][1]; x0,x1=proj[i][0],proj[j][0]
                if y0==y1: continue
                if (y0<=y<y1) or (y1<=y<y0): ints.append(x0+(y-y0)/(y1-y0)*(x1-x0))
            ints.sort()
            for k in range(0, len(ints)-1, 2):
                for x in range(max(mx,int(math.ceil(ints[k]))), min(Mx,int(math.floor(ints[k+1])))+1):
                    self.canvas.set_char(y, x, ch, col)


# ─── Scene: Terrain (Enhanced with dithering & half-block) ───────────
class TerrainScene:
    def __init__(self, canvas):
        self.canvas = canvas; self.t = 0.0; self.style = 0

    def _hcol(self, h):
        bands = [(0,.3,C.BLUE,C.CYAN),(.3,.35,C.CYAN,C.YELLOW),(.35,.55,C.YELLOW,C.GREEN),
                 (.55,.7,C.GREEN,QColor(0,180,60)),(.7,.85,QColor(0,180,60),QColor(120,80,40)),
                 (.85,1.01,QColor(120,80,40),C.WHITE)]
        for lo,hi,c1,c2 in bands:
            if lo<=h<hi: t=(h-lo)/(hi-lo); return QColor(int(c1.red()+(c2.red()-c1.red())*t),int(c1.green()+(c2.green()-c1.green())*t),int(c1.blue()+(c2.blue()-c1.blue())*t))
        return C.WHITE

    def _height(self, c, r, gw, gh, ox, oy):
        nx=c/gw*5+ox; ny=r/gh*5+oy
        return clamp(fbm(nx,ny,5,42)+math.sin(nx*1.5+self.t*2)*0.03, 0, 1)

    def update(self, dt):
        self.t += dt; self.canvas.clear()
        ox, oy = self.t*2.0, self.t*0.5
        if self.style == 0: self._braille(ox, oy)
        elif self.style == 1: self._block(ox, oy)
        elif self.style == 2: self._symbols(ox, oy)
        elif self.style == 3: self._dithered(ox, oy)
        else: self._ascii(ox, oy)
        self.canvas.update()

    def _shadow(self, c, r, h, gw, gh, ox, oy):
        s = 1.0
        if c > 0: s = clamp(s - (h - self._height(c-1, r, gw, gh, ox, oy)) * 3, 0.3, 1.0)
        if r > 0: s = clamp(s - (h - self._height(c, r-1, gw, gh, ox, oy)) * 2, 0.3, 1.0)
        return s

    def _braille(self, ox, oy):
        gw, gh = COLS*2, ROWS*4
        for br in range(ROWS):
            for bc in range(COLS):
                bits = 0
                for lr in range(4):
                    for lc in range(2):
                        h = self._height(bc*2+lc, br*4+lr, gw, gh, ox, oy)
                        if h > 0.15: bits |= (1 << BRAILLE_BIT_MAP[lr][lc])
                if bits:
                    self.canvas.set_char(br, bc, BRAILLE_LOOKUP[bits],
                                         self._hcol(self._height(bc*2, br*4, gw, gh, ox, oy)))

    def _block(self, ox, oy):
        for r in range(ROWS):
            for c in range(COLS):
                h = self._height(c, r, COLS, ROWS, ox, oy)
                he = h * self._shadow(c, r, h, COLS, ROWS, ox, oy)
                i = int(he*(len(BLOCK_RAMP)-1))
                self.canvas.set_char(r, c, BLOCK_RAMP[clamp(i,0,len(BLOCK_RAMP)-1)], self._hcol(he))

    def _symbols(self, ox, oy):
        bands = [(0,.30,list("≈≋∿~∽")),(0.30,.35,list("·∙∘○●")),(0.35,.55,list("∗✦✧∧")),(0.55,.70,list("♣♠♤♡")),(0.70,.85,list("▲△▴▵")),(0.85,1.01,list("❄❅❆✻"))]
        for r in range(ROWS):
            for c in range(COLS):
                h = self._height(c, r, COLS, ROWS, ox, oy)
                he = h * self._shadow(c, r, h, COLS, ROWS, ox, oy)
                for lo,hi,syms in bands:
                    if lo<=h<hi:
                        i=int((h-lo)/(hi-lo)*(len(syms)-1))
                        self.canvas.set_char(r, c, syms[clamp(i,0,len(syms)-1)], self._hcol(he)); break

    def _dithered(self, ox, oy):
        """Terrain with Bayer ordered dithering using block elements."""
        for r in range(ROWS):
            for c in range(COLS):
                h = self._height(c, r, COLS, ROWS, ox, oy)
                he = h * self._shadow(c, r, h, COLS, ROWS, ox, oy)
                threshold = BAYER_4[r % 4][c % 4]
                dithered = he + (threshold - 0.5) * 0.15
                i = int(dithered * (len(BLOCK_RAMP) - 1))
                self.canvas.set_char(r, c, BLOCK_RAMP[clamp(i, 0, len(BLOCK_RAMP)-1)], self._hcol(he))

    def _ascii(self, ox, oy):
        tc = " .'-:;~=+*!#%@"
        for r in range(ROWS):
            for c in range(COLS):
                h = self._height(c, r, COLS, ROWS, ox, oy)
                he = h * self._shadow(c, r, h, COLS, ROWS, ox, oy)
                i = int(he*(len(tc)-1))
                self.canvas.set_char(r, c, tc[clamp(i,0,len(tc)-1)], self._hcol(he))
        for r in range(1, ROWS-1):
            for c in range(1, COLS-1):
                h = self._height(c, r, COLS, ROWS, ox, oy)
                lv = h % 0.1
                if (lv < 0.008 or lv > 0.092) and h > 0.32:
                    self.canvas.set_char(r, c, '─', C.WHITE)


# ─── Scene: Particles (Enhanced) ─────────────────────────────────────
class Particle:
    __slots__ = ['x','y','vx','vy','life','mlife','char','color','grav']
    def __init__(self, x,y,vx,vy,life,ch,col,grav=0):
        self.x=x;self.y=y;self.vx=vx;self.vy=vy;self.life=life;self.mlife=life;self.char=ch;self.color=col;self.grav=grav

class ParticleScene:
    _stars = None

    def __init__(self, canvas):
        self.canvas=canvas;self.t=0.0;self.particles=[];self.max_p=800;self.mode=0
        if ParticleScene._stars is None:
            ParticleScene._stars = make_stars(50)

    def _fountain(self):
        cx,cy=COLS//2,ROWS-2
        for _ in range(8):
            a=-math.pi/2+random.gauss(0,.4);sp=random.uniform(15,35)
            ch=random.choice(list("✦✧✩✪✫✬✭✮✯✰⋆✺✻✼✽✾✿❀❁") + list("█▓▒░●◆■▲▼★○◇□△▽☆") + list("•∙∘◌◍◎●◐◑◒◓◔◕⬤"))
            co=random.choice(PALETTE_ALL)
            self.particles.append(Particle(cx,cy,math.cos(a)*sp,math.sin(a)*sp,random.uniform(1.5,3),ch,co,18))

    def _firework(self):
        cx,cy=random.randint(15,COLS-15),random.randint(5,ROWS//2)
        co=random.choice(PALETTE_ALL); n=random.randint(30,60)
        theme=random.choice([list("✦✧✩✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼"),list("♠♣♥♦♤♡♧♢★☆✦✧"),list("⬟⬠⬡⬢⬣●◆■▲▼★○◇□△▽"),list("♔♕♖♗♘♙♚♛♜♝♞♟"),list("☀☁☂☃☄★☆⚡✦✧✩✪")])
        for _ in range(n):
            a=random.uniform(0,2*math.pi);sp=random.uniform(5,25)
            self.particles.append(Particle(cx,cy,math.cos(a)*sp,math.sin(a)*sp,random.uniform(.8,2.5),random.choice(theme),co,8))

    def _rain(self):
        chs=list("│┃║↓⇓⇩❄❅❆✻✼⁂⁕·∙∘⋅✧✦")
        for _ in range(12):
            co=random.choice([C.CYAN,C.BLUE,C.TEAL,QColor(100,180,255),QColor(150,200,255)])
            self.particles.append(Particle(random.randint(0,COLS-1),random.randint(-5,0),random.uniform(-2,2),random.uniform(30,50),2,random.choice(chs),co,0))

    def _spiral(self):
        cx,cy=COLS//2,ROWS//2;chs=list("◆◇○●□■△▽☆★♦♢♤♡♧♣♠⊕⊗⊙")
        for i in range(6):
            a=self.t*3+i*math.pi/3;r=5+math.sin(self.t*2)*3
            co=hsv((self.t*50+i*60)%360,.9,1)
            self.particles.append(Particle(cx+math.cos(a)*r,cy+math.sin(a)*r,-math.sin(a)*12,math.cos(a)*12,random.uniform(1,2),chs[i%len(chs)],co,0))

    def _chess(self):
        cx,cy=COLS//2,ROWS-2;pcs=CHESS_WHITE+CHESS_BLACK
        for _ in range(4):
            a=-math.pi/2+random.gauss(0,.6);sp=random.uniform(12,28)
            self.particles.append(Particle(cx,cy,math.cos(a)*sp,math.sin(a)*sp,random.uniform(2,4),random.choice(pcs),C.GOLD,15))

    def _currency(self):
        for _ in range(8):
            self.particles.append(Particle(random.randint(0,COLS-1),random.randint(-5,0),random.uniform(-1,1),random.uniform(20,35),3,random.choice(CURRENCY),C.GOLD,5))

    def _explosion(self):
        """Spawn explosion at mouse click position."""
        now = time.time()
        for cx, cy, ct in list(self.canvas.mouse_clicks):
            if now - ct < 0.3:  # recent click
                co = hsv(random.uniform(0, 360), 0.9, 1.0)
                theme = list("✦✧✩✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼") + list("█▓▒░●◆■▲▼★○◇□△▽☆") + list("⚡✸❄☄")
                for _ in range(80):
                    a = random.uniform(0, 2*math.pi); sp = random.uniform(3, 30)
                    self.particles.append(Particle(cx, cy, math.cos(a)*sp, math.sin(a)*sp,
                                                   random.uniform(0.5, 2.5), random.choice(theme), co,
                                                   random.uniform(5, 15)))
        self.canvas.mouse_clicks.clear()

    def update(self, dt):
        self.t += dt; self.canvas.clear()
        draw_stars(self.canvas, self._stars, self.t, QColor(20, 25, 40))
        now = time.time()
        self.canvas.mouse_clicks = [(c, r, t) for c, r, t in self.canvas.mouse_clicks if now - t < 2.0]
        spawners = [self._fountain, self._firework, self._rain, self._spiral, self._chess, self._currency, self._explosion]
        if self.mode < len(spawners): spawners[self.mode]()
        if len(self.particles) > self.max_p: self.particles = self.particles[-self.max_p:]
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0: continue
            p.vy += p.grav * dt; p.x += p.vx * dt; p.y += p.vy * dt
            c, r = int(p.x), int(p.y)
            if 0 <= r < ROWS and 0 <= c < COLS:
                a = clamp(p.life / p.mlife, 0, 1)
                co = QColor(p.color); co.setAlphaF(a)
                self.canvas.set_char(r, c, p.char, co)
            alive.append(p)
        self.particles = alive
        self.canvas.update()


# ─── Scene: Emojis (Enhanced) ───────────────────────────────────────
class EmojiScene:
    def __init__(self, canvas):
        self.canvas=canvas;self.t=0.0;self.mode=0;self.cdata={}
        self.emojis = [
            "😀","😂","🥰","😎","🤩","🥳","😇","🤔","😈","👻","💀","🤖","👽","🎃","🤡","👹",
            "👺","💩","🤬","👾","🤺","🧙","🧚","🧛","🧜","🧝","🧞","🧟","🦹","🧐","🤓","🥸",
            "🐱","🐶","🦊","🐼","🦄","🐉","🦁","🐯","🐮","🐷","🐸","🐵","🐔","🦅","🦋","🐌",
            "🐙","🦑","🦈","🐳","🐬","🐟","🐠","🐡","🦀","🐢","🦎","🐍","🦂","🐛","🐝","🐞",
            "🍕","🍔","🌮","🍣","🍎","🍒","🍋","🍇","🍉","🥝","🍌","🥑","🍰","🎂","🧁","🍩",
            "🌸","🍀","🌊","🔥","⭐","🌈","☀️","🌙","❄️","⚡","🌪️","🌋","🌵","🎄","🍁","🍂",
            "💎","🎮","🎵","🏆","💰","🚀","🎯","💡","🔑","🔮","🎲","🧩","🎪","🎭","🎨","🎬",
            "👋","👍","👎","✊","✌️","🤞","🤟","🤘","🤙","👈","👉","☝️","👆","👇","✋","🤚",
            "🚗","🚕","🚙","🚌","🏎️","🚓","🚑","🚒","🚐","🚚","🛵","🏍️","🚲","✈️","🚀","🛸",
            "✨","💫","🌟","⭐","⚡","💥","💢","💦","💨","💣","🏅","🥇","🥈","🥉","🎖️","🎗️",
        ]

    def _de(self, r, c, e, co=None):
        if 0<=r<ROWS and 0<=c<COLS-1:
            self.canvas.set_char(r, c, e, co or C.WHITE)
            self.canvas.set_char(r, c+1, ' ', co or C.WHITE)

    def update(self, dt):
        self.t += dt; self.canvas.clear()
        [self._rain, self._matrix, self._wave, self._gallery, self._zodiac, self._fireworks_emoji][self.mode]()
        self.canvas.update()

    def _rain(self):
        if not self.cdata or random.random()<.05:
            c=random.randint(0,(COLS//2)-1)*2
            if c not in self.cdata:
                self.cdata[c]={'y':random.uniform(-20,0),'sp':random.uniform(3,10),'tr':[],'e':random.choice(self.emojis),'ln':random.randint(3,12)}
        nc={}
        for c,d in self.cdata.items():
            d['y']+=d['sp']*.05;d['tr'].append(int(d['y']))
            if len(d['tr'])>d['ln']:d['tr'].pop(0)
            for i,r in enumerate(d['tr']):
                if 0<=r<ROWS:
                    a=(i+1)/len(d['tr'])
                    if i==len(d['tr'])-1: self._de(r,c,d['e'],C.WHITE)
                    else: self._de(r,c,self.emojis[(int(d['y'])+i)%len(self.emojis)],QColor(0,int(180*a),int(80*a)))
            if d['tr'] and d['tr'][-1]<ROWS+5: nc[c]=d
        self.cdata=nc

    def _matrix(self):
        if not self.cdata or random.random()<.08:
            c=random.randint(0,COLS-2)
            if c not in self.cdata:
                self.cdata[c]={'y':-random.uniform(0,10),'sp':random.uniform(4,12),'tr':[],'ln':random.randint(5,20)}
        nc={}
        for c,d in self.cdata.items():
            d['y']+=d['sp']*.04;d['tr'].append(int(d['y']))
            if len(d['tr'])>d['ln']:d['tr'].pop(0)
            for i,r in enumerate(d['tr']):
                if 0<=r<ROWS:
                    a=(i+1)/len(d['tr'])
                    if random.random()<.12 and c<COLS-1:
                        self._de(r,c,random.choice(self.emojis),QColor(0,255,int(100*a)))
                    else:
                        ch=random.choice(list("⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏") + list(":;=+*#%@&~^·∙∘○●♠♣♥♦★☆✦✧"))
                        g=int(255*a);self.canvas.set_char(r,c,ch,QColor(0,g,int(g*.4)))
            if d['tr'] and d['tr'][-1]<ROWS+5: nc[c]=d
        self.cdata=nc

    def _wave(self):
        sets=[["🌊","🐟","🐠","🦈","🐙","🦑","🐚","🐳","🐬","🐡","🦀","🦞"],
              ["🌈","✨","💫","⭐","🌟","💖","🦋","🌸","🌺","🌻","🌹","🍀"],
              ["🚀","✈️","🛸","🚁","🛶","⛵","🏎️","🚲","🛵","🚂","🚀","🛸"],
              ["🍕","🍔","🌮","🍣","🍰","🎂","🍩","🍪","🍭","🍬","🧁","☕"],
              ["😀","😎","🤩","🥳","🤖","👽","👻","🦄","🐉","🦊","🐼","🐱"]]
        wi=int(self.t*.3)%len(sets);ws=sets[wi];n=15
        for i in range(n):
            p=self.t*2+i*.5;x=int(COLS/2+(i-n/2)*3+math.sin(p)*8);y=int(ROWS/2+math.sin(p*.7+i*.3)*6)
            self._de(max(0,min(ROWS-1,y)),max(0,min(COLS-2,x)),ws[i%len(ws)],C.WHITE)
        w2=sets[(wi+2)%len(sets)]
        for i in range(n):
            p=self.t*1.5+i*.5+math.pi;x=int(COLS/2+(i-n/2)*3+math.sin(p)*6);y=int(ROWS/2+8+math.sin(p*.8+i*.4)*4)
            self._de(max(0,min(ROWS-1,y)),max(0,min(COLS-2,x)),w2[i%len(w2)],C.WHITE)

    def _gallery(self):
        cats=[("FACES",self.emojis[0:24]),("ANIMALS",self.emojis[24:48]),("FOOD",self.emojis[48:64]),
              ("NATURE",self.emojis[64:80]),("OBJECTS",self.emojis[80:96]),("HANDS",self.emojis[96:112]),
              ("TRANSPORT",self.emojis[112:128]),("SYMBOLS",self.emojis[128:])]
        pg=int(self.t*.15)%len(cats);cn,ce=cats[pg]
        t=f" ╔══ {cn} ══╗ ";tx=(COLS-len(t))//2
        for i,ch in enumerate(t): self.canvas.set_char(2,tx+i,ch,C.CYAN)
        s=f"  ║  Page {pg+1}/{len(cats)} ║  ";sx=(COLS-len(s))//2
        for i,ch in enumerate(s): self.canvas.set_char(3,sx+i,ch,C.MAGENTA)
        for idx,e in enumerate(ce[:80]):
            r=5+(idx//10)*4;c=5+(idx%10)*10
            if r<ROWS-2 and c<COLS-2: self._de(r,c,e,C.WHITE)
        dy=ROWS-3;dx=(COLS-len(cats)*3)//2
        for di in range(len(cats)):
            self.canvas.set_char(dy,dx+di*3,'●' if di==pg else '○',C.YELLOW if di==pg else C.GRID)

    def _zodiac(self):
        cx,cy=COLS//2,ROWS//2
        for i,z in enumerate(ZODIAC):
            a=self.t*.3+i*math.pi/6
            x=int(cx+math.cos(a)*12);y=int(cy+math.sin(a)*6)
            if 0<=y<ROWS and 0<=x<COLS-1: self._de(y,x,z,C.GOLD)
            ax=int(cx+math.cos(a)*15);ay=int(cy+math.sin(a)*7.5)
            if 0<=ay<ROWS and 0<=ax<COLS: self.canvas.set_char(ay,ax,'→',C.CYAN)
        if 0<=cy<ROWS and 0<=cx<COLS-1: self._de(cy,cx,'☉',C.YELLOW)
        for a in range(0, 360, 3):
            rad=math.radians(a);rx=int(cx+math.cos(rad)*17);ry=int(cy+math.sin(rad)*8.5)
            if 0<=ry<ROWS and 0<=rx<COLS: self.canvas.set_char(ry,rx,'○',QColor(40,40,60))

    def _fireworks_emoji(self):
        """Emoji firework bursts at random positions."""
        # FIX: Draw sparkle trail BEFORE firework bursts so that the bursts
        # (the main visual element) are not overwritten by random sparkles.
        # Previously, sparkles were drawn after bursts, overwriting them.
        for _ in range(3):
            self.canvas.set_char(random.randint(0,ROWS-1), random.randint(0,COLS-1),
                                random.choice("✨💫🌟⭐"), random.choice(PALETTE_ALL))
        if random.random() < 0.03:
            cx = random.randint(10, COLS-10); cy = random.randint(5, ROWS//2)
            theme = random.choice([self.emojis[0:16], self.emojis[48:64], self.emojis[80:96], self.emojis[128:]])
            co = random.choice(PALETTE_ALL)
            for i in range(12):
                a = i * math.pi * 2 / 12 + random.uniform(-0.2, 0.2)
                r = random.uniform(2, 8)
                ex, ey = int(cx + math.cos(a) * r), int(cy + math.sin(a) * r * 0.5)
                if 0 <= ey < ROWS and 0 <= ex < COLS - 1:
                    self._de(ey, ex, random.choice(theme), co)


# ─── Scene: Plasma ──────────────────────────────────────────────────
class PlasmaScene:
    """Procedural plasma effect with multiple overlapping sine waves."""

    def __init__(self, canvas):
        self.canvas = canvas; self.t = 0.0; self.style = 0

    def update(self, dt):
        self.t += dt; self.canvas.clear()
        for r in range(ROWS):
            for c in range(COLS):
                x, y = c / COLS, r / ROWS
                v1 = math.sin(x * 10 + self.t)
                v2 = math.sin(y * 8 + self.t * 0.7)
                v3 = math.sin((x + y) * 6 + self.t * 1.3)
                cx2, cy2 = x + 0.5 * math.sin(self.t * 0.3), y + 0.5 * math.cos(self.t * 0.4)
                v4 = math.sin(math.sqrt((cx2 - 0.5)**2 + (cy2 - 0.5)**2) * 14 + self.t)
                v = (v1 + v2 + v3 + v4) / 4.0  # -1..1
                hue = (v + 1) * 180  # 0..360
                brightness = 0.5 + v * 0.3
                co = hsv(hue, 0.85, clamp(brightness, 0.2, 1.0))

                if self.style == 0:
                    i = int((v + 1) / 2 * (len(BLOCK_RAMP) - 1))
                    self.canvas.set_char(r, c, BLOCK_RAMP[clamp(i, 0, len(BLOCK_RAMP)-1)], co)
                elif self.style == 1:
                    bits = 0
                    for lr in range(4):
                        for lc in range(2):
                            sx = (c * 2 + lc) / (COLS * 2)
                            sy = (r * 4 + lr) / (ROWS * 4)
                            sv = (math.sin(sx*10+self.t)+math.sin(sy*8+self.t*.7)+math.sin((sx+sy)*6+self.t*1.3))/3
                            if sv > -0.1: bits |= (1 << BRAILLE_BIT_MAP[lr][lc])
                    if bits: self.canvas.set_char(r, c, BRAILLE_LOOKUP[bits], co)
                else:
                    # FIX: Use BRAILLE_DENSITY_CHARS (sorted by visual density) instead
                    # of raw BRAILLE_LOOKUP (sorted by bit pattern). Previously, the
                    # raw index produced a chaotic visual pattern since Unicode braille
                    # codepoints are ordered by bit pattern, not by number of dots.
                    # Now the plasma value maps to a smooth density ramp from blank to full.
                    i = int((v + 1) / 2 * (len(BRAILLE_DENSITY_CHARS) - 1))
                    self.canvas.set_char(r, c, BRAILLE_DENSITY_CHARS[clamp(i, 0, len(BRAILLE_DENSITY_CHARS)-1)], co)
        self.canvas.update()


# ─── Scene: Starfield ───────────────────────────────────────────────
class StarfieldScene:
    """Warp-speed star tunnel with depth-based Unicode symbols."""

    def __init__(self, canvas):
        self.canvas = canvas; self.t = 0.0
        self.num_stars = 300
        self.stars = []
        for _ in range(self.num_stars):
            self.stars.append([random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0.01, 1.0)])

    def update(self, dt):
        self.t += dt; self.canvas.clear()
        speed = 2.0 + min(self.t * 0.1, 18.0)  # capped at 20.0
        cx, cy = COLS / 2, ROWS / 2

        for s in self.stars:
            s[2] -= dt * speed * s[2]  # closer = faster
            if s[2] <= 0.001 or s[2] > 1.0:
                s[0] = random.uniform(-1, 1)
                s[1] = random.uniform(-1, 1)
                s[2] = 1.0
                continue

            sx = s[0] / s[2] * (COLS * 0.4) + cx
            sy = s[1] / s[2] * (ROWS * 0.4) + cy

            # Trail (streak)
            prev_z = s[2] + dt * speed * s[2] * 0.5
            psx = s[0] / prev_z * (COLS * 0.4) + cx
            psy = s[1] / prev_z * (ROWS * 0.4) + cy

            col_idx = int((1 - s[2]) * (len(PALETTE_ALL) - 1))
            co = PALETTE_ALL[clamp(col_idx, 0, len(PALETTE_ALL)-1)]
            brightness = 1.0 - s[2]

            # Draw streak
            self.canvas.draw_line(int(psx), int(psy), int(sx), int(sy), '·', co)

            # Draw star head with depth-based symbol
            c, r = int(sx), int(sy)
            if 0 <= r < ROWS and 0 <= c < COLS:
                if brightness > 0.8: ch = '✦'
                elif brightness > 0.6: ch = '✧'
                elif brightness > 0.4: ch = '·'
                else: ch = '⋅'
                self.canvas.set_char(r, c, ch, co)

        # HUD
        self.canvas.draw_text(1, 1, f"▸ WARP {speed:.1f}x ◂", C.CYAN)
        self.canvas.draw_text(1, 2, f"  Stars: {self.num_stars}", C.GREEN)
        self.canvas.update()


# ─── Scene: Fractal ─────────────────────────────────────────────────
class FractalScene:
    """Animated Mandelbrot set zoom with Unicode shading."""

    def __init__(self, canvas):
        self.canvas = canvas; self.t = 0.0; self.style = 0
        self.cx = -0.745; self.cy = 0.186  # Seahorse valley
        self.zoom = 0.8
        self.max_iter = 80
        self._zoom_start = 0.8  # for reset

    def update(self, dt):
        self.t += dt; self.canvas.clear()
        self.zoom *= (1.0 + dt * 0.08)
        if self.zoom > 500.0:
            self.zoom = self._zoom_start
            self.cx = -0.745
            self.cy = 0.186
        # Slight pan
        self.cx += math.sin(self.t * 0.2) * 0.0001
        self.cy += math.cos(self.t * 0.15) * 0.0001

        aspect = COLS / ROWS
        for r in range(ROWS):
            for c in range(COLS):
                x0 = self.cx + (c / COLS - 0.5) * 3.5 / self.zoom * aspect
                y0 = self.cy + (r / ROWS - 0.5) * 3.5 / self.zoom
                iter_count = mandelbrot(x0, y0, self.max_iter)

                if iter_count >= self.max_iter:
                    self.canvas.set_char(r, c, '█', C.WHITE)
                else:
                    t = iter_count / self.max_iter
                    hue = (iter_count * 7 + self.t * 20) % 360
                    co = hsv(hue, 0.8, 0.4 + t * 0.6)

                    if self.style == 0:
                        i = int(t * (len(BLOCK_RAMP) - 1))
                        self.canvas.set_char(r, c, BLOCK_RAMP[clamp(i, 0, len(BLOCK_RAMP)-1)], co)
                    elif self.style == 1:
                        i = int(t * 255)
                        self.canvas.set_char(r, c, BRAILLE_LOOKUP[clamp(i, 0, 255)], co)
                    else:
                        ch = SHADE_RAMP_ASCII[clamp(int(t * (len(SHADE_RAMP_ASCII)-1)), 0, len(SHADE_RAMP_ASCII)-1)]
                        self.canvas.set_char(r, c, ch, co)

        # FIX: Use fixed-width formatting for HUD box so all lines have the
        # same width and the box borders align properly. Previously, the box
        # edges were misaligned because zoom value, coordinates, etc. had
        # varying string lengths.
        self.canvas.draw_text(1, 1, f"╔═ Mandelbrot ═════════╗", C.CYAN)
        self.canvas.draw_text(1, 2, f"║ Zoom: {self.zoom:8.1f}x   ║", C.GREEN)
        self.canvas.draw_text(1, 3, f"║ Iter: {self.max_iter:<8}    ║", C.YELLOW)
        self.canvas.draw_text(1, 4, f"║ [{self.cx:+.4f},{self.cy:+.4f}] ║", C.MAGENTA)
        self.canvas.update()


# ─── Scene: Unicode Showcase ─────────────────────────────────────────
class UnicodeShowcase:
    def __init__(self, canvas):
        self.canvas=canvas;self.t=0.0;self.page=0
        self.pages=self._build()

    def _build(self):
        P = []
        def br(): return [BRAILLE_LOOKUP[v] for v in range(256)]
        P.append((br(), "BRAILLE PATTERNS (U+2800-U+28FF) — 2x4 dot matrix — 256 glyphs"))
        P.append((list("█▓▒░▀▄▌▐▘▝▗▖▔▕"), "BLOCK ELEMENTS (U+2580-U+259F) — density shading"))
        bs = []
        for _,b in [("S",BOX_SINGLE),("D",BOX_DOUBLE),("R",BOX_ROUNDED),("H",BOX_HEAVY)]:
            for k in ['tl','tr','bl','br','h','v','t','b','l','r','cross']: bs.append(b[k])
        P.append((bs, "BOX-DRAWING — single / double / rounded / heavy"))
        P.append((list("←→↑↓↖↗↘↙⇐⇒⇑⇓↩↪➜➡➢➣➤➥➦➧➨➩➪➫➬➭➮➯➱➲➳➴➵➶➷➸➹➺➻➼➽➾➔➘➙➚➛"), "ARROWS (U+2190-U+21FF)"))
        P.append((list("∑∏∫∮∂∇√∞≈≠≡≤≥±×÷∓⊕⊗⊙⊚⊡ΞΨΦΩαβγδεζηθλμπρσφψω"), "MATHEMATICAL & GREEK"))
        # FIX: Removed duplicate chess piece list. The original code appended
        # CHESS_WHITE+CHESS_BLACK and then list("♔♕♖♗♘♙♚♛♜♝♞♟") which is the
        # same set, causing each chess piece to appear twice on this page.
        P.append((CHESS_WHITE+CHESS_BLACK+DICE+list("🀄🀅🀆🀇🀈🀉🀊🀋🀌🀍🀎🀏🀐🀑🀒"), "GAMES — Chess · Dice · Mahjong"))
        P.append((list("●◆■▲▼★⬟⬠⬡⬢⬣◯◇□△▽☆✦✧✩✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿❀❁❂❃⬤◉◌◐◑◒◓◔◕◖◗◘◙◼◻◾◽"), "GEOMETRIC SHAPES"))
        P.append((list("✁✂✃✄✆✇✈✉✊✋✌✍✎✏✐✑✒✓✔✕✖✗✘✙✚✛✜✝✞✟✠✡✢✣✤✥✦✧✩✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿❀❁❂❃❄❅❆❇❈❉❊❋❖"), "DINGBATS (U+2700-U+27BF)"))
        P.append((CURRENCY+list("₠₡₢₣₤₥₦₧₨"), "CURRENCY (U+20A0-U+20CF)"))
        P.append((ZODIAC+list("☉☽☾☼"), "ZODIAC (U+2648-U+2673)"))
        P.append((HEARTS+list("💕💖💗💘💙💚💛💜🖤💝💞💓"), "HEARTS & AFFECTION"))
        # FIX: Removed redundant list("♩♪♫♬𝄞𝄢𝄡♭♮♯") + MUSIC concatenation.
        # MUSIC is already defined as list("♩♪♫♬𝄞𝄢𝄡♭♮♯"), so the original
        # code displayed every music symbol twice.
        P.append((MUSIC, "MUSICAL SYMBOLS"))
        P.append((list("☆★✦✧✩✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿❀❁❂❃❇☀☁☂☃☄⚡❄❅❆↯"), "STARS & WEATHER"))
        return P

    def update(self, dt):
        self.t += dt; self.canvas.clear()
        self.page = int(self.t * 0.2) % len(self.pages)
        chars, title = self.pages[self.page]
        self.canvas.draw_box(0, 0, COLS, ROWS, BOX_DOUBLE, C.CYAN)
        tx = (COLS - len(title)) // 2
        self.canvas.draw_text(tx, 1, title, C.YELLOW)
        sep = BOX_DOUBLE['l'] + BOX_DOUBLE['h'] * (COLS - 2) + BOX_DOUBLE['r']
        self.canvas.draw_text(0, 2, sep, C.MAGENTA)
        cpr = 20
        for idx, ch in enumerate(chars):
            r = 4 + idx // cpr; c = 2 + (idx % cpr) * ((COLS - 4) // cpr)
            if r >= ROWS - 3: break
            w = math.sin(self.t * 3 + idx * 0.15) * 0.5 + 0.5
            co = hsv((idx * 7 + self.t * 30) % 360, 0.7, 0.6 + w * 0.4)
            self.canvas.set_char(r, c, ch, co)
        pt = f"  ◀ Page {self.page+1}/{len(self.pages)} ▶  "
        self.canvas.draw_text((COLS - len(pt)) // 2, ROWS - 2, pt, C.GREEN)
        ds = (COLS - len(self.pages) * 2) // 2
        for di in range(len(self.pages)):
            self.canvas.set_char(ROWS - 3, ds + di * 2, '●' if di == self.page else '·',
                                C.YELLOW if di == self.page else C.GRID)
        self.canvas.update()


# ─── Scene: Combined (Enhanced) ─────────────────────────────────────
class CombinedScene:
    def __init__(self, canvas):
        self.canvas=canvas;self.cube=CubeScene(canvas);self.terrain=TerrainScene(canvas)
        self.particles=ParticleScene(canvas);self.emoji=EmojiScene(canvas);self.t=0.0

    def update(self, dt):
        self.t += dt; self.canvas.clear()
        # Braille terrain bg
        self.terrain.t = self.t
        for r in range(ROWS):
            for c in range(COLS):
                if random.random() > 0.7: continue
                h = clamp(fbm(c/COLS*5+self.t*.5, r/ROWS*5+self.t*.2, 4, 99), 0, 1)
                co = self.terrain._hcol(h)
                b = 0.3
                self.canvas.set_char(r, c, BLOCK_RAMP[clamp(int(h*(len(BLOCK_RAMP)-1)),0,len(BLOCK_RAMP)-1)],
                                    QColor(int(co.red()*b),int(co.green()*b),int(co.blue()*b)))
        # FIX: Use try/finally to guarantee cube.verts restoration even if
        # an exception occurs during cube.update(). Previously, if cube.update
        # raised an exception, the cube's vertex data would be permanently
        # corrupted (left at the smaller size), affecting future renders.
        sv = self.cube.verts[:]; s=0.8
        self.cube.verts = [(-s,-s,-s),(s,-s,-s),(s,s,-s),(-s,s,-s),(-s,-s,s),(s,-s,s),(s,s,s),(-s,s,s)]
        ot = self.cube.t; self.cube.t = self.t * 0.8
        try:
            self.cube.update(0, clear=False, draw_stars_bg=False, update_canvas=False)
        finally:
            self.cube.verts = sv; self.cube.t = ot
        # Orbiting symbols
        syms = ["✨","⭐","🌟","💫","🔥","💎","🔮","🎲","♠","♣","♥","♦","☆","★","◆","●","▲","■"]
        for i,sym in enumerate(syms):
            ex=int(COLS/2+math.cos(self.t+i*2*math.pi/len(syms))*35)
            ey=int(ROWS/2+math.sin(self.t*.7+i*2*math.pi/len(syms))*12)
            if 0<=ey<ROWS and 0<=ex<COLS-1:
                co=hsv((self.t*50+i*20)%360,.9,1)
                self.canvas.set_char(ey,ex,sym,co);self.canvas.set_char(ey,ex+1,' ',co)
        # Mouse glow
        if self.canvas.mouse_pos:
            mc, mr = self.canvas.mouse_pos
            draw_glow(self.canvas, mc, mr, 5, C.MAGENTA, self.t)
        self.canvas.update()


# ─── Main Window ────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⬡ Unicode Graphics Engine v3 ⬡")
        self.setMinimumSize(960, 700); self.resize(1100, 780)
        self.paused = False

        self.setStyleSheet("""
            QMainWindow { background-color: #0a0a12; }
            QPushButton { background-color: #1a1a2e; color: #e0e0f0; border: 1px solid #333355;
                border-radius: 6px; padding: 6px 12px; font-size: 12px; font-family: 'DejaVu Sans Mono'; }
            QPushButton:hover { background-color: #2a2a4e; border-color: #00ccff; }
            QPushButton:checked { background-color: #0a3a5a; border-color: #00ccff; color: #00ffcc; }
            QLabel { color: #a0a0c0; font-family: 'DejaVu Sans Mono'; font-size: 12px; }
            QComboBox { background-color: #1a1a2e; color: #e0e0f0; border: 1px solid #333355;
                border-radius: 4px; padding: 4px 8px; font-family: 'DejaVu Sans Mono'; }
            QComboBox QAbstractItemView { background-color: #1a1a2e; color: #e0e0f0; selection-background-color: #0a3a5a; }
            QCheckBox { color: #a0a0c0; font-family: 'DejaVu Sans Mono'; font-size: 11px; spacing: 4px; }
            QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #444466; border-radius: 3px;
                background-color: #1a1a2e; }
            QCheckBox::indicator:checked { background-color: #00aacc; border-color: #00ccff; }
        """)

        central = QWidget(); self.setCentralWidget(central)
        layout = QVBoxLayout(central); layout.setContentsMargins(8,8,8,8); layout.setSpacing(6)

        # Title row
        title_row = QHBoxLayout()
        title = QLabel("⬡ UNICODE GRAPHICS ENGINE v3 ⬡")
        title.setStyleSheet("font-size: 16px; color: #00ccff; font-weight: bold;")
        title_row.addWidget(title)
        title_row.addStretch()

        # Control buttons
        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setCheckable(True)
        self.btn_pause.clicked.connect(self._toggle_pause)
        title_row.addWidget(self.btn_pause)

        self.btn_screenshot = QPushButton("📷 Screenshot")
        self.btn_screenshot.clicked.connect(self._screenshot)
        title_row.addWidget(self.btn_screenshot)

        self.btn_fullscreen = QPushButton("⛶ Fullscreen")
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        title_row.addWidget(self.btn_fullscreen)
        layout.addLayout(title_row)

        # Scene buttons
        btn_layout = QHBoxLayout(); btn_layout.setSpacing(3)
        self.btn_group = []
        scenes = [("3D Cube","cube"),("Multi-Cube","multi"),("Terrain","terrain"),
                  ("Particles","particles"),("Emojis","emojis"),("Unicode","unicode"),
                  ("Plasma","plasma"),("Starfield","starfield"),("Fractal","fractal"),("Combined","combined")]
        for i,(label,key) in enumerate(scenes):
            btn=QPushButton(label);btn.setCheckable(True);btn.setProperty("sk",key)
            btn.clicked.connect(lambda _,k=key: self._switch(k))
            if i==0: btn.setChecked(True)
            btn_layout.addWidget(btn); self.btn_group.append(btn)
        layout.addLayout(btn_layout)

        # Sub-mode + speed + options
        sub = QHBoxLayout(); sub.setSpacing(8)
        sub.addWidget(QLabel("Mode:"))
        self.combo = QComboBox(); self.combo.setMinimumWidth(180)
        self.combo.currentIndexChanged.connect(self._on_mode)
        sub.addWidget(self.combo)

        sub.addWidget(QLabel("Speed:"))
        self.slider = QSlider(Qt.Horizontal); self.slider.setRange(1,30); self.slider.setValue(10); self.slider.setMaximumWidth(120)
        sub.addWidget(self.slider)

        self.chk_glow = QCheckBox("Glow"); self.chk_glow.setChecked(True); sub.addWidget(self.chk_glow)
        self.chk_stars = QCheckBox("Stars"); self.chk_stars.setChecked(True); sub.addWidget(self.chk_stars)

        self.fps_lbl = QLabel("FPS: --"); self.fps_lbl.setStyleSheet("color: #00ff88;"); sub.addWidget(self.fps_lbl)
        sub.addStretch(); layout.addLayout(sub)

        # Canvas
        self.canvas = Canvas()
        frame = QFrame(); frame.setStyleSheet("QFrame{border:2px solid #222244;border-radius:8px;background:#0a0a12;}")
        fl = QVBoxLayout(frame); fl.setContentsMargins(4,4,4,4); fl.addWidget(self.canvas)
        layout.addWidget(frame, stretch=1)

        # Status
        self.status = QLabel("Keys: 1-0=Scenes  Space=Pause  F11=Fullscreen  S=Screenshot  Click=Interact")
        self.status.setStyleSheet("color:#555577;font-size:10px;")
        layout.addWidget(self.status)

        # Scenes
        self.scenes = {
            'cube':CubeScene(self.canvas),'multi':MultiCubeScene(self.canvas),
            'terrain':TerrainScene(self.canvas),'particles':ParticleScene(self.canvas),
            'emojis':EmojiScene(self.canvas),'unicode':UnicodeShowcase(self.canvas),
            'plasma':PlasmaScene(self.canvas),'starfield':StarfieldScene(self.canvas),
            'fractal':FractalScene(self.canvas),'combined':CombinedScene(self.canvas),
        }
        self.cur = 'cube'; self._update_modes()

        self.last_t = time.time(); self.ftimes = []
        self.timer = QTimer(); self.timer.timeout.connect(self._tick); self.timer.start(16)

    def _update_modes(self):
        self.combo.blockSignals(True); self.combo.clear()
        m = {
            'cube':['Block Fill','Braille Fill','ASCII Fill'],
            'multi':['Nested Cubes'],
            'terrain':['Braille (2x4 sub-pixels)','Block Elements','Unicode Symbols','Bayer Dithered','Classic ASCII'],
            'particles':['Fountain ✦','Fireworks ✸','Rain ❄','Spiral ◆','Chess ♚','Currency 💰','Click Explosion 💥'],
            'emojis':['Emoji Rain','Matrix','Wave','Gallery','Zodiac Clock','Firework Bursts'],
            'unicode':['Auto-Scroll All Pages'],
            'plasma':['Block Shading','Braille Sub-Pixel','Braille Density Map'],
            'starfield':['Warp Tunnel'],
            'fractal':['Block Shading','Braille','ASCII'],
            'combined':['All Combined'],
        }
        for mode in m.get(self.cur, []): self.combo.addItem(mode)
        # FIX: Set combo box index to match the scene's current mode/style.
        # Previously, switching scenes would always reset the combo to index 0,
        # even if the scene was in a different mode (e.g., cube style=2 would
        # show "Block Fill" in the combo). Now the combo reflects the actual state.
        s = self.scenes.get(self.cur)
        if s is not None:
            if hasattr(s, 'style') and self.cur in ('cube','terrain','plasma','fractal'):
                idx = clamp(s.style, 0, max(0, self.combo.count() - 1))
                self.combo.setCurrentIndex(idx)
            elif hasattr(s, 'mode') and self.cur in ('particles','emojis'):
                idx = clamp(s.mode, 0, max(0, self.combo.count() - 1))
                self.combo.setCurrentIndex(idx)
        self.combo.blockSignals(False)

    def _on_mode(self, i):
        s = self.scenes.get(self.cur)
        if hasattr(s, 'style') and self.cur in ('cube','terrain','plasma','fractal'): s.style = i
        elif hasattr(s, 'mode') and self.cur in ('particles','emojis'): s.mode = i

    def _switch(self, key):
        self.cur = key
        for b in self.btn_group: b.setChecked(b.property("sk")==key)
        self._update_modes()
        if key=='emojis': self.scenes['emojis'].cdata={}
        elif key=='particles': self.scenes['particles'].particles=[]
        names={'cube':'3D Cube','multi':'Multi-Cube','terrain':'Terrain','particles':'Particles',
               'emojis':'Emojis','unicode':'Unicode','plasma':'Plasma','starfield':'Starfield',
               'fractal':'Fractal','combined':'Combined'}
        self.status.setText(f"Scene: {names.get(key,key)} ║ Keys: 1-0=Scenes  Space=Pause  F11=Fullscreen  S=Screenshot")

    def _toggle_pause(self):
        self.paused = self.btn_pause.isChecked()
        self.btn_pause.setText("▶ Play" if self.paused else "⏸ Pause")

    def _toggle_fullscreen(self):
        if self.isFullScreen(): self.showNormal()
        else: self.showFullScreen()

    def _screenshot(self):
        pixmap = self.canvas.take_screenshot()
        if pixmap.isNull():
            self.status.setText("Screenshot failed: pixmap is null")
            return
        path = os.path.expanduser(f"~/unicode_engine_{int(time.time())}.png")
        if pixmap.save(path):
            self.status.setText(f"Screenshot saved: {path}")
        else:
            self.status.setText(f"Screenshot failed to save: {path}")

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Space: self._toggle_pause(); self.btn_pause.setChecked(self.paused)
        elif key == Qt.Key_F11: self._toggle_fullscreen()
        elif key == Qt.Key_S: self._screenshot()
        elif Qt.Key_1 <= key <= Qt.Key_9:
            keys = list(self.scenes.keys())
            idx = key - Qt.Key_1
            if idx < len(keys): self._switch(keys[idx])
        elif key == Qt.Key_0:
            keys = list(self.scenes.keys())
            if 9 < len(keys): self._switch(keys[9])
        elif key == Qt.Key_Escape:
            if self.isFullScreen(): self.showNormal()
            else: self.close()
        else: super().keyPressEvent(event)

    def _tick(self):
        now = time.time(); dt = now - self.last_t; self.last_t = now
        dt = min(dt, 0.1)
        if not self.paused:
            dt *= self.slider.value() / 10.0
            scene = self.scenes.get(self.cur)
            if scene is not None:
                scene.update(dt)
        self.canvas.mouse_clicks = [(c, r, t) for c, r, t in self.canvas.mouse_clicks if now - t < 2.0]
        self.ftimes.append(now)
        self.ftimes = [t for t in self.ftimes if now - t < 1.0]
        self.fps_lbl.setText(f"FPS: {len(self.ftimes)}{' ⏸' if self.paused else ''}")


def main():
    app = QApplication(sys.argv); app.setStyle("Fusion")
    p = QPalette()
    for role, col in [(QPalette.Window, (10,10,18)), (QPalette.WindowText, (224,224,240)),
                       (QPalette.Base, (15,15,25)), (QPalette.Text, (224,224,240)),
                       (QPalette.Button, (26,26,46)), (QPalette.ButtonText, (224,224,240)),
                       (QPalette.Highlight, (0,120,200))]:
        p.setColor(role, QColor(*col))
    app.setPalette(p)
    w = MainWindow(); w.show(); sys.exit(app.exec())

if __name__ == "__main__": main()