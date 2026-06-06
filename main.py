import pygame
import sys
import random

# Voice dependencies — mode is disabled gracefully if not installed
try:
    import numpy as np
    import sounddevice as sd
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

pygame.mixer.pre_init(44100, -16, 2, 256)  # low-latency audio (~6 ms)
pygame.init()

WIDTH, HEIGHT = 400, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird")
clock = pygame.time.Clock()
FPS = 60

# Colours
SKY_BLUE   = (113, 197, 207)
GREEN      = (83,  254, 76)
DARK_GREEN = (52,  157, 47)
YELLOW     = (255, 222, 89)
WHITE      = (255, 255, 255)
GOLD       = (255, 215,   0)
GREY       = (130, 130, 130)
BLUE       = ( 50, 150, 255)
LIME       = ( 60, 190,  80)
BLACK      = (  0,   0,   0)

# Physics
GRAVITY       = 0.25
FLAP_FORCE    = -5
PIPE_SPEED    = 2
PIPE_GAP      = 160
PIPE_INTERVAL = 1500
GROUND_Y      = HEIGHT - 80

# Voice-mode constants
VOICE_THRESHOLD = 7.5    # RMS level below which mic is treated as silence (halved — no shouting needed)
VOICE_SCALE     = 0.56   # loudness → upward velocity added each frame (doubled to match lower input)
VOICE_MAX_VY    = -9     # maximum upward velocity in voice mode

font_big   = pygame.font.SysFont("Arial", 48, bold=True)
font_med   = pygame.font.SysFont("Arial", 30, bold=True)
font_small = pygame.font.SysFont("Arial", 22)
font_tiny  = pygame.font.SysFont("Arial", 15)


# ── Image loader ──────────────────────────────────────────────────────────────
def load(path, size=None):
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    except Exception:
        return None

# TODO: swap filenames below to change art
BIRD_IMG   = load("img/bird1.png",  size=(50, 38))
BG_IMG     = load("img/bg.png",     size=(WIDTH, HEIGHT))
PIPE_IMG   = load("img/pipe.png",   size=(70, 400))
GROUND_IMG = load("img/ground.png", size=(WIDTH, 80))


# ── Sound loader ──────────────────────────────────────────────────────────────
def load_snd(path):
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        return None

def play(snd):
    if snd:
        snd.play()

# TODO: swap filenames below to change sounds
SND_FLAP    = load_snd("sound/flapping.wav")   # plays on flap / voice trigger
SND_LOSE    = load_snd("sound/losing.wav")     # plays on death
SND_RECORD  = load_snd("sound/record.wav")     # plays every 10 points
SND_WELCOME = load_snd("sound/welcome.wav")    # plays on the mode-select screen
SND_PASS    = [
    load_snd("sound/voicears.wav"),            # alternates with voicebach on each pipe pass
    load_snd("sound/voicebach.wav"),
]


# ── Best score (persists across sessions) ─────────────────────────────────────
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


# ── Microphone (voice mode only) ──────────────────────────────────────────────
current_loudness = 0.0
mic_stream       = None

def audio_callback(indata, _frames, _time, _status):
    # runs in background thread; calculates RMS volume of each mic chunk
    global current_loudness
    current_loudness = np.linalg.norm(indata) * 10

def start_mic():
    global mic_stream
    if not VOICE_AVAILABLE:
        return False
    try:
        mic_stream = sd.InputStream(callback=audio_callback, channels=1, samplerate=44100)
        mic_stream.start()
        return True
    except Exception:
        return False

def stop_mic():
    global mic_stream, current_loudness
    if mic_stream:
        try:
            mic_stream.stop()
            mic_stream.close()
        except Exception:
            pass
        mic_stream = None
    current_loudness = 0.0


