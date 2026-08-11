import pygame

from constants import (
    COLOR_WHITE,
    HUD_MARGIN,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)


def draw_hud(screen, font, state):
    """Score on the left, remaining ships on the right."""
    score = font.render(f"SCORE {state.score}", True, COLOR_WHITE)
    screen.blit(score, (HUD_MARGIN, HUD_MARGIN))

    ships = font.render(f"SHIPS {state.lives}", True, COLOR_WHITE)
    screen.blit(ships, (SCREEN_WIDTH - ships.get_width() - HUD_MARGIN, HUD_MARGIN))


def draw_game_over(screen, title_font, font, state):
    """Dim the frozen playfield and prompt for a restart."""
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    _blit_centred(screen, title_font.render("GAME OVER", True, COLOR_WHITE), -60)
    _blit_centred(screen, font.render(f"SCORE {state.score}", True, COLOR_WHITE), 20)
    _blit_centred(
        screen, font.render("press R to play again", True, COLOR_WHITE), 70
    )


def _blit_centred(screen, surface, y_offset):
    rect = surface.get_rect(
        center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + y_offset)
    )
    screen.blit(surface, rect)
