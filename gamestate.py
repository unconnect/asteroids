from enum import Enum, auto

from constants import (
    ASTEROID_MIN_RADIUS,
    ASTEROID_SCORE,
    DIFFICULTY_MAX_SCORE,
    PLAYER_LIVES,
    SPAWN_RATE_MIN,
    SPAWN_RATE_START,
)


class Phase(Enum):
    PLAYING = auto()
    GAME_OVER = auto()


class GameState:
    """Score, lives and difficulty. Deliberately free of pygame.

    Keeping the rules separate from rendering is what lets them be tested
    without a display, and keeps the game loop readable.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.score = 0
        self.lives = PLAYER_LIVES
        self.phase = Phase.PLAYING

    def award(self, asteroid_radius):
        """Add points for destroying an asteroid; returns the points added."""
        kind = int(asteroid_radius) // ASTEROID_MIN_RADIUS
        points = ASTEROID_SCORE.get(kind, 0)
        self.score += points
        return points

    def lose_life(self):
        """Spend a life. Returns True if that was the last one."""
        self.lives = max(0, self.lives - 1)
        if self.lives == 0:
            self.phase = Phase.GAME_OVER
        return self.phase is Phase.GAME_OVER

    @property
    def spawn_interval(self):
        """Seconds between asteroid spawns, tightening as the score climbs."""
        progress = min(1.0, self.score / DIFFICULTY_MAX_SCORE)
        return SPAWN_RATE_START + (SPAWN_RATE_MIN - SPAWN_RATE_START) * progress
