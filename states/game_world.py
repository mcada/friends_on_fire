import pygame, random, math
from states.state import State
from objects.Rocks import Rock, BASIC, CLUSTER, IRON, BLACKHOLE
from objects.Pickup import UpgradePickup, ShieldPickup
from objects.Weapon import StraightCannon, SECONDARY_WEAPONS
from objects.Boss import Boss, BossProjectile, BOSS_BASE_HP
from objects.Enemy import Drone, Fighter, Striker, ENEMY_TYPES
from objects.Player import PLAYER_CENTER_OFFSET_X, PLAYER_CENTER_OFFSET_Y, MAX_LIVES

BASE_UPGRADE_CHANCE = 0.07
UPGRADE_CHANCE_DECAY = 0.35
ENEMY_UPGRADE_CHANCE = 0.25
ENEMY_SECONDARY_WEIGHT = 0.55

SHIELD_BASE_CHANCE = 0.02
SHIELD_PITY_FACTOR = 15

LEVEL_DURATION = 120.0
BOSS_COUNTDOWN = 3.0

ENEMY_FIRST_SPAWN = 8.0
ENEMY_SPAWN_INTERVAL = 10.0
ENEMY_MIN_INTERVAL = 4.0
ENEMY_INTERVAL_DECAY = 0.15
DRONE_MAX = 8
FIGHTER_MAX = 3
FIGHTER_UNLOCK_TIME = 35.0
STRIKER_MAX = 2
STRIKER_UNLOCK_TIME = 60.0

DRONE_WAVE_CHANCE = 0.35

TIER1_PATTERNS = ["line", "v", "diagonal"]
TIER2_PATTERNS = TIER1_PATTERNS + ["column", "stagger", "arrow"]
TIER3_PATTERNS = TIER2_PATTERNS + ["pincer", "spiral", "cross"]

FORMATION_TIERS = [
    (0,   TIER1_PATTERNS, 3, 5),
    (60,  TIER2_PATTERNS, 4, 6),
    (120, TIER3_PATTERNS, 5, 8),
]


class Particle:
    def __init__(self, x, y):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(60, 220)
        self.x, self.y = float(x), float(y)
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed
        self.lifetime = random.uniform(0.25, 0.5)
        self.age = 0
        self.color = random.choice([
            (255, 200, 50), (255, 150, 30), (255, 100, 20),
            (200, 180, 160), (180, 160, 140),
        ])
        self.size = random.uniform(2, 5)

    def update(self, dt):
        self.x += self.dx * dt
        self.y += self.dy * dt
        self.age += dt
        return self.age < self.lifetime

    def draw(self, surface):
        remaining = 1 - self.age / self.lifetime
        size = max(1, int(self.size * remaining))
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), size)


SUCKIN_DURATION = 0.8


class SuckInEffect:
    """Animated effect: a ship sprite spirals and shrinks into a black hole."""

    def __init__(self, sprite, start_x, start_y, target_x, target_y):
        self.sprite = sprite.copy()
        self.start_x, self.start_y = float(start_x), float(start_y)
        self.target_x, self.target_y = float(target_x), float(target_y)
        self.age = 0.0
        self.orig_w = sprite.get_width()
        self.orig_h = sprite.get_height()
        self._initial_angle = math.atan2(target_y - start_y, target_x - start_x)

    def update(self, dt):
        self.age += dt
        return self.age < SUCKIN_DURATION

    def draw(self, surface):
        t = min(1.0, self.age / SUCKIN_DURATION)
        ease = t * t * (3 - 2 * t)

        x = self.start_x + (self.target_x - self.start_x) * ease
        y = self.start_y + (self.target_y - self.start_y) * ease

        scale = max(0.05, 1.0 - ease)
        w = max(1, int(self.orig_w * scale))
        h = max(1, int(self.orig_h * scale))

        rotation = t * 720
        scaled = pygame.transform.scale(self.sprite, (w, h))
        rotated = pygame.transform.rotate(scaled, rotation)

        alpha = max(0, int(255 * (1.0 - ease * ease)))
        rotated.set_alpha(alpha)

        rect = rotated.get_rect(center=(int(x), int(y)))
        surface.blit(rotated, rect)


