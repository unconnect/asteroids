# Colors
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)

# Screen
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_COLOR = COLOR_BLACK
MAX_FRAME_TIME = 0.05  # seconds; guards against browser tab-refocus jumps

# Asteroid
ASTEROID_MIN_RADIUS = 20
ASTEROID_KINDS = 3
ASTEROID_MAX_RADIUS = ASTEROID_MIN_RADIUS * ASTEROID_KINDS

# Asteroids spawn ASTEROID_MAX_RADIUS outside the edge, so the cull margin
# MUST be larger than that or every asteroid dies on the frame it spawns.
ASTEROID_CULL_MARGIN = ASTEROID_MAX_RADIUS * 2

# Classic arcade scoring: smaller rocks are worth more.
# Keyed by radius // ASTEROID_MIN_RADIUS.
ASTEROID_SCORE = {1: 100, 2: 50, 3: 20}

# Difficulty: spawn interval falls linearly from START to MIN as the score
# climbs to DIFFICULTY_MAX_SCORE, then stays at MIN.
SPAWN_RATE_START = 0.8
SPAWN_RATE_MIN = 0.25
DIFFICULTY_MAX_SCORE = 5000

# Player
PLAYER_RADIUS = 20
PLAYER_SPEED = 200
PLAYER_TURN_SPEED = 300
PLAYER_SHOT_SPEED = 500
PLAYER_SHOOT_COOLDOWN = 0.3
PLAYER_LIVES = 3
PLAYER_INVULN_TIME = 2.0
PLAYER_BLINK_HZ = 10

# Shot
SHOT_RADIUS = 5

# HUD
HUD_FONT_SIZE = 28
HUD_TITLE_SIZE = 72
HUD_MARGIN = 20
