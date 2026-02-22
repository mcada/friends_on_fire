import pygame, os, math

GLOW_PAD = 6


HOMING_TURN_RATE = 0.12
HOMING_SPEED = 5


class Projectile(pygame.sprite.Sprite):
    _base_image = None

    def __init__(self, color, x, y, game, dx=8, dy=0, wave=None,
                 width=15, height=15, piercing=False, shiny=False,
                 pulse=False, homing=False):
        super().__init__()
        self.game = game
        self.dx = dx
        self.dy = dy
        self.wave = wave
        self.start_y = y
        self.age = 0
        self.piercing = piercing
        self.pulse = pulse
        self.homing = homing

        if homing:
            self.image = self._make_missile(color, width, height, shiny)
        elif pulse:
            self.image = self._make_pulse(color, width, height, shiny)
        elif piercing:
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
    def _make_pulse(color, width, height, shiny=False):
        c = pygame.Color(color)
        r = max(width, height) // 2
        pad = 8 if shiny else 4
        size = (r + pad) * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2

        outer_alpha = 120 if shiny else 90
        pygame.draw.circle(surf, (*c[:3], outer_alpha), (cx, cy), r + pad)

        mid = tuple(min(255, v + 60) for v in c[:3])
        pygame.draw.circle(surf, (*mid, 190), (cx, cy), r)

        bright = tuple(min(255, v + 140) for v in c[:3])
        core_r = max(3, r // 2)
        pygame.draw.circle(surf, (*bright, 255), (cx, cy), core_r)

        pygame.draw.circle(surf, (255, 255, 255, 240), (cx, cy), max(1, core_r // 2))

        if shiny:
            pygame.draw.circle(surf, (*c[:3], 50), (cx, cy), r + pad + 4)
            pygame.draw.circle(surf, (255, 255, 255, 80), (cx, cy), core_r + 2)
        return surf

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

    @staticmethod
    def _make_missile(color, width, height, shiny=False):
        c = pygame.Color(color)
        w, h = max(width, 14), max(height, 8)
        pad = 4 if shiny else 0
        surf = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        ox, oy = pad, pad
        bright = tuple(min(255, v + 80) for v in c[:3])
        nose = [(ox + w, oy + h // 2),
                (ox + w - 5, oy), (ox + w - 5, oy + h)]
        pygame.draw.polygon(surf, bright, nose)
        pygame.draw.rect(surf, c[:3], (ox, oy + 1, w - 5, h - 2))
        pygame.draw.rect(surf, bright, (ox + 2, oy + h // 2 - 1, w - 9, 2))
        fin_col = tuple(max(0, v - 40) for v in c[:3])
        pygame.draw.polygon(surf, fin_col,
                            [(ox, oy), (ox + 4, oy + 2), (ox + 4, oy)])
        pygame.draw.polygon(surf, fin_col,
                            [(ox, oy + h), (ox + 4, oy + h - 2), (ox + 4, oy + h)])
        if shiny:
            glow = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (*c[:3], 50), glow.get_rect())
            glow.blit(surf, (0, 0))
            return glow
        return surf

    def _steer_homing(self):
        best_dist = float("inf")
        target = None
        cx, cy = self.rect.centerx, self.rect.centery
        for rock in self.game.rocks:
            dx = rock.rect.centerx - cx
            dy = rock.rect.centery - cy
            d = dx * dx + dy * dy
            if d < best_dist:
                best_dist = d
                target = rock
        gw = self.game.active_game_world
        if gw and gw.boss and gw.boss.alive_flag:
            dx = gw.boss.rect.centerx - cx
            dy = gw.boss.rect.centery - cy
            d = dx * dx + dy * dy
            if d < best_dist:
                target = gw.boss

        if target is None:
            return
        tx, ty = target.rect.centerx, target.rect.centery
        desired = math.atan2(ty - cy, tx - cx)
        current = math.atan2(self.dy, self.dx)
        diff = desired - current
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        current += diff * HOMING_TURN_RATE
        speed = math.sqrt(self.dx ** 2 + self.dy ** 2)
        speed = max(speed, HOMING_SPEED)
        self.dx = speed * math.cos(current)
        self.dy = speed * math.sin(current)

    def update(self):
        if self.game.paused:
            return
        self.age += 1

        if self.homing:
            self._steer_homing()

        self.rect.centerx += self.dx
        if self.wave:
            amp, freq = self.wave[0], self.wave[1]
            phase = self.wave[2] if len(self.wave) > 2 else 0
            self.rect.centery = int(self.start_y + amp * math.sin(freq * self.age + phase))
        else:
            self.rect.centery += self.dy
        if (
            self.rect.x > self.game.GAME_WIDTH + 40
            or self.rect.x < -60
            or self.rect.bottom < -40
            or self.rect.top > self.game.GAME_HEIGHT + 40
        ):
            self.kill()
