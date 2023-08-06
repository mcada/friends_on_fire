import pygame, os

from states.pause_menu import PauseMenu


class Projectile(pygame.sprite.Sprite):
    def __init__(self, color, x, y, game, width=15, height=15) -> None:
        super().__init__()
        self.game = game
        self.image = pygame.transform.scale(
            pygame.image.load(
                os.path.join(game.assets_dir, "ammo", "ammo_1.png")
            ).convert_alpha(),
            (width, height),
        )

        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

    def update(self):
        # do not move projectile if game is paused
        if isinstance(self.game.state_stack[-1], PauseMenu):
            return
        self.rect.move_ip(3, 0)
        # hardcoded, this needs to be taken from global variable somehow from main (add to constructor?)
        if self.rect.x > self.game.GAME_WIDTH:
            self.kill()
