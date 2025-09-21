import pygame
from constants import *

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    # The gameloop
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
        # Fill screen with black
        screen.fill(BACKGROUND_COLOR)
        # Update the screen
        pygame.display.flip()


if __name__ == "__main__":
    main()