# ── Bird ──────────────────────────────────────────────────────────────────────
class Bird:
    W, H = 50, 38

    def __init__(self):
        self.x  = 80
        self.y  = HEIGHT // 2
        self.vy = 0

    def flap(self):
        # normal mode: single upward impulse
        self.vy = FLAP_FORCE
        play(SND_FLAP)

    def voice_push(self, loudness):
        # voice mode: continuous upward force proportional to mic volume
        # the louder you speak, the harder the bird climbs (capped at VOICE_MAX_VY)
        self.vy = max(self.vy - loudness * VOICE_SCALE, VOICE_MAX_VY)

    def update(self):
        self.vy += GRAVITY   # gravity pulls the bird down every frame
        self.y  += self.vy

    def draw(self, surface):
        if BIRD_IMG:
            angle   = max(-30, min(self.vy * -3, 90))
            rotated = pygame.transform.rotate(BIRD_IMG, angle)
            rect    = rotated.get_rect(center=(self.x, self.y))
            surface.blit(rotated, rect)      # TODO: image drawn here — set BIRD_IMG above
        else:
            pygame.draw.ellipse(surface, YELLOW, self.rect())

    def rect(self):
        # cast to int — pygame.Rect rejects floats, and y becomes float after physics update
        return pygame.Rect(int(self.x - self.W // 2), int(self.y - self.H // 2), self.W, self.H)


# ── Pipe pair ─────────────────────────────────────────────────────────────────
class Pipe:
    W = 70

    def __init__(self):
        gap_y            = random.randint(120, GROUND_Y - PIPE_GAP - 60)
        self.top_rect    = pygame.Rect(WIDTH, 0,               self.W, gap_y)
        self.bottom_rect = pygame.Rect(WIDTH, gap_y + PIPE_GAP, self.W, HEIGHT)
        self.passed      = False

    def update(self):
        self.top_rect.x    -= PIPE_SPEED
        self.bottom_rect.x -= PIPE_SPEED

    def draw(self, surface):
        if PIPE_IMG:
            flipped    = pygame.transform.flip(PIPE_IMG, False, True)
            top_scaled = pygame.transform.scale(flipped, (self.W, self.top_rect.h))
            surface.blit(top_scaled, self.top_rect.topleft)      # TODO: pipe image drawn here (top)
            bot_scaled = pygame.transform.scale(PIPE_IMG, (self.W, self.bottom_rect.h))
            surface.blit(bot_scaled, self.bottom_rect.topleft)   # TODO: pipe image drawn here (bottom)
        else:
            pygame.draw.rect(surface, GREEN,      self.top_rect)
            pygame.draw.rect(surface, DARK_GREEN, self.top_rect.inflate(-6, 0))
            pygame.draw.rect(surface, GREEN,      self.bottom_rect)
            pygame.draw.rect(surface, DARK_GREEN, self.bottom_rect.inflate(-6, 0))

    def off_screen(self):
        return self.top_rect.right < 0


# ── Scene helpers ─────────────────────────────────────────────────────────────
def draw_background(surface):
    if BG_IMG:
        surface.blit(BG_IMG, (0, 0))           # TODO: background image drawn here
    else:
        surface.fill(SKY_BLUE)

def draw_ground(surface):
    if GROUND_IMG:
        surface.blit(GROUND_IMG, (0, GROUND_Y))  # TODO: ground image drawn here
    else:
        pygame.draw.rect(surface, GREEN,      (0, GROUND_Y, WIDTH, 80))
        pygame.draw.rect(surface, DARK_GREEN, (0, GROUND_Y, WIDTH, 8))

def draw_volume_meter(surface, loudness):
    # thin bar on the right edge — shows live mic level so the player can calibrate their voice
    bar_w    = 14
    x        = WIDTH - bar_w - 4
    max_h    = GROUND_Y - 24
    fill_h   = min(int(loudness * 3), max_h)
    # trough
    pygame.draw.rect(surface, (20, 20, 20), (x, 20, bar_w, max_h))
    # level fill — green below threshold, red above
    if fill_h > 0:
        col = (255, 80, 80) if loudness >= VOICE_THRESHOLD else (80, 210, 80)
        pygame.draw.rect(surface, col, (x, 20 + max_h - fill_h, bar_w, fill_h))
    # threshold line
    thresh_y = 20 + max_h - min(int(VOICE_THRESHOLD * 3), max_h)
    pygame.draw.line(surface, WHITE, (x - 3, thresh_y), (x + bar_w + 3, thresh_y), 2)
    # label
    lbl = font_tiny.render("MIC", True, WHITE)
    surface.blit(lbl, (x + bar_w // 2 - lbl.get_width() // 2, GROUND_Y + 2))


# ── Mode-select screen ────────────────────────────────────────────────────────
def mode_select():
    """Shows the mode-select screen. Returns 'normal', 'voice', or None (quit)."""
    play(SND_WELCOME)

    while True:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if SND_WELCOME: SND_WELCOME.stop()
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if SND_WELCOME: SND_WELCOME.stop()
                    return None
                if event.key == pygame.K_1:
                    if SND_WELCOME: SND_WELCOME.stop()
                    return 'normal'
                if event.key == pygame.K_2 and VOICE_AVAILABLE:
                    if SND_WELCOME: SND_WELCOME.stop()
                    return 'voice'

        draw_background(screen)
        draw_ground(screen)

        # title
        title = font_big.render("FLAPPY BIRD", True, WHITE)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 75))

        sub = font_small.render("Choose your control:", True, WHITE)
        screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 148))

        # option 1 — Normal
        b1 = pygame.Rect(WIDTH // 2 - 145, 195, 290, 75)
        pygame.draw.rect(screen, BLUE, b1, border_radius=14)
        screen.blit(font_med.render("[1]  Normal",          True, WHITE), (b1.x + 18, b1.y + 8))
        screen.blit(font_tiny.render("Space or Click to flap", True, WHITE), (b1.x + 18, b1.y + 48))

        # option 2 — Voice
        b2_col = LIME if VOICE_AVAILABLE else GREY
        b2 = pygame.Rect(WIDTH // 2 - 145, 290, 290, 75)
        pygame.draw.rect(screen, b2_col, b2, border_radius=14)
        screen.blit(font_med.render("[2]  Voice Mode",      True, WHITE), (b2.x + 18, b2.y + 8))
        hint = "Speak / shout to fly" if VOICE_AVAILABLE else "Install sounddevice + numpy"
        screen.blit(font_tiny.render(hint, True, WHITE), (b2.x + 18, b2.y + 48))

        # escape hint
        esc = font_tiny.render("ESC to quit", True, WHITE)
        screen.blit(esc, (WIDTH // 2 - esc.get_width() // 2, 385))

        pygame.display.flip()


# ── Game loop ─────────────────────────────────────────────────────────────────
def game_loop(mode):
    """
    Runs one full round.  Returns the next mode to play ('normal'/'voice')
    or None if the player wants to quit.
    """
    bird           = Bird()
    pipes          = []
    score          = 0
    best           = load_best()
    alive          = True
    started        = False
    last_pipe      = pygame.time.get_ticks()
    pass_snd_idx   = 0
    voice_was_on   = False   # used to detect rising edge so flap sound only plays once per shout

    while True:
        clock.tick(FPS)
        now = pygame.time.get_ticks()

        # ── Input ─────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if not alive:
                    # game-over key choices
                    if event.key == pygame.K_1:
                        return 'normal'
                    if event.key == pygame.K_2 and VOICE_AVAILABLE:
                        return 'voice'
                    return mode          # any other key: restart same mode
                if mode == 'normal':
                    if not started:
                        started = True
                    bird.flap()
            if event.type == pygame.MOUSEBUTTONDOWN and mode == 'normal':
                if not alive:
                    return mode
                if not started:
                    started = True
                bird.flap()

        # voice mode: mic loudness drives the bird upward continuously
        if mode == 'voice' and alive:
            loud = current_loudness
            if loud > VOICE_THRESHOLD:
                if not started:
                    started = True       # first shout starts the game
                bird.voice_push(loud)
                if not voice_was_on:
                    play(SND_FLAP)       # flap sound only on the leading edge of each shout
                voice_was_on = True
            else:
                voice_was_on = False

        # ── Update ────────────────────────────────────────────────────────────
        if started and alive:
            bird.update()

            if now - last_pipe > PIPE_INTERVAL:
                pipes.append(Pipe())
                last_pipe = now

            for p in pipes:
                # score check runs BEFORE the pipe moves — tests the position the player sees this frame
                if not p.passed and p.top_rect.centerx <= bird.x:
                    p.passed     = True
                    score       += 1
                    play(SND_PASS[pass_snd_idx])
                    pass_snd_idx = 1 - pass_snd_idx   # flip between voicears / voicebach
                    if score % 10 == 0:
                        play(SND_RECORD)
                p.update()   # move the pipe AFTER scoring so the trigger frame matches what's rendered

            pipes = [p for p in pipes if not p.off_screen()]

            # ceiling: in voice mode clamp instead of kill (continuous loud voice would instantly
            # push the bird to y<0 every game); in normal mode the ceiling is a valid death zone
            if bird.y < 0:
                if mode == 'voice':
                    bird.y  = 0
                    bird.vy = 0   # bounce off ceiling, don't die
                else:
                    alive = False

            # collision
            bird_r = bird.rect()
            if bird.y >= GROUND_Y:
                alive = False
            for p in pipes:
                if bird_r.colliderect(p.top_rect) or bird_r.colliderect(p.bottom_rect):
                    alive = False

            # this runs exactly once — the frame alive flips to False
            if not alive:
                play(SND_LOSE)
                if score > best:
                    best = score
                    save_best(best)

        # ── Draw ──────────────────────────────────────────────────────────────
        draw_background(screen)
        for p in pipes:
            p.draw(screen)
        draw_ground(screen)
        bird.draw(screen)

        # mic volume meter (voice mode only)
        if mode == 'voice':
            draw_volume_meter(screen, current_loudness)

        # current score
        score_surf = font_big.render(str(score), True, WHITE)
        screen.blit(score_surf, (WIDTH // 2 - score_surf.get_width() // 2, 30))

        # best score below current
        best_surf = font_small.render(f"Best: {best}", True, WHITE)
        screen.blit(best_surf, (WIDTH // 2 - best_surf.get_width() // 2, 88))

        # mode badge — top-left corner
        badge_col  = LIME if mode == 'voice' else BLUE
        badge_text = "VOICE" if mode == 'voice' else "NORMAL"
        badge      = font_tiny.render(badge_text, True, WHITE)
        pygame.draw.rect(screen, badge_col, (4, 4, badge.get_width() + 12, 22), border_radius=5)
        screen.blit(badge, (10, 6))

        # waiting-screen prompt
        if not started:
            prompt = "Speak to start!" if mode == 'voice' else "Space / Click to start"
            msg = font_small.render(prompt, True, WHITE)
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 + 60))

        # game-over overlay
        if not alive:
            overlay = pygame.Surface((WIDTH, 220), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 155))
            screen.blit(overlay, (0, HEIGHT // 2 - 100))

            over = font_big.render("Game Over",                     True, WHITE)
            sc   = font_med.render(f"Score: {score}",               True, WHITE)
            bst  = font_med.render(f"Best:  {best}",                True, GOLD if score == best else WHITE)
            r1   = font_small.render("[1] Normal   [2] Voice",      True, WHITE)
            r2   = font_tiny.render("(any other key = same mode)",   True, WHITE)

            screen.blit(over, (WIDTH // 2 - over.get_width() // 2, HEIGHT // 2 - 92))
            screen.blit(sc,   (WIDTH // 2 - sc.get_width()   // 2, HEIGHT // 2 - 42))
            screen.blit(bst,  (WIDTH // 2 - bst.get_width()  // 2, HEIGHT // 2 +  2))
            screen.blit(r1,   (WIDTH // 2 - r1.get_width()   // 2, HEIGHT // 2 + 48))
            screen.blit(r2,   (WIDTH // 2 - r2.get_width()   // 2, HEIGHT // 2 + 78))

        pygame.display.flip()


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    mode = mode_select()

    while mode is not None:
        # start mic when entering voice mode
        if mode == 'voice':
            if not start_mic():
                mode = 'normal'   # fall back silently if mic unavailable

        next_mode = game_loop(mode)

        stop_mic()   # always release mic between rounds
        mode = next_mode

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
