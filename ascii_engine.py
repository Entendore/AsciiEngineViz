#!/usr/bin/env python3
"""
PySide6 ASCII Graphics Engine
Renders: 3D Cubes, Terrain, Particles, Emojis
"""

import sys
import math
import random
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFrame, QSizePolicy, QComboBox
)
from PySide6.QtCore import Qt, QTimer, QRect, QPointF, QSize
from PySide6.QtGui import (
    QPainter, QFont, QColor, QPen, QBrush, QPalette, QLinearGradient,
    QSurfaceFormat
)

# ─── Shared Constants ────────────────────────────────────────────────
COLS = 100
ROWS = 40
FONT_W = 9
FONT_H = 16

# Brightness ramp for shading  (dark → bright)
SHADE_RAMP = " .:-=+*#%@"

# ─── Color Palette ───────────────────────────────────────────────────
class Colors:
    BG = QColor(10, 10, 18)
    GRID = QColor(30, 30, 45)
    CYAN = QColor(0, 220, 255)
    GREEN = QColor(0, 255, 130)
    MAGENTA = QColor(255, 50, 200)
    YELLOW = QColor(255, 230, 50)
    ORANGE = QColor(255, 140, 30)
    RED = QColor(255, 60, 60)
    WHITE = QColor(240, 240, 250)
    BLUE = QColor(60, 120, 255)
    PURPLE = QColor(180, 80, 255)


# ─── 3D Math Helpers ─────────────────────────────────────────────────
def rotate_x(point, angle):
    x, y, z = point
    c, s = math.cos(angle), math.sin(angle)
    return (x, y * c - z * s, y * s + z * c)

def rotate_y(point, angle):
    x, y, z = point
    c, s = math.cos(angle), math.sin(angle)
    return (x * c + z * s, y, -x * s + z * c)

def rotate_z(point, angle):
    x, y, z = point
    c, s = math.cos(angle), math.sin(angle)
    return (x * c - y * s, x * s + y * c, z)

def project(point, fov=80, distance=6):
    """Perspective projection."""
    x, y, z = point
    factor = fov / (distance + z)
    px = x * factor + COLS / 2
    py = -y * factor + ROWS / 2
    return (px, py, z)

def lerp(a, b, t):
    return a + (b - a) * t

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ─── Simple Noise for Terrain ────────────────────────────────────────
def simple_noise(x, y, seed=42):
    """Hash-based value noise with bilinear interpolation."""
    def hash2d(ix, iy):
        n = ix * 374761393 + iy * 668265263 + seed
        n = (n ^ (n >> 13)) * 1274126177
        n = n ^ (n >> 16)
        return (n & 0x7fffffff) / 0x7fffffff  # 0..1

    ix, iy = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - ix, y - iy
    # Smoothstep
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)

    v00 = hash2d(ix, iy)
    v10 = hash2d(ix + 1, iy)
    v01 = hash2d(ix, iy + 1)
    v11 = hash2d(ix + 1, iy + 1)

    top = lerp(v00, v10, fx)
    bot = lerp(v01, v11, fx)
    return lerp(top, bot, fy)


def fbm(x, y, octaves=5, seed=42):
    """Fractal Brownian Motion."""
    value = 0.0
    amplitude = 0.5
    frequency = 1.0
    for _ in range(octaves):
        value += amplitude * simple_noise(x * frequency, y * frequency, seed)
        amplitude *= 0.5
        frequency *= 2.0
    return value


