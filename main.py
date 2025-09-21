import pygame
from constants import *

def main():
    # Init the game
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    # Game clock
    clock = pygame.time.Clock()
    # Delta time
    dt = 0

    # Start the gameloop
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
        # Fill screen with black
        screen.fill(BACKGROUND_COLOR)
        # Update the screen
        pygame.display.flip()
        # Update delta time by seconds 
        dt = clock.tick(60) / 1000

if __name__ == "__main__":
    main()
