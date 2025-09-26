import pygame
from circleshape import CircleShape
from constants import *
from shot import Shot

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

  def rotate(self, dt):
     self.rotation += PLAYER_TURN_SPEED * dt
     
  def update(self, dt):
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
  
  def move(self, dt):
     forward = pygame.Vector2(0, 1).rotate(self.rotation)
     self.position += forward * PLAYER_SPEED * dt
  
  def shoot(self):
    shot = Shot(self.position.x, self.position.y)
    # Create and rotate it's velocity vector in the players direction
    shot.velocity = pygame.Vector2(0, 1).rotate(self.rotation)
    # Scale up the velocity vector to move fast
    shot.velocity *= PLAYER_SHOT_SPEED