# ─── Render Canvas Widget ───────────────────────────────────────────
class AsciiCanvas(QWidget):
    """Custom widget that draws a grid of colored ASCII characters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(COLS * FONT_W, ROWS * FONT_H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._buffer = [[' ' for _ in range(COLS)] for _ in range(ROWS)]
        self._color_buffer = [[Colors.WHITE for _ in range(COLS)] for _ in range(ROWS)]
        self._font = QFont("DejaVu Sans Mono", 10)
        self._font.setStyleHint(QFont.Monospace)
        self.setFocusPolicy(Qt.NoFocus)

    def clear(self, ch=' ', color=None):
        c = color or Colors.WHITE
        for r in range(ROWS):
            for col in range(COLS):
                self._buffer[r][col] = ch
                self._color_buffer[r][col] = c

    def set_char(self, r, c, ch, color=None):
        if 0 <= r < ROWS and 0 <= c < COLS:
            self._buffer[r][c] = ch
            if color:
                self._color_buffer[r][c] = color

    def draw_line(self, x0, y0, x1, y1, ch='*', color=None):
        """Bresenham line."""
        c = color or Colors.CYAN
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set_char(y0, x0, ch, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Colors.BG)
        painter.setFont(self._font)

        fm = painter.fontMetrics()
        cw = fm.horizontalAdvance('M')
        ch = fm.height()

        # Scale to fit widget
        sx = self.width() / (COLS * cw)
        sy = self.height() / (ROWS * ch)
        scale = min(sx, sy)
        painter.scale(scale, scale)

        for r in range(ROWS):
            for c in range(COLS):
                char = self._buffer[r][c]
                if char != ' ':
                    painter.setPen(self._color_buffer[r][c])
                    painter.drawText(c * cw, (r + 1) * ch - fm.descent(), char)

    def render(self):
        self.update()


# ─── Scene: 3D Rotating Cube ────────────────────────────────────────
class CubeScene:
    """Renders one or more rotating 3D cubes with shaded faces."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.t = 0.0
        # Unit cube vertices
        s = 1.2
        self.vertices = [
            (-s, -s, -s), ( s, -s, -s), ( s,  s, -s), (-s,  s, -s),
            (-s, -s,  s), ( s, -s,  s), ( s,  s,  s), (-s,  s,  s),
        ]
        # Faces as index quads (winding = outward)
        self.faces = [
            (0, 1, 2, 3),  # back
            (4, 5, 6, 7),  # front
            (0, 1, 5, 4),  # bottom
            (2, 3, 7, 6),  # top
            (0, 3, 7, 4),  # left
            (1, 2, 6, 5),  # right
        ]
        self.face_colors = [
            Colors.CYAN, Colors.GREEN, Colors.MAGENTA,
            Colors.YELLOW, Colors.ORANGE, Colors.RED,
        ]
        self.face_chars = ['#', '#', '#', '#', '#', '#']

    def _normal_z(self, v0, v1, v2):
        """Return z-component of face normal (positive = facing camera)."""
        ax, ay = v1[0] - v0[0], v1[1] - v0[1]
        bx, by = v2[0] - v0[0], v2[1] - v0[1]
        return ax * by - ay * bx

    def _face_brightness(self, face_verts):
        """Simple diffuse lighting based on face normal."""
        # Two edge vectors
        e1 = (face_verts[1][0] - face_verts[0][0],
              face_verts[1][1] - face_verts[0][1],
              face_verts[1][2] - face_verts[0][2])
        e2 = (face_verts[3][0] - face_verts[0][0],
              face_verts[3][1] - face_verts[0][1],
              face_verts[3][2] - face_verts[0][2])
        # Cross product
        nx = e1[1]*e2[2] - e1[2]*e2[1]
        ny = e1[2]*e2[0] - e1[0]*e2[2]
        nz = e1[0]*e2[1] - e1[1]*e2[0]
        length = math.sqrt(nx*nx + ny*ny + nz*nz) + 1e-9
        nz /= length
        # Light direction (from upper-right-front)
        lz = 0.577
        return clamp(nz * lz + 0.4, 0.15, 1.0)

    def _shade_color(self, base_color, brightness):
        r = int(base_color.red() * brightness)
        g = int(base_color.green() * brightness)
        b = int(base_color.blue() * brightness)
        return QColor(clamp(r,0,255), clamp(g,0,255), clamp(b,0,255))

    @staticmethod
    def _color_key(c):
        """Return a hashable tuple (r, g, b, a) from a QColor."""
        return (c.red(), c.green(), c.blue(), c.alpha())

    def _shade_char(self, brightness):
        idx = int(brightness * (len(SHADE_RAMP) - 1))
        return SHADE_RAMP[clamp(idx, 0, len(SHADE_RAMP)-1)]

    def _fill_polygon_ascii(self, projected, char, color):
        """Scanline fill a convex polygon in ASCII."""
        if len(projected) < 3:
            return
        min_y = max(0, int(min(p[1] for p in projected)))
        max_y = min(ROWS - 1, int(max(p[1] for p in projected)))
        min_x = max(0, int(min(p[0] for p in projected)))
        max_x = min(COLS - 1, int(max(p[0] for p in projected)))

        n = len(projected)

        for y in range(min_y, max_y + 1):
            intersections = []
            for i in range(n):
                j = (i + 1) % n
                y0, y1 = projected[i][1], projected[j][1]
                x0, x1 = projected[i][0], projected[j][0]
                if y0 == y1:
                    continue
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    ix = x0 + t * (x1 - x0)
                    intersections.append(ix)
            intersections.sort()
            for k in range(0, len(intersections) - 1, 2):
                x_start = int(math.ceil(intersections[k]))
                x_end = int(math.floor(intersections[k + 1]))
                for x in range(max(min_x, x_start), min(max_x, x_end) + 1):
                    self.canvas.set_char(y, x, char, color)

    def _render_cube(self):
        """Render the cube without clearing canvas or calling render().
        Used by CombinedScene to layer cube on top of other content."""
        ax = self.t * 0.5
        ay = self.t * 0.7
        az = self.t * 0.3

        # Transform vertices
        transformed = []
        for v in self.vertices:
            tv = rotate_x(v, ax)
            tv = rotate_y(tv, ay)
            tv = rotate_z(tv, az)
            transformed.append(tv)

        projected = [project(v) for v in transformed]

        # Build face list with depth for painter's algorithm
        face_data = []
        for fi, face in enumerate(self.faces):
            verts_3d = [transformed[i] for i in face]
            verts_2d = [(projected[i][0], projected[i][1]) for i in face]
            avg_z = sum(v[2] for v in verts_3d) / 4.0
            nz = self._normal_z(verts_2d[0], verts_2d[1], verts_2d[2])
            if nz > 0:  # Back-face culling
                face_data.append((avg_z, fi, verts_2d))

        # Sort far-to-near
        face_data.sort(key=lambda f: -f[0])

        for _, fi, verts_2d in face_data:
            brightness = self._face_brightness([transformed[i] for i in self.faces[fi]])
            char = self._shade_char(brightness)
            color = self._shade_color(self.face_colors[fi], brightness)
            self._fill_polygon_ascii(verts_2d, char, color)

        # Draw wireframe edges on top
        edge_chars = {
            self._color_key(Colors.CYAN): '/', self._color_key(Colors.GREEN): '\\',
            self._color_key(Colors.MAGENTA): '|', self._color_key(Colors.YELLOW): '-',
            self._color_key(Colors.ORANGE): '+', self._color_key(Colors.RED): '*'
        }
        for fi, face in enumerate(self.faces):
            verts_2d = [(projected[i][0], projected[i][1]) for i in face]
            ec = edge_chars.get(self._color_key(self.face_colors[fi]), '/')
            for i in range(4):
                j = (i + 1) % 4
                self.canvas.draw_line(
                    verts_2d[i][0], verts_2d[i][1],
                    verts_2d[j][0], verts_2d[j][1],
                    ec, self._shade_color(self.face_colors[fi], 0.9)
                )

    def update(self, dt):
        self.t += dt
        self.canvas.clear()
        self._render_cube()
        self.canvas.render()


