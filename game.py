"""
Slice Ninja - Gesture-Controlled Shape Slicing Game
-----------------------------------------------------
Uses your webcam + MediaPipe hand tracking to let you slice falling
shapes with your index finger, ninja-style. Avoid the bombs.

Controls:
    S - start / restart game
    Q / ESC - quit

Requirements (see requirements.txt):
    pip install opencv-python mediapipe pygame numpy
"""

import math
import random
import time

import cv2
import mediapipe as mp
import numpy as np
import pygame

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
CAM_WIDTH, CAM_HEIGHT = 960, 720
GAME_DURATION = 60          # seconds
STARTING_LIVES = 3
SPAWN_INTERVAL_MS = 900     # base ms between spawns
TRAIL_LENGTH = 8
BOMB_CHANCE = 0.16

SHAPE_TYPES = ["circle", "square", "triangle", "star", "pentagon", "hexagon"]
PALETTE = [
    (76, 201, 240),   # cyan
    (247, 37, 133),   # magenta
    (255, 183, 3),    # amber
    (142, 224, 0),    # lime
    (179, 136, 255),  # violet
    (255, 122, 89),   # coral
]

# --------------------------------------------------------------------------
# MediaPipe setup
# --------------------------------------------------------------------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    model_complexity=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.55,
)

# --------------------------------------------------------------------------
# Shape / Particle classes
# --------------------------------------------------------------------------
class Shape:
    def __init__(self, x, w, h):
        self.is_bomb = random.random() < BOMB_CHANCE
        self.r = 26 if self.is_bomb else random.randint(30, 44)
        self.x = x
        self.y = h + self.r
        self.vy = -(h * 0.015 + random.random() * h * 0.006)
        self.vx = (random.random() - 0.5) * h * 0.006
        self.g = h * 0.0000145 + h * 0.0000015 * random.random()
        self.type = "bomb" if self.is_bomb else random.choice(SHAPE_TYPES)
        self.color = random.choice(PALETTE)
        self.rot = random.random() * math.tau
        self.rot_speed = (random.random() - 0.5) * 0.06
        self.sliced = False
        self.slice_t = 0
        self.dead = False

    def update(self, dt, h):
        if not self.sliced:
            self.vy += self.g * dt
            self.x += self.vx * dt * 0.06
            self.y += self.vy * dt * 0.06
            self.rot += self.rot_speed
            if self.y > h + 100:
                self.dead = True
        else:
            self.slice_t += dt
            if self.slice_t > 220:
                self.dead = True

    def polygon_points(self):
        r = self.r
        pts = []
        if self.type == "circle":
            return None  # drawn separately
        elif self.type == "square":
            corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
            pts = [(cx * r * 0.82, cy * r * 0.82) for cx, cy in corners]
        elif self.type == "triangle":
            for i in range(3):
                a = -math.pi / 2 + i * (2 * math.pi / 3)
                pts.append((math.cos(a) * r, math.sin(a) * r))
        elif self.type in ("pentagon", "hexagon"):
            n = 5 if self.type == "pentagon" else 6
            for i in range(n):
                a = -math.pi / 2 + i * (2 * math.pi / n)
                pts.append((math.cos(a) * r, math.sin(a) * r))
        elif self.type == "star":
            spikes, outer, inner = 5, r, r * 0.46
            for i in range(spikes * 2):
                a = -math.pi / 2 + i * math.pi / spikes
                rad = outer if i % 2 == 0 else inner
                pts.append((math.cos(a) * rad, math.sin(a) * rad))
        # rotate + translate
        cos_r, sin_r = math.cos(self.rot), math.sin(self.rot)
        return [
            (self.x + px * cos_r - py * sin_r, self.y + px * sin_r + py * cos_r)
            for px, py in pts
        ]


class Particle:
    def __init__(self, x, y, color):
        angle = random.random() * math.tau
        speed = 1.5 + random.random() * 4
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
        self.life = 1.0
        self.color = color

    def update(self, dt):
        self.x += self.vx * dt * 0.06
        self.y += self.vy * dt * 0.06
        self.vy += 0.02 * dt * 0.06
        self.life -= dt * 0.0018

    def dead(self):
        return self.life <= 0


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def seg_circle_hit(x1, y1, x2, y2, cx, cy, r):
    dx, dy = x2 - x1, y2 - y1
    len2 = dx * dx + dy * dy
    t = 0 if len2 == 0 else ((cx - x1) * dx + (cy - y1) * dy) / len2
    t = max(0, min(1, t))
    px, py = x1 + t * dx, y1 + t * dy
    ddx, ddy = cx - px, cy - py
    return (ddx * ddx + ddy * ddy) <= r * r


