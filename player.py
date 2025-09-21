import pygame
from circleshape import CircleShape
from constants import PLAYER_RADIUS, COLOR_WHITE


class Player(CircleShape):
  def __init__(self, x, y):
    super().__init__(
      x, y, 
      radius=PLAYER_RADIUS
      )
    self.rotation = 0

  # Define a triangle
  def triangle(self):
      forward = pygame.Vector2(0, 1).rotate(self.rotation)
      right = pygame.Vector2(0, 1).rotate(self.rotation + 90) * self.radius / 1.5
      a = self.position + forward * self.radius
      b = self.position - forward * self.radius - right
      c = self.position - forward * self.radius + right
      return [a, b, c]
  
  def draw(self, screen):
     pygame.draw.polygon(screen, COLOR_WHITE, self.triangle(), 2)