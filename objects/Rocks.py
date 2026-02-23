import pygame, os, random, math

BASIC = "basic"
CLUSTER = "cluster"
IRON = "iron"
BLACKHOLE = "blackhole"

BH_CORE_START = 8
BH_CORE_MAX = 28
BH_GRAVITY_START = 360
BH_GRAVITY_MAX = 640
BH_STRENGTH_START = 105
BH_STRENGTH_MAX = 196
BH_CONSUME_RADIUS_START = 14
BH_CONSUME_RADIUS_MAX = 32
BH_GROWTH_RATE = 0.12


class Rock(pygame.sprite.Sprite):
    sprites = None

    @classmethod
    def load_sprites(cls, sprite_dir):
        cls.sprites = []
        asteroid_dir = os.path.join(sprite_dir, "asteroids")
        for i in range(1, 5):
            path = os.path.join(asteroid_dir, f"asteroid_{i}.png")
            cls.sprites.append(pygame.image.load(path).convert_alpha())

    def __init__(self, x, y, width, height, game,
                 rock_type=BASIC, dx=-3, dy=0):
        super().__init__()
        if Rock.sprites is None:
            Rock.load_sprites(game.sprite_dir)
        self.game = game
        self.rock_type = rock_type
        self.dx = dx
        self.dy = dy
        self._fx = float(x)
        self._fy = float(y)

        if rock_type == BLACKHOLE:
            self.hp = 999
            self._bh_mass = 0.0
            self._spin = random.uniform(0, math.pi * 2)
            self._rebuild_bh_sprite()
        elif rock_type == IRON:
            self.hp = 3
        else:
            self.hp = 1
        self.max_hp = self.hp

        if rock_type != BLACKHOLE:
            w = max(10, width)
            h = max(10, height)
            base_sprite = random.choice(Rock.sprites)
            self._base_image = pygame.transform.scale(base_sprite, (w, h))

            if rock_type == IRON:
                self._apply_iron_visual()
            elif rock_type == CLUSTER:
                self._apply_cluster_visual()

            self.image = self._base_image.copy()

        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

    # ---- black hole properties (scale with consumed mass) ----

    @property
    def bh_growth(self):
        return min(1.0, self._bh_mass * BH_GROWTH_RATE)

    @property
    def core_radius(self):
        g = self.bh_growth
        return int(BH_CORE_START + (BH_CORE_MAX - BH_CORE_START) * g)

    @property
    def gravity_radius(self):
        g = self.bh_growth
        return BH_GRAVITY_START + (BH_GRAVITY_MAX - BH_GRAVITY_START) * g

    @property
    def gravity_strength(self):
        g = self.bh_growth
        return BH_STRENGTH_START + (BH_STRENGTH_MAX - BH_STRENGTH_START) * g

    @property
    def consume_radius(self):
        g = self.bh_growth
        return BH_CONSUME_RADIUS_START + (BH_CONSUME_RADIUS_MAX - BH_CONSUME_RADIUS_START) * g

    def feed(self, amount=1.0):
        self._bh_mass += amount
        self._rebuild_bh_sprite()

    def _rebuild_bh_sprite(self):
        """Tiny sprite: just the core circle for collision."""
        cr = self.core_radius
        d = cr * 2 + 2
        surf = pygame.Surface((d, d), pygame.SRCALPHA)
        c = d // 2
        pygame.draw.circle(surf, (10, 0, 20), (c, c), cr)
        pygame.draw.circle(surf, (0, 0, 0), (c, c), max(1, cr - 2))
        pygame.draw.circle(surf, (120, 50, 200, 180), (c, c), cr, 1)
        self.image = surf
        self.mask = pygame.mask.from_surface(surf)
        old_center = self.rect.center if hasattr(self, 'rect') and self.rect else (int(self._fx), int(self._fy))
        self.rect = surf.get_rect(center=old_center)

    def draw_blackhole_effects(self, surface):
        """Draw gravitational lensing distortion and dark vignette on canvas."""
        cx, cy = self.rect.centerx, self.rect.centery
        cr = self.core_radius
        gr = int(self.gravity_radius)

        # --- Gravitational lensing: warp the background toward the center ---
        dist_r = max(30, int(gr * 0.55))
        sw, sh = surface.get_size()
        x1 = max(0, cx - dist_r)
        y1 = max(0, cy - dist_r)
        x2 = min(sw, cx + dist_r)
        y2 = min(sh, cy + dist_r)
        cap_w, cap_h = x2 - x1, y2 - y1

        if cap_w > 8 and cap_h > 8:
            captured = surface.subsurface((x1, y1, cap_w, cap_h)).copy()
            lcx, lcy = cx - x1, cy - y1

            layers = [
                (dist_r,           0.96, 20),
                (dist_r * 2 // 3,  0.91, 45),
                (dist_r // 3,      0.84, 75),
            ]
            for radius, shrink, alpha in layers:
                if radius < 4:
                    continue
                small_w = max(4, int(cap_w * shrink))
                small_h = max(4, int(cap_h * shrink))
                distorted = pygame.transform.smoothscale(
                    pygame.transform.smoothscale(captured, (small_w, small_h)),
                    (cap_w, cap_h),
                )
                result = pygame.Surface((cap_w, cap_h), pygame.SRCALPHA)
                result.blit(distorted, (0, 0))
                mask = pygame.Surface((cap_w, cap_h), pygame.SRCALPHA)
                pygame.draw.circle(mask, (255, 255, 255, alpha),
                                   (lcx, lcy), radius)
                result.blit(mask, (0, 0),
                            special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(result, (x1, y1))

        # --- Dark vignette (light being swallowed) ---
        vig_r = cr + 22 + int(12 * self.bh_growth)
        vig_surf = pygame.Surface((vig_r * 2, vig_r * 2), pygame.SRCALPHA)
        vc = vig_r
        step = max(2, vig_r // 9)
        for i in range(9, 0, -1):
            r = cr + i * step
            a = min(220, 12 + (9 - i) * 22)
            pygame.draw.circle(vig_surf, (3, 0, 8, a), (vc, vc), r)
        surface.blit(vig_surf, (cx - vc, cy - vc))

        # --- Faint event-horizon ring ---
        glow_r = cr + 3
        glow_size = glow_r * 2 + 6
        glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
        gc = glow_r + 3
        pygame.draw.circle(glow_surf, (50, 12, 100, 35), (gc, gc), glow_r + 2)
        pygame.draw.circle(glow_surf, (90, 25, 160, 60), (gc, gc), glow_r, 1)
        surface.blit(glow_surf, (cx - gc, cy - gc))

    # ---- regular asteroid visuals ----

    @staticmethod
    def _shape_tint(mask, color):
        """Create a tint surface that only covers the asteroid's pixels."""
        return mask.to_surface(
            setcolor=color, unsetcolor=(0, 0, 0, 0),
        )

    def _apply_cluster_visual(self):
        w, h = self._base_image.get_size()
        mask = pygame.mask.from_surface(self._base_image)

        self._base_image.blit(self._shape_tint(mask, (180, 70, 10, 90)), (0, 0))

        cx, cy = w // 2, h // 2
        cracks = pygame.Surface((w, h), pygame.SRCALPHA)
        for _ in range(random.randint(3, 5)):
            x1 = cx + random.randint(-w // 3, w // 3)
            y1 = cy + random.randint(-h // 3, h // 3)
            angle = random.uniform(0, 2 * math.pi)
            length = random.randint(w // 4, w // 2)
            x2 = x1 + int(math.cos(angle) * length)
            y2 = y1 + int(math.sin(angle) * length)
            color = random.choice([
                (255, 140, 20), (255, 100, 10), (255, 180, 40),
            ])
            pygame.draw.line(cracks, color, (x1, y1), (x2, y2), 2)
        crack_mask = mask.to_surface(
            setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0),
        )
        cracks.blit(crack_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self._base_image.blit(cracks, (0, 0))

        outline = mask.outline()
        if len(outline) > 2:
            glow = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.lines(glow, (255, 120, 20, 100), True, outline, 1)
            self._base_image.blit(glow, (0, 0))

        px_arr = pygame.PixelArray(self._base_image)
        for _ in range(max(2, w * h // 200)):
            gx = random.randint(0, w - 1)
            gy = random.randint(0, h - 1)
            if mask.get_at((gx, gy)):
                px_arr[gx, gy] = random.choice([
                    (255, 200, 50, 255), (255, 160, 30, 255),
                ])
        del px_arr

    def _apply_iron_visual(self):
        w, h = self._base_image.get_size()
        mask = pygame.mask.from_surface(self._base_image)

        self._base_image.blit(self._shape_tint(mask, (140, 160, 190, 130)), (0, 0))

        outline = mask.outline()
        if len(outline) > 2:
            border = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.lines(border, (200, 220, 245, 180), True, outline, 1)
            self._base_image.blit(border, (0, 0))

        px_arr = pygame.PixelArray(self._base_image)
        for _ in range(max(3, w * h // 120)):
            sx = random.randint(0, w - 1)
            sy = random.randint(0, h - 1)
            if mask.get_at((sx, sy)):
                px_arr[sx, sy] = random.choice([
                    (230, 240, 255, 255), (210, 225, 245, 255),
                    (255, 255, 255, 255),
                ])
        del px_arr

    # ---- damage / update ----

    def take_damage(self, amount=1):
        if self.rock_type == BLACKHOLE:
            return
        self.hp -= amount
        if self.hp > 0 and self.rock_type == IRON:
            self._update_damage_visual()

    def _update_damage_visual(self):
        ratio = 1 - self.hp / self.max_hp
        self.image = self._base_image.copy()
        mask = pygame.mask.from_surface(self.image)
        color = (int(220 * ratio), 30, 0, int(120 * ratio))
        self.image.blit(self._shape_tint(mask, color), (0, 0))
        self.mask = mask

    def update(self):
        self._fx += self.dx
        self._fy += self.dy
        self.rect.center = (int(self._fx), int(self._fy))

        if self.rock_type == BLACKHOLE:
            self._spin += 0.03

        gh = self.game.GAME_HEIGHT
        if self.rect.right < -30 or self.rect.top > gh + 50 or self.rect.bottom < -50:
            self.kill()
