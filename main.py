import pygame
import sys
import random

pygame.init()

# Window size and basic setup
WIDTH, HEIGHT = 400, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird")
clock = pygame.time.Clock()
FPS = 60

# Fallback colours — used when no image is provided
SKY_BLUE   = (113, 197, 207)
GREEN      = (83,  254, 76)
DARK_GREEN = (52,  157, 47)
YELLOW     = (255, 222, 89)
WHITE      = (255, 255, 255)

# ── Physics constants ─────────────────────────────────────────────────────────
GRAVITY       = 0.5   # acceleration added to vertical speed every frame
FLAP_FORCE    = -9    # upward burst when the player taps
PIPE_SPEED    = 3     # pixels the pipes move left per frame
PIPE_GAP      = 160   # vertical gap the bird must fly through
PIPE_INTERVAL = 1500  # milliseconds between each new pipe pair
GROUND_Y      = HEIGHT - 80  # y-coordinate where the ground starts

# Fonts for score and messages
font_big   = pygame.font.SysFont("Arial", 48, bold=True)
font_small = pygame.font.SysFont("Arial", 24)


# ── Image loader ──────────────────────────────────────────────────────────────
# Returns None (instead of crashing) if the file isn't found yet
def load(path, size=None):
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# TODO: replace each filename string below with your own image file
# Drop the image files in the same folder as this script, then update the name.
# Until you do, the game draws plain coloured shapes instead.
# ─────────────────────────────────────────────────────────────────────────────

# TODO: bird image — 50×38 px works well (e.g. "bird.png")
BIRD_IMG   = load("bird.png",       size=(50, 38))

# TODO: background image — should be 400×600 px (e.g. "background.png")
BG_IMG     = load("background.png", size=(WIDTH, HEIGHT))

# TODO: pipe/obstacle image — drawn top & bottom, scaled to fit (e.g. "pipe.png")
PIPE_IMG   = load("pipe.png",       size=(70, 400))

# TODO: ground/floor strip image — should be 400×80 px (e.g. "ground.png")
GROUND_IMG = load("ground.png",     size=(WIDTH, 80))

# ─────────────────────────────────────────────────────────────────────────────


