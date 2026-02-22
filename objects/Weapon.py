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

    def get_projectiles(self, x, y):
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

    def get_projectiles(self, x, y):
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
    """Secondary: fires in a fan pattern. Each level widens the fan."""

    name = "Spread Shot"
    color = "cyan"
    fire_rate = 1.8
    sound_name = "spread"

    def get_projectiles(self, x, y):
        shiny = self.level >= self.max_level
        projs = [{"x": x, "y": y, "dx": 8}]
        if self.level >= 2:
            projs.append({"x": x, "y": y, "dx": 7, "dy": -2})
            projs.append({"x": x, "y": y, "dx": 7, "dy": 2})
        if self.level >= 3:
            projs.append({"x": x, "y": y, "dx": 5, "dy": -4})
            projs.append({"x": x, "y": y, "dx": 5, "dy": 4})
        if shiny:
            for p in projs:
                p["shiny"] = True
        return projs


class LaserCannon(Weapon):
    """Secondary: piercing laser beams. Each level adds more beams."""

    name = "Laser Cannon"
    color = "lime"
    fire_rate = 2.5
    sound_name = "laser"

    def get_projectiles(self, x, y):
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


SECONDARY_WEAPONS = [SpreadShot, LaserCannon]
