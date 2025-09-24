import pygame
from circleshape import CircleShape
from constants import *

class Asteroid(CircleShape):
  def __init__(self, x, y, radius = ASTEROID_MIN_RADIUS):
    super().__init__(x, y, radius) 

  def draw(self, screen):
    print(self.position)
    pygame.draw.circle(screen, COLOR_WHITE, self.position, self.radius, 2)

  def update(self, dt):
    self.position += self.velocity * dt