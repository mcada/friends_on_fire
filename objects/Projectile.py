import pygame, os, math

from states.pause_menu import PauseMenu

GLOW_PAD = 6


class Projectile(pygame.sprite.Sprite):
    _base_image = None

    def __init__(self, color, x, y, game, dx=8, dy=0, wave=None,
                 width=15, height=15, piercing=False, shiny=False):
        super().__init__()
        self.game = game
        self.dx = dx
        self.dy = dy
        self.wave = wave
        self.start_y = y
        self.age = 0
        self.piercing = piercing

        if piercing:
            self.image = self._make_beam(color, width, height, shiny)
        else:
            if Projectile._base_image is None:
                Projectile._base_image = pygame.image.load(
                    os.path.join(game.assets_dir, "ammo", "ammo_1.png")
                ).convert_alpha()
            self.image = pygame.transform.scale(
                Projectile._base_image.copy(), (width, height)
            )
            self.image.fill(pygame.Color(color), special_flags=pygame.BLEND_RGB_MULT)
            if shiny:
                self.image = self._add_glow(self.image, color)

        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

    @staticmethod
    def _add_glow(base, color):
        c = pygame.Color(color)
        gw = base.get_width() + GLOW_PAD
        gh = base.get_height() + GLOW_PAD
        glow = pygame.Surface((gw, gh), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*c[:3], 70), glow.get_rect())
        pygame.draw.ellipse(glow, (255, 255, 255, 40), glow.get_rect().inflate(-4, -4))
        glow.blit(base, (GLOW_PAD // 2, GLOW_PAD // 2))
        return glow

    @staticmethod
    def _make_beam(color, width, height, shiny=False):
        c = pygame.Color(color)
        if shiny:
            total_h = height + GLOW_PAD
            surf = pygame.Surface((width, total_h), pygame.SRCALPHA)
            pygame.draw.rect(surf, (*c[:3], 40), (0, 0, width, total_h), border_radius=3)
            bright = tuple(min(255, v + 120) for v in c[:3])
            core_h = max(2, height // 2)
            core_y = (total_h - core_h) // 2
            pygame.draw.rect(surf, bright, (0, core_y, width, core_h))
            cy = total_h // 2
            pygame.draw.line(surf, (255, 255, 255), (0, cy), (width - 1, cy), 2)
        else:
            surf = pygame.Surface((width, height), pygame.SRCALPHA)
            surf.fill((*c[:3], 50))
            core_h = max(2, height // 3)
            core_y = (height - core_h) // 2
            bright = tuple(min(255, v + 100) for v in c[:3])
            pygame.draw.rect(surf, bright, (0, core_y, width, core_h))
            cy = height // 2
            pygame.draw.line(surf, (255, 255, 255), (0, cy), (width - 1, cy))
        return surf

    def update(self):
        if isinstance(self.game.state_stack[-1], PauseMenu):
            return
        self.age += 1
        self.rect.centerx += self.dx
        if self.wave:
            amp, freq = self.wave[0], self.wave[1]
            phase = self.wave[2] if len(self.wave) > 2 else 0
            self.rect.centery = int(self.start_y + amp * math.sin(freq * self.age + phase))
        else:
            self.rect.centery += self.dy
        if (
            self.rect.x > self.game.GAME_WIDTH
            or self.rect.bottom < -20
            or self.rect.top > self.game.GAME_HEIGHT + 20
        ):
            self.kill()
