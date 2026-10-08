import math
import random

import pygame
from .player import Player
from .obstacle import Obstacle
from .sounds import Sounds

# Game Engine

WHITE = (255, 255, 255)
BROWN = (120, 80, 40)
DARK_GREEN = (30, 100, 30)
BLACK = (0, 0, 0)

# Game states
MENU = "menu"
PLAYING = "playing"
GAME_OVER = "game_over"

# key -> (label, start speed, spawn interval in frames, max speed)
DIFFICULTIES = {
    pygame.K_1: ("Easy",   5, 100, 10),
    pygame.K_2: ("Medium", 6,  70, 14),
    pygame.K_3: ("Hard",   8,  50, 18),
}

# visual-only colors / settings
DIFF_COLORS = [(90, 200, 120), (245, 190, 70), (235, 90, 90)]
GRASS = (96, 170, 70)
GRASS_LIGHT = (130, 200, 90)
GRASS_DARK = (66, 130, 52)
DIRT = (150, 106, 66)
DIRT_DARK = (124, 84, 52)
DIRT_LIGHT = (176, 132, 88)
POP_FRAMES = 12  # how long the score "pop" lasts


def _lerp(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def _make_hills(width, height, base_y, a1, a2, k1, k2, p1, p2, color, rim):
    """Tileable hill silhouette (integer k's make it wrap seamlessly)."""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    xs = list(range(0, width, 4)) + [width]
    ridge = []
    for x in xs:
        t = 2 * math.pi * x / width
        y = base_y - a1 * math.sin(k1 * t + p1) - a2 * math.sin(k2 * t + p2)
        ridge.append((x, y))
    pygame.draw.polygon(surf, color, [(0, height)] + ridge + [(width, height)])
    pygame.draw.lines(surf, rim, False, ridge, 3)
    return surf


def _make_cloud(scale):
    base = pygame.Surface((120, 54), pygame.SRCALPHA)
    for dy, col in ((3, (205, 220, 240, 210)), (0, (255, 255, 255, 240))):
        for cx, cy, r in ((24, 32, 16), (48, 22, 22), (76, 26, 19), (98, 34, 13)):
            pygame.draw.circle(base, col, (cx, cy + dy), r)
        pygame.draw.rect(base, col, (24, 30 + dy, 74, 17), border_radius=8)
    return pygame.transform.smoothscale(base, (int(120 * scale), int(54 * scale)))


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.ground_y = height - 40

        self.player = Player(80, self.ground_y)
        self.sounds = Sounds()

        # Defaults (medium) so every attribute exists before the first run
        self.speed = 6
        self.max_speed = 14  # px/frame cap
        self.speed_increase_per_frame = 0.003

        self.spawn_interval = 70  # frames between obstacle spawns
        self._spawn_timer = 0
        self.obstacles = []

        self.distance = 0
        self.score = 0
        self.font = pygame.font.SysFont("Arial", 30)
        self.big_font = pygame.font.SysFont("Arial", 64, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 24)

        # visual-only fonts / state
        self.title_font = pygame.font.SysFont("Arial", 48, bold=True)
        self.score_big_font = pygame.font.SysFont("Arial", 56, bold=True)
        self.score_font = pygame.font.SysFont("Arial", 32, bold=True)
        self.option_font = pygame.font.SysFont("Arial", 26, bold=True)
        self.label_font = pygame.font.SysFont("Arial", 15, bold=True)
        self.key_font = pygame.font.SysFont("Arial", 17, bold=True)
        self._pop = 0
        self._last_score = 0
        self._menu_scroll = 0
        self._build_visuals()

        # Start on the difficulty menu
        self.state = MENU

    @property
    def game_over(self):
        return self.state == GAME_OVER

    def start_game(self, difficulty_key):
        """Full reset using the chosen difficulty's settings."""
        _, start_speed, spawn_interval, max_speed = DIFFICULTIES[difficulty_key]
        self.speed = start_speed
        self.spawn_interval = spawn_interval
        self.max_speed = max_speed

        self.player = Player(80, self.ground_y)
        self.obstacles = []
        self._spawn_timer = 0
        self.distance = 0
        self.score = 0
        self.state = PLAYING

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if self.state == PLAYING:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                # only play the sound if the jump actually happened
                if self.player.jump():
                    self.sounds.play_jump()

        elif self.state == GAME_OVER:
            if event.key in (pygame.K_r, pygame.K_RETURN):
                self.state = MENU
            elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                pygame.event.post(pygame.event.Event(pygame.QUIT))

        elif self.state == MENU:
            if event.key in DIFFICULTIES:
                self.start_game(event.key)
            elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    def handle_input(self):
        # Reserved for continuously-held-key input; this runner only
        # needs an edge-triggered jump, handled in handle_event.
        pass

    def update(self):
        if self.state != PLAYING:
            return

        # Ramp up speed, but never past max_speed
        self.speed = min(self.speed + self.speed_increase_per_frame, self.max_speed)
        self.player.update()

        self._spawn_timer += 1
        if self._spawn_timer >= self.spawn_interval:
            self._spawn_timer = 0
            self.obstacles.append(Obstacle(self.width, self.ground_y, self.speed))

        # Sync speed BEFORE moving so every obstacle moves at the current
        # speed this frame, and record the full area each one swept through
        # (old rect + new rect) so fast movers can't skip the hitbox.
        swept_rects = []
        for obstacle in self.obstacles:
            obstacle.speed = self.speed
            old_rect = obstacle.rect()
            obstacle.move()
            swept_rects.append(old_rect.union(obstacle.rect()))

        player_rect = self.player.rect()
        for swept in swept_rects:
            if swept.colliderect(player_rect):
                self.state = GAME_OVER
                self.sounds.play_death()  # update() returns early once state != PLAYING, so this fires once
                return

        for obstacle in self.obstacles:
            if not obstacle.scored and obstacle.x + obstacle.width < self.player.x:
                obstacle.scored = True  # guarantees one score sound per obstacle
                self.score += 1
                self.sounds.play_score()

        self.obstacles = [o for o in self.obstacles if not o.off_screen()]

        self.distance += self.speed

    # ------------------------------------------------------------------
    # visuals only below this line
    # ------------------------------------------------------------------
    def _build_visuals(self):
        """Pre-render everything static once so render() stays cheap."""
        w, h, gy = self.width, self.height, self.ground_y

        # sky gradient + sun
        self._sky = pygame.Surface((w, h))
        top, bottom = (84, 150, 228), (252, 238, 216)
        for y in range(h):
            pygame.draw.line(self._sky, _lerp(top, bottom, min(1.0, y / gy)), (0, y), (w, y))
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        sun = (int(w * 0.82), 75)
        for i, r in enumerate(range(88, 24, -8)):
            pygame.draw.circle(glow, (255, 244, 200, 14 + i * 9), sun, r)
        pygame.draw.circle(glow, (255, 246, 196, 255), sun, 24)
        self._sky.blit(glow, (0, 0))

        # parallax hills (far = slower, near = faster)
        self._hill_far = _make_hills(w, h, gy - 72, 26, 12, 2, 5, 0.5, 1.3,
                                     (158, 190, 214), (178, 206, 228))
        self._hill_near = _make_hills(w, h, gy - 34, 20, 9, 3, 7, 2.0, 0.4,
                                      (112, 168, 128), (134, 188, 148))

        # clouds: (x, y, surface index, parallax factor)
        self._cloud_surfs = [_make_cloud(0.8), _make_cloud(1.1), _make_cloud(1.4)]
        self._clouds = [
            (w * 0.08, 38, 0, 0.05),
            (w * 0.40, 72, 1, 0.035),
            (w * 0.68, 26, 2, 0.06),
            (w * 0.92, 92, 0, 0.04),
        ]

        # ground strip tile (same width as the screen so it wraps cleanly)
        top_pad = 6
        grass_h = 9
        th = top_pad + (h - gy)
        tile = pygame.Surface((w, th), pygame.SRCALPHA)
        rng = random.Random(7)  # local rng so we don't disturb the global one
        pygame.draw.rect(tile, GRASS, (0, top_pad, w, grass_h))
        pygame.draw.rect(tile, GRASS_DARK, (0, top_pad + grass_h - 3, w, 3))
        pygame.draw.rect(tile, GRASS_LIGHT, (0, top_pad, w, 2))
        dirt_top = top_pad + grass_h
        pygame.draw.rect(tile, DIRT, (0, dirt_top, w, th - dirt_top))
        pygame.draw.rect(tile, DIRT_DARK, (0, dirt_top, w, 2))
        for _ in range(30):  # dashes
            x = rng.randint(6, w - 22)
            y = rng.randint(dirt_top + 5, th - 4)
            pygame.draw.line(tile, DIRT_DARK, (x, y), (x + rng.randint(6, 14), y), 2)
        for _ in range(30):  # pebbles
            x = rng.randint(8, w - 8)
            y = rng.randint(dirt_top + 5, th - 5)
            rx, ry = rng.randint(2, 4), rng.randint(1, 3)
            col = DIRT_LIGHT if rng.random() < 0.5 else DIRT_DARK
            pygame.draw.ellipse(tile, col, (x - rx, y - ry, rx * 2, ry * 2))
        for _ in range(45):  # grass tufts poking above the strip
            x = rng.randint(8, w - 8)
            ht = rng.randint(4, 6)
            for dx in (-2, 0, 2):
                col = GRASS if dx else GRASS_LIGHT
                pygame.draw.line(tile, col, (x, top_pad + 1), (x + dx, top_pad - ht + abs(dx)), 2)
        self._ground_tile = tile
        self._ground_tile_y = gy - top_pad

    def _draw_background(self, screen, scroll):
        screen.blit(self._sky, (0, 0))

        for x0, y, idx, f in self._clouds:
            cs = self._cloud_surfs[idx]
            cw = cs.get_width()
            x = (x0 - scroll * f) % (self.width + cw) - cw
            screen.blit(cs, (x, y))

        for layer, factor in ((self._hill_far, 0.12), (self._hill_near, 0.30)):
            off = int(scroll * factor) % self.width
            screen.blit(layer, (-off, 0))
            screen.blit(layer, (self.width - off, 0))

    def _draw_ground(self, screen, scroll):
        off = int(scroll) % self.width
        screen.blit(self._ground_tile, (-off, self._ground_tile_y))
        screen.blit(self._ground_tile, (self.width - off, self._ground_tile_y))

    def _panel(self, screen, rect, fill, border=None, radius=14):
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, fill, surf.get_rect(), border_radius=radius)
        if border:
            pygame.draw.rect(surf, border, surf.get_rect(), width=2, border_radius=radius)
        screen.blit(surf, rect.topleft)

    def _draw_card(self, screen, rect):
        self._panel(screen, rect.move(0, 6), (0, 0, 0, 90), None, 22)  # drop shadow
        self._panel(screen, rect, (24, 32, 56, 242), (255, 255, 255, 55), 22)

    def _keycap_width(self, label):
        return max(28, self.key_font.size(label)[0] + 16)

    def _draw_keycap(self, screen, label, x, cy):
        w, h = self._keycap_width(label), 28
        base = pygame.Rect(x, cy - h // 2 + 1, w, h)
        top = pygame.Rect(x, cy - h // 2 - 2, w, h)
        pygame.draw.rect(screen, (120, 130, 155), base, border_radius=7)
        pygame.draw.rect(screen, (238, 242, 250), top, border_radius=7)
        txt = self.key_font.render(label, True, (40, 48, 70))
        screen.blit(txt, txt.get_rect(center=top.center))
        return w

    def _draw_hint_row(self, screen, keys, label, cy, color=(200, 210, 230)):
        sep_w, gap = 16, 14
        label_surf = self.small_font.render(label, True, color)
        total = (sum(self._keycap_width(k) for k in keys) + sep_w * (len(keys) - 1)
                 + gap + label_surf.get_width())
        x = (self.width - total) // 2
        for i, k in enumerate(keys):
            if i:
                slash = self.small_font.render("/", True, color)
                screen.blit(slash, slash.get_rect(center=(x + sep_w // 2, cy)))
                x += sep_w
            x += self._draw_keycap(screen, k, x, cy)
        screen.blit(label_surf, label_surf.get_rect(midleft=(x + gap, cy)))

    def _draw_centered(self, screen, font, text, y, color=WHITE):
        surf = font.render(text, True, color)
        screen.blit(surf, surf.get_rect(center=(self.width // 2, y)))

    def _draw_overlay(self, screen):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((10, 16, 34, 120))
        screen.blit(overlay, (0, 0))

    def _draw_score_panel(self, screen):
        panel = pygame.Rect(12, 12, 150, 58)
        self._panel(screen, panel, (18, 28, 48, 180), (255, 255, 255, 60), 14)
        label = self.label_font.render("SCORE", True, (150, 175, 215))
        screen.blit(label, (panel.x + 16, panel.y + 8))

        t = self._pop / POP_FRAMES
        color = _lerp(WHITE, (255, 214, 80), t)
        num = self.score_font.render(str(self.score), True, color)
        if self._pop > 0:
            k = 1 + 0.5 * t
            num = pygame.transform.smoothscale(
                num, (int(num.get_width() * k), int(num.get_height() * k)))
            self._pop -= 1
        screen.blit(num, num.get_rect(midleft=(panel.x + 16, panel.y + 38)))

    def _draw_menu(self, screen):
        self._draw_overlay(screen)
        card = pygame.Rect(0, 0, 480, 340)
        card.center = (self.width // 2, self.height // 2)
        self._draw_card(screen, card)

        self._draw_centered(screen, self.title_font, "ENDLESS RUNNER", card.y + 46, (255, 214, 90))
        self._draw_centered(screen, self.small_font, "Choose difficulty", card.y + 82, (170, 185, 215))

        for i, key in enumerate(DIFFICULTIES):
            name = DIFFICULTIES[key][0]
            row = pygame.Rect(card.x + 40, card.y + 108 + i * 54, card.w - 80, 44)
            pygame.draw.rect(screen, (44, 54, 82), row, border_radius=12)
            pygame.draw.rect(screen, (70, 84, 118), row, width=1, border_radius=12)
            self._draw_keycap(screen, str(i + 1), row.x + 12, row.centery)
            label = self.option_font.render(name, True, WHITE)
            screen.blit(label, label.get_rect(midleft=(row.x + 12 + 28 + 16, row.centery)))
            for j in range(3):  # difficulty pips
                col = DIFF_COLORS[i] if j <= i else (80, 90, 115)
                pygame.draw.circle(screen, col, (row.right - 24 - (2 - j) * 16, row.centery), 5)

        self._draw_hint_row(screen, ["Esc", "Q"], "Quit", card.bottom - 36)

    def _draw_game_over(self, screen):
        self._draw_overlay(screen)
        card = pygame.Rect(0, 0, 440, 262)
        card.center = (self.width // 2, self.height // 2)
        self._draw_card(screen, card)

        self._draw_centered(screen, self.title_font, "GAME OVER", card.y + 52, (240, 100, 100))
        pygame.draw.line(screen, (70, 82, 112), (card.x + 40, card.y + 90),
                         (card.right - 40, card.y + 90), 2)
        self._draw_centered(screen, self.label_font, "FINAL SCORE", card.y + 112, (150, 170, 205))
        self._draw_centered(screen, self.score_big_font, str(self.score), card.y + 148)
        self._draw_hint_row(screen, ["R", "Enter"], "Choose difficulty", card.y + 205)
        self._draw_hint_row(screen, ["Esc", "Q"], "Quit", card.y + 238)

    def render(self, screen):
        if self.state == MENU:
            self._menu_scroll += 2  # gentle idle scroll behind the menu
            scroll = self._menu_scroll
        else:
            scroll = self.distance  # world scroll is tied to real game distance

        self._draw_background(screen, scroll)
        self._draw_ground(screen, scroll)

        self.player.draw_shadow(screen)
        for obstacle in self.obstacles:
            obstacle.draw_shadow(screen)
        for obstacle in self.obstacles:
            obstacle.draw(screen)
        self.player.draw(screen, scroll * 0.06, dead=(self.state == GAME_OVER))

        if self.score > self._last_score:
            self._pop = POP_FRAMES
        self._last_score = self.score

        if self.state != MENU:
            self._draw_score_panel(screen)

        if self.state == GAME_OVER:
            self._draw_game_over(screen)
        elif self.state == MENU:
            self._draw_menu(screen)