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


class Brick(GameObject):
    DAMAGED = '#ecf0f1'

    def __init__(self, canvas, x, y, hits, color):
        self.width = BRICK_W
        self.height = BRICK_H
        self.hits = hits
        item = canvas.create_rectangle(x - self.width / 2,
                                       y - self.height / 2,
                                       x + self.width / 2,
                                       y + self.height / 2,
                                       fill=color, outline='#222222',
                                       tags='brick')
        super(Brick, self).__init__(canvas, item)

    def hit(self):
        self.hits -= 1
        if self.hits <= 0:
            self.delete()
        else:
            self.canvas.itemconfig(self.item, fill=Brick.DAMAGED)


class Game(tk.Frame):
    def __init__(self, master, width, height):
        super(Game, self).__init__(master)
        self.width = width
        self.height = height
        self.canvas = tk.Canvas(self, bg='#aaaaff',
                                width=self.width,
                                height=self.height,
                                highlightthickness=0)
        self.canvas.pack()
        self.pack()

        self.items = {}
        self.ball = None
        self.paddle = None
        self.hud = None
        self.score = 0
        self.speed = BASE_SPEED
        self.started = False
        self.shape_mode = 'heart'

        self.canvas.focus_set()
        self.show_menu()

    # ------------------------------------------------------------ Menu
    def show_menu(self):
        self.canvas.config(cursor='arrow')
        cx, cy = self.width / 2, self.height / 2
        self.canvas.create_text(cx, cy - 170, text='Pilih Bentuk Brick',
                                font=('Arial', 36, 'bold'), tags='menu')

        options = [('heart', 'Love'), ('circle', 'Lingkaran'),
                   ('triangle', 'Segitiga'), ('random', 'Random')]
        bw, bh, gap = 200, 180, 40
        start_x = cx - (len(options) * bw + (len(options) - 1) * gap) / 2

        for i, (key, label) in enumerate(options):
            x1 = start_x + i * (bw + gap)
            y1 = cy - 100
            x2, y2 = x1 + bw, y1 + bh
            tag = 'btn_' + key
            self.canvas.create_rectangle(x1, y1, x2, y2, fill='white',
                                         outline='black', width=2,
                                         tags=('menu', tag))
            icon_x, icon_y = (x1 + x2) / 2, y1 + 70
            if key == 'random':
                # Tampilkan ketiga bentuk sekaligus
                for j, shape in enumerate(SHAPES):
                    draw_shape(self.canvas, shape, x1 + 45 + j * 55,
                               icon_y, 36, '#3498db', ('menu', tag))
            else:
                draw_shape(self.canvas, key, icon_x, icon_y, 70,
                           '#e74c3c', ('menu', tag))
            self.canvas.create_text(icon_x, y2 - 35, text=label,
                                    font=('Arial', 20), tags=('menu', tag))
            self.canvas.tag_bind(tag, '<Button-1>',
                                 lambda e, k=key: self.choose_shape(k))

    def choose_shape(self, shape):
        self.shape_mode = shape
        self.canvas.delete('menu')
        self.canvas.config(cursor='none')
        # Jeda singkat supaya klik pilihan tidak langsung memulai game
        self.after(250, self.build_level)

    # ----------------------------------------------------------- Level
    def build_level(self):
        self.paddle_y = self.height - 100
        self.paddle = Paddle(self.canvas, self.width / 2, self.paddle_y)
        self.spawn_bricks()
        self.setup_game()
        # Paddle mengikuti posisi mouse (sumbu x)
        self.canvas.bind('<Motion>',
                         lambda e: self.paddle.move_to(e.x))

    def spawn_bricks(self):
        """Susun brick membentuk formasi (dipanggil lagi saat brick habis)."""
        # Buang referensi brick lama, sisakan paddle
        self.items = {self.paddle.item: self.paddle}

        # Random = pilih salah satu formasi secara acak
        if self.shape_mode == 'random':
            shape = random.choice(SHAPES)
        else:
            shape = self.shape_mode

        cx = self.width / 2
        top = 80
        size = min(self.height * 0.5, self.width * 0.55)
        max_i = int(size * 0.7 / CELL_W) + 1
        rows = int(size // CELL_H) + 1

        for j in range(rows):
            py = top + CELL_H / 2 + j * CELL_H
            # Warna pelangi berdasarkan posisi baris
            band = min(int((py - top) / size * len(RAINBOW)),
                       len(RAINBOW) - 1)
            hits = 2 if band == 0 else 1   # band ungu teratas 2x pukulan
            for i in range(-max_i, max_i + 1):
                px = cx + i * CELL_W
                if inside(shape, px, py, cx, top, size):
                    self.add_brick(px, py, hits, RAINBOW[band])

    def setup_game(self):
        self.started = False
        self.add_ball()
        self.update_hud()
        self.text = self.draw_text(self.width / 2, self.height / 2,
                                   'Click or Press Space', 40)
        self.canvas.bind('<space>', lambda _: self.start_game())
        self.canvas.bind('<Button-1>', lambda _: self.start_game())

    def add_ball(self):
        if self.ball is not None:
            self.ball.delete()
        paddle_coords = self.paddle.get_position()
        x = (paddle_coords[0] + paddle_coords[2]) * 0.5
        self.ball = Ball(self.canvas, x, self.paddle_y - 16, self.speed)
        self.paddle.set_ball(self.ball)

    def add_brick(self, x, y, hits, color):
        brick = Brick(self.canvas, x, y, hits, color)
        self.items[brick.item] = brick

    def draw_text(self, x, y, text, size=40):
        font = ('Arial', size)
        return self.canvas.create_text(x, y, text=text, font=font)

    def update_hud(self):
        score_text = 'Score: %s' % self.score
        if self.hud is None:
            self.hud = self.draw_text(100, 30, score_text, 18)
        else:
            self.canvas.itemconfig(self.hud, text=score_text)

    def add_score(self, points):
        self.score += points
        # Kecepatan naik setiap kelipatan 100 skor
        self.speed = min(BASE_SPEED + (self.score // 100) * SPEED_STEP,
                         MAX_SPEED)
        self.ball.speed = self.speed
        self.update_hud()

    def start_game(self):
        if self.started:
            return
        self.started = True
        self.canvas.unbind('<space>')
        self.canvas.unbind('<Button-1>')
        self.canvas.delete(self.text)
        self.paddle.ball = None
        self.game_loop()

    def game_loop(self):
        before = len(self.canvas.find_withtag('brick'))
        self.check_collisions()
        num_bricks = len(self.canvas.find_withtag('brick'))

        destroyed = before - num_bricks
        if destroyed > 0:
            self.add_score(destroyed * POINTS_PER_BRICK)

        if num_bricks == 0:
            # Semua brick habis -> spawn lagi, bola kembali ke paddle
            self.spawn_bricks()
            self.setup_game()
        elif self.ball.get_position()[3] >= self.height:
            # Bola jatuh ke bawah -> game over
            self.game_over()
        else:
            self.ball.update()
            self.after(16, self.game_loop)

    def game_over(self):
        cx, cy = self.width / 2, self.height / 2
        self.draw_text(cx, cy - 60, 'GAME OVER', 70)
        self.draw_text(cx, cy + 20, 'SKILL ISSUE', 50)
        self.draw_text(cx, cy + 80, 'Score: %s' % self.score, 24)
        # Setelah 3 detik, game mengulang dari awal
        self.after(3000, self.restart_game)

    def restart_game(self):
        """Reset semuanya dan kembali ke menu pilihan bentuk."""
        self.canvas.delete('all')
        self.canvas.unbind('<Motion>')
        self.canvas.unbind('<space>')
        self.canvas.unbind('<Button-1>')
        self.items = {}
        self.ball = None
        self.paddle = None
        self.hud = None
        self.score = 0
        self.speed = BASE_SPEED
        self.started = False
        self.show_menu()

    def check_collisions(self):
        ball_coords = self.ball.get_position()
        items = self.canvas.find_overlapping(*ball_coords)
        objects = [self.items[x] for x in items if x in self.items]
        self.ball.collide(objects)


if __name__ == '__main__':
    root = tk.Tk()
    root.title('Brick Breaker')
    root.attributes('-fullscreen', True)   # tekan Esc untuk keluar
    root.bind('<Escape>', lambda _: root.destroy())
    # Ukuran game mengikuti resolusi layar yang sebenarnya
    game = Game(root, root.winfo_screenwidth(), root.winfo_screenheight())
    start_music()
    game.mainloop()