class Game_World(State):
    def __init__(self, game, game_mode="endless", level_num=0):
        State.__init__(self, game)
        self.game.active_game_world = self
        self.game_mode = game_mode
        self.level_num = level_num
        self.background = self.game.background
        self.elapsed_time = 0
        self.rock_spawn_timer = 0
        self.rock_spawn_interval = 1.8
        self.game_over = False
        self.level_won = False
        self.is_new_record = False
        self.asteroids_killed = 0
        self.particles = []

        self.upgrade_count = 0
        self.upgrade_msg = ""
        self.upgrade_msg_timer = 0

        self.kills_since_shield = 0
        self.total_kills_ever = 0

        self.boss = None
        self.boss_phase = False
        self.boss_countdown = 0
        self.boss_encounter = 0
        self.next_boss_time = LEVEL_DURATION
        self._boss_challenge_started = False

        self.enemy_spawn_timer = 0
        self.enemy_spawn_interval = ENEMY_SPAWN_INTERVAL
        self._enemies_started = False

        self.game.rocks.empty()
        self.game.projectiles.empty()
        self.game.pickups.empty()
        self.game.enemies.empty()
        self.game.enemy_projectiles.empty()
        self.game.setup_players(self.game.num_players)
        for player in self.game.players:
            player.reset()
            if self.game_mode == "testing":
                for weapon_cls in SECONDARY_WEAPONS:
                    player.set_secondary(weapon_cls)
                player.has_shield = True
        if self.game_mode == "testing":
            self.next_boss_time = 45
            self._enemies_started = True
            self._spawn_enemy()
            bh_x = self.game.GAME_WIDTH * 0.7
            bh_y = self.game.GAME_HEIGHT / 2
            self.game.rocks.add(
                Rock(bh_x, bh_y, 16, 16, self.game, rock_type=BLACKHOLE, dx=-0.75)
            )
        self.game.play_music("game")

    # ---- asteroid type selection ----

    def _pick_asteroid_type(self):
        if self.game_mode == "level":
            return self._pick_asteroid_type_level()
        return self._pick_asteroid_type_endless()

    def _pick_asteroid_type_endless(self):
        t = self.elapsed_time
        cluster_w = min(0.35, max(0, (t - 20) * 0.006))
        iron_w = min(0.30, max(0, (t - 45) * 0.004))
        bh_w = min(0.04, max(0, (t - 70) * 0.0005))
        r = random.random()
        if r < bh_w:
            return BLACKHOLE
        r2 = (r - bh_w) / (1 - bh_w) if bh_w < 1 else 0
        if r2 < 1 - cluster_w - iron_w:
            return BASIC
        if r2 < 1 - iron_w:
            return CLUSTER
        return IRON

    def _pick_asteroid_type_level(self):
        t = self.elapsed_time
        if self.level_num == 1:
            return BASIC
        elif self.level_num == 2:
            cluster_w = 0.15 + min(0.40, t * 0.005)
            if random.random() < cluster_w:
                return CLUSTER
            return BASIC
        else:
            bh_w = min(0.03, max(0, (t - 50) * 0.0004))
            if random.random() < bh_w:
                return BLACKHOLE
            cluster_w = 0.20 + min(0.30, t * 0.004)
            iron_w = 0.10 + min(0.25, t * 0.003)
            r = random.random()
            if r < 1 - cluster_w - iron_w:
                return BASIC
            if r < 1 - iron_w:
                return CLUSTER
            return IRON

    def _spawn_asteroid(self):
        rtype = self._pick_asteroid_type()
        x = self.game.GAME_WIDTH + random.randint(0, 200)
        y = random.randint(25, self.game.GAME_HEIGHT - 25)
        if rtype == BLACKHOLE:
            dx = random.uniform(-1.8, -0.9)
            self.game.rocks.add(Rock(x, y, 16, 16, self.game, rock_type=rtype, dx=dx))
            return
        if rtype == CLUSTER:
            w = random.randint(50, 80)
            h = random.randint(45, 75)
            dx = random.uniform(-3.0, -1.5)
        elif rtype == IRON:
            w = random.randint(40, 70)
            h = random.randint(38, 65)
            dx = random.uniform(-2.0, -1.0)
        else:
            w = random.randint(12, 55)
            h = random.randint(12, 50)
            dx = random.uniform(-4.0, -2.0)
        self.game.rocks.add(Rock(x, y, w, h, self.game, rock_type=rtype, dx=dx))

    def _max_rocks(self):
        base = 8
        if self.game_mode == "level":
            base = 6 + self.level_num * 2
        return base + int(self.elapsed_time * 0.05)

    def _spawn_batch(self):
        if self.game_mode == "level":
            base = self.level_num
            return min(base + int(self.elapsed_time // 40), 2)
        return min(1 + int(self.elapsed_time // 50), 2)

    def _min_spawn_interval(self):
        if self.game_mode == "level":
            return max(0.6, 0.9 - self.level_num * 0.05)
        return 0.7

    def _spawn_decay(self):
        if self.game_mode == "level":
            return 0.005 + self.level_num * 0.002
        return 0.006

    def _spawn_fragments(self, rock):
        if len(self.game.rocks) >= self._max_rocks():
            return
        cx, cy = rock.rect.centerx, rock.rect.centery
        for _ in range(random.randint(2, 3)):
            dx = random.randint(-6, -2)
            dy = random.randint(-4, 4)
            sz = random.randint(10, 18)
            frag = Rock(cx, cy, sz, sz, self.game, rock_type=BASIC, dx=dx, dy=dy)
            self.game.rocks.add(frag)

    # ---- black hole gravity ----

    def _update_black_hole_gravity(self, dt):
        black_holes = [r for r in self.game.rocks if r.rock_type == BLACKHOLE]
        if not black_holes:
            return

        for bh in black_holes:
            bcx, bcy = bh._fx, bh._fy
            gr = bh.gravity_radius
            gs = bh.gravity_strength
            eat_r = bh.consume_radius

            for player in self.game.players:
                if not player.alive:
                    continue
                dx = bcx - player.position_x
                dy = bcy - player.position_y
                dist = max(1.0, math.hypot(dx, dy))
                if dist < eat_r + 4:
                    self._kill_player_blackhole(player, bh)
                    continue
                if dist < gr:
                    pull = gs * dt * (1 - dist / gr) ** 2
                    player.position_x += pull * dx / dist
                    player.position_y += pull * dy / dist

            for proj in list(self.game.projectiles):
                dx = bcx - proj.rect.centerx
                dy = bcy - proj.rect.centery
                dist = max(1.0, math.hypot(dx, dy))
                if dist < gr:
                    pull = gs * 0.7 * dt * (1 - dist / gr)
                    proj.rect.x += int(pull * dx / dist)
                    proj.rect.y += int(pull * dy / dist)
                if dist < eat_r:
                    proj.kill()
                    bh.feed(0.3)

            for proj in list(self.game.enemy_projectiles):
                dx = bcx - proj.rect.centerx
                dy = bcy - proj.rect.centery
                dist = max(1.0, math.hypot(dx, dy))
                if dist < gr:
                    pull = gs * 0.7 * dt * (1 - dist / gr)
                    proj.rect.x += int(pull * dx / dist)
                    proj.rect.y += int(pull * dy / dist)
                if dist < eat_r:
                    proj.kill()
                    bh.feed(0.3)

            for pickup in list(self.game.pickups):
                dx = bcx - pickup._fx
                dy = bcy - pickup._fy
                dist = max(1.0, math.hypot(dx, dy))
                if dist < gr:
                    pull = gs * 0.8 * dt * (1 - dist / gr)
                    pickup._fx += pull * dx / dist
                    pickup._base_fy += pull * dy / dist
                if dist < eat_r:
                    pickup.kill()
                    bh.feed(0.5)

            for rock in list(self.game.rocks):
                if rock is bh or rock.rock_type == BLACKHOLE:
                    continue
                dx = bcx - rock._fx
                dy = bcy - rock._fy
                dist = max(1.0, math.hypot(dx, dy))
                if dist < gr * 0.8:
                    pull = gs * 0.4 * dt * (1 - dist / (gr * 0.8))
                    rock._fx += pull * dx / dist
                    rock._fy += pull * dy / dist
                if dist < eat_r + 10:
                    self.spawn_particles(rock.rect.centerx, rock.rect.centery, count=5)
                    rock.kill()
                    bh.feed(1.0)

    # ---- upgrade helpers ----

    def _upgrade_chance(self):
        return BASE_UPGRADE_CHANCE / (1 + self.upgrade_count * UPGRADE_CHANCE_DECAY)

    def _should_spawn_upgrade(self):
        return random.random() < self._upgrade_chance()

    def _should_spawn_enemy_upgrade(self):
        return random.random() < ENEMY_UPGRADE_CHANCE

    @staticmethod
    def _random_enemy_pickup_type():
        """Enemies can drop primary or secondary upgrades."""
        if random.random() < (1 - ENEMY_SECONDARY_WEIGHT):
            return None
        return random.choice(SECONDARY_WEAPONS)

    def _apply_upgrade(self, pickup, player):
        weapon_cls = pickup.weapon_cls

        if weapon_cls is None:
            if player.primary.upgrade():
                self.upgrade_msg = f"Primary Lv{player.primary.level}"
            else:
                self.upgrade_msg = "Primary MAX!"
        elif player.secondary and isinstance(player.secondary, weapon_cls):
            if player.upgrade_secondary():
                self.upgrade_msg = f"{player.secondary.name} Lv{player.secondary.level}"
            else:
                self.upgrade_msg = f"{player.secondary.name} MAX!"
        else:
            had_before = weapon_cls in player.secondary_levels
            player.set_secondary(weapon_cls)
            if had_before:
                if player.upgrade_secondary():
                    self.upgrade_msg = f"{player.secondary.name} Lv{player.secondary.level}"
                else:
                    self.upgrade_msg = f"{player.secondary.name} MAX!"
            else:
                self.upgrade_msg = f"{player.secondary.name} Lv{player.secondary.level}"

        self.upgrade_count += 1
        self.upgrade_msg_timer = 2.0

    # ---- shield helpers ----

    def _shield_chance(self):
        return SHIELD_BASE_CHANCE * (1 + self.kills_since_shield / SHIELD_PITY_FACTOR)

    def _should_spawn_shield(self):
        if all(p.has_shield for p in self.game.players if p.alive):
            return False
        if self.total_kills_ever == 1:
            return True
        return random.random() < self._shield_chance()

    # ---- boss helpers ----

    def _should_spawn_boss(self):
        if self.game_mode == "boss_challenge":
            return not self._boss_challenge_started
        if self.game_mode == "level":
            return self.elapsed_time >= LEVEL_DURATION
        return self.elapsed_time >= self.next_boss_time

    def _boss_attack_level(self):
        if self.game_mode in ("boss_challenge", "testing"):
            return 4
        if self.game_mode == "level":
            return self.level_num
        return min(self.boss_encounter + 1, 4)

    def _boss_hp(self):
        if self.game_mode == "boss_challenge":
            return BOSS_BASE_HP + 3 * 10
        if self.game_mode == "level":
            return BOSS_BASE_HP + (self.level_num - 1) * 10
        return BOSS_BASE_HP + self.boss_encounter * 15

    def _begin_boss_countdown(self):
        """Stop spawning and start the countdown before the boss enters."""
        self.boss_phase = True
        self._boss_challenge_started = True
        if self.game_mode == "boss_challenge":
            self.boss_countdown = 0
            self._start_boss()
        else:
            self.boss_countdown = BOSS_COUNTDOWN

    def _start_boss(self):
        """Actually spawn the boss after the countdown expires."""
        self.boss_countdown = 0
        self.boss = Boss(self.game,
                         attack_level=self._boss_attack_level(),
                         hp_override=self._boss_hp())

    def _on_boss_defeated(self):
        from objects.Player import HIT_INVULN_DURATION
        self.spawn_particles(self.boss.rect.centerx, self.boss.rect.centery, count=30)
        self.game.play_boss_death_sound()
        self.boss.boss_projectiles.empty()
        self.boss.boss_lasers.clear()
        self.boss = None
        self.boss_phase = False
        self.boss_encounter += 1
        for player in self.game.players:
            was_dead = not player.alive
            player.alive = True
            player.lives = MAX_LIVES
            player.hit_invuln = HIT_INVULN_DURATION
            if was_dead:
                player.position_x = 100
                player.position_y = player._default_y()
        if self.game_mode in ("level", "boss_challenge"):
            self.level_won = True
            self.game.reset_keys()
            self.game.stop_music()
        else:
            self.next_boss_time = self.elapsed_time + LEVEL_DURATION
            self.game.play_music("game")

    # ---- enemies ----

    def _count_enemies_by_type(self):
        drones = sum(1 for e in self.game.enemies if isinstance(e, Drone))
        fighters = sum(1 for e in self.game.enemies if isinstance(e, Fighter))
        strikers = sum(1 for e in self.game.enemies if isinstance(e, Striker))
        return drones, fighters, strikers

    def _spawn_enemy(self):
        drones, fighters, strikers = self._count_enemies_by_type()

        can_drone = drones < DRONE_MAX
        can_fighter = (self.elapsed_time >= FIGHTER_UNLOCK_TIME
                       and fighters < FIGHTER_MAX)
        can_striker = (self.elapsed_time >= STRIKER_UNLOCK_TIME
                       and strikers < STRIKER_MAX)

        if can_drone and random.random() < DRONE_WAVE_CHANCE:
            self._spawn_drone_wave()
            return

        candidates, weights = [], []
        if can_drone:
            candidates.append(Drone); weights.append(3)
        if can_fighter:
            candidates.append(Fighter); weights.append(2)
        if can_striker:
            candidates.append(Striker); weights.append(1)
        if not candidates:
            return

        enemy_cls = random.choices(candidates, weights=weights)[0]
        x = self.game.GAME_WIDTH + 40
        y = random.randint(40, self.game.GAME_HEIGHT - 40)
        self.game.enemies.add(enemy_cls(x, y, self.game))

    def _formation_tier(self):
        for threshold, patterns, lo, hi in reversed(FORMATION_TIERS):
            if self.elapsed_time >= threshold:
                return patterns, lo, hi
        return TIER1_PATTERNS, 3, 5

    def _spawn_drone_wave(self):
        drones_now = sum(1 for e in self.game.enemies if isinstance(e, Drone))
        slots = DRONE_MAX - drones_now
        patterns, wave_min, wave_max = self._formation_tier()
        count = min(random.randint(wave_min, wave_max), slots)
        if count <= 0:
            return
        pattern = random.choice(patterns)

        W = self.game.GAME_WIDTH
        H = self.game.GAME_HEIGHT
        base_x = W + 40
        sx, sy = 40, 30

        if pattern == "line":
            base_y = random.randint(60, H - 60)
            for i in range(count):
                self._add_drone(base_x + i * sx, base_y)

        elif pattern == "v":
            base_y = random.randint(80, H - 80)
            for i in range(count):
                row = abs(i - count // 2)
                dy = (i - count // 2) * sy
                self._add_drone(base_x + row * sx, base_y + dy)

        elif pattern == "diagonal":
            base_y = random.randint(60, H - 60)
            for i in range(count):
                dy = i * sy - (count * sy) // 2
                self._add_drone(base_x + i * sx, base_y + dy)

        elif pattern == "column":
            base_y = H // 2 - (count - 1) * sy // 2
            for i in range(count):
                self._add_drone(base_x, base_y + i * sy)

        elif pattern == "stagger":
            base_y = random.randint(80, H - 80)
            for i in range(count):
                offset_y = ((-1) ** i) * ((i + 1) // 2) * sy
                self._add_drone(base_x + i * sx, base_y + offset_y)

        elif pattern == "arrow":
            base_y = random.randint(80, H - 80)
            for i in range(count):
                mid = count // 2
                if i <= mid:
                    dy = (i - mid) * sy
                    dx = (mid - i) * sx
                else:
                    dy = (i - mid) * sy
                    dx = (i - mid) * sx
                self._add_drone(base_x + dx, base_y + dy)

        elif pattern == "pincer":
            half = count // 2
            remainder = count - half
            top_y = random.randint(30, 80)
            bot_y = random.randint(H - 80, H - 30)
            mid_y = H // 2
            fly_dy_top = (mid_y - top_y) / ((W + 80) / 150) * 0.5
            fly_dy_bot = (mid_y - bot_y) / ((W + 80) / 150) * 0.5
            for i in range(half):
                self._add_drone(base_x + i * sx, top_y, dy=fly_dy_top)
            for i in range(remainder):
                self._add_drone(base_x + i * sx, bot_y, dy=fly_dy_bot)

        elif pattern == "spiral":
            center_y = H // 2
            radius = min(120, H // 3)
            for i in range(count):
                angle = (i / count) * math.pi * 1.5
                offset_y = int(radius * math.sin(angle))
                delay = i * 0.25
                self._add_drone(base_x + i * sx, center_y + offset_y, delay=delay)

        elif pattern == "cross":
            half = count // 2
            remainder = count - half
            top_y = random.randint(30, 60)
            bot_y = random.randint(H - 60, H - 30)
            cross_dy = (H // 2 - top_y) / ((W + 80) / 150) * 0.7
            for i in range(half):
                self._add_drone(base_x + i * sx, top_y, dy=cross_dy)
            for i in range(remainder):
                self._add_drone(base_x + i * sx, bot_y, dy=-cross_dy)

    def _add_drone(self, x, y, dy=0, delay=0.0):
        H = self.game.GAME_HEIGHT
        y = max(20, min(H - 20, int(y)))
        self.game.enemies.add(Drone(x, y, self.game, dy=dy, delay=delay))

    def _update_enemy_combat(self):
        """Player projectiles vs enemies (HP-based, same pattern as rocks)."""
        if not self.game.enemies:
            return

        normal_group = pygame.sprite.Group()
        piercing_group = pygame.sprite.Group()
        for p in self.game.projectiles:
            (piercing_group if p.piercing else normal_group).add(p)

        hits_normal = pygame.sprite.groupcollide(
            normal_group, self.game.enemies, True, False,
            collided=pygame.sprite.collide_mask,
        )
        hits_piercing = pygame.sprite.groupcollide(
            piercing_group, self.game.enemies, False, False,
            collided=pygame.sprite.collide_mask,
        )

        enemy_damage = {}
        enemy_killers = {}
        for proj, enemies_hit in hits_normal.items():
            for enemy in enemies_hit:
                enemy_damage[enemy] = enemy_damage.get(enemy, 0) + getattr(proj, "damage", 1)
                if proj.owner:
                    enemy_killers[enemy] = proj.owner
        for proj, enemies_hit in hits_piercing.items():
            for enemy in enemies_hit:
                enemy_damage[enemy] = enemy_damage.get(enemy, 0) + getattr(proj, "damage", 1)
                if proj.owner:
                    enemy_killers[enemy] = proj.owner

        for enemy, dmg in enemy_damage.items():
            enemy.take_damage(dmg)
            if not enemy.alive_flag:
                self.spawn_particles(enemy.rect.centerx, enemy.rect.centery, count=10)
                self.asteroids_killed += enemy.score_value
                self.total_kills_ever += enemy.score_value
                self.kills_since_shield += enemy.score_value
                killer = enemy_killers.get(enemy)
                if killer:
                    killer.kills += enemy.score_value
                if self._should_spawn_shield():
                    self.game.pickups.add(
                        ShieldPickup(enemy.rect.centerx, enemy.rect.centery,
                                     self.game)
                    )
                    self.kills_since_shield = 0
                elif self._should_spawn_enemy_upgrade():
                    wtype = self._random_enemy_pickup_type()
                    self.game.pickups.add(
                        UpgradePickup(enemy.rect.centerx, enemy.rect.centery,
                                      wtype, self.game)
                    )
                enemy.kill()

        if any(not e.alive_flag for e in enemy_damage):
            self.game.play_sound("explosion")

    def _update_projectile_vs_projectile(self):
        """Player projectiles destroy enemy projectiles on contact."""
        if not self.game.enemy_projectiles or not self.game.projectiles:
            return
        hits = pygame.sprite.groupcollide(
            self.game.projectiles, self.game.enemy_projectiles,
            False, True,
            collided=pygame.sprite.collide_mask,
        )
        for proj in hits:
            if not proj.piercing:
                proj.kill()

    # ---- boss ----

    def _update_boss_combat(self):
        if not self.boss or not self.boss.alive_flag:
            return

        # Player projectiles vs boss (play hit sound at most once per frame)
        normal_group = pygame.sprite.Group()
        piercing_group = pygame.sprite.Group()
        for p in self.game.projectiles:
            (piercing_group if p.piercing else normal_group).add(p)

        boss_hit_this_frame = False
        for proj in list(normal_group):
            offset = (self.boss.rect.x - proj.rect.x, self.boss.rect.y - proj.rect.y)
            if proj.mask.overlap(self.boss.mask, offset):
                if self.boss.take_damage(getattr(proj, "damage", 1)):
                    boss_hit_this_frame = True
                proj.kill()

        for proj in list(piercing_group):
            offset = (self.boss.rect.x - proj.rect.x, self.boss.rect.y - proj.rect.y)
            if proj.mask.overlap(self.boss.mask, offset):
                if self.boss.take_damage(getattr(proj, "damage", 1)):
                    boss_hit_this_frame = True

        if boss_hit_this_frame:
            self.game.play_sound("explosion")

        for _drop_t in self.boss.pop_pending_drops():
            drop_x = self.boss.rect.left - 20
            drop_y = self.boss.rect.centery + random.randint(-40, 40)
            wtype = random.choice(SECONDARY_WEAPONS)
            self.game.pickups.add(
                UpgradePickup(drop_x, drop_y, wtype, self.game)
            )
            self.upgrade_msg = f"Boss dropped {wtype.name}!"
            self.upgrade_msg_timer = 2.5
            self.game.play_sound("powerup")

        # Player projectiles vs destroyable boss projectiles
        destroyable = pygame.sprite.Group(
            [bp for bp in self.boss.boss_projectiles if bp.destroyable]
        )
        pygame.sprite.groupcollide(
            self.game.projectiles, destroyable, True, True,
            collided=pygame.sprite.collide_mask,
        )

        # Boss projectiles vs players
        for player in self.game.players:
            if not player.alive:
                continue
            px, py = int(player.position_x), int(player.position_y)
            for bp in list(self.boss.boss_projectiles):
                if player.hit_invuln > 0:
                    break
                offset = (bp.rect.x - px, bp.rect.y - py)
                if player.mask.overlap(bp.mask, offset):
                    bp.kill()
                    if not self._damage_player(player) and self.game_over:
                        return

            # Boss lasers vs player
            if not player.alive or player.hit_invuln > 0:
                continue
            for laser in self.boss.boss_lasers:
                if player.hit_invuln > 0:
                    break
                if laser.hits_player(player):
                    if not self._damage_player(player) and self.game_over:
                        return
                    break

            # Boss body vs player
            if not player.alive or player.hit_invuln > 0:
                continue
            offset = (self.boss.rect.x - px, self.boss.rect.y - py)
            if player.mask.overlap(self.boss.mask, offset):
                self._damage_player(player)

    def _damage_player(self, player):
        """Apply one hit of damage. Caller must check hit_invuln. Returns True if survived."""
        from objects.Player import HIT_INVULN_DURATION, DAMAGE_INDICATOR_DURATION
        if player.has_shield:
            player.has_shield = False
            player.shield_flash = 30
            player.damage_indicator = DAMAGE_INDICATOR_DURATION
            self.upgrade_msg = "Shield broken!"
            self.upgrade_msg_timer = 1.5
            return True
        player.lives -= 1
        player.hit_invuln = HIT_INVULN_DURATION
        player.damage_indicator = DAMAGE_INDICATOR_DURATION
        if player.lives <= 0:
            self._trigger_player_death(player)
            return False
        self.spawn_particles(
            int(player.position_x) + PLAYER_CENTER_OFFSET_X,
            int(player.position_y) + PLAYER_CENTER_OFFSET_Y,
            count=8,
        )
        self.game.play_sound("explosion")
        return True

    def _trigger_player_death(self, player):
        player.alive = False
        self.spawn_particles(
            int(player.position_x) + PLAYER_CENTER_OFFSET_X,
            int(player.position_y) + PLAYER_CENTER_OFFSET_Y,
            count=15,
        )
        self.game.play_sound("death")

        if not any(p.alive for p in self.game.players):
            self._end_session()

    def _kill_player_blackhole(self, player, bh):
        """Insta-kill: black hole swallows the player regardless of shield/lives."""
        px = int(player.position_x) + PLAYER_CENTER_OFFSET_X
        py = int(player.position_y) + PLAYER_CENTER_OFFSET_Y
        self.particles.append(
            SuckInEffect(player.curr_image, px, py, bh._fx, bh._fy)
        )
        player.has_shield = False
        player.lives = 0
        player.alive = False
        bh.feed(2.0)
        self.game.play_sound("death")
        if not any(p.alive for p in self.game.players):
            self._end_session()

    def _end_session(self):
        self.game_over = True
        self.game.reset_keys()
        self.game.stop_all_sounds()
        self.game.stop_music()
        self.game.save_score(round(self.elapsed_time), self.asteroids_killed)
        self.is_new_record = (
            self.game.high_scores
            and self.game.high_scores[0]["kills"] == self.asteroids_killed
            and self.game.high_scores[0]["time"] == round(self.elapsed_time)
        )

    # ---- particles ----

    def spawn_particles(self, x, y, count=8):
        for _ in range(count):
            self.particles.append(Particle(x, y))

    # ---- main loop ----

    def update(self, delta_time, actions):
        self.particles = [p for p in self.particles if p.update(delta_time)]

        if self.upgrade_msg_timer > 0:
            self.upgrade_msg_timer -= delta_time

        if self.level_won:
            if actions["start"] or actions["space"] or actions["escape"]:
                self.game.return_to_menu()
            self.game.reset_keys()
            return

        if self.game_over:
            if actions["start"] or actions["space"] or actions["escape"]:
                self.game.return_to_menu()
            self.game.reset_keys()
            return

        if actions["start"] or actions["escape"]:
            self.game.stop_all_sounds()
            from states.pause_menu import PauseMenu
            PauseMenu(self.game).enter_state()
            return

        self.elapsed_time += delta_time

        # Boss spawning trigger
        if not self.boss_phase and not self.boss and self._should_spawn_boss():
            self._begin_boss_countdown()

        # Boss countdown — spawning has stopped, existing entities clear naturally
        if self.boss_phase and not self.boss and self.boss_countdown > 0:
            self.boss_countdown -= delta_time
            if self.boss_countdown <= 0:
                self._start_boss()

        # Boss phase update
        if self.boss:
            self.boss.update(delta_time)
            self._update_boss_combat()
            if not self.boss.alive_flag:
                self._on_boss_defeated()
                return

        # Rock spawning (paused during boss and boss_challenge)
        if not self.boss_phase and self.game_mode != "boss_challenge":
            self.rock_spawn_timer += delta_time
            if self.rock_spawn_timer >= self.rock_spawn_interval:
                self.rock_spawn_timer = 0
                cap = self._max_rocks()
                batch = self._spawn_batch()
                for _ in range(batch):
                    if len(self.game.rocks) < cap:
                        self._spawn_asteroid()
                self.rock_spawn_interval = max(self._min_spawn_interval(),
                                               self.rock_spawn_interval - self._spawn_decay())

        # Enemy spawning (paused during boss and boss_challenge)
        if not self.boss_phase and self.game_mode != "boss_challenge":
            if not self._enemies_started and self.elapsed_time >= ENEMY_FIRST_SPAWN:
                self._enemies_started = True
                self.enemy_spawn_timer = 0
            if self._enemies_started:
                self.enemy_spawn_timer += delta_time
                if self.enemy_spawn_timer >= self.enemy_spawn_interval:
                    self.enemy_spawn_timer = 0
                    self._spawn_enemy()
                    self.enemy_spawn_interval = max(
                        ENEMY_MIN_INTERVAL,
                        self.enemy_spawn_interval - ENEMY_INTERVAL_DECAY,
                    )

        for enemy in self.game.enemies:
            enemy.update(delta_time)

        self.game.rocks.update()
        self._update_black_hole_gravity(delta_time)

        # --- Player projectiles vs enemy projectiles ---
        self._update_projectile_vs_projectile()

        # --- Projectile-enemy collisions ---
        self._update_enemy_combat()

        # --- Projectile-rock collisions (HP-based) ---
        normal_group = pygame.sprite.Group()
        piercing_group = pygame.sprite.Group()
        for p in self.game.projectiles:
            (piercing_group if p.piercing else normal_group).add(p)

        hits_normal = pygame.sprite.groupcollide(
            normal_group, self.game.rocks, True, False,
            collided=pygame.sprite.collide_mask,
        )
        hits_piercing = pygame.sprite.groupcollide(
            piercing_group, self.game.rocks, False, False,
            collided=pygame.sprite.collide_mask,
        )

        rock_damage = {}
        rock_killers = {}
        for proj, rocks_hit in hits_normal.items():
            for rock in rocks_hit:
                rock_damage[rock] = rock_damage.get(rock, 0) + getattr(proj, "damage", 1)
                if proj.owner:
                    rock_killers[rock] = proj.owner
        for proj, rocks_hit in hits_piercing.items():
            for rock in rocks_hit:
                rock_damage[rock] = rock_damage.get(rock, 0) + getattr(proj, "damage", 1)
                if proj.owner:
                    rock_killers[rock] = proj.owner

        destroyed = []
        for rock, dmg in rock_damage.items():
            rock.take_damage(dmg)
            if rock.hp <= 0:
                destroyed.append(rock)
                rock.kill()

        for rock in destroyed:
            self.spawn_particles(rock.rect.centerx, rock.rect.centery)
            self.asteroids_killed += 1
            self.total_kills_ever += 1
            self.kills_since_shield += 1
            killer = rock_killers.get(rock)
            if killer:
                killer.kills += 1
            if rock.rock_type == CLUSTER:
                self._spawn_fragments(rock)
            if self._should_spawn_shield():
                self.game.pickups.add(
                    ShieldPickup(rock.rect.centerx, rock.rect.centery, self.game)
                )
                self.kills_since_shield = 0
            elif self._should_spawn_upgrade():
                self.game.pickups.add(
                    UpgradePickup(
                        rock.rect.centerx, rock.rect.centery,
                        None, self.game,
                    )
                )
        if destroyed:
            self.game.play_sound("explosion")

        # Pickup collection (mask-based)
        for player in self.game.players:
            if not player.alive:
                continue
            px, py = int(player.position_x), int(player.position_y)
            for pickup in list(self.game.pickups):
                offset = (pickup.rect.x - px, pickup.rect.y - py)
                if player.mask.overlap(pickup.mask, offset):
                    if pickup.pickup_type == "shield":
                        player.has_shield = True
                        self.kills_since_shield = 0
                        self.upgrade_msg = "Shield!"
                        self.upgrade_msg_timer = 2.0
                    else:
                        self._apply_upgrade(pickup, player)
                    self.game.play_sound("powerup")
                    pickup.kill()

        # Player-rock collision
        for player in self.game.players:
            if not player.alive or player.hit_invuln > 0:
                continue
            px, py = int(player.position_x), int(player.position_y)
            for rock in list(self.game.rocks):
                offset = (rock.rect.x - px, rock.rect.y - py)
                if player.mask.overlap(rock.mask, offset):
                    if rock.rock_type == BLACKHOLE:
                        self._kill_player_blackhole(player, rock)
                        break
                    if player.has_shield:
                        self._damage_player(player)
                        self.spawn_particles(rock.rect.centerx, rock.rect.centery, count=12)
                        rock.kill()
                        self.asteroids_killed += 1
                        player.kills += 1
                        self.game.play_sound("explosion")
                        continue
                    self._damage_player(player)
                    break

        # Enemy projectile vs player / Enemy body vs player
        for player in self.game.players:
            if not player.alive:
                continue
            px, py = int(player.position_x), int(player.position_y)
            for ep in list(self.game.enemy_projectiles):
                if player.hit_invuln > 0:
                    break
                offset = (ep.rect.x - px, ep.rect.y - py)
                if player.mask.overlap(ep.mask, offset):
                    ep.kill()
                    if not self._damage_player(player) and self.game_over:
                        return

            for enemy in list(self.game.enemies):
                if not enemy.alive_flag or player.hit_invuln > 0:
                    continue
                offset = (enemy.rect.x - px, enemy.rect.y - py)
                if player.mask.overlap(enemy.mask, offset):
                    self._damage_player(player)
                    break

    # ---- rendering ----

    ICON_SIZE = 30
    ICON_PAD = 4
    ICON_RADIUS = 5

    def _draw_star(self, surface, cx, cy, size, color):
        points = []
        for i in range(10):
            angle = math.radians(i * 36 - 90)
            r = size if i % 2 == 0 else size * 0.38
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        pygame.draw.polygon(surface, color, points)

    def _draw_weapon_icon(self, display, x, y, weapon, fill_ratio=1.0,
                          glowing=False, greyed=False):
        sz = self.ICON_SIZE
        rd = self.ICON_RADIUS
        color = pygame.Color(weapon.color)
        r, g, b = color.r, color.g, color.b

        icon = pygame.Surface((sz, sz), pygame.SRCALPHA)

        # Base (dark background)
        pygame.draw.rect(icon, (25, 25, 30, 220), (0, 0, sz, sz), border_radius=rd)

        if greyed and fill_ratio < 1.0:
            pygame.draw.rect(icon, (20, 20, 25, 210), (0, 0, sz, sz), border_radius=rd)

            if fill_ratio > 0:
                fill_h = max(1, int(sz * fill_ratio))
                fill_y = sz - fill_h
                colored = pygame.Surface((sz, sz), pygame.SRCALPHA)
                pygame.draw.rect(colored, (r, g, b, 140), (0, 0, sz, sz), border_radius=rd)
                clip = pygame.Surface((sz, sz), pygame.SRCALPHA)
                pygame.draw.rect(clip, (255, 255, 255, 255), (0, fill_y, sz, fill_h))
                colored.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                icon.blit(colored, (0, 0))
        elif glowing:
            t = pygame.time.get_ticks() / 1000
            pulse = 0.55 + 0.45 * math.sin(t * 8)
            bg_alpha = int(160 + 80 * pulse)
            pygame.draw.rect(icon, (r, g, b, bg_alpha), (0, 0, sz, sz), border_radius=rd)
            flash = pygame.Surface((sz, sz), pygame.SRCALPHA)
            pygame.draw.rect(flash, (255, 255, 255, int(50 * pulse)),
                             (0, 0, sz, sz), border_radius=rd)
            icon.blit(flash, (0, 0))
        else:
            alpha = 140 if not greyed else 70
            pygame.draw.rect(icon, (r, g, b, alpha), (0, 0, sz, sz), border_radius=rd)

        self._draw_weapon_symbol(icon, weapon, sz)

        level = weapon.level
        max_lvl = weapon.max_level
        star_r = max(2, int(5 * sz / 44))
        star_gap = max(1, int(3 * sz / 44))
        total_w = max_lvl * (star_r * 2 + star_gap) - star_gap
        sx_start = (sz - total_w) / 2
        star_cy = sz - star_r - max(2, int(4 * sz / 44))
        for i in range(max_lvl):
            scx = sx_start + i * (star_r * 2 + star_gap) + star_r
            if i < level:
                self._draw_star(icon, scx, star_cy, star_r, (255, 255, 100))
            else:
                self._draw_star(icon, scx, star_cy, star_r, (70, 70, 70))

        gp = max(4, int(14 * sz / 44))
        if glowing:
            t = pygame.time.get_ticks() / 1000
            pulse = 0.55 + 0.45 * math.sin(t * 8)
            bright = (min(255, r + 100), min(255, g + 100), min(255, b + 100))
            pygame.draw.rect(icon, (*bright, int(220 * pulse)),
                             (0, 0, sz, sz), max(1, int(3 * sz / 44)), border_radius=rd)
            glow = pygame.Surface((sz + gp, sz + gp), pygame.SRCALPHA)
            pygame.draw.rect(glow, (r, g, b, int(70 * pulse)),
                             (0, 0, sz + gp, sz + gp), border_radius=rd + 3)
            display.blit(glow, (x - gp // 2, y - gp // 2))
        else:
            border_col = (160, 160, 170, 200) if not greyed else (90, 90, 95, 180)
            pygame.draw.rect(icon, border_col, (0, 0, sz, sz), max(1, int(2 * sz / 44)),
                             border_radius=rd)

        display.blit(icon, (x, y))

    def _draw_state_label(self, display, x, y, label, color):
        """Draw a small state label centered below an icon."""
        font = self.game.get_font(max(8, int(11 * self.ICON_SIZE / 44)))
        shadow = font.render(label, True, (0, 0, 0))
        txt = font.render(label, True, color)
        tx = x + self.ICON_SIZE // 2 - txt.get_width() // 2
        ty = y + self.ICON_SIZE + 1
        display.blit(shadow, (tx + 1, ty + 1))
        display.blit(txt, (tx, ty))

    def _draw_weapon_symbol(self, surface, weapon, sz):
        from objects.Weapon import StraightCannon, SpreadShot, LaserCannon, HomingMissile
        color = pygame.Color(weapon.color)
        bright = (min(255, color.r + 100), min(255, color.g + 100),
                  min(255, color.b + 100))
        f = sz / 44.0
        cx, cy = sz // 2, int(sz / 2 - 4 * f)

        if isinstance(weapon, StraightCannon):
            bw, bh = int(18 * f), max(2, int(6 * f))
            pygame.draw.rect(surface, bright, (cx - int(2 * f), cy - bh // 2, bw, bh))
            pygame.draw.rect(surface, (255, 255, 255, 180),
                             (cx, cy - 1, int(14 * f), max(1, int(2 * f))))
            s7 = int(7 * f)
            body = [(cx - int(10 * f), cy - s7), (cx - int(2 * f), cy - s7),
                    (cx - int(2 * f), cy + s7), (cx - int(10 * f), cy + s7),
                    (cx - int(14 * f), cy)]
            pygame.draw.polygon(surface, bright, body)
            dim = (max(0, bright[0] - 50), max(0, bright[1] - 50), max(0, bright[2] - 50))
            pygame.draw.polygon(surface, dim, body, max(1, int(2 * f)))
            pygame.draw.circle(surface, (255, 230, 150),
                               (cx + int(17 * f), cy), max(1, int(3 * f)))
        elif isinstance(weapon, SpreadShot):
            origin = (cx - int(8 * f), cy)
            reach = int(22 * f)
            for angle_deg in (-25, 0, 25):
                a = math.radians(angle_deg)
                ex = origin[0] + reach * math.cos(a)
                ey = origin[1] + reach * math.sin(a)
                pygame.draw.line(surface, (*bright[:3], 100),
                                 origin, (int(ex), int(ey)), 1)
                pygame.draw.circle(surface, bright, (int(ex), int(ey)), max(1, int(3 * f)))
                pygame.draw.circle(surface, (255, 255, 255), (int(ex), int(ey)), 1)
        elif isinstance(weapon, LaserCannon):
            hw = int(14 * f)
            pygame.draw.rect(surface, bright, (cx - hw, cy - max(1, int(2 * f)),
                                               hw * 2, max(3, int(5 * f))))
            pygame.draw.line(surface, (255, 255, 255),
                             (cx - hw + 2, cy), (cx + hw - 2, cy), 1)
        elif isinstance(weapon, HomingMissile):
            s = f
            pts = [(cx + int(12 * s), cy), (cx + int(6 * s), cy - int(4 * s)),
                   (cx - int(8 * s), cy - int(3 * s)),
                   (cx - int(8 * s), cy + int(3 * s)),
                   (cx + int(6 * s), cy + int(4 * s))]
            pygame.draw.polygon(surface, bright, pts)
            dim = (max(0, bright[0] - 60), max(0, bright[1] - 60), max(0, bright[2] - 60))
            pygame.draw.polygon(surface, dim,
                                [(cx - int(8 * s), cy - int(3 * s)),
                                 (cx - int(12 * s), cy - int(8 * s)),
                                 (cx - int(5 * s), cy - int(2 * s))])
            pygame.draw.polygon(surface, dim,
                                [(cx - int(8 * s), cy + int(3 * s)),
                                 (cx - int(12 * s), cy + int(8 * s)),
                                 (cx - int(5 * s), cy + int(2 * s))])
            cr = max(2, int(5 * s))
            tcx, tcy = cx - int(2 * s), cy - int(10 * s)
            pygame.draw.circle(surface, bright, (tcx, tcy), cr, 1)
            pygame.draw.line(surface, bright,
                             (tcx - cr - 1, tcy), (tcx + cr + 1, tcy), 1)
            pygame.draw.line(surface, bright,
                             (tcx, tcy - cr - 1), (tcx, tcy + cr + 1), 1)

    HEART_SIZE = 13

    @staticmethod
    def _draw_heart(surface, x, y, size, filled=True):
        s = size
        r = s // 4
        heart = pygame.Surface((s, s), pygame.SRCALPHA)
        hcx = s // 2

        if filled:
            color = (220, 40, 40)
            highlight = (255, 130, 130)
        else:
            color = (55, 55, 60)
            highlight = None

        pygame.draw.circle(heart, color, (hcx - r + 1, r + 2), r)
        pygame.draw.circle(heart, color, (hcx + r - 1, r + 2), r)
        pygame.draw.polygon(heart, color, [
            (1, r + 2), (s - 1, r + 2), (hcx, s - 2)
        ])

        if highlight:
            pygame.draw.circle(heart, highlight, (hcx - r, r), r // 2)

        if not filled:
            outline = pygame.Surface((s, s), pygame.SRCALPHA)
            mask = pygame.mask.from_surface(heart)
            outline_pts = mask.outline()
            if len(outline_pts) > 2:
                pygame.draw.lines(outline, (90, 90, 95), True, outline_pts, 1)
            heart = outline

        surface.blit(heart, (x, y))

    def _draw_lives_and_shield(self, display, x, y, player):
        row_h = self.ICON_SIZE
        hs = self.HEART_SIZE
        gap = 3
        heart_y = y + (row_h - hs) // 2
        for i in range(MAX_LIVES):
            hx = x + i * (hs + gap)
            self._draw_heart(display, hx, heart_y, hs, filled=(i < player.lives))

        sz = hs + 2
        shield_x = x + MAX_LIVES * (hs + gap) + 2
        shield_y = y + (row_h - sz) // 2
        icon = pygame.Surface((sz, sz), pygame.SRCALPHA)
        cx, cy = sz // 2, sz // 2
        s = sz // 2 - 1
        points = [
            (cx, cy - s), (cx + s, cy - s // 2), (cx + s, cy + s // 3),
            (cx + s // 2, cy + s - 1), (cx, cy + s),
            (cx - s // 2, cy + s - 1), (cx - s, cy + s // 3), (cx - s, cy - s // 2),
        ]
        if player.has_shield:
            t = pygame.time.get_ticks() / 1000
            pulse = 0.7 + 0.3 * math.sin(t * 4)
            sc = (80, 200, 255)
            pygame.draw.polygon(icon, (*sc, int(200 * pulse)), points)
            bright = tuple(min(255, c + 60) for c in sc)
            pygame.draw.polygon(icon, (*bright, int(240 * pulse)), points, 2)
        else:
            pygame.draw.polygon(icon, (55, 55, 60), points, 1)
        display.blit(icon, (shield_x, shield_y))

    def _draw_cooldown_bar(self, display, x, y, ratio, color):
        """Draw a colored progress bar below a weapon icon."""
        bar_w = self.ICON_SIZE
        bar_h = 5
        bg = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        pygame.draw.rect(bg, (20, 20, 25, 200), (0, 0, bar_w, bar_h), border_radius=2)
        display.blit(bg, (x, y))
        if ratio > 0:
            fill_w = max(2, int(bar_w * ratio))
            c = pygame.Color(color)
            bar = pygame.Surface((fill_w, bar_h), pygame.SRCALPHA)
            pygame.draw.rect(bar, (c.r, c.g, c.b, 230), (0, 0, fill_w, bar_h),
                             border_radius=2)
            bright = (min(255, c.r + 80), min(255, c.g + 80), min(255, c.b + 80))
            pygame.draw.line(bar, (*bright, 180), (1, 1), (fill_w - 2, 1))
            display.blit(bar, (x, y))

    def _draw_cooldown_text(self, display, x, y, seconds_left):
        """Draw remaining seconds centered on the icon."""
        font = self.game.get_font(max(10, int(16 * self.ICON_SIZE / 44)))
        txt = font.render(f"{seconds_left:.1f}", True, (255, 255, 255))
        tx = x + self.ICON_SIZE // 2 - txt.get_width() // 2
        ty = y + self.ICON_SIZE // 2 - txt.get_height() // 2
        shadow = font.render(f"{seconds_left:.1f}", True, (0, 0, 0))
        display.blit(shadow, (tx + 1, ty + 1))
        display.blit(txt, (tx, ty))

    def _draw_empty_icon(self, display, x, y):
        sz = self.ICON_SIZE
        rd = self.ICON_RADIUS
        icon = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.rect(icon, (25, 25, 30, 150), (0, 0, sz, sz), border_radius=rd)
        pygame.draw.rect(icon, (60, 60, 65, 120), (0, 0, sz, sz), 2, border_radius=rd)
        cx, cy = sz // 2, sz // 2
        font = self.game.get_font(max(10, int(18 * sz / 44)))
        txt = font.render("?", True, (80, 80, 80))
        icon.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2))
        display.blit(icon, (x, y))

    def _draw_player_hud(self, display, player, hud_x, hud_y):
        from objects.Player import Player
        step = self.ICON_SIZE + self.ICON_PAD
        hint_y = hud_y + self.ICON_SIZE + 12
        hint_font = self.game.get_font(max(8, int(11 * self.ICON_SIZE / 44)))
        labels = self.game.get_binding_labels()
        bl = labels[player.index] if player.index < len(labels) else labels[0]

        pc = Player.PLAYER_COLORS[player.index] if player.index < len(Player.PLAYER_COLORS) else (255, 255, 255)
        label = f"P{player.index + 1}"
        if not player.alive:
            label += " \u2620"
            pc = (120, 120, 120)
        lbl_font = self.game.get_font(max(10, int(14 * self.ICON_SIZE / 44)))
        lbl_surf = lbl_font.render(label, True, pc)
        display.blit(lbl_surf, (hud_x, hud_y))
        hud_x += lbl_surf.get_width() + 4

        self._draw_weapon_icon(display, hud_x, hud_y, player.primary,
                               fill_ratio=1.0, glowing=player.auto_fire)

        fire_label = "AUTO" if player.auto_fire else bl["fire"]
        fire_color = (80, 255, 80) if player.auto_fire else (140, 140, 150)
        htxt = hint_font.render(fire_label, True, fire_color)
        display.blit(htxt, (hud_x + self.ICON_SIZE // 2 - htxt.get_width() // 2,
                            hint_y))

        ix = hud_x + step
        if player.secondary_inventory:
            from objects.Player import (SEC_READY, SEC_ACTIVE, SEC_COOLDOWN,
                                        SECONDARY_CYCLE, SECONDARY_ACTIVE_PER_LEVEL)
            first_sec_x = ix
            for weapon_cls in player.secondary_inventory:
                is_selected = player.secondary and type(player.secondary) is weapon_cls
                if is_selected:
                    sec = player.secondary
                    sec_color = pygame.Color(sec.color)
                    if player.sec_state == SEC_ACTIVE:
                        self._draw_weapon_icon(display, ix, hud_y, sec,
                                               fill_ratio=1.0, glowing=True)
                        self._draw_state_label(display, ix, hud_y,
                                               "FIRING",
                                               (min(255, sec_color.r + 100),
                                                min(255, sec_color.g + 100),
                                                min(255, sec_color.b + 100)))
                    elif player.sec_state == SEC_COOLDOWN:
                        total_cd = player._sec_cooldown_duration()
                        elapsed_cd = total_cd - player.sec_state_timer
                        ratio = min(1.0, elapsed_cd / total_cd) if total_cd > 0 else 1.0
                        self._draw_weapon_icon(display, ix, hud_y, sec,
                                               fill_ratio=ratio, greyed=True)
                        bar_y = hud_y + self.ICON_SIZE + 2
                        self._draw_cooldown_bar(display, ix, bar_y, ratio,
                                                sec.color)
                        self._draw_cooldown_text(display, ix, hud_y,
                                                 player.sec_state_timer)
                        self._draw_state_label(display, ix, bar_y + 6,
                                               f"{player.sec_state_timer:.1f}s",
                                               (255, 160, 60))
                    else:
                        self._draw_weapon_icon(display, ix, hud_y, sec, fill_ratio=1.0)
                        self._draw_state_label(display, ix, hud_y,
                                               "READY", (80, 255, 80))
                    if len(player.secondary_inventory) > 1:
                        acx = ix + self.ICON_SIZE // 2
                        pygame.draw.polygon(display, (255, 255, 100),
                                            [(acx - 4, hud_y - 2),
                                             (acx + 4, hud_y - 2),
                                             (acx, hud_y - 7)])
                else:
                    tmp = weapon_cls()
                    tmp.level = player.secondary_levels.get(weapon_cls, 1)
                    ws = player.sec_weapon_states.get(weapon_cls,
                                                      {"state": SEC_READY, "timer": 0})
                    if ws["state"] == SEC_COOLDOWN:
                        wlevel = player.secondary_levels.get(weapon_cls, 1)
                        total_cd = max(1.0, SECONDARY_CYCLE
                                       - wlevel * SECONDARY_ACTIVE_PER_LEVEL)
                        elapsed_cd = total_cd - ws["timer"]
                        ratio = min(1.0, elapsed_cd / total_cd) if total_cd > 0 else 1.0
                        self._draw_weapon_icon(display, ix, hud_y, tmp,
                                               fill_ratio=ratio, greyed=True)
                        bar_y = hud_y + self.ICON_SIZE + 2
                        self._draw_cooldown_bar(display, ix, bar_y, ratio, tmp.color)
                        self._draw_state_label(display, ix, bar_y + 6,
                                               f"{ws['timer']:.1f}s",
                                               (180, 120, 50))
                    elif ws["state"] == SEC_ACTIVE:
                        self._draw_weapon_icon(display, ix, hud_y, tmp,
                                               fill_ratio=1.0, greyed=False)
                        self._draw_state_label(display, ix, hud_y,
                                               "ACTIVE",
                                               (255, 200, 60))
                    else:
                        self._draw_weapon_icon(display, ix, hud_y, tmp,
                                               fill_ratio=1.0, greyed=True)
                        self._draw_state_label(display, ix, hud_y,
                                               "READY", (60, 160, 60))
                ix += step

            sec_count = len(player.secondary_inventory)
            sec_mid = first_sec_x + (sec_count * step - self.ICON_PAD) // 2
            parts = [bl["secondary"]]
            if sec_count > 1:
                parts.append(bl["cycle"])
            hint_str = " \u00b7 ".join(parts)
            htxt = hint_font.render(hint_str, True, (140, 140, 150))
            display.blit(htxt, (sec_mid - htxt.get_width() // 2, hint_y))
            ix_after = first_sec_x + sec_count * step
        else:
            self._draw_empty_icon(display, ix, hud_y)
            ix_after = ix + step

        self._draw_lives_and_shield(display, ix_after, hud_y, player)

    def render(self, display):
        display.blit(self.background, (0, 0))

        for p in self.particles:
            p.draw(display)

        if self.boss_phase and self.boss_countdown > 0:
            secs = max(1, int(math.ceil(self.boss_countdown)))
            self.game.draw_text(
                display, f"BOSS INCOMING  {secs}",
                (255, 180, 40),
                self.game.GAME_WIDTH - 120, 20,
            )
        elif self.boss_phase:
            self.game.draw_text(
                display, "BOSS FIGHT!",
                (255, 60, 60),
                self.game.GAME_WIDTH - 100, 20,
            )
        elif self.game_mode == "level":
            remaining = max(0, LEVEL_DURATION - self.elapsed_time)
            time_color = (255, 80, 80) if remaining < 10 else "blue"
            self.game.draw_text(
                display,
                f"Level {self.level_num}  |  {remaining:.1f}s left",
                time_color,
                self.game.GAME_WIDTH - 120,
                20,
            )
        elif self.game_mode == "boss_challenge":
            self.game.draw_text(
                display,
                f"Time: {round(self.elapsed_time)} s",
                "blue",
                self.game.GAME_WIDTH - 100,
                20,
            )
        else:
            self.game.draw_text(
                display,
                f"Time alive: {round(self.elapsed_time)} s",
                "blue",
                self.game.GAME_WIDTH - 100,
                20,
            )
        self.game.draw_text(
            display,
            f"Kills: {self.asteroids_killed}",
            "blue",
            self.game.GAME_WIDTH - 100,
            50,
        )

        n = len(self.game.players)
        hud_h = self.ICON_SIZE + 22
        for i, player in enumerate(self.game.players):
            if n == 1:
                hx, hy = 8, 6
            elif i == 0:
                hx, hy = 8, 6
            elif i == 1:
                hx, hy = 8, self.game.GAME_HEIGHT - hud_h - 4
            else:
                hx, hy = self.game.GAME_WIDTH // 2, self.game.GAME_HEIGHT - hud_h - 4
            self._draw_player_hud(display, player, hx, hy)

        if self.upgrade_msg_timer > 0:
            alpha = min(1.0, self.upgrade_msg_timer / 0.3)
            color = (
                int(255 * alpha),
                int(220 * alpha),
                int(60 * alpha),
            )
            self.game.draw_text(
                display,
                self.upgrade_msg,
                color,
                self.game.GAME_WIDTH / 2,
                80,
            )

        if self.level_won:
            cx = self.game.GAME_WIDTH / 2
            cy = self.game.GAME_HEIGHT / 2
            if self.game_mode == "boss_challenge":
                win_text = "Boss Defeated!"
            else:
                win_text = f"Level {self.level_num} Complete!"
            self.game.draw_text_sized(
                display, win_text, (60, 255, 60), cx, cy - 50, 48,
            )
            self.game.draw_text(
                display,
                f"{self.asteroids_killed} kills",
                (255, 255, 255),
                cx, cy + 10,
            )
            self.game.draw_text(
                display,
                "Press Space to continue",
                (180, 180, 180),
                cx, cy + 65,
            )
        elif self.game_over:
            cx = self.game.GAME_WIDTH / 2
            cy = self.game.GAME_HEIGHT / 2
            self.game.draw_text(display, "You lost!", (255, 0, 0), cx, cy - 50)
            self.game.draw_text(
                display,
                f"Survived {round(self.elapsed_time)}s  |  {self.asteroids_killed} kills",
                (255, 255, 255),
                cx,
                cy,
            )
            if self.is_new_record:
                self.game.draw_text(
                    display, "NEW RECORD!", (255, 220, 60), cx, cy + 40
                )
            self.game.draw_text(
                display,
                "Press Space to continue",
                (180, 180, 180),
                cx,
                cy + 85,
            )
