import pygame, math, random

from objects.Player import PLAYER_CENTER_OFFSET_X, PLAYER_CENTER_OFFSET_Y

PRIMARY_UPGRADE_COLOR = (255, 210, 60)
SHIELD_COLOR = (80, 180, 255)

BOB_AMPLITUDE = 18
BOB_SPEED = 2.5
DRIFT_SPEED = 1.5


class _BasePickup(pygame.sprite.Sprite):
    """Shared movement / magnet logic for all pickups."""

    pickup_type = "generic"

    def __init__(self, x, y, game, image):
        super().__init__()
        self.game = game
        self._fx, self._fy = float(x), float(y)
        self._base_fy = self._fy
        self.age = random.uniform(0, math.pi * 2)
        self.magnet_range = 80
        self.image = image
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect(center=(x, y))

    def _closest_player_center(self):
        best_dist = float("inf")
        best_px, best_py = self._fx, self._fy
        for p in self.game.players:
            if not p.alive:
                continue
            px = p.position_x + PLAYER_CENTER_OFFSET_X
            py = p.position_y + PLAYER_CENTER_OFFSET_Y
            d = (px - self._fx) ** 2 + (py - self._fy) ** 2
            if d < best_dist:
                best_dist = d
                best_px, best_py = px, py
        return best_px, best_py

    def update(self):
        if self.game.paused:
            return
        dt = self.game.delta_time
        self.age += dt * BOB_SPEED
        self._fx -= DRIFT_SPEED

        px, py = self._closest_player_center()
        dx = px - self._fx
        dy = py - self._fy
        dist = max(1, (dx ** 2 + dy ** 2) ** 0.5)

        if dist < self.magnet_range:
            pull = 5 * (1 - dist / self.magnet_range) + 1
            self._fx += pull * dx / dist
            self._base_fy += pull * dy / dist

        bob = math.sin(self.age) * BOB_AMPLITUDE
        self._fy = self._base_fy + bob
        self.rect.center = (int(self._fx), int(self._fy))

        if self.rect.right < -30:
            self.kill()


def _make_bubble_with_wings(color, size=26):
    """Draw a translucent bubble with small wings -- clearly not an enemy."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    parsed = pygame.Color(color) if isinstance(color, str) else pygame.Color(*color[:3])
    r, g, b = parsed.r, parsed.g, parsed.b
    cx, cy = size // 2, size // 2
    radius = size // 2 - 2

    # Wings (drawn behind the bubble)
    wing_color = (min(255, r + 40), min(255, g + 40), min(255, b + 40), 160)
    wing_w = max(3, size // 5)
    wing_h = max(5, size // 3)
    # Left wing
    pygame.draw.polygon(surf, wing_color, [
        (cx - radius + 2, cy - 1),
        (cx - radius - wing_w, cy - wing_h),
        (cx - radius - wing_w + 2, cy),
        (cx - radius - wing_w, cy + wing_h),
        (cx - radius + 2, cy + 1),
    ])
    # Right wing
    pygame.draw.polygon(surf, wing_color, [
        (cx + radius - 2, cy - 1),
        (cx + radius + wing_w, cy - wing_h),
        (cx + radius + wing_w - 2, cy),
        (cx + radius + wing_w, cy + wing_h),
        (cx + radius - 2, cy + 1),
    ])

    # Outer glow
    glow_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (r, g, b, 50), (cx, cy), radius + 1)
    surf.blit(glow_surf, (0, 0))

    # Main bubble
    pygame.draw.circle(surf, (r, g, b, 140), (cx, cy), radius)

    # Inner bright ring
    bright = (min(255, r + 80), min(255, g + 80), min(255, b + 80))
    pygame.draw.circle(surf, (*bright, 120), (cx, cy), radius - 2, 2)

    # Highlight / shine
    shine_cx = cx - radius // 3
    shine_cy = cy - radius // 3
    shine_r = max(2, radius // 3)
    pygame.draw.circle(surf, (255, 255, 255, 180), (shine_cx, shine_cy), shine_r)

    # Outer border
    pygame.draw.circle(surf, (255, 255, 255, 200), (cx, cy), radius, 1)

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
        super().__init__(x, y, game, _make_bubble_with_wings(color))


class ShieldPickup(_BasePickup):
    """Shield pickup -- grants one-hit protection."""

    pickup_type = "shield"

    def __init__(self, x, y, game):
        super().__init__(x, y, game, _make_bubble_with_wings(SHIELD_COLOR, size=28))
