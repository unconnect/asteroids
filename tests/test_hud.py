import pygame
import pytest

from constants import (
    COLOR_BLACK,
    HUD_FONT_SIZE,
    HUD_TITLE_SIZE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from gamestate import GameState, Phase
from hud import draw_game_over, draw_hud


@pytest.fixture
def surface():
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.fill(COLOR_BLACK)
    return screen


def pixels(screen):
    """Raw pixel buffer — compares exactly, unlike an averaged colour.

    average_color() dilutes a few hundred text pixels across 921,600 into
    a rounded (0, 0, 0), so it cannot tell "drew some text" from "drew
    nothing at all".
    """
    return pygame.image.tostring(screen, "RGB")


def test_draw_hud_puts_something_on_screen(surface):
    before = pixels(surface)
    font = pygame.font.Font(None, HUD_FONT_SIZE)
    state = GameState()
    state.award(60)
    draw_hud(surface, font, state)
    assert pixels(surface) != before


def test_draw_hud_writes_on_both_sides(surface):
    # Score goes left, ships go right. Check each half changed, so a HUD
    # that silently dropped one of them fails.
    font = pygame.font.Font(None, HUD_FONT_SIZE)
    state = GameState()
    state.award(60)

    left_before = pixels(surface.subsurface(pygame.Rect(0, 0, SCREEN_WIDTH // 2, 100)))
    right_before = pixels(
        surface.subsurface(pygame.Rect(SCREEN_WIDTH // 2, 0, SCREEN_WIDTH // 2, 100))
    )

    draw_hud(surface, font, state)

    left_after = pixels(surface.subsurface(pygame.Rect(0, 0, SCREEN_WIDTH // 2, 100)))
    right_after = pixels(
        surface.subsurface(pygame.Rect(SCREEN_WIDTH // 2, 0, SCREEN_WIDTH // 2, 100))
    )

    assert left_after != left_before
    assert right_after != right_before


def test_draw_game_over_puts_something_on_screen(surface):
    before = pixels(surface)
    font = pygame.font.Font(None, HUD_FONT_SIZE)
    title_font = pygame.font.Font(None, HUD_TITLE_SIZE)
    state = GameState()
    state.phase = Phase.GAME_OVER
    draw_game_over(surface, title_font, font, state)
    assert pixels(surface) != before


def test_game_over_overlay_dims_the_playfield(surface):
    # The overlay must be translucent, not opaque, or the frozen playfield
    # behind it would be invisible. Sample a corner well away from any text:
    # that pixel reflects the overlay's alpha and nothing else.
    surface.fill((255, 255, 255))

    font = pygame.font.Font(None, HUD_FONT_SIZE)
    title_font = pygame.font.Font(None, HUD_TITLE_SIZE)
    state = GameState()
    state.phase = Phase.GAME_OVER
    draw_game_over(surface, title_font, font, state)

    red, green, blue = surface.get_at((5, 5))[:3]
    assert 0 < red < 255, "corner is either untouched or blacked out"
    assert (red, green, blue) == (red, red, red), "dimming should be neutral grey"
