import pygame, math

from states.pause_menu import PauseMenu

PRIMARY_UPGRADE_COLOR = (255, 210, 60)


class UpgradePickup(pygame.sprite.Sprite):
    """Floating upgrade pickup.

    weapon_cls=None  → gold primary-weapon upgrade
    weapon_cls=<cls> → colored secondary-weapon pickup
    """

    def __init__(self, x, y, weapon_cls, game):
        super().__init__()
        self.game = game
        self.weapon_cls = weapon_cls
        self.fx, self.fy = float(x), float(y)
        self.age = 0
        self.magnet_range = 80

        color = PRIMARY_UPGRADE_COLOR if weapon_cls is None else pygame.Color(weapon_cls.color)
        size = 22
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        diamond = [(c, 1), (size - 2, c), (c, size - 2), (1, c)]
        parsed = pygame.Color(color) if isinstance(color, str) else color
        pygame.draw.polygon(self.image, parsed, diamond)
        bright = tuple(min(255, v + 80) for v in parsed[:3])
        inner = [(c, 5), (size - 6, c), (c, size - 6), (5, c)]
        pygame.draw.polygon(self.image, bright, inner)
        pygame.draw.polygon(self.image, (255, 255, 255), diamond, 2)

        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        if isinstance(self.game.state_stack[-1], PauseMenu):
            return
        self.age += 1
        self.fx -= 1.5

        px = self.game.player.position_x + 40
        py = self.game.player.position_y + 17
        dx = px - self.fx
        dy = py - self.fy
        dist = max(1, (dx ** 2 + dy ** 2) ** 0.5)

        if dist < self.magnet_range:
            pull = 5 * (1 - dist / self.magnet_range) + 1
            self.fx += pull * dx / dist
            self.fy += pull * dy / dist

        bob = math.sin(self.age * 0.08) * 4
        self.rect.center = (int(self.fx), int(self.fy + bob))

        if self.rect.right < -30:
            self.kill()
