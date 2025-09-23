import pygame
from circleshape import CircleShape
from constants import COLOR_WHITE

class Asteroids(CircleShape):
  def __init__(self, x, y, radius):
    super().__init__(self, x, y, radius)

  def draw(self, screen):
    pygame.draw.circle(screen, COLOR_WHITE, (self.x, self.y), self.radius, 2)

  def update(self, dt):
    for frame in dt:
      self.x += self.velocity * dt
      self.y += self.velocity * dt