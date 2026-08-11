import pygame

from asteroid import Asteroid
from asteroidfield import AsteroidField
from constants import (
    ASTEROID_MAX_RADIUS,
    ASTEROID_MIN_RADIUS,
    PLAYER_INVULN_TIME,
    PLAYER_LIVES,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from game import handle_collisions, start_new_game
from gamestate import GameState, Phase
from player import Player
from shot import Shot


def make_groups():
    """Wire fresh scratch groups the way main() does, for one test's world."""
    updatable = pygame.sprite.Group()
    drawable = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots = pygame.sprite.Group()
    Player.containers = (updatable, drawable)
    Asteroid.containers = (asteroids, updatable, drawable)
    AsteroidField.containers = (updatable,)
    Shot.containers = (shots, updatable, drawable)
    return updatable, drawable, asteroids, shots


def make_collision_world():
    """A leaner world for handle_collisions tests: just the groups it reads."""
    updatable = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots = pygame.sprite.Group()
    Player.containers = (updatable,)
    Asteroid.containers = (asteroids,)
    Shot.containers = (shots,)
    return asteroids, shots


# --- start_new_game -------------------------------------------------------


def test_start_new_game_empties_every_group_first():
    updatable, drawable, asteroids, shots = make_groups()
    junk = pygame.sprite.Sprite()
    updatable.add(junk)
    drawable.add(junk)
    asteroids.add(junk)
    shots.add(junk)

    state = GameState()
    start_new_game(state, (updatable, drawable, asteroids, shots))

    assert junk not in updatable
    assert junk not in drawable
    assert junk not in asteroids
    assert junk not in shots


def test_start_new_game_leaves_exactly_one_player_and_one_field():
    updatable, drawable, asteroids, shots = make_groups()
    state = GameState()
    player = start_new_game(state, (updatable, drawable, asteroids, shots))

    assert len(asteroids) == 0
    assert len(shots) == 0
    assert len(drawable) == 1
    assert list(drawable)[0] is player

    players_in_updatable = [s for s in updatable if isinstance(s, Player)]
    fields_in_updatable = [s for s in updatable if isinstance(s, AsteroidField)]
    assert len(updatable) == 2
    assert players_in_updatable == [player]
    assert len(fields_in_updatable) == 1


def test_start_new_game_resets_score_and_lives():
    updatable, drawable, asteroids, shots = make_groups()
    state = GameState()
    state.award(60)
    for _ in range(PLAYER_LIVES):
        state.lose_life()
    assert state.phase is Phase.GAME_OVER

    start_new_game(state, (updatable, drawable, asteroids, shots))

    assert state.score == 0
    assert state.lives == PLAYER_LIVES
    assert state.phase is Phase.PLAYING


def test_start_new_game_returns_the_player_that_is_in_the_groups():
    updatable, drawable, asteroids, shots = make_groups()
    state = GameState()
    groups = (updatable, drawable, asteroids, shots)

    stale_player = start_new_game(state, groups)
    fresh_player = start_new_game(state, groups)

    assert fresh_player is not stale_player
    assert fresh_player in drawable
    assert fresh_player in updatable
    assert stale_player not in drawable
    assert stale_player not in updatable


# --- handle_collisions: respawn polarity -----------------------------------


def test_non_fatal_hit_drops_a_life_and_respawns_the_player():
    asteroids, shots = make_collision_world()
    state = GameState()
    player = Player(100, 100)
    player.invuln_timer = 0  # not invulnerable
    player.position = pygame.Vector2(100, 100)
    Asteroid(100, 100, ASTEROID_MIN_RADIUS)

    handle_collisions(state, player, asteroids, shots)

    assert state.lives == PLAYER_LIVES - 1
    assert state.phase is Phase.PLAYING
    assert player.position == pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    assert player.invuln_timer == PLAYER_INVULN_TIME


def test_fatal_hit_ends_the_game_without_respawning():
    asteroids, shots = make_collision_world()
    state = GameState()
    state.lives = 1
    player = Player(200, 200)
    player.invuln_timer = 0  # not invulnerable
    death_position = pygame.Vector2(200, 200)
    player.position = pygame.Vector2(death_position)
    Asteroid(200, 200, ASTEROID_MIN_RADIUS)

    handle_collisions(state, player, asteroids, shots)

    assert state.phase is Phase.GAME_OVER
    assert state.lives == 0
    # Not respawned: stays put at the position where the fatal hit landed.
    assert player.position == death_position


# --- handle_collisions: shot resolution ------------------------------------


def test_one_shot_destroys_exactly_one_asteroid():
    asteroids, shots = make_collision_world()
    state = GameState()
    player = Player(-9999, -9999)
    Asteroid(100, 100, ASTEROID_MIN_RADIUS)
    Asteroid(105, 100, ASTEROID_MIN_RADIUS)
    Shot(100, 100)

    handle_collisions(state, player, asteroids, shots)

    assert len(shots) == 0
    assert len(asteroids) == 1
    assert state.score == 100  # exactly one hit at ASTEROID_MIN_RADIUS, not two


def test_shot_hit_awards_the_pre_split_radius_and_children_survive():
    asteroids, shots = make_collision_world()
    state = GameState()
    player = Player(-9999, -9999)
    Asteroid(300, 300, ASTEROID_MAX_RADIUS)
    Shot(300, 300)

    handle_collisions(state, player, asteroids, shots)

    assert state.score == 20  # scored off the pre-split radius (60), not 0
    assert len(asteroids) == 2
    for child in asteroids:
        assert child.radius == ASTEROID_MAX_RADIUS - ASTEROID_MIN_RADIUS


def test_invulnerable_player_takes_no_damage():
    asteroids, shots = make_collision_world()
    state = GameState()
    player = Player(100, 100)
    player.invuln_timer = 5.0  # still invulnerable
    Asteroid(100, 100, ASTEROID_MIN_RADIUS)

    handle_collisions(state, player, asteroids, shots)

    assert state.lives == PLAYER_LIVES
    assert state.phase is Phase.PLAYING
