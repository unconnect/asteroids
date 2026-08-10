import pygame
import pytest

from constants import (
    PLAYER_BLINK_HZ,
    PLAYER_INVULN_TIME,
    PLAYER_RADIUS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from player import Player


def make_player(x=SCREEN_WIDTH / 2, y=SCREEN_HEIGHT / 2):
    group = pygame.sprite.Group()
    Player.containers = (group,)
    return Player(x, y)


def test_player_spawns_invulnerable():
    player = make_player()
    assert player.is_invulnerable is True
    assert player.invuln_timer == PLAYER_INVULN_TIME


def test_invulnerability_expires():
    player = make_player()
    player.invuln_timer = 0.01
    player.update(0.5)
    assert player.is_invulnerable is False


def test_visible_when_not_invulnerable():
    player = make_player()
    player.invuln_timer = 0
    assert player.is_visible() is True


def test_blinks_while_invulnerable():
    player = make_player()
    seen = set()
    # Sample a full blink cycle; both states must occur.
    for step in range(PLAYER_BLINK_HZ * 2):
        player.invuln_timer = PLAYER_INVULN_TIME - step / (PLAYER_BLINK_HZ * 2)
        seen.add(player.is_visible())
    assert seen == {True, False}

    # The set check above catches a stuck blink but not an inverted one:
    # flipping the parity would leave {True, False} unchanged. Pin actual
    # values against the spec formula.
    for t in (2.0, 1.95, 1.9, 1.85):
        player.invuln_timer = t
        assert player.is_visible() is (int(t * PLAYER_BLINK_HZ) % 2 == 0)


def test_respawn_recentres_and_grants_grace():
    player = make_player(10, 10)
    player.rotation = 123
    player.velocity = pygame.Vector2(50, 50)
    player.invuln_timer = 0

    player.respawn()

    assert player.position == pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    assert player.velocity == pygame.Vector2(0, 0)
    assert player.rotation == 0
    assert player.invuln_timer == PLAYER_INVULN_TIME


def test_update_wraps_the_player():
    player = make_player(-PLAYER_RADIUS - 5, 300)
    player.update(0.0)
    assert player.position.x == SCREEN_WIDTH + PLAYER_RADIUS


def test_update_ticks_down_the_shoot_cooldown():
    player = make_player()
    player.cooldown_timer = 0.3
    player.update(0.1)
    assert player.cooldown_timer == pytest.approx(0.2)


def test_triangle_has_three_points():
    player = make_player()
    assert len(player.triangle()) == 3
