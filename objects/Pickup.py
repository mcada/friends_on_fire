import pygame, math

from states.pause_menu import PauseMenu

PRIMARY_UPGRADE_COLOR = (255, 210, 60)
SHIELD_COLOR = (80, 180, 255)


class _BasePickup(pygame.sprite.Sprite):
    """Shared movement / magnet logic for all pickups."""

    pickup_type = "generic"

    def __init__(self, x, y, game, image):
        super().__init__()
        self.game = game
        self.fx, self.fy = float(x), float(y)
        self.age = 0
        self.magnet_range = 80
        self.image = image
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


def _make_diamond(color, size=22):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    diamond = [(c, 1), (size - 2, c), (c, size - 2), (1, c)]
    parsed = pygame.Color(color) if isinstance(color, str) else color
    pygame.draw.polygon(surf, parsed, diamond)
    bright = tuple(min(255, v + 80) for v in parsed[:3])
    inner = [(c, 5), (size - 6, c), (c, size - 6), (5, c)]
    pygame.draw.polygon(surf, bright, inner)
    pygame.draw.polygon(surf, (255, 255, 255), diamond, 2)
    return surf


class UpgradePickup(_BasePickup):
    """Weapon upgrade pickup.

    weapon_cls=None  -> gold primary-weapon upgrade
    weapon_cls=<cls> -> colored secondary-weapon pickup
    """

    pickup_type = "upgrade"

    def __init__(self, x, y, weapon_cls, game):
        self.weapon_cls = weapon_cls
        color = PRIMARY_UPGRADE_COLOR if weapon_cls is None else pygame.Color(weapon_cls.color)
        super().__init__(x, y, game, _make_diamond(color))


class ShieldPickup(_BasePickup):
    """Shield pickup -- grants one-hit protection."""

    pickup_type = "shield"

    def __init__(self, x, y, game):
        size = 24
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        pygame.draw.circle(surf, SHIELD_COLOR, (c, c), c - 1)
        pygame.draw.circle(surf, (200, 230, 255), (c, c), c - 4)
        pygame.draw.circle(surf, SHIELD_COLOR, (c, c), c - 1, 2)
        pygame.draw.circle(surf, (255, 255, 255), (c, c), c - 1, 1)
        super().__init__(x, y, game, surf)