def draw_shape(surf, shape):
    color = (30, 31, 38) if shape.type == "bomb" else shape.color
    alpha = 255
    if shape.sliced:
        alpha = max(0, int(255 * (1 - shape.slice_t / 220)))
    tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)

    if shape.type == "circle":
        pygame.draw.circle(tmp, (*color, alpha), (int(shape.x), int(shape.y)), shape.r)
        pygame.draw.circle(tmp, (255, 255, 255, min(alpha, 160)), (int(shape.x), int(shape.y)), shape.r, 2)
    elif shape.type == "bomb":
        pygame.draw.circle(tmp, (*color, alpha), (int(shape.x), int(shape.y)), int(shape.r * 0.8))
        pygame.draw.circle(tmp, (255, 90, 90, alpha), (int(shape.x), int(shape.y)), int(shape.r * 0.8), 3)
        for i in range(8):
            a = i * math.pi / 4 + shape.rot
            x1 = shape.x + math.cos(a) * shape.r * 0.8
            y1 = shape.y + math.sin(a) * shape.r * 0.8
            x2 = shape.x + math.cos(a) * shape.r * 1.15
            y2 = shape.y + math.sin(a) * shape.r * 1.15
            pygame.draw.line(tmp, (255, 90, 90, alpha), (x1, y1), (x2, y2), 2)
        pygame.draw.circle(tmp, (255, 223, 107, alpha), (int(shape.x), int(shape.y)), 4)
    else:
        pts = shape.polygon_points()
        if pts:
            pygame.draw.polygon(tmp, (*color, alpha), pts)
            pygame.draw.polygon(tmp, (255, 255, 255, min(alpha, 160)), pts, 2)

    surf.blit(tmp, (0, 0))


def draw_trail(surf, trail):
    if len(trail) < 2:
        return
    tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for i in range(1, len(trail)):
        p0, p1 = trail[i - 1], trail[i]
        a = i / len(trail)
        width = int(3 + a * 7)
        pygame.draw.line(tmp, (76, 201, 240, int(a * 230)), p0, p1, width)
    pygame.draw.circle(tmp, (234, 252, 255, 255), trail[-1], 6)
    surf.blit(tmp, (0, 0))


def cv2_frame_to_surface(frame):
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_rgb = cv2.flip(frame_rgb, 1)  # mirror for natural interaction
    h, w = frame_rgb.shape[:2]
    surf = pygame.image.frombuffer(frame_rgb.tobytes(), (w, h), "RGB")
    return surf


