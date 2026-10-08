import random
import pygame

OUTLINE = (28, 78, 40)
FILL = (62, 150, 70)
LIGHT = (118, 200, 105)
DARK = (40, 108, 52)
SPINE = (240, 235, 190)


class Obstacle:
    def __init__(self, x, ground_y, speed, width=25, height=40):
        self.x = x
        self.width = width
        self.height = height
        self.y = ground_y - height
        self.speed = speed
        self.scored = False
        self.variant = random.randint(0, 2)  # visual only: which arms the cactus has

    def move(self):
        self.x -= self.speed

    def off_screen(self):
        return self.x + self.width < 0

    def rect(self):
        # collision box - do not change
        return pygame.Rect(self.x, self.y, self.width, self.height)

    # ------------------------------------------------------------------
    # visuals only below this line
    # ------------------------------------------------------------------
    def draw_shadow(self, screen):
        ground_y = int(self.y + self.height)
        surf = pygame.Surface((34, 9), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (20, 40, 20, 85), surf.get_rect())
        screen.blit(surf, surf.get_rect(center=(int(self.x + self.width / 2), ground_y + 4)))

    def draw(self, screen):
        x, y = int(self.x), int(self.y)
        w, h = self.width, self.height

        trunk_w = max(8, int(w * 0.52))
        tx = x + (w - trunk_w) // 2
        arm_w = max(4, int(w * 0.24))

        # each shape: (rect, kwargs for draw.rect)
        shapes = []
        arms = []  # (vertical arm rect) for highlights

        if self.variant in (0, 1):  # left arm
            top = y + int(h * 0.28)
            conn = y + int(h * 0.50)
            vert = pygame.Rect(x, top, arm_w, conn + arm_w - top)
            horiz = pygame.Rect(x, conn, tx - x + 3, arm_w)
            shapes.append((vert, {"border_radius": arm_w // 2}))
            shapes.append((horiz, {"border_radius": 2}))
            arms.append(vert)
        if self.variant in (0, 2):  # right arm (a bit higher)
            rx = x + w - arm_w
            top = y + int(h * 0.18)
            conn = y + int(h * 0.38)
            vert = pygame.Rect(rx, top, arm_w, conn + arm_w - top)
            horiz = pygame.Rect(tx + trunk_w - 3, conn, rx + arm_w - (tx + trunk_w - 3), arm_w)
            shapes.append((vert, {"border_radius": arm_w // 2}))
            shapes.append((horiz, {"border_radius": 2}))
            arms.append(vert)

        r = trunk_w // 2
        trunk = pygame.Rect(tx, y, trunk_w, h)
        shapes.append((trunk, {"border_top_left_radius": r, "border_top_right_radius": r}))

        # outline pass, then fill pass
        for rect, kw in shapes:
            pygame.draw.rect(screen, OUTLINE, rect.inflate(2, 2), **kw)
        for rect, kw in shapes:
            pygame.draw.rect(screen, FILL, rect, **kw)

        # shading: light strip on the left, dark strip on the right, center ridge
        pygame.draw.rect(screen, LIGHT, (tx + 2, y + 5, 3, h - 7), border_radius=1)
        pygame.draw.rect(screen, DARK, (tx + trunk_w - 5, y + 5, 3, h - 7), border_radius=1)
        cx = tx + trunk_w // 2
        pygame.draw.line(screen, DARK, (cx, y + 6), (cx, y + h - 2), 1)
        for vert in arms:
            pygame.draw.line(screen, LIGHT, (vert.x + 2, vert.y + 4), (vert.x + 2, vert.bottom - 4), 1)

        # spines
        for py, side in ((y + 10, -1), (y + 17, 1), (y + 24, -1), (y + 31, 1)):
            sx = tx + 1 if side < 0 else tx + trunk_w - 2
            pygame.draw.line(screen, SPINE, (sx, py), (sx + side * 3, py - 1), 1)

        # flower on top for one variant
        if self.variant == 0:
            pygame.draw.circle(screen, (240, 110, 150), (cx, y + 1), 3)
            pygame.draw.circle(screen, (255, 220, 90), (cx, y + 1), 1)