# ── Bird ──────────────────────────────────────────────────────────────────────
class Bird:
    W, H = 50, 38

    def __init__(self):
        self.x  = 80           # fixed horizontal position
        self.y  = HEIGHT // 2  # starts in the middle of the screen
        self.vy = 0            # vertical velocity (positive = falling)

    def flap(self):
        # reset vertical speed to a negative (upward) value
        self.vy = FLAP_FORCE

    def update(self):
        # gravity pulls the bird down every frame
        self.vy += GRAVITY
        self.y  += self.vy

    def draw(self, surface):
        if BIRD_IMG:
            # tilt the sprite to match the direction of travel
            angle   = max(-30, min(self.vy * -3, 90))
            rotated = pygame.transform.rotate(BIRD_IMG, angle)
            rect    = rotated.get_rect(center=(self.x, self.y))
            surface.blit(rotated, rect)  # TODO: image drawn here — set BIRD_IMG above
        else:
            # fallback: yellow oval
            pygame.draw.ellipse(surface, YELLOW, self.rect())

    def rect(self):
        # collision rectangle centred on the bird's position
        return pygame.Rect(self.x - self.W // 2, self.y - self.H // 2, self.W, self.H)


# ── Pipe pair (top + bottom obstacle) ────────────────────────────────────────
class Pipe:
    W = 70

    def __init__(self):
        # pick a random vertical position for the gap
        gap_y            = random.randint(120, GROUND_Y - PIPE_GAP - 60)
        self.top_rect    = pygame.Rect(WIDTH, 0,              self.W, gap_y)
        self.bottom_rect = pygame.Rect(WIDTH, gap_y + PIPE_GAP, self.W, HEIGHT)
        self.passed      = False  # flips to True once the bird clears this pipe

    def update(self):
        # slide both rects left at a constant speed
        self.top_rect.x    -= PIPE_SPEED
        self.bottom_rect.x -= PIPE_SPEED

    def draw(self, surface):
        if PIPE_IMG:
            # top pipe: flip the image upside-down then scale to the rect height
            flipped    = pygame.transform.flip(PIPE_IMG, False, True)
            top_scaled = pygame.transform.scale(flipped, (self.W, self.top_rect.h))
            surface.blit(top_scaled, self.top_rect.topleft)  # TODO: image drawn here — set PIPE_IMG above

            # bottom pipe: right-side up, scaled to the rect height
            bot_scaled = pygame.transform.scale(PIPE_IMG, (self.W, self.bottom_rect.h))
            surface.blit(bot_scaled, self.bottom_rect.topleft)  # TODO: same PIPE_IMG, bottom
        else:
            # fallback: green rectangles
            pygame.draw.rect(surface, GREEN,      self.top_rect)
            pygame.draw.rect(surface, DARK_GREEN, self.top_rect.inflate(-6, 0))
            pygame.draw.rect(surface, GREEN,      self.bottom_rect)
            pygame.draw.rect(surface, DARK_GREEN, self.bottom_rect.inflate(-6, 0))

    def off_screen(self):
        # True once the pipe has scrolled fully off the left edge
        return self.top_rect.right < 0


# ── Background & ground drawing ───────────────────────────────────────────────
def draw_background(surface):
    if BG_IMG:
        surface.blit(BG_IMG, (0, 0))  # TODO: image drawn here — set BG_IMG above
    else:
        surface.fill(SKY_BLUE)  # fallback: solid sky colour


def draw_ground(surface):
    if GROUND_IMG:
        surface.blit(GROUND_IMG, (0, GROUND_Y))  # TODO: image drawn here — set GROUND_IMG above
    else:
        # fallback: two-tone green strip
        pygame.draw.rect(surface, GREEN,      (0, GROUND_Y, WIDTH, 80))
        pygame.draw.rect(surface, DARK_GREEN, (0, GROUND_Y, WIDTH, 8))


# ── Main game loop ────────────────────────────────────────────────────────────
def main():
    bird      = Bird()
    pipes     = []
    score     = 0
    alive     = True
    started   = False           # waits for first tap before physics start
    last_pipe = pygame.time.get_ticks()

    while True:
        clock.tick(FPS)         # keep the loop running at exactly 60 fps
        now = pygame.time.get_ticks()

        # ── Input ─────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if not alive:
                    main(); return   # any key after death restarts the game
                if not started:
                    started = True   # first tap kicks off physics
                bird.flap()

        # ── Update (only while the bird is alive and the game has started) ────
        if started and alive:
            bird.update()

            # spawn a new pipe pair every PIPE_INTERVAL milliseconds
            if now - last_pipe > PIPE_INTERVAL:
                pipes.append(Pipe())
                last_pipe = now

            for p in pipes:
                p.update()
                # award a point when the bird passes the right edge of a pipe
                if not p.passed and p.top_rect.right < bird.x:
                    p.passed = True
                    score += 1

            # remove pipes that have scrolled off the left edge
            pipes = [p for p in pipes if not p.off_screen()]

            # ── Collision detection ────────────────────────────────────────────
            bird_r = bird.rect()
            if bird.y >= GROUND_Y or bird.y < 0:  # hit ground or flew off top
                alive = False
            for p in pipes:
                if bird_r.colliderect(p.top_rect) or bird_r.colliderect(p.bottom_rect):
                    alive = False

        # ── Draw (every frame, even when paused or dead) ──────────────────────
        draw_background(screen)
        for p in pipes:
            p.draw(screen)
        draw_ground(screen)
        bird.draw(screen)

        # score counter at the top centre of the screen
        score_surf = font_big.render(str(score), True, WHITE)
        screen.blit(score_surf, (WIDTH // 2 - score_surf.get_width() // 2, 40))

        # "tap to start" prompt shown before the first flap
        if not started:
            msg = font_small.render("Press SPACE or click to start", True, WHITE)
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 + 60))

        # game-over overlay
        if not alive:
            over  = font_big.render("Game Over",              True, WHITE)
            retry = font_small.render("Press any key to restart", True, WHITE)
            screen.blit(over,  (WIDTH // 2 - over.get_width()  // 2, HEIGHT // 2 - 30))
            screen.blit(retry, (WIDTH // 2 - retry.get_width() // 2, HEIGHT // 2 + 30))

        pygame.display.flip()  # push the finished frame to the screen


if __name__ == "__main__":
    main()
