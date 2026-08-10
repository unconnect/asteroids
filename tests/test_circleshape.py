import pygame

from circleshape import CircleShape


def make(x, y, radius):
    return CircleShape(x, y, radius)


def test_overlapping_circles_collide():
    a = make(0, 0, 10)
    b = make(5, 0, 10)
    assert a.collision(b) is True


def test_distant_circles_do_not_collide():
    a = make(0, 0, 10)
    b = make(100, 0, 10)
    assert a.collision(b) is False


def test_exactly_touching_circles_do_not_collide():
    # Distance == sum of radii. The implementation uses a strict >, so
    # circles that only graze are not a hit.
    a = make(0, 0, 10)
    b = make(20, 0, 10)
    assert a.collision(b) is False


def test_collision_is_symmetric():
    a = make(0, 0, 30)
    b = make(25, 0, 10)
    assert a.collision(b) == b.collision(a)


def test_new_shape_starts_at_rest():
    shape = make(3, 4, 10)
    assert shape.position == pygame.Vector2(3, 4)
    assert shape.velocity == pygame.Vector2(0, 0)
