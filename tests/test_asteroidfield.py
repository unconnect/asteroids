import pygame

from asteroid import Asteroid
from asteroidfield import AsteroidField
from constants import DIFFICULTY_MAX_SCORE, SPAWN_RATE_START
from gamestate import GameState


def make_field(state):
    field_group = pygame.sprite.Group()
    asteroid_group = pygame.sprite.Group()
    AsteroidField.containers = (field_group,)
    Asteroid.containers = (asteroid_group,)
    return AsteroidField(state), asteroid_group


def test_no_spawn_before_the_interval_elapses():
    state = GameState()
    field, asteroids = make_field(state)
    field.update(SPAWN_RATE_START / 2)
    assert len(asteroids) == 0


def test_spawns_once_the_interval_elapses():
    state = GameState()
    field, asteroids = make_field(state)
    field.update(SPAWN_RATE_START + 0.01)
    assert len(asteroids) == 1


def test_spawned_asteroid_is_moving():
    state = GameState()
    field, asteroids = make_field(state)
    field.update(SPAWN_RATE_START + 0.01)
    assert list(asteroids)[0].velocity.length() > 0


def test_high_score_spawns_faster():
    state = GameState()
    state.score = DIFFICULTY_MAX_SCORE
    field, asteroids = make_field(state)
    # This dt would not have been enough at the starting interval.
    field.update(state.spawn_interval + 0.01)
    assert len(asteroids) == 1
    assert state.spawn_interval < SPAWN_RATE_START
