import pygame, math, random


# ---------------------------------------------------------------------------
# Enemy projectile — passes through asteroids, only damages players
# ---------------------------------------------------------------------------

class EnemyProjectile(pygame.sprite.Sprite):
    def __init__(self, x, y, dx, dy, game, size=10,
                 color=(255, 60, 60)):
        super().__init__()
        self.game = game
        self.dx = dx
        self.dy = dy
        w = h = size
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        r = w // 2
        pygame.draw.circle(self.image, (*color[:3], 200), (r, r), r)
        bright = tuple(min(255, c + 100) for c in color[:3])
        pygame.draw.circle(self.image, bright, (r, r), max(1, r - 2))
        pygame.draw.circle(self.image, (255, 255, 255, 220), (r, r), max(1, r // 2))
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        if self.game.paused:
            return
        self.rect.x += self.dx
        self.rect.y += self.dy
        if (self.rect.right < -20 or self.rect.left > self.game.GAME_WIDTH + 20
                or self.rect.bottom < -20 or self.rect.top > self.game.GAME_HEIGHT + 20):
            self.kill()


# ---------------------------------------------------------------------------
# Base Enemy — subclass and override _shoot() and movement for new types
# ---------------------------------------------------------------------------

ENTER_SPEED = 5

class Enemy(pygame.sprite.Sprite):
    """Base class for enemy ships. Subclass for different behaviours."""

    hp = 1
    speed = 80
    shoot_interval = 2.5
    color = (255, 80, 80)
    width = 40
    height = 30
    projectile_speed = 4
    projectile_size = 16
    projectile_color = (255, 80, 80)
    score_value = 1

    def __init__(self, x, y, game):
        super().__init__()
        self.game = game
        self.max_hp = self.hp
        self.shoot_timer = random.uniform(0.5, self.shoot_interval)
        self.alive_flag = True

        self.image = self._build_image()
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect(center=(x, y))

        self._target_x = self._pick_patrol_x()
        self.entering = True
        self.base_y = float(y)
        self.bob_timer = random.uniform(0, math.pi * 2)

    def _build_image(self):
        """Override for custom sprites. Default draws a chevron ship."""
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        c = self.color
        bright = tuple(min(255, v + 80) for v in c)
        w, h = self.width, self.height
        # Leftward-facing chevron body
        body = [(0, h // 2), (w * 3 // 4, 0), (w, h // 4),
                (w * 3 // 4, h // 2),
                (w, h * 3 // 4), (w * 3 // 4, h)]
        pygame.draw.polygon(surf, c, body)
        pygame.draw.polygon(surf, bright, body, 2)
        # Cockpit glow
        pygame.draw.circle(surf, bright, (w * 2 // 3, h // 2), max(2, h // 6))
        pygame.draw.circle(surf, (255, 255, 255), (w * 2 // 3, h // 2), max(1, h // 8))
        return surf

    def _pick_patrol_x(self):
        return random.randint(
            int(self.game.GAME_WIDTH * 0.55),
            int(self.game.GAME_WIDTH * 0.85),
        )

    def _player_center(self):
        best_dist = float("inf")
        default = (self.game.GAME_WIDTH // 4, self.game.GAME_HEIGHT // 2)
        cx, cy = self.rect.centerx, self.rect.centery
        for p in self.game.players:
            if not p.alive:
                continue
            from objects.Player import PLAYER_CENTER_OFFSET_X, PLAYER_CENTER_OFFSET_Y
            px = p.position_x + PLAYER_CENTER_OFFSET_X
            py = p.position_y + PLAYER_CENTER_OFFSET_Y
            d = (px - cx) ** 2 + (py - cy) ** 2
            if d < best_dist:
                best_dist = d
                best = (px, py)
                default = best
        return default

    def take_damage(self, amount=1):
        self.hp -= amount
        if self.hp <= 0:
            self.alive_flag = False
            return True
        return False

    def update(self, dt):
        if self.game.paused:
            return

        if self.entering:
            self.rect.x -= ENTER_SPEED
            if self.rect.x <= self._target_x:
                self.rect.x = self._target_x
                self.entering = False
            return

        self._move(dt)

        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self._shoot()
            self.shoot_timer = self.shoot_interval

    def _move(self, dt):
        """Default movement: gentle vertical bobbing at patrol position."""
        self.bob_timer += dt * 2.0
        self.rect.centery = int(self.base_y + 30 * math.sin(self.bob_timer))
        # Clamp to screen
        self.rect.clamp_ip(pygame.Rect(0, 0, self.game.GAME_WIDTH, self.game.GAME_HEIGHT))

    def _shoot(self):
        """Override for different shooting patterns."""
        pass

    def draw(self, surface):
        if not self.alive_flag:
            return
        surface.blit(self.image, self.rect)
        if self.max_hp > 1:
            self._draw_health_bar(surface)

    def _draw_health_bar(self, surface):
        bar_w = self.width + 4
        bar_h = 4
        x = self.rect.centerx - bar_w // 2
        y = self.rect.top - 8
        pygame.draw.rect(surface, (40, 40, 40), (x - 1, y - 1, bar_w + 2, bar_h + 2))
        fill_w = max(0, int(bar_w * self.hp / self.max_hp))
        color = (220, 40, 40) if self.hp / self.max_hp < 0.35 else (40, 220, 40)
        pygame.draw.rect(surface, color, (x, y, fill_w, bar_h))


# ---------------------------------------------------------------------------
# Fighter — basic enemy ship, fires aimed shots at the player
# ---------------------------------------------------------------------------

class Fighter(Enemy):
    """Ranged sentry — sits far right and fires aimed shots at players."""

    hp = 4
    speed = 80
    shoot_interval = 1.4
    color = (220, 50, 50)
    width = 44
    height = 32
    projectile_speed = 5.5
    projectile_size = 18
    projectile_color = (255, 70, 70)
    score_value = 2

    def _pick_patrol_x(self):
        return random.randint(
            int(self.game.GAME_WIDTH * 0.75),
            int(self.game.GAME_WIDTH * 0.92),
        )

    def _shoot(self):
        cx, cy = self.rect.left, self.rect.centery
        px, py = self._player_center()
        angle = math.atan2(py - cy, px - cx)
        dx = self.projectile_speed * math.cos(angle)
        dy = self.projectile_speed * math.sin(angle)
        self.game.enemy_projectiles.add(
            EnemyProjectile(cx, cy, dx, dy, self.game,
                            size=self.projectile_size,
                            color=self.projectile_color)
        )


# ---------------------------------------------------------------------------
# Striker — aggressive mid-range enemy, patrols closer and fires bursts
# ---------------------------------------------------------------------------

class Striker(Enemy):
    """Mid-range aggressor — patrols near the centre and fires quick bursts."""

    hp = 3
    speed = 100
    shoot_interval = 1.8
    color = (180, 50, 200)
    width = 38
    height = 28
    projectile_speed = 5.0
    projectile_size = 14
    projectile_color = (220, 100, 255)
    score_value = 3

    _BURST_COUNT = 2
    _BURST_GAP = 0.15

    def __init__(self, x, y, game):
        super().__init__(x, y, game)
        self._burst_left = 0
        self._burst_timer = 0.0

    def _pick_patrol_x(self):
        return random.randint(
            int(self.game.GAME_WIDTH * 0.45),
            int(self.game.GAME_WIDTH * 0.65),
        )

    def _build_image(self):
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        c = self.color
        bright = tuple(min(255, v + 80) for v in c)
        w, h = self.width, self.height
        body = [(0, h // 2), (w // 2, 0), (w, h // 4),
                (w, h * 3 // 4), (w // 2, h)]
        pygame.draw.polygon(surf, c, body)
        pygame.draw.polygon(surf, bright, body, 2)
        pygame.draw.circle(surf, bright, (w // 3, h // 2), max(2, h // 5))
        pygame.draw.circle(surf, (255, 255, 255), (w // 3, h // 2), max(1, h // 7))
        return surf

    def _move(self, dt):
        self.bob_timer += dt * 3.0
        self.rect.centery = int(self.base_y + 45 * math.sin(self.bob_timer))
        self.rect.clamp_ip(pygame.Rect(0, 0, self.game.GAME_WIDTH, self.game.GAME_HEIGHT))

    def update(self, dt):
        if self.game.paused:
            return
        if self._burst_left > 0:
            self._burst_timer -= dt
            if self._burst_timer <= 0:
                self._fire_one()
                self._burst_left -= 1
                self._burst_timer = self._BURST_GAP
        super().update(dt)

    def _shoot(self):
        self._burst_left = self._BURST_COUNT
        self._burst_timer = 0.0
        self._fire_one()

    def _fire_one(self):
        cx, cy = self.rect.left, self.rect.centery
        px, py = self._player_center()
        angle = math.atan2(py - cy, px - cx)
        spread = random.uniform(-0.12, 0.12)
        dx = self.projectile_speed * math.cos(angle + spread)
        dy = self.projectile_speed * math.sin(angle + spread)
        self.game.enemy_projectiles.add(
            EnemyProjectile(cx, cy, dx, dy, self.game,
                            size=self.projectile_size,
                            color=self.projectile_color)
        )


# ---------------------------------------------------------------------------
# Drone — disposable scout, flies straight across, fires 1–2 unguided shots
# ---------------------------------------------------------------------------

class Drone(Enemy):
    """Level-1 fodder enemy. Flies left like an asteroid, shoots straight."""

    hp = 2
    speed = 150
    color = (200, 120, 50)
    width = 30
    height = 22
    projectile_speed = 4
    projectile_size = 14
    projectile_color = (255, 140, 60)
    score_value = 1

    def __init__(self, x, y, game, dy=0, delay=0.0):
        super().__init__(x, y, game)
        self.entering = False
        self._fx = float(self.rect.x)
        self._fy = float(self.rect.y)
        self._dy = dy
        self._delay = delay
        cross_time = (game.GAME_WIDTH + 80) / self.speed
        n_shots = random.choice([1, 2])
        self._shot_schedule = sorted(
            random.uniform(cross_time * 0.15, cross_time * 0.70)
            for _ in range(n_shots)
        )
        self._flight_time = 0.0

    def _build_image(self):
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        c = self.color
        bright = tuple(min(255, v + 70) for v in c)
        w, h = self.width, self.height
        body = [(0, h // 2), (w, 0), (w * 3 // 4, h // 2), (w, h)]
        pygame.draw.polygon(surf, c, body)
        pygame.draw.polygon(surf, bright, body, 2)
        pygame.draw.circle(surf, (255, 200, 120), (w - 4, h // 2), max(2, h // 6))
        return surf

    def update(self, dt):
        if self.game.paused:
            return
        if self._delay > 0:
            self._delay -= dt
            return
        self._flight_time += dt
        self._fx -= self.speed * dt
        self._fy += self._dy * dt
        self.rect.x = int(self._fx)
        self.rect.y = max(-10, min(self.game.GAME_HEIGHT + 10, int(self._fy)))

        while self._shot_schedule and self._flight_time >= self._shot_schedule[0]:
            self._shot_schedule.pop(0)
            self._shoot()

        if self.rect.right < -10:
            self.alive_flag = False
            self.kill()

    def _shoot(self):
        cx = self.rect.left
        cy = self.rect.centery
        self.game.enemy_projectiles.add(
            EnemyProjectile(cx, cy, -self.projectile_speed, 0, self.game,
                            size=self.projectile_size,
                            color=self.projectile_color)
        )


ENEMY_TYPES = [Drone, Fighter, Striker]
