import pygame
import sys
from constants import *
from player import Player
from asteroid import Asteroid
from asteroidfield import AsteroidField
from shot import Shot

def main():
    # Init the game
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    # Game clock
    clock = pygame.time.Clock()
    # Delta time
    dt = 0

    # Groups
    updatable = pygame.sprite.Group()
    drawable = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots = pygame.sprite.Group()

    # Automatically add all instaces of the classes to groups
    Player.containers = (updatable, drawable)
    Asteroid.containers = (asteroids, updatable, drawable)
    AsteroidField.containers = (updatable)
    Shot.containers = (shots, updatable, drawable)
 
    # Create a player and spawn in middle of the screen.
    player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    asteroidfield = AsteroidField()


    # Start the gameloop
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
        # Fill screen with black
        screen.fill(SCREEN_COLOR)

        # Update all instaces
        updatable.update(dt)

        # Check for asteroid collision with player
        for asteroid in asteroids:
            if asteroid.collision(player):
                print("Game over!")
                sys.exit()

        # Draw all instances
        for drawable_instace in drawable:
            drawable_instace.draw(screen)

        # Decrease players cooldown timer
        player.cooldown_timer -= dt

        # Update the screen
        pygame.display.flip()

        # Update delta time by seconds 
        dt = clock.tick(60) / 1000

if __name__ == "__main__":
    main()