# ─── Scene: Multi-Cube ──────────────────────────────────────────────
class MultiCubeScene:
    """Multiple nested/orbiting cubes."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.t = 0.0
        self.inner = CubeScene(canvas)
        self.cube_data = []  # (offset_x, offset_y, size, speed, axis, color)
        self.setup()

    def setup(self):
        self.cube_data = [
            (0, 0, 1.5, 0.4, 'y', Colors.CYAN),
            (0, 0, 2.2, 0.3, 'x', Colors.GREEN),
            (0, 0, 2.8, 0.25, 'z', Colors.MAGENTA),
        ]

    def update(self, dt):
        self.t += dt
        self.canvas.clear()

        for offset_x, offset_y, size, speed, axis, color in reversed(self.cube_data):
            self._draw_single_cube(offset_x, offset_y, size, speed, axis, color)

        self.canvas.render()

    def _draw_single_cube(self, ox, oy, size, speed, axis, base_color):
        s = size / 2
        vertices = [
            (-s+ox, -s+oy, -s), ( s+ox, -s+oy, -s), ( s+ox,  s+oy, -s), (-s+ox,  s+oy, -s),
            (-s+ox, -s+oy,  s), ( s+ox, -s+oy,  s), ( s+ox,  s+oy,  s), (-s+ox,  s+oy,  s),
        ]
        faces = [
            (0,1,2,3),(4,5,6,7),(0,1,5,4),(2,3,7,6),(0,3,7,4),(1,2,6,5)
        ]
        t = self.t * speed
        if axis == 'x':
            transformed = [rotate_x(v, t) for v in vertices]
        elif axis == 'y':
            transformed = [rotate_y(v, t) for v in vertices]
        else:
            transformed = [rotate_z(v, t) for v in vertices]

        projected = [project(v) for v in transformed]

        face_data = []
        for fi, face in enumerate(faces):
            verts_3d = [transformed[i] for i in face]
            verts_2d = [(projected[i][0], projected[i][1]) for i in face]
            avg_z = sum(v[2] for v in verts_3d) / 4.0
            nz = (verts_2d[1][0]-verts_2d[0][0])*(verts_2d[2][1]-verts_2d[0][1]) - \
                 (verts_2d[1][1]-verts_2d[0][1])*(verts_2d[2][0]-verts_2d[0][0])
            if nz > 0:
                # Simple brightness based on z-normal magnitude
                brightness = clamp(0.4 + 0.6 * min(nz / 50.0, 1.0), 0.2, 1.0)
                shaded = QColor(
                    int(base_color.red() * brightness),
                    int(base_color.green() * brightness),
                    int(base_color.blue() * brightness),
                )
                face_data.append((avg_z, verts_2d, shaded))

        face_data.sort(key=lambda f: -f[0])

        for _, verts_2d, shaded in face_data:
            self._scanline_fill(verts_2d, shaded)

        # Draw wireframe only for front-facing faces
        for fi, face in enumerate(faces):
            v2d = [(projected[i][0], projected[i][1]) for i in face]
            nz = (v2d[1][0]-v2d[0][0])*(v2d[2][1]-v2d[0][1]) - \
                 (v2d[1][1]-v2d[0][1])*(v2d[2][0]-v2d[0][0])
            if nz > 0:
                for i in range(4):
                    j = (i+1)%4
                    self.canvas.draw_line(
                        v2d[i][0], v2d[i][1],
                        v2d[j][0], v2d[j][1],
                        '+', base_color
                    )

    def _scanline_fill(self, projected, color):
        n = len(projected)
        if n < 3:
            return
        min_y = max(0, int(min(p[1] for p in projected)))
        max_y = min(ROWS-1, int(max(p[1] for p in projected)))
        min_x = max(0, int(min(p[0] for p in projected)))
        max_x = min(COLS-1, int(max(p[0] for p in projected)))

        for y in range(min_y, max_y+1):
            intersections = []
            for i in range(n):
                j = (i+1) % n
                y0, y1 = projected[i][1], projected[j][1]
                x0, x1 = projected[i][0], projected[j][0]
                if y0 == y1:
                    continue
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    intersections.append(x0 + t*(x1 - x0))
            intersections.sort()
            for k in range(0, len(intersections)-1, 2):
                xs = int(math.ceil(intersections[k]))
                xe = int(math.floor(intersections[k+1]))
                for x in range(max(min_x, xs), min(max_x, xe)+1):
                    self.canvas.set_char(y, x, '#', color)


# ─── Scene: Terrain ─────────────────────────────────────────────────
class TerrainScene:
    """Animated 3D terrain rendered as ASCII with height-based coloring."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.t = 0.0
        self.terrain_chars = " .'-:;~=+*!#%@"
        self.height_colors = [
            Colors.BLUE,      # deep water
            Colors.CYAN,      # shallow water
            Colors.YELLOW,    # sand
            Colors.GREEN,     # grass
            (QColor(0, 180, 60)),  # forest
            (QColor(120, 80, 40)),  # mountain
            Colors.WHITE,     # snow
        ]

    def _height_color(self, h):
        """Map height 0..1 to color."""
        if h < 0.3:
            return self._lerp_color(Colors.BLUE, Colors.CYAN, h / 0.3)
        elif h < 0.35:
            return self._lerp_color(Colors.CYAN, Colors.YELLOW, (h - 0.3) / 0.05)
        elif h < 0.55:
            return self._lerp_color(Colors.YELLOW, Colors.GREEN, (h - 0.35) / 0.2)
        elif h < 0.7:
            return self._lerp_color(Colors.GREEN, QColor(0, 180, 60), (h - 0.55) / 0.15)
        elif h < 0.85:
            return self._lerp_color(QColor(0, 180, 60), QColor(120, 80, 40), (h - 0.7) / 0.15)
        else:
            return self._lerp_color(QColor(120, 80, 40), Colors.WHITE, (h - 0.85) / 0.15)

    def _lerp_color(self, c1, c2, t):
        t = clamp(t, 0, 1)
        return QColor(
            int(c1.red() + (c2.red()-c1.red())*t),
            int(c1.green() + (c2.green()-c1.green())*t),
            int(c1.blue() + (c2.blue()-c1.blue())*t),
        )

    def _height_char(self, h):
        idx = int(h * (len(self.terrain_chars) - 1))
        return self.terrain_chars[clamp(idx, 0, len(self.terrain_chars)-1)]

    def update(self, dt):
        self.t += dt
        self.canvas.clear()

        grid_w = COLS
        grid_h = ROWS

        # Generate heightmap with animation offset
        offset_x = self.t * 2.0
        offset_y = self.t * 0.5
        heights = []
        for r in range(grid_h):
            row = []
            for c in range(grid_w):
                nx = c / grid_w * 5.0 + offset_x
                ny = r / grid_h * 5.0 + offset_y
                h = fbm(nx, ny, octaves=5, seed=42)
                # Add wave animation
                wave = math.sin(nx * 1.5 + self.t * 2) * 0.03
                h = clamp(h + wave, 0, 1)
                row.append(h)
            heights.append(row)

        # Simple shadow: compare with neighbor
        for r in range(grid_h):
            for c in range(grid_w):
                h = heights[r][c]
                # Shadow from left neighbor
                shadow = 1.0
                if c > 0:
                    diff = h - heights[r][c-1]
                    shadow = clamp(shadow - diff * 3, 0.3, 1.0)
                if r > 0:
                    diff = h - heights[r-1][c]
                    shadow = clamp(shadow - diff * 2, 0.3, 1.0)

                color = self._height_color(h * shadow)
                char = self._height_char(h * shadow)
                self.canvas.set_char(r, c, char, color)

        # Overlay contour lines
        for r in range(1, grid_h - 1):
            for c in range(1, grid_w - 1):
                h = heights[r][c]
                contour_interval = 0.1
                level = h % contour_interval
                if level < 0.008 or level > contour_interval - 0.008:
                    if h > 0.32:  # Don't draw contours on water
                        self.canvas.set_char(r, c, '-', Colors.WHITE)

        self.canvas.render()


