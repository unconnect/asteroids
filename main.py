import asyncio

import pygame

from asteroid import Asteroid
from asteroidfield import AsteroidField
from constants import *
from game import handle_collisions, start_new_game
from gamestate import GameState, Phase
from hud import draw_game_over, draw_hud
from player import Player
from shot import Shot


async def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Asteroids")

    clock = pygame.time.Clock()
    dt = 0

    font = pygame.font.Font(None, HUD_FONT_SIZE)
    title_font = pygame.font.Font(None, HUD_TITLE_SIZE)

    updatable = pygame.sprite.Group()
    drawable = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots = pygame.sprite.Group()
    groups = (updatable, drawable, asteroids, shots)

    # Automatically add all instances of the classes to groups
    Player.containers = (updatable, drawable)
    Asteroid.containers = (asteroids, updatable, drawable)
    AsteroidField.containers = (updatable,)
    Shot.containers = (shots, updatable, drawable)

    state = GameState()
    player = start_new_game(state, groups)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if state.phase is Phase.GAME_OVER and event.key == pygame.K_r:
                    player = start_new_game(state, groups)

        screen.fill(SCREEN_COLOR)

        if state.phase is Phase.PLAYING:
            updatable.update(dt)
            player = handle_collisions(state, player, asteroids, shots)

        for drawable_instance in drawable:
            drawable_instance.draw(screen)

        draw_hud(screen, font, state)
        if state.phase is Phase.GAME_OVER:
            draw_game_over(screen, title_font, font, state)

        pygame.display.flip()

        # Cap the step so a browser tab that regains focus after being
        # throttled cannot deliver one multi-second frame: that would teleport
        # sprites straight through each other without a collision test and
        # burn the whole invulnerability grace in a single decrement.
        dt = min(clock.tick(60) / 1000, MAX_FRAME_TIME)

        # Yields to the browser event loop under pygbag. On the desktop this
        # is a no-op that costs nothing.
        await asyncio.sleep(0)

    pygame.quit()


asyncio.run(main())
