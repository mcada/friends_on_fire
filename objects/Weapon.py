import math


class Weapon:
    """Base class for all weapons. Subclass and override get_projectiles().

    get_projectiles() returns a list of dicts.  Each dict must contain
    "x" and "y"; all other keys are forwarded as kwargs to Projectile().
    Every level must be a strict superset of the previous one.
    """

    name = ""
    color = ""
    max_level = 3

    def __init__(self):
        self.level = 1

    def get_projectiles(self, x, y, game=None):
        raise NotImplementedError

    def upgrade(self):
        if self.level < self.max_level:
            self.level += 1
            return True
        return False

    def is_max_level(self):
        return self.level >= self.max_level


# ---------------------------------------------------------------------------
# Primary weapon -- always equipped, upgrades via gold pickups
# ---------------------------------------------------------------------------

class StraightCannon(Weapon):
    """Primary weapon. Each level adds projectiles on top of the previous."""

    name = "Primary"
    color = "crimson"
    max_level = 5

    def get_projectiles(self, x, y, game=None):
        shiny = self.level >= self.max_level
        projs = [{"x": x, "y": y, "dx": 8}]
        if self.level >= 2:
            projs.append({"x": x, "y": y - 14, "dx": 8})
            projs.append({"x": x, "y": y + 14, "dx": 8})
        if self.level >= 3:
            projs.append({"x": x, "y": y, "dx": 7, "dy": -1})
            projs.append({"x": x, "y": y, "dx": 7, "dy": 1})
        if self.level >= 4:
            projs.append({"x": x, "y": y - 28, "dx": 8})
            projs.append({"x": x, "y": y + 28, "dx": 8})
        if shiny:
            for p in projs:
                p["shiny"] = True
        return projs


# ---------------------------------------------------------------------------
# Secondary weapons -- obtained from colored pickups, one active at a time
# ---------------------------------------------------------------------------

class SpreadShot(Weapon):
    """Secondary: fires pulse orbs that spread across distinct targets."""

    name = "Pulse Spread"
    color = "orchid"
    fire_rate = 1.8
    sound_name = "spread"
    _SPEED = 8
    _MAX_AIM_ANGLE = math.pi / 3
    _FAN = [0, -0.28, 0.28, -0.68, 0.68]

    def _proj_count(self):
        if self.level >= 3:
            return 5
        if self.level >= 2:
            return 3
        return 1

    def get_projectiles(self, x, y, game=None):
        shiny = self.level >= self.max_level
        n = self._proj_count()
        angles = self._smart_angles(x, y, n, game) if game else self._fan_angles(n)
        pw, ph = 24, 24
        projs = []
        for a in angles:
            dx = self._SPEED * math.cos(a)
            dy = self._SPEED * math.sin(a)
            p = {"x": x, "y": y, "dx": dx, "dy": dy,
                 "pulse": True, "width": pw, "height": ph}
            if shiny:
                p["shiny"] = True
            projs.append(p)
        return projs

    def _fan_angles(self, n):
        return self._FAN[:n]

    def _smart_angles(self, x, y, n, game):
        targets = self._find_targets(x, y, game)
        if not targets:
            return self._fan_angles(n)

        targets.sort(key=lambda t: (t.rect.centerx - x) ** 2
                                   + (t.rect.centery - y) ** 2)

        assigned = []
        used = set()
        for _ in range(n):
            for t in targets:
                tid = id(t)
                if tid not in used:
                    a = math.atan2(t.rect.centery - y, t.rect.centerx - x)
                    a = max(-self._MAX_AIM_ANGLE, min(self._MAX_AIM_ANGLE, a))
                    assigned.append(a)
                    used.add(tid)
                    break
            else:
                break

        while len(assigned) < n:
            fan = self._fan_angles(n)
            assigned.append(fan[len(assigned)])

        return assigned

    @staticmethod
    def _find_targets(x, y, game):
        targets = [r for r in game.rocks if r.rect.centerx > x - 50]
        from states.game_world import Game_World
        gw = next((s for s in game.state_stack if isinstance(s, Game_World)), None)
        if gw and gw.boss and gw.boss.alive_flag:
            targets.append(gw.boss)
        return targets


class LaserCannon(Weapon):
    """Secondary: piercing laser beams. Each level adds more beams."""

    name = "Laser Cannon"
    color = "lime"
    fire_rate = 2.5
    sound_name = "laser"

    def get_projectiles(self, x, y, game=None):
        shiny = self.level >= self.max_level
        projs = [{"x": x, "y": y, "dx": 10, "width": 60, "height": 6, "piercing": True}]
        if self.level >= 2:
            projs.append({"x": x, "y": y - 16, "dx": 10, "width": 60, "height": 6, "piercing": True})
            projs.append({"x": x, "y": y + 16, "dx": 10, "width": 60, "height": 6, "piercing": True})
        if self.level >= 3:
            projs[0]["width"] = 80
            projs[0]["height"] = 10
            projs.append({"x": x, "y": y - 32, "dx": 9, "dy": 1, "width": 50, "height": 5, "piercing": True})
            projs.append({"x": x, "y": y + 32, "dx": 9, "dy": -1, "width": 50, "height": 5, "piercing": True})
        if shiny:
            for p in projs:
                p["shiny"] = True
        return projs


class HomingMissile(Weapon):
    """Secondary: homing missiles that track enemies. Each level adds missiles."""

    name = "Homing Missile"
    color = "orange"
    fire_rate = 2.0
    sound_name = "missile"

    def get_projectiles(self, x, y, game=None):
        shiny = self.level >= self.max_level
        projs = [{"x": x, "y": y, "dx": 5, "dy": -1, "homing": True,
                  "width": 14, "height": 8}]
        if self.level >= 2:
            projs.append({"x": x, "y": y - 12, "dx": 5, "dy": -2, "homing": True,
                          "width": 14, "height": 8})
            projs.append({"x": x, "y": y + 12, "dx": 5, "dy": 2, "homing": True,
                          "width": 14, "height": 8})
        if self.level >= 3:
            projs.append({"x": x, "y": y - 24, "dx": 4, "dy": -3, "homing": True,
                          "width": 14, "height": 8})
            projs.append({"x": x, "y": y + 24, "dx": 4, "dy": 3, "homing": True,
                          "width": 14, "height": 8})
        if shiny:
            for p in projs:
                p["shiny"] = True
        return projs


SECONDARY_WEAPONS = [SpreadShot, LaserCannon, HomingMissile]
