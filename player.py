import pygame

from circleshape import CircleShape
from constants import *
from shot import Shot


class Player(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, radius=PLAYER_RADIUS)
        self.rotation = 0
        self.cooldown_timer = 0
        # Spawn with grace so the player is not killed by whatever is already
        # on screen before they can react.
        self.invuln_timer = PLAYER_INVULN_TIME

    @property
    def is_invulnerable(self):
        return self.invuln_timer > 0

    def is_visible(self):
        """Blink while invulnerable so the grace period is legible."""
        if not self.is_invulnerable:
            return True
        return int(self.invuln_timer * PLAYER_BLINK_HZ) % 2 == 0

    def respawn(self):
        self.position = pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        self.velocity = pygame.Vector2(0, 0)
        self.rotation = 0
        self.invuln_timer = PLAYER_INVULN_TIME

    # Define a triangle
    def triangle(self):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        right = pygame.Vector2(0, 1).rotate(self.rotation + 90) * self.radius / 1.5
        a = self.position + forward * self.radius
        b = self.position - forward * self.radius - right
        c = self.position - forward * self.radius + right
        return [a, b, c]

    def draw(self, screen):
        if self.is_visible():
            pygame.draw.polygon(screen, COLOR_WHITE, self.triangle(), 2)

    def rotate(self, dt):
        self.rotation += PLAYER_TURN_SPEED * dt

    def update(self, dt):
        self.cooldown_timer -= dt
        self.invuln_timer -= dt

        keys = pygame.key.get_pressed()

        # Classic WASD movement
        if keys[pygame.K_a]:
            self.rotate(dt)
        if keys[pygame.K_d]:
            self.rotate(-dt)
        if keys[pygame.K_w]:
            self.move(dt)
        if keys[pygame.K_s]:
            self.move(-dt)
        if keys[pygame.K_SPACE]:
            self.shoot()

        self.wrap()

    def move(self, dt):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        self.position += forward * PLAYER_SPEED * dt

    def shoot(self):
        if self.cooldown_timer <= 0:
            shot = Shot(self.position.x, self.position.y)
            # Create and rotate its velocity vector in the player's direction
            shot.velocity = pygame.Vector2(0, 1).rotate(self.rotation)
            # Scale up the velocity vector to move fast
            shot.velocity *= PLAYER_SHOT_SPEED
            # Set shot cooldown timer
            self.cooldown_timer = PLAYER_SHOOT_COOLDOWN
