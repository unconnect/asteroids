import os

# Must run before pygame is imported anywhere: forces headless SDL so tests
# work in CI with no display or sound device.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest


@pytest.fixture(scope="session", autouse=True)
def _pygame_session():
    """Init pygame once per test session.

    Player.update() calls pygame.key.get_pressed(), which needs the video
    subsystem. Keeping this beside the dummy SDL env vars means any test
    file works standalone, not just when collected alongside another that
    happened to init pygame.
    """
    pygame.init()
    yield
    pygame.quit()