# ─── Scene: Particles ───────────────────────────────────────────────
class Particle:
    __slots__ = ['x', 'y', 'vx', 'vy', 'life', 'max_life', 'char', 'color', 'gravity']

    def __init__(self, x, y, vx, vy, life, char, color, gravity=0.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.char = char
        self.color = color
        self.gravity = gravity


class ParticleScene:
    """ASCII particle system with multiple emitters."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.t = 0.0
        self.particles = []
        self.max_particles = 600
        self.emitter_mode = 0  # 0=fountain, 1=firework, 2=rain, 3=spiral

    def _spawn_fountain(self, dt):
        cx, cy = COLS // 2, ROWS - 2
        for _ in range(8):
            angle = -math.pi/2 + random.gauss(0, 0.4)
            speed = random.uniform(15, 35)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.uniform(1.5, 3.0)
            chars = ['*', '+', '.', 'o', '^', '#', '@']
            ch = random.choice(chars)
            colors = [Colors.CYAN, Colors.GREEN, Colors.YELLOW, Colors.MAGENTA, Colors.ORANGE]
            color = random.choice(colors)
            self.particles.append(Particle(cx, cy, vx, vy, life, ch, color, gravity=18))

    def _spawn_firework(self, dt):
        cx = random.randint(15, COLS - 15)
        cy = random.randint(5, ROWS // 2)
        burst_chars = ['*', '.', '+', '#', '@', 'o', ':']
        palette = [Colors.RED, Colors.YELLOW, Colors.MAGENTA, Colors.CYAN, Colors.GREEN, Colors.ORANGE]
        color = random.choice(palette)
        count = random.randint(30, 60)
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(5, 25)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.uniform(0.8, 2.5)
            ch = random.choice(burst_chars)
            self.particles.append(Particle(cx, cy, vx, vy, life, ch, color, gravity=8))

    def _spawn_rain(self, dt):
        for _ in range(12):
            x = random.randint(0, COLS - 1)
            y = random.randint(-5, 0)
            speed = random.uniform(30, 50)
            chars = ['|', '|', '|', ':', '.', '.']
            ch = random.choice(chars)
            self.particles.append(Particle(x, y, random.uniform(-2, 2), speed, 2.0, ch, Colors.CYAN, gravity=0))

    def _spawn_spiral(self, dt):
        cx, cy = COLS // 2, ROWS // 2
        count = 6
        for i in range(count):
            angle = self.t * 3.0 + i * (2 * math.pi / count)
            r = 5 + math.sin(self.t * 2) * 3
            x = cx + math.cos(angle) * r
            y = cy + math.sin(angle) * r
            # Tangential velocity
            vx = -math.sin(angle) * 12
            vy = math.cos(angle) * 12
            life = random.uniform(1.0, 2.0)
            chars = ['@', '#', '*', '+', 'o', '.']
            ch = chars[i % len(chars)]
            hue = (self.t * 50 + i * 60) % 360
            color = QColor.fromHsv(hue / 360.0, 0.9, 1.0)
            self.particles.append(Particle(x, y, vx, vy, life, ch, color, gravity=0))

    def update(self, dt):
        self.t += dt
        self.canvas.clear()

        # Spawn
        if self.emitter_mode == 0:
            self._spawn_fountain(dt)
        elif self.emitter_mode == 1:
            self._spawn_firework(dt)
        elif self.emitter_mode == 2:
            self._spawn_rain(dt)
        elif self.emitter_mode == 3:
            self._spawn_spiral(dt)

        # Cap particles
        if len(self.particles) > self.max_particles:
            self.particles = self.particles[-self.max_particles:]

        # Update & render
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.vy += p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt

            col = int(p.x)
            row = int(p.y)
            if 0 <= row < ROWS and 0 <= col < COLS:
                alpha = clamp(p.life / p.max_life, 0, 1)
                color = QColor(p.color)
                color.setAlphaF(alpha)
                self.canvas.set_char(row, col, p.char, color)
            alive.append(p)

        self.particles = alive
        self.canvas.render()


# ─── Scene: Emoji Art ────────────────────────────────────────────────
class EmojiScene:
    """Renders emoji art compositions and animated emoji patterns."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.t = 0.0
        self.mode = 0  # 0=rain, 1=matrix, 2=fireworks, 3=wave, 4=gallery
        self.emojis = [
            "😀", "😂", "🥰", "😎", "🤩", "🥳", "😇", "🤔",
            "😈", "👻", "💀", "🤖", "👽", "🎃", "🦊", "🐱",
            "🐶", "🐼", "🦄", "🐉", "🌈", "⭐", "🔥", "💫",
            "💎", "🎮", "🎵", "❤️", "🌟", "✨", "🍕", "🎄",
            "🌸", "🍀", "🌊", "⚡", "🎯", "🏆", "💰", "🚀",
        ]
        self.emoji_width = 2  # Each emoji occupies 2 columns in grid
        self.columns_data = {}  # For matrix rain effect

    def _draw_emoji(self, r, c, emoji, color=None):
        """Place an emoji on the canvas (occupies 2 cols, 1 row)."""
        if 0 <= r < ROWS and 0 <= c < COLS - 1:
            # We store the emoji in first col and mark second
            self.canvas.set_char(r, c, emoji, color or Colors.WHITE)
            self.canvas.set_char(r, c + 1, ' ', color or Colors.WHITE)  # placeholder

    def _clear_emoji(self, r, c):
        if 0 <= r < ROWS and 0 <= c < COLS:
            self.canvas.set_char(r, c, ' ')
            if c + 1 < COLS:
                self.canvas.set_char(r, c + 1, ' ')

    def _mode_emoji_rain(self):
        """Falling emoji rain."""
        if not self.columns_data or random.random() < 0.05:
            col = random.randint(0, (COLS // 2) - 1) * 2
            if col not in self.columns_data:
                self.columns_data[col] = {
                    'y': random.uniform(-20, 0),
                    'speed': random.uniform(3, 10),
                    'trail': [],
                    'emoji': random.choice(self.emojis),
                    'length': random.randint(3, 12),
                }

        new_cols = {}
        for col, data in self.columns_data.items():
            data['y'] += data['speed'] * 0.05
            data['trail'].append(int(data['y']))
            if len(data['trail']) > data['length']:
                data['trail'].pop(0)

            # Draw trail
            for i, row in enumerate(data['trail']):
                if 0 <= row < ROWS:
                    alpha = (i + 1) / len(data['trail'])
                    if i == len(data['trail']) - 1:
                        # Head - bright
                        self._draw_emoji(row, col, data['emoji'], Colors.WHITE)
                    else:
                        # Trail - faded
                        faded = QColor(0, int(180 * alpha), int(80 * alpha))
                        ch_idx = (int(data['y']) + i) % len(self.emojis)
                        self._draw_emoji(row, col, self.emojis[ch_idx], faded)

            if data['trail'] and data['trail'][-1] < ROWS + 5:
                new_cols[col] = data

        self.columns_data = new_cols

    def _mode_matrix(self):
        """Emoji matrix digital rain - mixed with ASCII."""
        if not self.columns_data or random.random() < 0.08:
            col = random.randint(0, COLS - 1)
            if col not in self.columns_data:
                self.columns_data[col] = {
                    'y': -random.uniform(0, 10),
                    'speed': random.uniform(4, 12),
                    'trail': [],
                    'length': random.randint(5, 20),
                }

        new_cols = {}
        for col, data in self.columns_data.items():
            data['y'] += data['speed'] * 0.04
            data['trail'].append(int(data['y']))
            if len(data['trail']) > data['length']:
                data['trail'].pop(0)

            for i, row in enumerate(data['trail']):
                if 0 <= row < ROWS:
                    alpha = (i + 1) / len(data['trail'])
                    # Mix emoji and ASCII
                    if random.random() < 0.15 and col < COLS - 1:
                        e = random.choice(self.emojis)
                        color = QColor(0, 255, int(100 * alpha))
                        self._draw_emoji(row, col, e, color)
                    else:
                        # ASCII chars from emoji-like set
                        ascii_chars = ":;=+*#%@&~^"
                        ch = random.choice(ascii_chars)
                        g = int(255 * alpha)
                        color = QColor(0, g, int(g * 0.4))
                        self.canvas.set_char(row, col, ch, color)

            if data['trail'] and data['trail'][-1] < ROWS + 5:
                new_cols[col] = data

        self.columns_data = new_cols

    def _mode_wave(self):
        """Emoji sine wave."""
        wave_emojis = ["🌊", "🐟", "🐠", "🦈", "🐙", "🦑", "🐚", "🌊"]
        count = 15
        for i in range(count):
            phase = self.t * 2.0 + i * 0.5
            x = int(COLS / 2 + (i - count/2) * 3 + math.sin(phase) * 8)
            y = int(ROWS / 2 + math.sin(phase * 0.7 + i * 0.3) * 6)
            x = max(0, min(COLS - 2, x))
            y = max(0, min(ROWS - 1, y))
            e_idx = i % len(wave_emojis)
            self._draw_emoji(y, x, wave_emojis[e_idx], Colors.WHITE)

        # Second wave (offset)
        wave2 = ["🌈", "✨", "💫", "⭐", "🌟", "💖", "🦋", "🌈"]
        for i in range(count):
            phase = self.t * 1.5 + i * 0.5 + math.pi
            x = int(COLS / 2 + (i - count/2) * 3 + math.sin(phase) * 6)
            y = int(ROWS / 2 + 8 + math.sin(phase * 0.8 + i * 0.4) * 4)
            x = max(0, min(COLS - 2, x))
            y = max(0, min(ROWS - 1, y))
            e_idx = i % len(wave2)
            self._draw_emoji(y, x, wave2[e_idx], Colors.WHITE)

    def _mode_gallery(self):
        """Static emoji art gallery with selection highlight."""
        gallery = [
            ["😀", "😂", "🥰", "😎", "🤩", "🥳", "😇", "🤔"],
            ["😈", "👻", "💀", "🤖", "👽", "🎃", "🦊", "🐱"],
            ["🐶", "🐼", "🦄", "🐉", "🌈", "⭐", "🔥", "💫"],
            ["💎", "🎮", "🎵", "❤️", "🌟", "✨", "🍕", "🎄"],
            ["🌸", "🍀", "🌊", "⚡", "🎯", "🏆", "💰", "🚀"],
        ]
        label = "~ EMOJI GALLERY ~"
        label_x = (COLS // 2) - len(label) // 2
        for i, ch in enumerate(label):
            self.canvas.set_char(2, label_x + i, ch, Colors.CYAN)

        border_top = "+" + "-" * (COLS - 2) + "+"
        for i, ch in enumerate(border_top):
            self.canvas.set_char(3, i, ch, Colors.MAGENTA)
        for i, ch in enumerate(border_top):
            self.canvas.set_char(3 + len(gallery) * 2 + 1, i, ch, Colors.MAGENTA)

        for ri, row in enumerate(gallery):
            y = 5 + ri * 2
            # Row label
            row_label = f"[{ri*8}-{ri*8+7}]"
            self.canvas.set_char(y, 2, '|', Colors.MAGENTA)
            for li, lc in enumerate(row_label):
                self.canvas.set_char(y, 4 + li, lc, Colors.YELLOW)
            for ci, emoji in enumerate(row):
                x = 14 + ci * 10
                self._draw_emoji(y, x, emoji, Colors.WHITE)
            self.canvas.set_char(y, COLS - 1, '|', Colors.MAGENTA)

    def update(self, dt):
        self.t += dt
        self.canvas.clear()

        if self.mode == 0:
            self._mode_emoji_rain()
        elif self.mode == 1:
            self._mode_matrix()
        elif self.mode == 2:
            self._mode_wave()
        elif self.mode == 3:
            self._mode_gallery()

        self.canvas.render()


# ─── Scene: Combined Demo ───────────────────────────────────────────
class CombinedScene:
    """All effects in one view: cube + terrain bg + particles + emoji."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.cube = CubeScene(canvas)
        self.terrain = TerrainScene(canvas)
        self.particles = ParticleScene(canvas)
        self.emoji = EmojiScene(canvas)
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        self.canvas.clear()

        # 1. Draw terrain in background (half brightness)
        self.terrain.t = self.t
        grid_w, grid_h = COLS, ROWS
        for r in range(grid_h):
            for c in range(grid_w):
                nx = c / grid_w * 5.0 + self.t * 0.5
                ny = r / grid_h * 5.0 + self.t * 0.2
                h = fbm(nx, ny, octaves=4, seed=99)
                h = clamp(h, 0, 1)
                # Dim terrain
                brightness = 0.3
                color = self.terrain._height_color(h)
                color = QColor(
                    int(color.red() * brightness),
                    int(color.green() * brightness),
                    int(color.blue() * brightness),
                )
                ch = self.terrain._height_char(h)
                if random.random() < 0.7:  # sparse it out
                    self.canvas.set_char(r, c, ch, color)

        # 2. Draw small cube in center (inline to avoid canvas.clear())
        saved_verts = self.cube.vertices[:]
        s = 0.8
        self.cube.vertices = [
            (-s,-s,-s),(s,-s,-s),(s,s,-s),(-s,s,-s),
            (-s,-s,s),(s,-s,s),(s,s,s),(-s,s,s),
        ]
        old_t = self.cube.t
        self.cube.t = self.t * 0.8
        # Manually run cube rendering without calling update (which clears canvas)
        self.cube._render_cube()
        self.cube.vertices = saved_verts
        self.cube.t = old_t

        # 3. Sprinkle emoji
        emojis = ["✨", "⭐", "🌟", "💫", "🔥"]
        for i in range(5):
            ex = int(COLS/2 + math.cos(self.t + i*1.3) * 30)
            ey = int(ROWS/2 + math.sin(self.t*0.7 + i*1.3) * 10)
            if 0 <= ey < ROWS and 0 <= ex < COLS - 1:
                self.canvas.set_char(ey, ex, emojis[i % len(emojis)], Colors.YELLOW)
                self.canvas.set_char(ey, ex+1, ' ', Colors.YELLOW)

        # 4. A few particles
        for i in range(3):
            px = int(COLS/2 + math.cos(self.t*2 + i*2.1) * 20)
            py = int(ROWS/2 + math.sin(self.t*1.5 + i*2.1) * 8)
            if 0 <= py < ROWS and 0 <= px < COLS:
                self.canvas.set_char(py, px, '.', Colors.CYAN)

        self.canvas.render()


# ─── Main Window ────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 ASCII Graphics Engine")
        self.setMinimumSize(960, 700)
        self.resize(1100, 780)

        # Dark theme
        self.setStyleSheet("""
            QMainWindow { background-color: #0a0a12; }
            QPushButton {
                background-color: #1a1a2e;
                color: #e0e0f0;
                border: 1px solid #333355;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-family: 'DejaVu Sans Mono', monospace;
            }
            QPushButton:hover { background-color: #2a2a4e; border-color: #00ccff; }
            QPushButton:checked { background-color: #0a3a5a; border-color: #00ccff; color: #00ffcc; }
            QLabel {
                color: #a0a0c0;
                font-family: 'DejaVu Sans Mono', monospace;
                font-size: 12px;
            }
            QComboBox {
                background-color: #1a1a2e;
                color: #e0e0f0;
                border: 1px solid #333355;
                border-radius: 4px;
                padding: 4px 8px;
                font-family: 'DejaVu Sans Mono', monospace;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a2e;
                color: #e0e0f0;
                selection-background-color: #0a3a5a;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Title
        title = QLabel("⬡ ASCII GRAPHICS ENGINE ⬡")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; color: #00ccff; font-weight: bold; padding: 4px;")
        layout.addWidget(title)

        # Scene buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.scene_buttons = []
        scenes = [
            ("3D Cube", "cube"),
            ("Multi-Cube", "multi_cube"),
            ("Terrain", "terrain"),
            ("Particles", "particles"),
            ("Emojis", "emojis"),
            ("Combined", "combined"),
        ]
        self.button_group = []
        for i, (label, key) in enumerate(scenes):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("scene_key", key)
            btn.clicked.connect(lambda checked, k=key: self.switch_scene(k))
            if i == 0:
                btn.setChecked(True)
            btn_layout.addWidget(btn)
            self.scene_buttons.append(btn)
            self.button_group.append(btn)

        layout.addLayout(btn_layout)

        # Sub-mode selector
        sub_layout = QHBoxLayout()
        sub_layout.setSpacing(8)

        self.sub_label = QLabel("Mode:")
        sub_layout.addWidget(self.sub_label)

        self.sub_combo = QComboBox()
        self.sub_combo.setMinimumWidth(200)
        self.sub_combo.currentIndexChanged.connect(self._on_sub_mode_changed)
        sub_layout.addWidget(self.sub_combo)

        self.speed_label = QLabel("Speed:")
        sub_layout.addWidget(self.speed_label)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(30)
        self.speed_slider.setValue(10)
        self.speed_slider.setMaximumWidth(150)
        sub_layout.addWidget(self.speed_slider)

        self.fps_label = QLabel("FPS: --")
        self.fps_label.setStyleSheet("color: #00ff88;")
        sub_layout.addWidget(self.fps_label)

        sub_layout.addStretch()
        layout.addLayout(sub_layout)

        # Canvas
        self.canvas = AsciiCanvas()
        canvas_frame = QFrame()
        canvas_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #222244;
                border-radius: 8px;
                background-color: #0a0a12;
            }
        """)
        frame_layout = QVBoxLayout(canvas_frame)
        frame_layout.setContentsMargins(4, 4, 4, 4)
        frame_layout.addWidget(self.canvas)
        layout.addWidget(canvas_frame, stretch=1)

        # Status bar
        self.status_label = QLabel("Scene: 3D Cube | Press buttons to switch scenes")
        self.status_label.setStyleSheet("color: #666688; font-size: 11px; padding: 2px;")
        layout.addWidget(self.status_label)

        # Scenes
        self.scenes = {}
        self.scenes['cube'] = CubeScene(self.canvas)
        self.scenes['multi_cube'] = MultiCubeScene(self.canvas)
        self.scenes['terrain'] = TerrainScene(self.canvas)
        self.scenes['particles'] = ParticleScene(self.canvas)
        self.scenes['emojis'] = EmojiScene(self.canvas)
        self.scenes['combined'] = CombinedScene(self.canvas)

        self.current_scene = 'cube'
        self._update_sub_modes()

        # Timer
        self.last_time = time.time()
        self.frame_times = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)  # ~60fps

    def _update_sub_modes(self):
        self.sub_combo.blockSignals(True)
        self.sub_combo.clear()
        modes = {
            'cube': ['Standard Rotation'],
            'multi_cube': ['Nested Cubes'],
            'terrain': ['Scrolling Terrain'],
            'particles': ['Fountain', 'Fireworks', 'Rain', 'Spiral'],
            'emojis': ['Emoji Rain', 'Matrix', 'Wave', 'Gallery'],
            'combined': ['All Combined'],
        }
        for m in modes.get(self.current_scene, []):
            self.sub_combo.addItem(m)
        self.sub_combo.blockSignals(False)

    def _on_sub_mode_changed(self, index):
        if self.current_scene == 'particles':
            self.scenes['particles'].emitter_mode = index
        elif self.current_scene == 'emojis':
            self.scenes['emojis'].mode = index
            self.scenes['emojis'].columns_data = {}

    def switch_scene(self, key):
        self.current_scene = key
        for btn in self.button_group:
            btn.setChecked(btn.property("scene_key") == key)
        self._update_sub_modes()

        # Reset scene-specific state
        if key == 'emojis':
            self.scenes['emojis'].columns_data = {}
        elif key == 'particles':
            self.scenes['particles'].particles = []

        scene_names = {
            'cube': '3D Cube', 'multi_cube': 'Multi-Cube',
            'terrain': 'Terrain', 'particles': 'Particles',
            'emojis': 'Emojis', 'combined': 'Combined',
        }
        self.status_label.setText(f"Scene: {scene_names.get(key, key)} | Use combo box for sub-modes")

    def tick(self):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        # Speed multiplier
        speed = self.speed_slider.value() / 10.0
        dt *= speed

        scene = self.scenes.get(self.current_scene)
        if scene:
            if isinstance(scene, (CubeScene, MultiCubeScene, TerrainScene,
                                   ParticleScene, EmojiScene, CombinedScene)):
                scene.update(dt)

        # FPS counter
        self.frame_times.append(now)
        self.frame_times = [t for t in self.frame_times if now - t < 1.0]
        fps = len(self.frame_times)
        self.fps_label.setText(f"FPS: {fps}")


# ─── Entry Point ────────────────────────────────────────────────────
def main():
    # Prefer a display; fall back gracefully
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(10, 10, 18))
    palette.setColor(QPalette.WindowText, QColor(224, 224, 240))
    palette.setColor(QPalette.Base, QColor(15, 15, 25))
    palette.setColor(QPalette.Text, QColor(224, 224, 240))
    palette.setColor(QPalette.Button, QColor(26, 26, 46))
    palette.setColor(QPalette.ButtonText, QColor(224, 224, 240))
    palette.setColor(QPalette.Highlight, QColor(0, 120, 200))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()