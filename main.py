import pygame
import sys
import random

pygame.init()
pygame.mixer.init()  # must init mixer before loading any sounds

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
GOLD       = (255, 215, 0)

# ── Physics constants ─────────────────────────────────────────────────────────
GRAVITY       = 0.25  # acceleration added to vertical speed every frame
FLAP_FORCE    = -5   # upward burst when the player taps
PIPE_SPEED    = 2     # pixels the pipes move left per frame
PIPE_GAP      = 160   # vertical gap the bird must fly through
PIPE_INTERVAL = 1500  # milliseconds between each new pipe pair
GROUND_Y      = HEIGHT - 80  # y-coordinate where the ground starts

# Fonts for score and messages
font_big   = pygame.font.SysFont("Arial", 48, bold=True)
font_med   = pygame.font.SysFont("Arial", 30, bold=True)
font_small = pygame.font.SysFont("Arial", 22)


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

# TODO: bird image — swap filename to change the bird sprite
BIRD_IMG   = load("img/bird1.png",  size=(50, 38))

# TODO: background image — swap filename to change the sky/scenery
BG_IMG     = load("img/bg.png",     size=(WIDTH, HEIGHT))

# TODO: pipe/obstacle image — drawn top & bottom, scaled to fit
PIPE_IMG   = load("img/pipe.png",   size=(70, 400))

# TODO: ground/floor strip image — swap filename to change the floor
GROUND_IMG = load("img/ground.png", size=(WIDTH, 80))


# ── Sound loader ──────────────────────────────────────────────────────────────
# Returns None (instead of crashing) if the file isn't supported or missing
def load_snd(path):
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        return None

def play(snd):
    """Play a sound effect if it loaded successfully."""
    if snd:
        snd.play()

# TODO: flap sound — plays every time the player presses Space or clicks
SND_FLAP    = load_snd("sound/flapping.wav")

# TODO: lose sound — plays the moment the bird hits a pipe or the ground
SND_LOSE    = load_snd("sound/losing.wav")

# TODO: record sound — plays every time the score hits a new multiple of 10
SND_RECORD  = load_snd("sound/record.wav")

# TODO: welcome sound — plays once on the waiting screen before game starts
SND_WELCOME = load_snd("sound/welcome.wav")

# TODO: passing voices — alternate between these two on each pipe the player clears
#       1st pass → voicears,  2nd pass → voicebach,  3rd → voicears, …
SND_PASS = [
    load_snd("sound/voicears.wav"),
    load_snd("sound/voicebach.wav"),
]


# ── Best score (saved to disk so it survives game restarts) ───────────────────
SCORE_FILE = "best_score.txt"

def load_best():
    try:
        return int(open(SCORE_FILE).read().strip())
    except Exception:
        return 0

def save_best(score):
    try:
        open(SCORE_FILE, "w").write(str(score))
    except Exception:
        pass


# ── Bird ──────────────────────────────────────────────────────────────────────
class Bird:
    W, H = 50, 38

    def __init__(self):
        self.x  = 80           # fixed horizontal position
        self.y  = HEIGHT // 2  # starts in the middle of the screen
        self.vy = 0            # vertical velocity (positive = falling)

    def flap(self):
        self.vy = FLAP_FORCE   # snap velocity upward
        play(SND_FLAP)         # flap sound on every tap

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
        self.top_rect    = pygame.Rect(WIDTH, 0,               self.W, gap_y)
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
            surface.blit(top_scaled, self.top_rect.topleft)      # TODO: image drawn here — set PIPE_IMG above

            # bottom pipe: right-side up, scaled to the rect height
            bot_scaled = pygame.transform.scale(PIPE_IMG, (self.W, self.bottom_rect.h))
            surface.blit(bot_scaled, self.bottom_rect.topleft)   # TODO: same PIPE_IMG, bottom
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
        surface.blit(BG_IMG, (0, 0))           # TODO: image drawn here — set BG_IMG above
    else:
        surface.fill(SKY_BLUE)                 # fallback: solid sky colour


