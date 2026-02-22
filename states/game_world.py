import pygame, os, random, math
from states.state import State
from states.pause_menu import PauseMenu
from objects.Rocks import Rock, BASIC, CLUSTER, IRON
from objects.Pickup import UpgradePickup
from objects.Weapon import StraightCannon, SECONDARY_WEAPONS

BASE_UPGRADE_CHANCE = 0.07
UPGRADE_CHANCE_DECAY = 0.35
PRIMARY_PICKUP_WEIGHT = 0.4


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
    def __init__(self, game):
        State.__init__(self, game)
        self.background = pygame.image.load(
            os.path.join(self.game.assets_dir, "bg.jpeg")
        )
        self.elapsed_time = 0
        self.rock_spawn_timer = 0
        self.rock_spawn_interval = 1.0
        self.game_over = False
        self.is_new_record = False
        self.asteroids_killed = 0
        self.particles = []

        self.upgrade_count = 0
        self.upgrade_msg = ""
        self.upgrade_msg_timer = 0

        self.game.rocks.empty()
        self.game.projectiles.empty()
        self.game.pickups.empty()
        player = self.game.player
        player.position_x = 100
        player.position_y = self.game.GAME_HEIGHT / 2
        player.primary = StraightCannon()
        player.secondary = None
        player.secondary_levels = {}
        player._build_sprites()
        self.game.play_music("game")

    # ---- asteroid type selection ----

    def _pick_asteroid_type(self):
        t = self.elapsed_time
        cluster_w = min(0.35, max(0, (t - 20) * 0.006))
        iron_w = min(0.30, max(0, (t - 45) * 0.004))
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
        return 15 + int(self.elapsed_time * 0.1)

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
            player.set_secondary(weapon_cls)
            self.upgrade_msg = f"{player.secondary.name} Lv{player.secondary.level}"

        self.upgrade_count += 1
        self.upgrade_msg_timer = 2.0

    # ---- particles ----

    def spawn_particles(self, x, y, count=8):
        for _ in range(count):
            self.particles.append(Particle(x, y))

    # ---- main loop ----

    def update(self, delta_time, actions):
        self.particles = [p for p in self.particles if p.update(delta_time)]

        if self.upgrade_msg_timer > 0:
            self.upgrade_msg_timer -= delta_time

        if self.game_over:
            if actions["start"] or actions["space"] or actions["escape"]:
                self.game.return_to_menu()
            self.game.reset_keys()
            return

        if actions["start"] or actions["escape"]:
            new_state = PauseMenu(self.game)
            new_state.enter_state()
            return

        self.elapsed_time += delta_time

        # Rock spawning
        self.rock_spawn_timer += delta_time
        if self.rock_spawn_timer >= self.rock_spawn_interval:
            self.rock_spawn_timer = 0
            cap = self._max_rocks()
            batch = 1 + int(self.elapsed_time // 40)
            batch = min(batch, 3)
            for _ in range(batch):
                if len(self.game.rocks) < cap:
                    self._spawn_asteroid()
            self.rock_spawn_interval = max(0.45, self.rock_spawn_interval - 0.01)

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
            if rock.rock_type == CLUSTER:
                self._spawn_fragments(rock)
            if self._should_spawn_upgrade():
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
                self._apply_upgrade(pickup)
                self.game.play_sound("powerup")
                pickup.kill()

        # Player-rock collision
        for rock in self.game.rocks:
            offset = (rock.rect.x - px, rock.rect.y - py)
            if player.mask.overlap(rock.mask, offset):
                self.game_over = True
                self.game.reset_keys()
                self.spawn_particles(rock.rect.centerx, rock.rect.centery, count=15)
                self.game.play_sound("death")
                self.game.stop_music()
                self.game.save_score(round(self.elapsed_time), self.asteroids_killed)
                self.is_new_record = (
                    self.game.high_scores
                    and self.game.high_scores[0]["kills"] == self.asteroids_killed
                    and self.game.high_scores[0]["time"] == round(self.elapsed_time)
                )
                break

    # ---- rendering ----

    def render(self, display):
        display.blit(self.background, (0, 0))

        for p in self.particles:
            p.draw(display)

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

        # Weapon HUD
        player = self.game.player
        self.game.draw_text(
            display,
            f"Primary Lv{player.primary.level}",
            pygame.Color(player.primary.color),
            90,
            20,
        )
        if player.secondary:
            self.game.draw_text(
                display,
                f"{player.secondary.name} Lv{player.secondary.level}",
                pygame.Color(player.secondary.color),
                90,
                44,
            )

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

        if self.game_over:
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
