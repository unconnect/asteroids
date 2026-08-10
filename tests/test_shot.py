import pygame

from constants import SCREEN_WIDTH
from shot import Shot


def make_group():
    group = pygame.sprite.Group()
    Shot.containers = (group,)
    return group


def test_update_moves_by_velocity():
    make_group()
    shot = Shot(100, 100)
    shot.velocity = pygame.Vector2(0, 50)
    shot.update(2.0)
    assert shot.position == pygame.Vector2(100, 200)


def test_shot_that_leaves_the_screen_is_culled():
    group = make_group()
    shot = Shot(SCREEN_WIDTH - 10, 300)
    shot.velocity = pygame.Vector2(500, 0)
    shot.update(1.0)
    assert len(group) == 0


def test_shot_on_screen_survives():
    group = make_group()
    shot = Shot(640, 360)
    shot.velocity = pygame.Vector2(0, 100)
    shot.update(0.1)
    assert len(group) == 1
