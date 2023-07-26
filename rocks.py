import pygame

class Rock(pygame.sprite.Sprite):
    def __init__(self, color, x, y, height, width) -> None:
        super().__init__()
        self.image = pygame.Surface((height,width))
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

    def update(self):
        self.rect.move_ip(-5,0)
        if self.rect.x < 0:
            self.kill()


    