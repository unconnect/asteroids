import pygame
import random
from circleshape import CircleShape
from constants import *


class Asteroid(CircleShape):
  def __init__(self, x, y, radius = ASTEROID_MIN_RADIUS):
    super().__init__(x, y, radius) 

  def draw(self, screen):
    pygame.draw.circle(screen, COLOR_WHITE, self.position, self.radius, 2)

  def update(self, dt):
    self.position += self.velocity * dt

  def split(self):
    # Remove this asteroid from game
    self.kill()
    # In case this asteroid is of the smallest kind, we are done here.
    if self.radius <= ASTEROID_MIN_RADIUS:
      return
    # In case this asteroid is larger than smallest radius we spawn new ones.
    random_angle = random.uniform(20, 50)
    new_velocity1 = self.velocity.rotate(random_angle)
    new_velocity2 = self.velocity.rotate(-random_angle)
    new_radius = self.radius - ASTEROID_MIN_RADIUS
    new_asteroid1 = Asteroid(self.position.x, self.position.y, new_radius)
    new_asteroid2 = Asteroid(self.position.x, self.position.y, new_radius)
    new_asteroid1.velocity = new_velocity1 * 1.2
    new_asteroid2.velocity = new_velocity2 * 1.2