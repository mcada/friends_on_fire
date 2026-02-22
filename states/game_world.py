import pygame, os, random, math
from states.state import State
from states.pause_menu import PauseMenu
from objects.Rocks import Rock, BASIC, CLUSTER, IRON
from objects.Pickup import UpgradePickup, ShieldPickup
from objects.Weapon import StraightCannon, SECONDARY_WEAPONS
from objects.Boss import Boss, BossProjectile, BOSS_BASE_HP
from objects.Player import PLAYER_CENTER_OFFSET_X, PLAYER_CENTER_OFFSET_Y

BASE_UPGRADE_CHANCE = 0.07
UPGRADE_CHANCE_DECAY = 0.35
PRIMARY_PICKUP_WEIGHT = 0.4

SHIELD_BASE_CHANCE = 0.02
SHIELD_PITY_FACTOR = 15

LEVEL_DURATION = 120.0


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


class Game_World(State):
    def __init__(self, game, game_mode="endless", level_num=0):
        State.__init__(self, game)
        self.game_mode = game_mode
        self.level_num = level_num
        self.background = pygame.image.load(
            os.path.join(self.game.assets_dir, "bg.jpeg")
        ).convert()
        self.elapsed_time = 0
        self.rock_spawn_timer = 0
        self.rock_spawn_interval = 1.0
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
        self.boss_encounter = 0
        self.next_boss_time = LEVEL_DURATION
        self._boss_challenge_started = False

        self.game.rocks.empty()
        self.game.projectiles.empty()
        self.game.pickups.empty()
        player = self.game.player
        player.position_x = 100
        player.position_y = self.game.GAME_HEIGHT / 2
        player.primary = StraightCannon()
        player.secondary = None
        player.secondary_levels = {}
        player.secondary_inventory = []
        player.sec_weapon_states = {}
        player.sec_state = "ready"
        player.sec_state_timer = 0
        player.auto_fire = False
        player.has_shield = False
        player.shield_flash = 0
        player._build_sprites()
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
        r = random.random()
        if r < 1 - cluster_w - iron_w:
            return BASIC
        if r < 1 - iron_w:
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
        base = 15
        if self.game_mode == "level":
            base = 10 + self.level_num * 3
        return base + int(self.elapsed_time * 0.1)

    def _spawn_batch(self):
        if self.game_mode == "level":
            base = self.level_num
            return min(base + int(self.elapsed_time // 30), 3)
        return min(1 + int(self.elapsed_time // 40), 3)

    def _min_spawn_interval(self):
        if self.game_mode == "level":
            return max(0.35, 0.55 - self.level_num * 0.05)
        return 0.45

    def _spawn_decay(self):
        if self.game_mode == "level":
            return 0.008 + self.level_num * 0.003
        return 0.01

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

    # ---- upgrade helpers ----

    def _upgrade_chance(self):
        return BASE_UPGRADE_CHANCE / (1 + self.upgrade_count * UPGRADE_CHANCE_DECAY)

    def _should_spawn_upgrade(self):
        return random.random() < self._upgrade_chance()

    @staticmethod
    def _random_pickup_type():
        if random.random() < PRIMARY_PICKUP_WEIGHT:
            return None
        return random.choice(SECONDARY_WEAPONS)

    def _apply_upgrade(self, pickup):
        player = self.game.player
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
        if self.game.player.has_shield:
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
        if self.game_mode == "boss_challenge":
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

    def _start_boss(self):
        self.boss_phase = True
        self._boss_challenge_started = True
        for rock in list(self.game.rocks):
            rock.kill()
        self.boss = Boss(self.game,
                         attack_level=self._boss_attack_level(),
                         hp_override=self._boss_hp())

    def _on_boss_defeated(self):
        self.spawn_particles(self.boss.rect.centerx, self.boss.rect.centery, count=30)
        self.game.play_boss_death_sound()
        self.boss.boss_projectiles.empty()
        self.boss = None
        self.boss_phase = False
        self.boss_encounter += 1
        if self.game_mode in ("level", "boss_challenge"):
            self.level_won = True
            self.game.reset_keys()
            self.game.stop_music()
        else:
            self.next_boss_time = self.elapsed_time + LEVEL_DURATION
            self.game.play_music("game")

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
                if self.boss.take_damage(1):
                    boss_hit_this_frame = True
                proj.kill()

        for proj in list(piercing_group):
            offset = (self.boss.rect.x - proj.rect.x, self.boss.rect.y - proj.rect.y)
            if proj.mask.overlap(self.boss.mask, offset):
                if self.boss.take_damage(1):
                    boss_hit_this_frame = True

        if boss_hit_this_frame:
            self.game.play_sound("explosion")

        # Player projectiles vs destroyable boss projectiles
        destroyable = pygame.sprite.Group(
            [bp for bp in self.boss.boss_projectiles if bp.destroyable]
        )
        pygame.sprite.groupcollide(
            self.game.projectiles, destroyable, True, True,
            collided=pygame.sprite.collide_mask,
        )

        # Boss projectiles vs player
        player = self.game.player
        px, py = int(player.position_x), int(player.position_y)
        for bp in list(self.boss.boss_projectiles):
            offset = (bp.rect.x - px, bp.rect.y - py)
            if player.mask.overlap(bp.mask, offset):
                if player.has_shield:
                    player.has_shield = False
                    player.shield_flash = 30
                    self.upgrade_msg = "Shield broken!"
                    self.upgrade_msg_timer = 1.5
                    bp.kill()
                    continue
                self._trigger_death()
                return

        # Boss body vs player
        offset = (self.boss.rect.x - px, self.boss.rect.y - py)
        if player.mask.overlap(self.boss.mask, offset):
            if player.has_shield:
                player.has_shield = False
                player.shield_flash = 30
                self.upgrade_msg = "Shield broken!"
                self.upgrade_msg_timer = 1.5
            else:
                self._trigger_death()

    def _trigger_death(self):
        self.game_over = True
        self.game.reset_keys()
        self.game.stop_all_sounds()
        self.spawn_particles(
            int(self.game.player.position_x) + PLAYER_CENTER_OFFSET_X,
            int(self.game.player.position_y) + PLAYER_CENTER_OFFSET_Y,
            count=15,
        )
        self.game.play_sound("death")
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
            new_state = PauseMenu(self.game)
            new_state.enter_state()
            return

        self.elapsed_time += delta_time

        # Boss spawning trigger
        if not self.boss_phase and not self.boss and self._should_spawn_boss():
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

        self.game.rocks.update()

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
        for rocks_hit in hits_normal.values():
            for rock in rocks_hit:
                rock_damage[rock] = rock_damage.get(rock, 0) + 1
        for rocks_hit in hits_piercing.values():
            for rock in rocks_hit:
                rock_damage[rock] = rock_damage.get(rock, 0) + 1

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
            if rock.rock_type == CLUSTER:
                self._spawn_fragments(rock)
            if self._should_spawn_shield():
                self.game.pickups.add(
                    ShieldPickup(rock.rect.centerx, rock.rect.centery, self.game)
                )
                self.kills_since_shield = 0
            elif self._should_spawn_upgrade():
                wtype = self._random_pickup_type()
                self.game.pickups.add(
                    UpgradePickup(
                        rock.rect.centerx, rock.rect.centery,
                        wtype, self.game,
                    )
                )
        if destroyed:
            self.game.play_sound("explosion")

        # Pickup collection (mask-based)
        player = self.game.player
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
                    self._apply_upgrade(pickup)
                self.game.play_sound("powerup")
                pickup.kill()

        # Player-rock collision
        for rock in self.game.rocks:
            offset = (rock.rect.x - px, rock.rect.y - py)
            if player.mask.overlap(rock.mask, offset):
                if player.has_shield:
                    player.has_shield = False
                    player.shield_flash = 30
                    self.spawn_particles(rock.rect.centerx, rock.rect.centery, count=12)
                    rock.kill()
                    self.asteroids_killed += 1
                    self.game.play_sound("explosion")
                    self.upgrade_msg = "Shield broken!"
                    self.upgrade_msg_timer = 1.5
                    continue
                self._trigger_death()
                break

    # ---- rendering ----

    ICON_SIZE = 44
    ICON_PAD = 6
    ICON_RADIUS = 7

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
        else:
            alpha = 140 if not greyed else 70
            pygame.draw.rect(icon, (r, g, b, alpha), (0, 0, sz, sz), border_radius=rd)

        # Weapon symbol in top portion
        self._draw_weapon_symbol(icon, weapon, sz)

        # Level stars along the bottom
        level = weapon.level
        max_lvl = weapon.max_level
        star_r = 5
        total_w = max_lvl * (star_r * 2 + 3) - 3
        sx_start = (sz - total_w) / 2
        star_cy = sz - star_r - 4
        for i in range(max_lvl):
            scx = sx_start + i * (star_r * 2 + 3) + star_r
            if i < level:
                self._draw_star(icon, scx, star_cy, star_r, (255, 255, 100))
            else:
                self._draw_star(icon, scx, star_cy, star_r, (70, 70, 70))

        # Border
        if glowing:
            t = pygame.time.get_ticks() / 1000
            pulse = 0.6 + 0.4 * math.sin(t * 6)
            border_alpha = int(200 * pulse)
            border_col = (min(255, r + 80), min(255, g + 80), min(255, b + 80), border_alpha)
            pygame.draw.rect(icon, border_col, (0, 0, sz, sz), 3, border_radius=rd)
            glow = pygame.Surface((sz + 10, sz + 10), pygame.SRCALPHA)
            pygame.draw.rect(glow, (r, g, b, int(50 * pulse)),
                             (0, 0, sz + 10, sz + 10), border_radius=rd + 3)
            display.blit(glow, (x - 5, y - 5))
        else:
            border_col = (160, 160, 170, 200) if not greyed else (90, 90, 95, 180)
            pygame.draw.rect(icon, border_col, (0, 0, sz, sz), 2, border_radius=rd)

        display.blit(icon, (x, y))

    def _draw_weapon_symbol(self, surface, weapon, sz):
        from objects.Weapon import StraightCannon, SpreadShot, LaserCannon, HomingMissile
        color = pygame.Color(weapon.color)
        bright = (min(255, color.r + 100), min(255, color.g + 100),
                  min(255, color.b + 100))
        cx, cy = sz // 2, sz // 2 - 4

        if isinstance(weapon, StraightCannon):
            # Barrel
            pygame.draw.rect(surface, bright, (cx - 2, cy - 3, 18, 6))
            pygame.draw.rect(surface, (255, 255, 255, 180), (cx, cy - 1, 14, 2))
            # Body
            body = [(cx - 10, cy - 7), (cx - 2, cy - 7),
                    (cx - 2, cy + 7), (cx - 10, cy + 7),
                    (cx - 14, cy)]
            pygame.draw.polygon(surface, bright, body)
            dim = (max(0, bright[0] - 50), max(0, bright[1] - 50), max(0, bright[2] - 50))
            pygame.draw.polygon(surface, dim, body, 2)
            # Muzzle flash
            pygame.draw.circle(surface, (255, 230, 150), (cx + 17, cy), 3)
        elif isinstance(weapon, SpreadShot):
            origin = (cx - 8, cy)
            for angle_deg in (-25, 0, 25):
                a = math.radians(angle_deg)
                ex = origin[0] + 22 * math.cos(a)
                ey = origin[1] + 22 * math.sin(a)
                pygame.draw.line(surface, (*bright[:3], 100) if len(bright) >= 3 else bright,
                                 origin, (int(ex), int(ey)), 1)
                pygame.draw.circle(surface, bright, (int(ex), int(ey)), 3)
                pygame.draw.circle(surface, (255, 255, 255), (int(ex), int(ey)), 1)
        elif isinstance(weapon, LaserCannon):
            pygame.draw.rect(surface, bright, (cx - 14, cy - 2, 28, 5))
            pygame.draw.line(surface, (255, 255, 255), (cx - 12, cy), (cx + 12, cy), 1)
        elif isinstance(weapon, HomingMissile):
            # Missile body
            pygame.draw.polygon(surface, bright,
                                [(cx + 12, cy), (cx + 6, cy - 4), (cx - 8, cy - 3),
                                 (cx - 8, cy + 3), (cx + 6, cy + 4)])
            # Fins
            dim = (max(0, bright[0] - 60), max(0, bright[1] - 60), max(0, bright[2] - 60))
            pygame.draw.polygon(surface, dim,
                                [(cx - 8, cy - 3), (cx - 12, cy - 8), (cx - 5, cy - 2)])
            pygame.draw.polygon(surface, dim,
                                [(cx - 8, cy + 3), (cx - 12, cy + 8), (cx - 5, cy + 2)])
            # Target crosshair
            cr = 5
            tcx, tcy = cx - 2, cy - 10
            pygame.draw.circle(surface, bright, (tcx, tcy), cr, 1)
            pygame.draw.line(surface, bright, (tcx - cr - 1, tcy), (tcx + cr + 1, tcy), 1)
            pygame.draw.line(surface, bright, (tcx, tcy - cr - 1), (tcx, tcy + cr + 1), 1)

    def _draw_shield_icon(self, display, x, y, active):
        sz = self.ICON_SIZE
        rd = self.ICON_RADIUS
        icon = pygame.Surface((sz, sz), pygame.SRCALPHA)
        if active:
            pygame.draw.rect(icon, (40, 100, 180, 140), (0, 0, sz, sz), border_radius=rd)
            t = pygame.time.get_ticks() / 1000
            pulse = 0.7 + 0.3 * math.sin(t * 4)
            border_a = int(220 * pulse)
            pygame.draw.rect(icon, (80, 180, 255, border_a), (0, 0, sz, sz), 3, border_radius=rd)
        else:
            pygame.draw.rect(icon, (30, 30, 35, 180), (0, 0, sz, sz), border_radius=rd)
            pygame.draw.rect(icon, (70, 70, 75, 150), (0, 0, sz, sz), 2, border_radius=rd)
        cx, cy = sz // 2, sz // 2
        sc = (80, 200, 255) if active else (80, 80, 80)
        points = [
            (cx, cy - 12), (cx + 10, cy - 6), (cx + 10, cy + 4),
            (cx + 5, cy + 10), (cx, cy + 13),
            (cx - 5, cy + 10), (cx - 10, cy + 4), (cx - 10, cy - 6),
        ]
        pygame.draw.polygon(icon, sc, points)
        pygame.draw.polygon(icon, (min(255, sc[0] + 60), min(255, sc[1] + 60),
                                   min(255, sc[2] + 60)), points, 2)
        display.blit(icon, (x, y))

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
        font = self.game.get_font(16)
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
        font = self.game.get_font(18)
        txt = font.render("?", True, (80, 80, 80))
        icon.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2))
        display.blit(icon, (x, y))

    def render(self, display):
        display.blit(self.background, (0, 0))

        for p in self.particles:
            p.draw(display)

        if self.boss_phase:
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

        # Weapon icon HUD
        player = self.game.player
        hud_x = 10
        hud_y = 8
        step = self.ICON_SIZE + self.ICON_PAD
        hint_y = hud_y + self.ICON_SIZE + 18
        hint_font = self.game.get_font(13)

        self._draw_weapon_icon(display, hud_x, hud_y, player.primary,
                               fill_ratio=1.0, glowing=player.auto_fire)

        # Primary key hint
        if player.auto_fire:
            htxt = hint_font.render("AUTO", True, (80, 255, 80))
        else:
            htxt = hint_font.render("SPACE", True, (140, 140, 150))
        display.blit(htxt, (hud_x + self.ICON_SIZE // 2 - htxt.get_width() // 2,
                            hint_y))

        ix = hud_x + step
        if player.secondary_inventory:
            from objects.Player import (SEC_READY, SEC_ACTIVE, SEC_COOLDOWN,
                                        SECONDARY_CYCLE, SECONDARY_ACTIVE_PER_LEVEL)
            first_sec_x = ix
            for weapon_cls in player.secondary_inventory:
                is_active = player.secondary and type(player.secondary) is weapon_cls
                if is_active:
                    sec = player.secondary
                    if player.sec_state == SEC_ACTIVE:
                        self._draw_weapon_icon(display, ix, hud_y, sec,
                                               fill_ratio=1.0, glowing=True)
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
                    else:
                        self._draw_weapon_icon(display, ix, hud_y, sec, fill_ratio=1.0)
                    if len(player.secondary_inventory) > 1:
                        acx = ix + self.ICON_SIZE // 2
                        acy = hud_y + self.ICON_SIZE + 2
                        if player.sec_state == SEC_COOLDOWN:
                            acy += 8
                        pygame.draw.polygon(display, (255, 255, 100),
                                            [(acx - 4, acy + 5),
                                             (acx + 4, acy + 5),
                                             (acx, acy)])
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
                        self._draw_cooldown_text(display, ix, hud_y, ws["timer"])
                    else:
                        self._draw_weapon_icon(display, ix, hud_y, tmp,
                                               fill_ratio=1.0, greyed=True)
                ix += step

            # Secondary key hints
            sec_count = len(player.secondary_inventory)
            sec_mid = first_sec_x + (sec_count * step - self.ICON_PAD) // 2
            parts = ["SHIFT"]
            if sec_count > 1:
                parts.append("Q")
            hint_str = " \u00b7 ".join(parts)
            htxt = hint_font.render(hint_str, True, (140, 140, 150))
            display.blit(htxt, (sec_mid - htxt.get_width() // 2, hint_y))
            ix_after = first_sec_x + sec_count * step
        else:
            self._draw_empty_icon(display, ix, hud_y)
            ix_after = ix + step

        self._draw_shield_icon(display, ix_after, hud_y, player.has_shield)

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
