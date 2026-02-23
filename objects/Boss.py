import pygame, os, math, random

from objects.Player import PLAYER_CENTER_OFFSET_X, PLAYER_CENTER_OFFSET_Y

BOSS_WIDTH, BOSS_HEIGHT = 150, 150
BOSS_BASE_HP = 20
HIT_COOLDOWN = 0.3
INVULN_PHASE_DURATION = 3.0
INVULN_THRESHOLDS = [0.75, 0.50, 0.25]
BOSS_DROP_THRESHOLDS = [0.67, 0.34]

ENTER_SPEED = 4
PATROL_LEFT_RATIO = 0.52
PATROL_RIGHT_RATIO = 0.85
PATROL_SPEED = 120
BOB_AMP = 70
BOB_SPEED = 2.2

ATTACK_INTERVAL = 2.0

SHIELD_RADIUS = 100
SHIELD_COLOR_BASE = (80, 180, 255)


LASER_CHARGE_DURATION = 0.7
LASER_ACTIVE_DURATION = 2.5
LASER_BEAM_SPEED = 300
LASER_BEAM_RADIUS = 7
LASER_EMIT_INTERVAL = 0.016
LASER_MAX_CONCURRENT = 2


class BossLaser:
    """A laser stream emitted from the boss that paints across the screen.

    Lifecycle: charging (warning glow) -> active (emitting segments) -> fading
    (segments fly off) -> done.

    Because the boss bobs vertically while emitting, the stream naturally
    forms a wavy pattern.  Players dodge by reading the wave and positioning
    between streams.
    """

    def __init__(self, boss, offset_y, game):
        self.boss = boss
        self.game = game
        self.offset_y = offset_y
        self.timer = 0.0
        self.emit_timer = 0.0
        self.phase = "charging"
        self.segments = []

    @property
    def done(self):
        return self.phase == "done"

    @property
    def active(self):
        return self.phase in ("active", "fading")

    def update(self, dt):
        if self.game.paused:
            return
        self.timer += dt

        if self.phase == "charging" and self.timer >= LASER_CHARGE_DURATION:
            self.phase = "active"
            self.timer = 0.0
            self.emit_timer = 0.0
        elif self.phase == "active" and self.timer >= LASER_ACTIVE_DURATION:
            self.phase = "fading"
        elif self.phase == "fading" and not self.segments:
            self.phase = "done"

        speed = LASER_BEAM_SPEED * dt
        self.segments = [(x - speed, y) for x, y in self.segments
                         if x - speed > -20]

        if self.phase == "active":
            self.emit_timer += dt
            while self.emit_timer >= LASER_EMIT_INTERVAL:
                self.emit_timer -= LASER_EMIT_INTERVAL
                bx = float(self.boss.rect.left)
                by = float(self.boss.rect.centery + self.offset_y)
                self.segments.append((bx, by))

    def draw(self, surface):
        if self.phase == "charging":
            self._draw_charge(surface)
        elif self.segments:
            self._draw_stream(surface)

    def _draw_charge(self, surface):
        progress = min(1.0, self.timer / LASER_CHARGE_DURATION)
        boss_left = self.boss.rect.left
        y = int(self.boss.rect.centery + self.offset_y)
        t = pygame.time.get_ticks() / 1000.0
        pulse = 0.5 + 0.5 * math.sin(t * 12)
        line_len = int(80 * progress)
        end_x = max(0, boss_left - line_len)
        la = max(60, int(200 * progress * pulse))
        pygame.draw.line(surface, (200, 0, 200), (boss_left, y), (end_x, y), 1)
        gr = int(10 * progress)
        if gr > 0:
            glow = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 100, 255, int(180 * progress)),
                               (gr, gr), gr)
            surface.blit(glow, (boss_left - gr, y - gr))

    def _draw_stream(self, surface):
        if len(self.segments) < 2:
            return
        pts = [(int(x), int(y)) for x, y in self.segments]
        r = LASER_BEAM_RADIUS
        pygame.draw.lines(surface, (100, 0, 100), False, pts, r * 2 + 4)
        pygame.draw.lines(surface, (220, 60, 220), False, pts, r + 2)
        pygame.draw.lines(surface, (255, 180, 255), False, pts, max(2, r // 2))
        if self.phase == "active" and self.segments:
            lx, ly = self.segments[-1]
            gr = 10
            glow = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 200, 255, 220), (gr, gr), gr)
            surface.blit(glow, (int(lx) - gr, int(ly) - gr))

    def hits_player(self, player):
        if not self.active or not self.segments:
            return False
        px, py = int(player.position_x), int(player.position_y)
        img = player.curr_image
        pr = pygame.Rect(px, py, img.get_width(), img.get_height())
        r = LASER_BEAM_RADIUS
        step = max(1, len(self.segments) // 50)
        for i in range(0, len(self.segments), step):
            sx, sy = self.segments[i]
            seg_rect = pygame.Rect(int(sx) - r, int(sy) - r, r * 2, r * 2)
            if pr.colliderect(seg_rect):
                return True
        return False


class BossProjectile(pygame.sprite.Sprite):
    """Projectile fired by the boss, moving toward the player."""

    def __init__(self, x, y, dx, dy, game, destroyable=True, size=12,
                 color=(255, 50, 50), width=None, height=None):
        super().__init__()
        self.game = game
        self.dx = dx
        self.dy = dy
        self.destroyable = destroyable
        w = width or size
        h = height or size
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        if width and height and width > height * 2:
            self._draw_laser(w, h, color)
        elif destroyable:
            r = min(w, h) // 2
            pygame.draw.circle(self.image, color, (w // 2, h // 2), r)
            bright = tuple(min(255, c + 80) for c in color[:3])
            pygame.draw.circle(self.image, bright, (w // 2, h // 2), max(1, r - 3))
        else:
            r = min(w, h) // 2
            pygame.draw.circle(self.image, (200, 0, 200), (w // 2, h // 2), r)
            pygame.draw.circle(self.image, (255, 100, 255), (w // 2, h // 2), max(1, r - 2))
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect(center=(x, y))

    def _draw_laser(self, w, h, color):
        glow = (*color[:3], 40)
        pygame.draw.rect(self.image, glow, (0, 0, w, h), border_radius=4)
        core_h = max(2, h // 2)
        core_y = (h - core_h) // 2
        bright = tuple(min(255, c + 100) for c in color[:3])
        pygame.draw.rect(self.image, bright, (0, core_y, w, core_h))
        center_y = h // 2
        pygame.draw.line(self.image, (255, 255, 255), (0, center_y), (w - 1, center_y), 1)

    def update(self):
        if self.game.paused:
            return
        self.rect.x += self.dx
        self.rect.y += self.dy
        if (self.rect.right < -20 or self.rect.left > self.game.GAME_WIDTH + 20
                or self.rect.bottom < -20 or self.rect.top > self.game.GAME_HEIGHT + 20):
            self.kill()


class Boss(pygame.sprite.Sprite):
    def __init__(self, game, attack_level=1, hp_override=None):
        super().__init__()
        self.game = game
        self.attack_level = min(attack_level, 4)

        self.max_hp = hp_override if hp_override else BOSS_BASE_HP
        self.hp = self.max_hp

        sprite_path = os.path.join(game.assets_dir, "enemies", "enemy_1.png")
        self._base_image = pygame.transform.scale(
            pygame.image.load(sprite_path).convert_alpha(),
            (BOSS_WIDTH, BOSS_HEIGHT),
        )
        self.image = self._base_image.copy()
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()

        self.rect.x = game.GAME_WIDTH + 20
        self.rect.centery = game.GAME_HEIGHT // 2
        self.patrol_left = int(game.GAME_WIDTH * PATROL_LEFT_RATIO) - BOSS_WIDTH // 2
        self.patrol_right = int(game.GAME_WIDTH * PATROL_RIGHT_RATIO) - BOSS_WIDTH // 2
        self.park_x = self.patrol_right
        self.entering = True
        self.patrol_dir = -1

        self.bob_timer = 0
        self.base_y = float(self.rect.centery)

        self.hit_cooldown = 0
        self.invuln_timer = 0
        self._triggered_thresholds = set()
        self._triggered_drops = set()
        self._pending_drops = []

        self.attack_timer = ATTACK_INTERVAL
        self.attack_cycle = 0

        self.alive_flag = True
        self.boss_projectiles = pygame.sprite.Group()
        self.boss_lasers = []

    @property
    def is_invulnerable(self):
        return self.hit_cooldown > 0 or self.invuln_timer > 0

    def take_damage(self, amount=1):
        if self.is_invulnerable or not self.alive_flag:
            return False
        self.hp = max(0, self.hp - amount)
        self.hit_cooldown = HIT_COOLDOWN

        ratio = self.hp / self.max_hp
        for threshold in INVULN_THRESHOLDS:
            if ratio <= threshold and threshold not in self._triggered_thresholds:
                self._triggered_thresholds.add(threshold)
                self.invuln_timer = INVULN_PHASE_DURATION
                break

        for drop_t in BOSS_DROP_THRESHOLDS:
            if ratio <= drop_t and drop_t not in self._triggered_drops:
                self._triggered_drops.add(drop_t)
                self._pending_drops.append(drop_t)

        if self.hp <= 0:
            self.alive_flag = False
        return True

    def pop_pending_drops(self):
        """Return and clear any drop events triggered since last check."""
        drops = list(self._pending_drops)
        self._pending_drops.clear()
        return drops

    def update(self, dt):
        if not self.alive_flag:
            return

        if self.hit_cooldown > 0:
            self.hit_cooldown = max(0, self.hit_cooldown - dt)
        if self.invuln_timer > 0:
            self.invuln_timer = max(0, self.invuln_timer - dt)

        if self.entering:
            self.rect.x -= ENTER_SPEED
            if self.rect.x <= self.park_x:
                self.rect.x = self.park_x
                self.entering = False
                self.base_y = float(self.rect.centery)
            return

        # Horizontal patrol
        self.rect.x += int(self.patrol_dir * PATROL_SPEED * dt)
        if self.rect.x <= self.patrol_left:
            self.rect.x = self.patrol_left
            self.patrol_dir = 1
        elif self.rect.x >= self.patrol_right:
            self.rect.x = self.patrol_right
            self.patrol_dir = -1

        # Vertical bob
        self.bob_timer += dt
        self.rect.centery = int(self.base_y + BOB_AMP * math.sin(BOB_SPEED * self.bob_timer))

        self.attack_timer -= dt
        if self.attack_timer <= 0:
            self._do_attack()
            self.attack_timer = ATTACK_INTERVAL

        self.boss_projectiles.update()

        for laser in self.boss_lasers:
            laser.update(dt)
        self.boss_lasers = [l for l in self.boss_lasers if not l.done]

    # ---- attacks ----

    _ATTACK_POOLS = {
        1: ["aimed_burst", "shotgun_fan", "wall_with_gap"],
        2: ["laser_sweep", "laser_cross"],
        3: ["rock_barrage"],
        4: ["spiral_storm", "ring_pulse"],
    }

    def _do_attack(self):
        available_tiers = list(range(1, self.attack_level + 1))
        tier = available_tiers[self.attack_cycle % len(available_tiers)]
        self.attack_cycle += 1
        pool = self._ATTACK_POOLS[tier]
        name = random.choice(pool)
        getattr(self, f"_attack_{name}")()

    def _player_center(self):
        best_dist = float("inf")
        best = (self.game.GAME_WIDTH // 4, self.game.GAME_HEIGHT // 2)
        cx, cy = self.rect.centerx, self.rect.centery
        for p in self.game.players:
            if not p.alive:
                continue
            px = p.position_x + PLAYER_CENTER_OFFSET_X
            py = p.position_y + PLAYER_CENTER_OFFSET_Y
            d = (px - cx) ** 2 + (py - cy) ** 2
            if d < best_dist:
                best_dist = d
                best = (px, py)
        return best

    # -- Tier 1: destroyable projectile patterns --

    def _attack_aimed_burst(self):
        """Three rapid bursts of 5 aimed projectiles."""
        cx, cy = self.rect.left, self.rect.centery
        px, py = self._player_center()
        for burst in range(3):
            for i in range(-2, 3):
                angle = math.atan2(py - cy + i * 25, px - cx)
                speed = 4.5 + burst * 0.5
                self.boss_projectiles.add(
                    BossProjectile(
                        cx - burst * 8, cy, speed * math.cos(angle),
                        speed * math.sin(angle), self.game,
                        destroyable=True, size=10, color=(255, 80, 80),
                    )
                )

    def _attack_shotgun_fan(self):
        """Wide fan of 9 projectiles in an arc."""
        cx, cy = self.rect.left, self.rect.centery
        px, py = self._player_center()
        base_angle = math.atan2(py - cy, px - cx)
        for i in range(9):
            a = base_angle + math.radians(-40 + i * 10)
            speed = 3.5
            self.boss_projectiles.add(
                BossProjectile(
                    cx, cy, speed * math.cos(a), speed * math.sin(a),
                    self.game, destroyable=True, size=9,
                    color=(255, 140, 40),
                )
            )

    def _attack_wall_with_gap(self):
        """Vertical wall of projectiles with a gap at the player's Y."""
        cx = self.rect.left
        _, py = self._player_center()
        gap_y = py + random.randint(-40, 40)
        gap_half = 45
        for y in range(20, self.game.GAME_HEIGHT - 20, 30):
            if abs(y - gap_y) < gap_half:
                continue
            self.boss_projectiles.add(
                BossProjectile(
                    cx, y, -4, 0, self.game,
                    destroyable=True, size=10, color=(255, 200, 60),
                )
            )

    # -- Tier 2: laser streams emitted from the boss --

    def _laser_slots_free(self):
        return LASER_MAX_CONCURRENT - len(self.boss_lasers)

    def _attack_laser_sweep(self):
        """One or two streams — player dodges through the middle."""
        slots = self._laser_slots_free()
        if slots >= 2 and random.random() < 0.5:
            offsets = [-70, 70]
        else:
            offsets = [random.choice([-70, 0, 70])]
        for off in offsets[:slots]:
            self.boss_lasers.append(BossLaser(self, off, self.game))

    def _attack_laser_cross(self):
        """One or two wide-spread streams — dodge through the middle."""
        slots = self._laser_slots_free()
        if slots >= 2 and random.random() < 0.5:
            offsets = [-90, 90]
        else:
            offsets = [random.choice([-90, 0, 90])]
        for off in offsets[:slots]:
            self.boss_lasers.append(BossLaser(self, off, self.game))

    # -- Tier 3: rock throw --

    def _attack_rock_barrage(self):
        """Throw a burst of rocks at the player."""
        cx, cy = self.rect.left, self.rect.centery
        from objects.Rocks import Rock, BASIC
        for _ in range(random.randint(3, 5)):
            dy = random.uniform(-4, 4)
            dx = random.uniform(-6, -3)
            sz = random.randint(20, 40)
            rock = Rock(cx, cy + random.randint(-50, 50), sz, sz, self.game,
                        rock_type=BASIC, dx=dx, dy=dy)
            self.game.rocks.add(rock)

    # -- Tier 4: overwhelming patterns --

    def _attack_spiral_storm(self):
        """Rotating spiral of destroyable projectiles."""
        cx, cy = self.rect.centerx, self.rect.centery
        arms = 4
        bullets_per_arm = 6
        for arm in range(arms):
            base = (2 * math.pi / arms) * arm + self.attack_cycle * 0.3
            for j in range(bullets_per_arm):
                a = base + j * 0.18
                speed = 2.5 + j * 0.4
                self.boss_projectiles.add(
                    BossProjectile(
                        cx, cy, speed * math.cos(a), speed * math.sin(a),
                        self.game, destroyable=True, size=8,
                        color=(255, 160, 30),
                    )
                )

    def _attack_ring_pulse(self):
        """Two concentric rings fired outward with offset gaps."""
        cx, cy = self.rect.centerx, self.rect.centery
        for ring in range(2):
            offset = ring * 15
            count = 16
            speed = 3 + ring * 1.5
            for i in range(count):
                a = math.radians(i * (360 / count) + offset)
                self.boss_projectiles.add(
                    BossProjectile(
                        cx, cy, speed * math.cos(a), speed * math.sin(a),
                        self.game, destroyable=True, size=7,
                        color=(100, 255, 100) if ring == 0 else (255, 100, 100),
                    )
                )

    # ---- drawing ----

    def draw(self, surface):
        if not self.alive_flag:
            return

        if self.invuln_timer > 0:
            self._draw_shield_bubble(surface)

        for laser in self.boss_lasers:
            laser.draw(surface)

        surface.blit(self.image, self.rect)
        self.boss_projectiles.draw(surface)
        self._draw_health_bar(surface)

    def _draw_shield_bubble(self, surface):
        cx, cy = self.rect.centerx, self.rect.centery
        t = pygame.time.get_ticks() / 1000
        pulse = 0.85 + 0.15 * math.sin(t * 4)
        radius = int(SHIELD_RADIUS * pulse)

        shield_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        r, g, b = SHIELD_COLOR_BASE
        pygame.draw.circle(shield_surf, (r, g, b, 50), (radius, radius), radius)
        pygame.draw.circle(shield_surf, (r, g, b, 90), (radius, radius),
                           int(radius * 0.85), 3)
        pygame.draw.circle(shield_surf, (200, 230, 255, 120), (radius, radius),
                           radius, 2)
        surface.blit(shield_surf, (cx - radius, cy - radius))

    def _draw_health_bar(self, surface):
        bar_w = BOSS_WIDTH + 20
        bar_h = 10
        x = self.rect.centerx - bar_w // 2
        y = self.rect.top - 20
        pygame.draw.rect(surface, (60, 60, 60), (x - 1, y - 1, bar_w + 2, bar_h + 2))
        pygame.draw.rect(surface, (80, 0, 0), (x, y, bar_w, bar_h))
        fill_w = max(0, int(bar_w * self.hp / self.max_hp))
        if self.invuln_timer > 0:
            color = (80, 180, 255)
        else:
            color = (220, 30, 30) if self.hp / self.max_hp < 0.3 else (30, 200, 30)
        pygame.draw.rect(surface, color, (x, y, fill_w, bar_h))
