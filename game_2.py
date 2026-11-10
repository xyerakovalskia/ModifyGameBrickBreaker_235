import math
import os
import random
import tkinter as tk

SHAPES = ['heart', 'circle', 'triangle']

# Ukuran brick (persegi panjang) dan jarak antar brick
BRICK_W, BRICK_H = 32, 12
CELL_W, CELL_H = 35, 15

# Backsound: taruh file lagunya di folder yang sama dengan game ini
# dengan nama "backsound" (mp3 / ogg / wav), mis. backsound.mp3
MUSIC_NAME = 'backsound'
MUSIC_VOLUME = 0.5        # 0.0 (hening) sampai 1.0 (maksimal)

# Pengaturan skor dan kecepatan bola
POINTS_PER_BRICK = 10     # skor per brick yang hancur
BASE_SPEED = 4            # kecepatan awal bola
SPEED_STEP = 0.5          # tambahan kecepatan tiap kelipatan 100 skor
MAX_SPEED = 12            # batas kecepatan (supaya tetap bisa dimainkan)

# Warna pelangi dari baris atas ke bawah
RAINBOW = ['#8e44ad', '#2980b9', '#27ae60',
           '#f1c40f', '#e67e22', '#e74c3c']


def inside(shape, px, py, cx, top, size):
    """True jika titik (px, py) berada di dalam formasi `shape`."""
    cy = top + size / 2
    if shape == 'circle':
        return (px - cx) ** 2 + (py - cy) ** 2 <= (size / 2) ** 2
    if shape == 'triangle':
        dy = py - top
        half = dy / size * (size * 1.3 / 2)
        return 0 <= dy <= size and abs(px - cx) <= half
    # love: (x^2 + y^2 - 1)^3 - x^2 * y^3 <= 0
    k = size / 2.28
    x = (px - cx) / k
    y = (cy - py) / k + 0.125
    return (x * x + y * y - 1) ** 3 - x * x * y ** 3 <= 0


def heart_points(cx, cy, size):
    """Titik-titik polygon bentuk love dengan lebar sekitar `size`."""
    pts = []
    scale = size / 32.0
    for deg in range(0, 360, 12):
        t = math.radians(deg)
        hx = 16 * math.sin(t) ** 3
        hy = (13 * math.cos(t) - 5 * math.cos(2 * t)
              - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append(cx + hx * scale)
        pts.append(cy - (hy + 2.5) * scale)
    return pts


def draw_shape(canvas, shape, cx, cy, size, fill, tags=()):
    """Gambar satu bentuk (heart / circle / triangle) di canvas."""
    half = size / 2
    if shape == 'circle':
        return canvas.create_oval(cx - half, cy - half,
                                  cx + half, cy + half,
                                  fill=fill, outline='black', tags=tags)
    if shape == 'triangle':
        return canvas.create_polygon(cx, cy - half,
                                     cx + half, cy + half,
                                     cx - half, cy + half,
                                     fill=fill, outline='black', tags=tags)
    return canvas.create_polygon(heart_points(cx, cy, size),
                                 fill=fill, outline='black', tags=tags)


def start_music():
    """Putar backsound berulang-ulang. Game tetap jalan walau gagal."""
    folder = os.path.dirname(os.path.abspath(__file__))
    path = None
    for ext in ('mp3', 'ogg', 'wav'):
        candidate = os.path.join(folder, '%s.%s' % (MUSIC_NAME, ext))
        if os.path.exists(candidate):
            path = candidate
            break
    if path is None:
        print('Backsound: file "%s.mp3" tidak ditemukan di %s'
              % (MUSIC_NAME, folder))
        return
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(MUSIC_VOLUME)
        pygame.mixer.music.play(-1)   # -1 = ulang terus
    except Exception as e:
        print('Backsound tidak bisa diputar:', e)
        print('Pastikan pygame terpasang: python -m pip install pygame')


class GameObject(object):
    def __init__(self, canvas, item):
        self.canvas = canvas
        self.item = item

    def get_position(self):
        return self.canvas.coords(self.item)

    def move(self, x, y):
        self.canvas.move(self.item, x, y)

    def delete(self):
        self.canvas.delete(self.item)


class Ball(GameObject):
    def __init__(self, canvas, x, y, speed):
        self.radius = 8
        self.direction = [1, -1]
        self.speed = speed
        item = canvas.create_oval(x - self.radius, y - self.radius,
                                  x + self.radius, y + self.radius,
                                  fill='white')
        super(Ball, self).__init__(canvas, item)

    def update(self):
        coords = self.get_position()
        width = self.canvas.winfo_width()
        if coords[0] <= 0 or coords[2] >= width:
            self.direction[0] *= -1
        if coords[1] <= 0:
            self.direction[1] *= -1
        x = self.direction[0] * self.speed
        y = self.direction[1] * self.speed
        self.move(x, y)

    def collide(self, game_objects):
        coords = self.get_position()
        x = (coords[0] + coords[2]) * 0.5
        if len(game_objects) > 1:
            self.direction[1] *= -1
        elif len(game_objects) == 1:
            game_object = game_objects[0]
            coords = game_object.get_position()
            if x > coords[2]:
                self.direction[0] = 1
            elif x < coords[0]:
                self.direction[0] = -1
            else:
                self.direction[1] *= -1

        for game_object in game_objects:
            if isinstance(game_object, Brick):
                game_object.hit()
            elif isinstance(game_object, Paddle):
                # Kena paddle -> selalu mantul ke atas (anti bolak-balik)
                self.direction[1] = -1


class Paddle(GameObject):
    def __init__(self, canvas, x, y):
        self.width = 160
        self.height = 14
        self.ball = None
        item = canvas.create_rectangle(x - self.width / 2,
                                       y - self.height / 2,
                                       x + self.width / 2,
                                       y + self.height / 2,
                                       fill='yellow')
        super(Paddle, self).__init__(canvas, item)

    def set_ball(self, ball):
        self.ball = ball

    def move_to(self, x):
        """Pindahkan paddle agar titik tengahnya ada di x (dibatasi layar)."""
        coords = self.get_position()
        width = self.canvas.winfo_width()
        half = self.width / 2
        x = max(half, min(x, width - half))
        offset = x - (coords[0] + coords[2]) / 2
        super(Paddle, self).move(offset, 0)
        if self.ball is not None:
            self.ball.move(offset, 0)