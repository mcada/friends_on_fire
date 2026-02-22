import pygame, os, random, math

BASIC = "basic"
CLUSTER = "cluster"
IRON = "iron"


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

        if rock_type == IRON:
            self.hp = 3
        else:
            self.hp = 1
        self.max_hp = self.hp

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

    def take_damage(self, amount=1):
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
        self.rect.move_ip(self.dx, self.dy)
        gh = self.game.GAME_HEIGHT
        if self.rect.right < 0 or self.rect.top > gh + 50 or self.rect.bottom < -50:
            self.kill()
