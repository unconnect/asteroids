import pygame
from constants import *
from player import Player
from asteroids import Asteroids

def main():
    # Init the game
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    # Game clock
    clock = pygame.time.Clock()
    # Delta time
    dt = 0

    # Groups
    updatables = pygame.sprite.Group()
    drawables = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()

    # 
    Player.containers = (updatables, drawables)
    Asteroids.containers = (asteroids, updatables, drawables)
 
    # Create a player and spawn in middle of the screen.
    player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)



    # Start the gameloop
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
        # Fill screen with black
        screen.fill(SCREEN_COLOR)

        # Update all instaces
        updatables.update(dt)
        # Draw all instances
        for drawable in drawables:
            drawable.draw(screen)

        # Update the screen
        pygame.display.flip()

        # Update delta time by seconds 
        dt = clock.tick(60) / 1000

if __name__ == "__main__":
    main()
