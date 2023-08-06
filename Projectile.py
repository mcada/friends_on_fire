import pygame


class Projectile(pygame.sprite.Sprite):
    def __init__(self, color, x, y) -> None:
        super().__init__()
        self.image = pygame.Surface((15, 15))
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

    def update(self):
        self.rect.move_ip(7, 0)
        # hardcoded, this needs to be taken from global variable somehow from main (add to constructor?)
        if self.rect.x > 1280:
            self.kill()
