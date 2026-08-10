import pygame

from asteroid import Asteroid
from asteroidfield import AsteroidField
from constants import (
    ASTEROID_CULL_MARGIN,
    ASTEROID_MAX_RADIUS,
    ASTEROID_MIN_RADIUS,
)


def make_group():
    """Asteroids auto-add to Asteroid.containers; give them a scratch group."""
    group = pygame.sprite.Group()
    Asteroid.containers = (group,)
    return group


def test_update_moves_by_velocity():
    make_group()
    asteroid = Asteroid(100, 100, ASTEROID_MIN_RADIUS)
    asteroid.velocity = pygame.Vector2(10, 20)
    asteroid.update(1.0)
    assert asteroid.position == pygame.Vector2(110, 120)


def test_asteroid_far_off_screen_is_culled():
    group = make_group()
    asteroid = Asteroid(-ASTEROID_CULL_MARGIN - 100, 300, ASTEROID_MIN_RADIUS)
    asteroid.update(0.0)
    assert len(group) == 0


def test_asteroid_on_screen_survives():
    group = make_group()
    asteroid = Asteroid(640, 360, ASTEROID_MIN_RADIUS)
    asteroid.update(0.0)
    assert len(group) == 1


def test_asteroid_at_its_spawn_position_is_not_culled():
    # Regression guard: asteroids spawn exactly ASTEROID_MAX_RADIUS outside
    # the edge. If the cull margin were <= that, every asteroid would be
    # destroyed on the frame it spawned and the game would be silently empty.
    group = make_group()
    for _, place in AsteroidField.edges:
        position = place(0.5)
        asteroid = Asteroid(position.x, position.y, ASTEROID_MAX_RADIUS)
        asteroid.update(0.0)
    assert len(group) == len(AsteroidField.edges)


def test_split_of_smallest_asteroid_spawns_nothing():
    group = make_group()
    asteroid = Asteroid(640, 360, ASTEROID_MIN_RADIUS)
    asteroid.velocity = pygame.Vector2(10, 0)
    asteroid.split()
    assert len(group) == 0


def test_split_of_large_asteroid_spawns_two_smaller_ones():
    group = make_group()
    asteroid = Asteroid(640, 360, ASTEROID_MAX_RADIUS)
    asteroid.velocity = pygame.Vector2(10, 0)
    asteroid.split()

    children = list(group)
    assert len(children) == 2
    for child in children:
        assert child.radius == ASTEROID_MAX_RADIUS - ASTEROID_MIN_RADIUS
        assert child.position == pygame.Vector2(640, 360)


def test_split_children_move_faster_and_diverge():
    group = make_group()
    asteroid = Asteroid(640, 360, ASTEROID_MAX_RADIUS)
    asteroid.velocity = pygame.Vector2(10, 0)
    asteroid.split()

    first, second = list(group)
    assert first.velocity.length() > asteroid.velocity.length()
    assert second.velocity.length() > asteroid.velocity.length()
    assert first.velocity != second.velocity
