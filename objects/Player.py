import math

import pygame, os

from objects.Projectile import Projectile
from objects.Weapon import StraightCannon

PLAYER_WIDTH, PLAYER_HEIGHT = 80, 35
PLAYER_CENTER_OFFSET_X = PLAYER_WIDTH // 2
PLAYER_CENTER_OFFSET_Y = PLAYER_HEIGHT // 2
CANNON_PAD = 10

SECONDARY_CYCLE = 10.0
SECONDARY_ACTIVE_PER_LEVEL = 3.0

SEC_READY = "ready"
SEC_ACTIVE = "active"
SEC_COOLDOWN = "cooldown"


class Player:
    def __init__(self, game):
        self.game = game
        self.load_sprites()
        self.position_x, self.position_y = 100, self.game.GAME_HEIGHT / 2
        self.current_frame, self.last_frame_update = 0, 0
        self.player_speed = 300
        self.primary_fire_rate = 0.5
        self.primary_cooldown = 0
        self.secondary_shot_cooldown = 0
        self.primary = StraightCannon()
        self.secondary = None
        self.secondary_levels = {}
        self.secondary_inventory = []
        self.sec_weapon_states = {}
        self.sec_state = SEC_READY
        self.sec_state_timer = 0
        self.auto_fire = False
        self.has_shield = False
        self.shield_flash = 0
        self._build_sprites()

    # ---- secondary weapon management ----

    def set_secondary(self, weapon_cls):
        """Equip a secondary weapon. Remembers levels of previous weapons."""
        if self.secondary:
            cur = type(self.secondary)
            self.secondary_levels[cur] = self.secondary.level
            self.sec_weapon_states[cur] = {
                "state": self.sec_state, "timer": self.sec_state_timer,
                "shot_cooldown": self.secondary_shot_cooldown,
            }
        new_weapon = weapon_cls()
        new_weapon.level = self.secondary_levels.get(weapon_cls, 1)
        self.secondary = new_weapon
        self.secondary_levels[weapon_cls] = new_weapon.level
        if weapon_cls not in self.secondary_inventory:
            self.secondary_inventory.append(weapon_cls)
        self.sec_state = SEC_READY
        self.sec_state_timer = 0
        self.secondary_shot_cooldown = 0
        self.sec_weapon_states[weapon_cls] = {
            "state": SEC_READY, "timer": 0, "shot_cooldown": 0,
        }
        self._build_sprites()

    def _cycle_secondary(self):
        """Rotate to the next collected secondary weapon with independent cooldowns."""
        if len(self.secondary_inventory) <= 1:
            return
        cur_cls = type(self.secondary)
        self.secondary_levels[cur_cls] = self.secondary.level
        self.sec_weapon_states[cur_cls] = {
            "state": self.sec_state, "timer": self.sec_state_timer,
            "shot_cooldown": self.secondary_shot_cooldown,
        }
        current_idx = self.secondary_inventory.index(cur_cls)
        next_idx = (current_idx + 1) % len(self.secondary_inventory)
        next_cls = self.secondary_inventory[next_idx]
        new_weapon = next_cls()
        new_weapon.level = self.secondary_levels.get(next_cls, 1)
        self.secondary = new_weapon
        ws = self.sec_weapon_states.get(next_cls, {
            "state": SEC_READY, "timer": 0, "shot_cooldown": 0,
        })
        self.sec_state = ws["state"]
        self.sec_state_timer = ws["timer"]
        self.secondary_shot_cooldown = ws.get("shot_cooldown", 0)
        self._build_sprites()

    def upgrade_secondary(self):
        if self.secondary and self.secondary.upgrade():
            self.secondary_levels[type(self.secondary)] = self.secondary.level
            return True
        return False

    # ---- sprite compositing ----

    def _build_sprites(self):
        """Rebuild working sprite lists, compositing cannon module when equipped."""
        if self.secondary:
            cannon = self._make_cannon(self.secondary.color)
            self.stationary = [self._composite(s, cannon) for s in self._base_stationary]
            self.flames = [self._composite(s, cannon) for s in self._base_flames]
        else:
            self.stationary = list(self._base_stationary)
            self.flames = list(self._base_flames)
        self.stationary_masks = [pygame.mask.from_surface(s) for s in self.stationary]
        self.flames_masks = [pygame.mask.from_surface(s) for s in self.flames]
        self.curr_anim_list = self.stationary
        self.curr_masks = self.stationary_masks
        self.current_frame = 0
        self.curr_image = self.stationary[0]
        self.mask = self.stationary_masks[0]

    @staticmethod
    def _make_cannon(color):
        c = pygame.Color(color)
        w, h = 30, 8
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surf, c, (0, 0, w, h), border_radius=3)
        bright = tuple(min(255, v + 60) for v in c[:3])
        pygame.draw.rect(surf, bright, (2, 2, w - 4, h - 4), border_radius=2)
        pygame.draw.rect(surf, (200, 200, 200), (w - 8, 1, 8, h - 2), border_radius=2)
        return surf

    @staticmethod
    def _composite(base, cannon):
        new_h = base.get_height() + CANNON_PAD
        comp = pygame.Surface((base.get_width(), new_h), pygame.SRCALPHA)
        comp.blit(base, (0, 0))
        cx = base.get_width() - cannon.get_width() - 2
        cy = base.get_height() + 1
        comp.blit(cannon, (cx, cy))
        return comp

    # ---- update / render ----

    def update(self, delta_time, actions):
        direction_x = actions["right"] - actions["left"]
        direction_y = actions["down"] - actions["up"]
        self.position_x += self.player_speed * delta_time * direction_x
        self.position_y += self.player_speed * delta_time * direction_y
        self.position_x = max(0, min(self.position_x, self.game.GAME_WIDTH * 4 / 5))
        self.position_y = max(
            0, min(self.position_y, self.game.GAME_HEIGHT - self.curr_image.get_height())
        )
        self.animate(delta_time, direction_x, direction_y)
        if self.primary_cooldown > 0:
            self.primary_cooldown -= delta_time
        if self.secondary_shot_cooldown > 0:
            self.secondary_shot_cooldown -= delta_time

        if actions.get("toggle_autofire"):
            self.auto_fire = not self.auto_fire
            actions["toggle_autofire"] = False

        should_fire = actions["space"]
        if not should_fire and self.auto_fire:
            should_fire = (self.game.active_game_world is not None
                           and not self.game.paused)

        if should_fire and self.primary_cooldown <= 0:
            muzzle_x = self.position_x + PLAYER_WIDTH
            muzzle_y = self.position_y + PLAYER_HEIGHT / 2
            self._spawn_projectiles(self.primary, muzzle_x, muzzle_y)
            self.game.play_sound("shoot")
            self.primary_cooldown = self.primary_fire_rate

        self._update_secondary(delta_time, actions)

    def _sec_active_duration(self):
        if not self.secondary:
            return 0
        return self.secondary.level * SECONDARY_ACTIVE_PER_LEVEL

    def _sec_cooldown_duration(self):
        return max(1.0, SECONDARY_CYCLE - self._sec_active_duration())

    def _update_secondary(self, dt, actions):
        if actions.get("cycle_weapon"):
            if self.secondary and len(self.secondary_inventory) > 1:
                self._cycle_secondary()
            actions["cycle_weapon"] = False

        # Tick background timers for non-selected weapons
        active_cls = type(self.secondary) if self.secondary else None
        muzzle_x = self.position_x + PLAYER_WIDTH
        sec_y = self.position_y + PLAYER_HEIGHT + CANNON_PAD / 2
        for cls, ws in self.sec_weapon_states.items():
            if cls == active_cls:
                continue
            if ws["state"] == SEC_COOLDOWN:
                ws["timer"] -= dt
                if ws["timer"] <= 0:
                    ws["state"] = SEC_READY
                    ws["timer"] = 0
            elif ws["state"] == SEC_ACTIVE:
                ws["timer"] -= dt
                ws["shot_cooldown"] = ws.get("shot_cooldown", 0) - dt
                if ws["timer"] <= 0:
                    wlevel = self.secondary_levels.get(cls, 1)
                    cd = max(1.0, SECONDARY_CYCLE - wlevel * SECONDARY_ACTIVE_PER_LEVEL)
                    ws["state"] = SEC_COOLDOWN
                    ws["timer"] = cd
                elif ws["shot_cooldown"] <= 0:
                    tmp = cls()
                    tmp.level = self.secondary_levels.get(cls, 1)
                    self._spawn_projectiles(tmp, muzzle_x, sec_y)
                    self.game.play_sound(tmp.sound_name)
                    ws["shot_cooldown"] = tmp.fire_rate

        if not self.secondary:
            return

        if self.sec_state == SEC_READY:
            if actions["secondary"]:
                self.sec_state = SEC_ACTIVE
                self.sec_state_timer = self._sec_active_duration()
                self.secondary_shot_cooldown = 0

        if self.sec_state == SEC_ACTIVE:
            self.sec_state_timer -= dt
            if self.sec_state_timer <= 0:
                self.sec_state = SEC_COOLDOWN
                self.sec_state_timer = self._sec_cooldown_duration()
            elif self.secondary_shot_cooldown <= 0:
                muzzle_x = self.position_x + PLAYER_WIDTH
                sec_y = self.position_y + PLAYER_HEIGHT + CANNON_PAD / 2
                self._spawn_projectiles(self.secondary, muzzle_x, sec_y)
                self.game.play_sound(self.secondary.sound_name)
                self.secondary_shot_cooldown = self.secondary.fire_rate

        elif self.sec_state == SEC_COOLDOWN:
            self.sec_state_timer -= dt
            if self.sec_state_timer <= 0:
                self.sec_state = SEC_READY
                self.sec_state_timer = 0

        self.sec_weapon_states[active_cls] = {
            "state": self.sec_state, "timer": self.sec_state_timer,
            "shot_cooldown": self.secondary_shot_cooldown,
        }

    def _spawn_projectiles(self, weapon, mx, my):
        for spec in weapon.get_projectiles(mx, my, game=self.game):
            kwargs = {k: v for k, v in spec.items() if k not in ("x", "y")}
            self.game.projectiles.add(
                Projectile(weapon.color, spec["x"], spec["y"], self.game, **kwargs)
            )

    def render(self, display):
        display.blit(self.curr_image, (self.position_x, self.position_y))
        if self.has_shield:
            cx = int(self.position_x) + self.curr_image.get_width() // 2
            cy = int(self.position_y) + self.curr_image.get_height() // 2
            r = max(self.curr_image.get_width(), self.curr_image.get_height()) // 2 + 6
            pulse = int(25 + 15 * math.sin(pygame.time.get_ticks() * 0.005))
            shield_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            sc = r + 2
            pygame.draw.circle(shield_surf, (80, 180, 255, pulse), (sc, sc), r, 3)
            pygame.draw.circle(shield_surf, (180, 220, 255, pulse // 2), (sc, sc), r - 2, 1)
            display.blit(shield_surf, (cx - sc, cy - sc))
        if self.shield_flash > 0:
            self.shield_flash -= 1

    def animate(self, delta_time, direction_x, direction_y):
        self.last_frame_update += delta_time
        if direction_x or direction_y:
            self.curr_anim_list = self.flames
            self.curr_masks = self.flames_masks
        else:
            self.curr_anim_list = self.stationary
            self.curr_masks = self.stationary_masks

        if self.last_frame_update > 0.15:
            self.last_frame_update = 0
            self.current_frame = (self.current_frame + 1) % len(self.curr_anim_list)
            self.curr_image = self.curr_anim_list[self.current_frame]
            self.mask = self.curr_masks[self.current_frame]

    def load_sprites(self):
        self.sprite_dir = os.path.join(self.game.sprite_dir, "ship")
        self._base_stationary, self._base_flames = [], []
        self._base_stationary.append(
            pygame.transform.scale(
                pygame.image.load(
                    os.path.join(self.sprite_dir, "ship_0.png")
                ).convert_alpha(),
                (PLAYER_WIDTH, PLAYER_HEIGHT),
            )
        )
        for i in range(1, 4):
            self._base_flames.append(
                pygame.transform.scale(
                    pygame.image.load(
                        os.path.join(self.sprite_dir, "ship_flames_" + str(i) + ".png")
                    ).convert_alpha(),
                    (PLAYER_WIDTH, PLAYER_HEIGHT),
                )
            )
