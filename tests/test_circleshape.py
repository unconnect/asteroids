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


from constants import SCREEN_HEIGHT, SCREEN_WIDTH


def test_wrap_leaves_centred_shape_alone():
    shape = make(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 20)
    shape.wrap()
    assert shape.position == pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)


def test_wrap_left_edge_to_right():
    shape = make(-21, 300, 20)
    shape.wrap()
    assert shape.position.x == SCREEN_WIDTH + 20


def test_wrap_right_edge_to_left():
    shape = make(SCREEN_WIDTH + 21, 300, 20)
    shape.wrap()
    assert shape.position.x == -20


def test_wrap_top_edge_to_bottom():
    shape = make(300, -21, 20)
    shape.wrap()
    assert shape.position.y == SCREEN_HEIGHT + 20


def test_wrap_bottom_edge_to_top():
    shape = make(300, SCREEN_HEIGHT + 21, 20)
    shape.wrap()
    assert shape.position.y == -20


def test_wrap_preserves_the_other_axis():
    shape = make(-21, 137, 20)
    shape.wrap()
    assert shape.position.y == 137


def test_is_off_screen_false_just_inside_margin():
    shape = make(-49, 300, 20)
    assert shape.is_off_screen(50) is False


def test_is_off_screen_true_just_outside_margin():
    shape = make(-51, 300, 20)
    assert shape.is_off_screen(50) is True


def test_is_off_screen_checks_all_four_sides():
    margin = 50
    assert make(300, -51, 20).is_off_screen(margin) is True
    assert make(300, SCREEN_HEIGHT + 51, 20).is_off_screen(margin) is True
    assert make(SCREEN_WIDTH + 51, 300, 20).is_off_screen(margin) is True
    assert make(-51, 300, 20).is_off_screen(margin) is True
