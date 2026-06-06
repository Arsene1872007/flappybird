import pygame
import sounddevice as sd
import numpy as np
import sys

# --- AUDIO SETUP ---

# Global variable to store the current loudness
current_loudness = 0.0

def audio_callback(indata, frames, time, status):
    """
    This function runs automatically in the background every time the mic picks up a chunk of audio.
    """
    global current_loudness
    if status:
        print(status, file=sys.stderr)
    
    # Calculate the Root Mean Square (RMS) of the audio signal to get a positive volume value
    # We multiply by 10 (or any multiplier) to scale the number to something easier to work with.
    volume_norm = np.linalg.norm(indata) * 10
    current_loudness = volume_norm

# Start the microphone stream
# We open it before the game loop so it continuously listens in the background
try:
    mic_stream = sd.InputStream(callback=audio_callback, channels=1, samplerate=44100)
    mic_stream.start()
except Exception as e:
    print(f"Could not open microphone: {e}")
    sys.exit()

# --- PYGAME INTEGRATION EXAMPLE ---

pygame.init()
screen = pygame.display.set_mode((400, 600))
clock = pygame.time.Clock()

# Bird variables
bird_y = 300
bird_x = 100
gravity = 5

# Set a threshold so background noise doesn't move the bird
VOLUME_THRESHOLD = 10.0 

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- THE CORE LOGIC ---
    # 1. Apply gravity pulling the bird down
    bird_y += gravity

    # 2. Check the microphone loudness to push the bird up
    if current_loudness > VOLUME_THRESHOLD:
        # The louder you yell, the higher the bird flies.
        # (Remember in Pygame, subtracting from Y moves the object UP)
        jump_strength = current_loudness * 0.5
        bird_y -= jump_strength

    # Keep bird on screen (Floor and Ceiling collision)
    if bird_y > 580: bird_y = 580
    if bird_y < 0: bird_y = 0

    # --- DRAWING ---
    screen.fill((135, 206, 235)) # Sky blue background
    pygame.draw.circle(screen, (255, 255, 0), (bird_x, int(bird_y)), 20) # Draw the bird
    
    # Optional: Draw a volume meter on the screen to help you debug
    meter_height = min(current_loudness * 2, 600)
    pygame.draw.rect(screen, (255, 0, 0), (370, 600 - meter_height, 30, meter_height))

    pygame.display.flip()
    clock.tick(60)

# Clean up when closing
mic_stream.stop()
mic_stream.close()
pygame.quit()