def draw_ground(surface):
    if GROUND_IMG:
        surface.blit(GROUND_IMG, (0, GROUND_Y))  # TODO: image drawn here — set GROUND_IMG above
    else:
        # fallback: two-tone green strip
        pygame.draw.rect(surface, GREEN,      (0, GROUND_Y, WIDTH, 80))
        pygame.draw.rect(surface, DARK_GREEN, (0, GROUND_Y, WIDTH, 8))


# ── Main game loop ────────────────────────────────────────────────────────────
def main():
    bird           = Bird()
    pipes          = []
    score          = 0
    best           = load_best()   # all-time best loaded from disk
    alive          = True
    started        = False         # waits for first tap before physics start
    last_pipe      = pygame.time.get_ticks()
    pass_snd_idx   = 0             # alternates 0/1 to switch between the two voices
    welcome_played = False

    while True:
        clock.tick(FPS)            # keep the loop running at exactly 60 fps
        now = pygame.time.get_ticks()

        # play welcome sound exactly once while on the waiting screen
        if not started and not welcome_played:
            play(SND_WELCOME)
            welcome_played = True

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
                    if SND_WELCOME:
                        SND_WELCOME.stop()   # cut welcome sound the moment game begins
                bird.flap()          # flap sound is played inside Bird.flap()

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
                if not p.passed and p.top_rect.centerx < bird.x:
                    p.passed     = True
                    score       += 1

                    # alternate between voicears and voicebach on each pass
                    play(SND_PASS[pass_snd_idx])
                    pass_snd_idx = 1 - pass_snd_idx   # flips 0→1→0→1…

                    # record fanfare every 10 points (10, 20, 30 …)
                    if score % 10 == 0:
                        play(SND_RECORD)

            # remove pipes that have scrolled off the left edge
            pipes = [p for p in pipes if not p.off_screen()]

            # ── Collision detection ────────────────────────────────────────────
            bird_r = bird.rect()
            if bird.y >= GROUND_Y or bird.y < 0:  # hit ground or flew off top
                alive = False
            for p in pipes:
                if bird_r.colliderect(p.top_rect) or bird_r.colliderect(p.bottom_rect):
                    alive = False

            # this block runs exactly once — the frame alive flips to False
            if not alive:
                play(SND_LOSE)         # losing sound on death
                if score > best:
                    best = score
                    save_best(best)    # write new best to disk immediately

        # ── Draw (every frame, even when paused or dead) ──────────────────────
        draw_background(screen)
        for p in pipes:
            p.draw(screen)
        draw_ground(screen)
        bird.draw(screen)

        # current score — top centre
        score_surf = font_big.render(str(score), True, WHITE)
        screen.blit(score_surf, (WIDTH // 2 - score_surf.get_width() // 2, 30))

        # best score shown just below the current score at all times
        best_surf = font_small.render(f"Best: {best}", True, WHITE)
        screen.blit(best_surf, (WIDTH // 2 - best_surf.get_width() // 2, 88))

        # "tap to start" prompt shown before the first flap
        if not started:
            msg = font_small.render("Press SPACE or click to start", True, WHITE)
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 + 60))

        # game-over overlay
        if not alive:
            # semi-transparent dark band so text is readable over any background
            overlay = pygame.Surface((WIDTH, 210), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, HEIGHT // 2 - 85))

            over  = font_big.render("Game Over",                  True, WHITE)
            sc    = font_med.render(f"Score: {score}",            True, WHITE)
            # highlight best in gold when the player just set a new record
            bst   = font_med.render(f"Best:  {best}",             True, GOLD if score == best else WHITE)
            retry = font_small.render("Press any key to restart", True, WHITE)

            screen.blit(over,  (WIDTH // 2 - over.get_width()  // 2, HEIGHT // 2 - 70))
            screen.blit(sc,    (WIDTH // 2 - sc.get_width()    // 2, HEIGHT // 2 - 20))
            screen.blit(bst,   (WIDTH // 2 - bst.get_width()   // 2, HEIGHT // 2 + 22))
            screen.blit(retry, (WIDTH // 2 - retry.get_width() // 2, HEIGHT // 2 + 65))

        pygame.display.flip()  # push the finished frame to the screen


if __name__ == "__main__":
    main()
