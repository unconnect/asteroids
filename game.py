from asteroidfield import AsteroidField
from constants import SCREEN_HEIGHT, SCREEN_WIDTH
from player import Player


def start_new_game(state, groups):
    """Clear the world and build a fresh one.

    Used for both first start and restart, so there is exactly one code path
    that produces a playable game.
    """
    for group in groups:
        group.empty()
    state.reset()
    player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    AsteroidField(state)
    return player


def handle_collisions(state, player, asteroids, shots):
    """Resolve shot hits and player impacts for one frame.

    Returns the player, respawned if they were hit and had a life left.
    """
    for asteroid in list(asteroids):
        for shot in list(shots):
            if shot.collision(asteroid):
                state.award(asteroid.radius)
                asteroid.split()
                shot.kill()
                break

    if player.is_invulnerable:
        return player

    for asteroid in list(asteroids):
        if asteroid.collision(player):
            if not state.lose_life():
                player.respawn()
            break
    return player