# --------------------------------------------------------------------------
# Main game
# --------------------------------------------------------------------------
def main():
    pygame.init()
    pygame.display.set_caption("Slice Ninja")
    screen = pygame.display.set_mode((CAM_WIDTH, CAM_HEIGHT))
    clock = pygame.time.Clock()

    font_big = pygame.font.SysFont("segoeui", 48, bold=True)
    font_med = pygame.font.SysFont("segoeui", 28, bold=True)
    font_small = pygame.font.SysFont("segoeui", 18)

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

    if not cap.isOpened():
        print("Could not open webcam. Check it's connected and not used by another app.")
        return

    running_game = False
    score = 0
    lives = STARTING_LIVES
    time_left = GAME_DURATION
    combo = 0
    combo_timer = 0
    shapes = []
    particles = []
    trail = []
    spawn_timer = 0
    last_time = time.time()

    def reset_game():
        nonlocal score, lives, time_left, combo, combo_timer, shapes, particles, trail, spawn_timer
        score, lives, time_left = 0, STARTING_LIVES, GAME_DURATION
        combo, combo_timer = 0, 0
        shapes, particles, trail = [], [], []
        spawn_timer = 0

    def slice_check():
        nonlocal score, lives, combo, combo_timer
        if len(trail) < 2:
            return
        x1, y1 = trail[-2]
        x2, y2 = trail[-1]
        for s in shapes:
            if s.sliced or s.dead:
                continue
            if seg_circle_hit(x1, y1, x2, y2, s.x, s.y, s.r):
                s.sliced, s.slice_t = True, 0
                if s.type == "bomb":
                    lives -= 1
                    combo, combo_timer = 0, 0
                    for _ in range(18):
                        particles.append(Particle(s.x, s.y, (255, 90, 90)))
                else:
                    combo += 1
                    combo_timer = 1400
                    score += 10 * max(1, min(combo, 6))
                    for _ in range(16):
                        particles.append(Particle(s.x, s.y, s.color))

    quit_app = False
    while not quit_app:
        now = time.time()
        dt = (now - last_time) * 1000  # ms
        dt = min(dt, 40)
        last_time = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_app = True
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    quit_app = True
                elif event.key == pygame.K_s:
                    reset_game()
                    running_game = True

        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.resize(frame, (CAM_WIDTH, CAM_HEIGHT))

        # hand tracking
        rgb_for_mp = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_for_mp)
        hand_visible = False
        if results.multi_hand_landmarks:
            hand_visible = True
            lm = results.multi_hand_landmarks[0].landmark[8]  # index fingertip
            nx, ny = lm.x * CAM_WIDTH, lm.y * CAM_HEIGHT
            trail.append((nx, ny))
            if len(trail) > TRAIL_LENGTH:
                trail.pop(0)
            if running_game:
                slice_check()
        else:
            trail = []

        # draw camera feed (already mirrored via flip above, mirror again for display consistency)
        cam_surf = cv2_frame_to_surface(frame)
        cam_surf = pygame.transform.smoothscale(cam_surf, (CAM_WIDTH, CAM_HEIGHT))
        dark = pygame.Surface((CAM_WIDTH, CAM_HEIGHT), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 90))
        screen.blit(cam_surf, (0, 0))
        screen.blit(dark, (0, 0))

        if running_game:
            time_left -= dt / 1000
            if combo_timer > 0:
                combo_timer -= dt
                if combo_timer <= 0:
                    combo = 0

            spawn_timer += dt
            difficulty = max(0.55, 1 - (GAME_DURATION - time_left) / 140)
            if spawn_timer > SPAWN_INTERVAL_MS * difficulty:
                spawn_timer = 0
                x = random.randint(60, CAM_WIDTH - 60)
                shapes.append(Shape(x, CAM_WIDTH, CAM_HEIGHT))
                if random.random() < 0.35:
                    shapes.append(Shape(random.randint(60, CAM_WIDTH - 60), CAM_WIDTH, CAM_HEIGHT))

            for s in shapes:
                s.update(dt, CAM_HEIGHT)
            shapes = [s for s in shapes if not s.dead]

            for p in particles:
                p.update(dt)
            particles = [p for p in particles if not p.dead()]

            if time_left <= 0 or lives <= 0:
                running_game = False

        for s in shapes:
            draw_shape(screen, s)
        for p in particles:
            col = (*p.color, max(0, int(p.life * 255)))
            tmp = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(tmp, col, (int(p.x), int(p.y)), 3)
            screen.blit(tmp, (0, 0))
        if running_game:
            draw_trail(screen, trail)

        # ---------------- HUD ----------------
        hud = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(hud, (255, 255, 255, 25), (14, 14, 130, 60), border_radius=14)
        hud.blit(font_small.render("SCORE", True, (170, 190, 220)), (26, 20))
        hud.blit(font_med.render(str(score), True, (76, 201, 240)), (26, 38))

        pygame.draw.rect(hud, (255, 255, 255, 25), (CAM_WIDTH - 110, 14, 96, 60), border_radius=14)
        hud.blit(font_small.render("TIME", True, (170, 190, 220)), (CAM_WIDTH - 98, 20))
        t_color = (247, 37, 133) if time_left <= 10 else (255, 255, 255)
        hud.blit(font_med.render(str(max(0, int(time_left))), True, t_color), (CAM_WIDTH - 98, 38))

        for i in range(STARTING_LIVES):
            col = (247, 37, 133) if i < lives else (90, 90, 100)
            pygame.draw.circle(hud, col, (CAM_WIDTH // 2 - 30 + i * 30, 44), 9)

        if combo > 1 and combo_timer > 0:
            combo_surf = font_med.render(f"COMBO x{combo}", True, (255, 183, 3))
            hud.blit(combo_surf, (26, 84))

        status = "tracking your hand" if hand_visible else "show your hand to the camera"
        status_col = (142, 224, 0) if hand_visible else (170, 190, 220)
        status_surf = font_small.render(status, True, status_col)
        hud.blit(status_surf, (CAM_WIDTH // 2 - status_surf.get_width() // 2, CAM_HEIGHT - 30))

        screen.blit(hud, (0, 0))

        if not running_game:
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((5, 8, 16, 190))
            screen.blit(overlay, (0, 0))
            if score == 0 and time_left == GAME_DURATION:
                title = font_big.render("SLICE NINJA", True, (76, 201, 240))
                sub = font_small.render("Show your hand, slice shapes, dodge bombs.", True, (170, 190, 220))
                prompt = font_med.render("Press S to start", True, (255, 255, 255))
            else:
                title = font_big.render("GAME OVER", True, (255, 183, 3))
                sub = font_small.render(f"Final score: {score}", True, (255, 255, 255))
                prompt = font_med.render("Press S to play again", True, (255, 255, 255))
            screen.blit(title, (CAM_WIDTH // 2 - title.get_width() // 2, CAM_HEIGHT // 2 - 90))
            screen.blit(sub, (CAM_WIDTH // 2 - sub.get_width() // 2, CAM_HEIGHT // 2 - 30))
            screen.blit(prompt, (CAM_WIDTH // 2 - prompt.get_width() // 2, CAM_HEIGHT // 2 + 20))

        pygame.display.flip()
        clock.tick(30)

    cap.release()
    pygame.quit()


if __name__ == "__main__":
    main()