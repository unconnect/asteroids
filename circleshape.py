import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH

# Base class for game objects
class CircleShape(pygame.sprite.Sprite):
    def __init__(self, x, y, radius):
        # we will be using this later
        if hasattr(self, "containers"):
            super().__init__(self.containers)
        else:
            super().__init__()

        self.position = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0)
        self.radius = radius

    def draw(self, screen):
        # sub-classes must override
        pass

    def update(self, dt):
        # sub-classes must override
        pass

    def collision(self, other: "CircleShape"):
        # In case the combined radi
        if self.radius + other.radius > self.position.distance_to(other.position):
            return True
        return False

    def wrap(self):
        """Teleport to the opposite edge once fully off-screen.

        The radius offset means the shape reappears just outside the far edge
        rather than popping into view at the boundary.
        """
        if self.position.x < -self.radius:
            self.position.x = SCREEN_WIDTH + self.radius
        elif self.position.x > SCREEN_WIDTH + self.radius:
            self.position.x = -self.radius

        if self.position.y < -self.radius:
            self.position.y = SCREEN_HEIGHT + self.radius
        elif self.position.y > SCREEN_HEIGHT + self.radius:
            self.position.y = -self.radius

    def is_off_screen(self, margin):
        """True once the shape is further than `margin` outside the playfield."""
        return (
            self.position.x < -margin
            or self.position.x > SCREEN_WIDTH + margin
            or self.position.y < -margin
            or self.position.y > SCREEN_HEIGHT + margin
        )
