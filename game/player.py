import math
import pygame

SQUASH_FRAMES = 9  # how long the landing squash lasts

OUTLINE = (120, 52, 30)
BODY = (255, 140, 80)
BODY_DARK = (214, 100, 55)
BELLY = (255, 205, 160)
HIGHLIGHT = (255, 178, 125)
LEG = (110, 50, 30)


class Player:
    def __init__(self, x, ground_y, width=30, height=40):
        self.x = x
        self.ground_y = ground_y
        self.width = width
        self.height = height
        self.y = ground_y - height
        self.vy = 0
        self.gravity = 0.8
        self.jump_strength = -15
        self.on_ground = True

        # visual-only state
        self._was_air = False
        self._squash = 0

    def jump(self):
        """Returns True if the jump actually happened, False if mid-air."""
        if self.on_ground:
            self.vy = self.jump_strength
            self.on_ground = False
            return True
        return False

    def update(self):
        self.vy += self.gravity
        self.y += self.vy

        ground_level = self.ground_y - self.height
        if self.y >= ground_level:
            self.y = ground_level
            self.vy = 0
            self.on_ground = True

    def rect(self):
        # collision box - do not change
        return pygame.Rect(self.x, self.y, self.width, self.height)

    # ------------------------------------------------------------------
    # visuals only below this line
    # ------------------------------------------------------------------
    def draw_shadow(self, screen):
        ground_level = self.ground_y - self.height
        height_above = max(0.0, ground_level - self.y)
        k = max(0.35, 1.0 - height_above / 160)  # smaller + fainter when airborne
        w = int(36 * k)
        h = max(3, int(9 * k))
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (20, 40, 20, int(95 * k)), surf.get_rect())
        cx = int(self.x + self.width / 2)
        screen.blit(surf, surf.get_rect(center=(cx, int(self.ground_y) + 4)))

    def draw(self, screen, run_phase=0.0, dead=False):
        # detect the frame we land on, start the squash
        if self.on_ground and self._was_air:
            self._squash = SQUASH_FRAMES
        self._was_air = not self.on_ground

        w, h = self.width, self.height
        ox, oy = 8, 4  # padding so tail/crest can poke outside the box
        sw, sh = w + 16, h + 8
        surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        body_h = h - 6

        # legs: alternate while running, tucked while jumping
        if self.on_ground:
            s = math.sin(run_phase)
            lifts = (max(0.0, s) * 5, max(0.0, -s) * 5)
            dx = math.cos(run_phase) * 3
            shifts = (dx, -dx)
        else:
            lifts = (4, 2)
            shifts = (-3, 3)
        for frac, lift, shift in zip((0.2, 0.55), lifts, shifts):
            leg = pygame.Rect(0, 0, 8, 11)
            leg.topleft = (int(ox + w * frac + shift), int(oy + h - 11 - lift))
            pygame.draw.rect(surf, LEG, leg, border_radius=4)

        # tail (wags while running)
        wag = math.sin(run_phase) * 2 if self.on_ground else -2
        pygame.draw.circle(surf, BODY_DARK, (ox - 1, int(oy + body_h * 0.62 + wag)), 5)

        # little crest on top of the head
        crest = [(ox + 7, oy + 3), (ox + 9, oy - 3), (ox + 12, oy + 2),
                 (ox + 15, oy - 4), (ox + 18, oy + 3)]
        pygame.draw.polygon(surf, BODY_DARK, crest)

        # body
        body = pygame.Rect(ox, oy, w, body_h)
        pygame.draw.rect(surf, BODY, body, border_radius=14)
        pygame.draw.ellipse(surf, BELLY, (ox + int(w * 0.38), oy + int(body_h * 0.50),
                                          int(w * 0.52), int(body_h * 0.42)))
        pygame.draw.ellipse(surf, HIGHLIGHT, (ox + 4, oy + 3, 11, 8))
        pygame.draw.rect(surf, OUTLINE, body, width=2, border_radius=14)

        # face
        ex, ey = ox + int(w * 0.68), oy + int(body_h * 0.34)
        if dead:
            pygame.draw.line(surf, OUTLINE, (ex - 4, ey - 4), (ex + 4, ey + 4), 2)
            pygame.draw.line(surf, OUTLINE, (ex - 4, ey + 4), (ex + 4, ey - 4), 2)
        else:
            pygame.draw.circle(surf, (255, 255, 255), (ex, ey), 6)
            pygame.draw.circle(surf, OUTLINE, (ex, ey), 6, 1)
            pygame.draw.circle(surf, (30, 30, 45), (ex + 2, ey), 3)
            pygame.draw.circle(surf, (255, 255, 255), (ex + 3, ey - 1), 1)
        pygame.draw.circle(surf, (255, 150, 140), (ex - 5, ey + 8), 3)  # cheek

        # squash on landing, slight stretch in the air
        sx = sy = 1.0
        if self._squash > 0:
            t = self._squash / SQUASH_FRAMES
            sx = 1 + 0.28 * t
            sy = 1 - 0.28 * t
            self._squash -= 1
        elif not self.on_ground:
            stretch = min(abs(self.vy), 15) / 15
            sx = 1 - 0.10 * stretch
            sy = 1 + 0.14 * stretch

        out = surf
        if (sx, sy) != (1.0, 1.0):
            out = pygame.transform.smoothscale(surf, (max(1, int(sw * sx)), max(1, int(sh * sy))))

        # anchor at the feet so squash/stretch happens around the ground
        r = self.rect()
        osw, osh = out.get_size()
        bx = r.centerx - osw // 2
        by = r.bottom - int((oy + h) * (osh / sh))
        screen.blit(out, (bx, by))