from objects.Weapon import (
    Weapon, StraightCannon, SpreadShot, LaserCannon, HomingMissile,
    SECONDARY_WEAPONS,
)


class TestStraightCannon:
    def test_level1_single(self):
        w = StraightCannon()
        assert len(w.get_projectiles(100, 200)) == 1

    def test_level2_adds_parallel(self):
        w = StraightCannon()
        w.level = 2
        projs = w.get_projectiles(100, 200)
        assert len(projs) == 3

    def test_level3_adds_diagonals(self):
        w = StraightCannon()
        w.level = 3
        projs = w.get_projectiles(100, 200)
        assert len(projs) == 5
        dys = [p.get("dy", 0) for p in projs]
        assert any(d < 0 for d in dys) and any(d > 0 for d in dys)

    def test_level4_adds_outer(self):
        w = StraightCannon()
        w.level = 4
        assert len(w.get_projectiles(100, 200)) == 7

    def test_level5_same_count_but_shiny(self):
        w = StraightCannon()
        w.level = 5
        projs = w.get_projectiles(100, 200)
        assert len(projs) == 7
        assert all(p.get("shiny") for p in projs)

    def test_levels_are_additive(self):
        w = StraightCannon()
        prev_count = 0
        for lv in range(1, w.max_level + 1):
            w.level = lv
            count = len(w.get_projectiles(100, 200))
            assert count >= prev_count
            prev_count = count

    def test_not_shiny_before_max(self):
        w = StraightCannon()
        w.level = 4
        for p in w.get_projectiles(100, 200):
            assert not p.get("shiny", False)


class TestSpreadShot:
    def test_level1_single(self):
        w = SpreadShot()
        assert len(w.get_projectiles(100, 200)) == 1

    def test_level2_adds_diagonals(self):
        w = SpreadShot()
        w.level = 2
        projs = w.get_projectiles(100, 200)
        assert len(projs) == 3
        dys = [p.get("dy", 0) for p in projs]
        assert any(d < 0 for d in dys) and any(d > 0 for d in dys)

    def test_level3_adds_steep_and_shiny(self):
        w = SpreadShot()
        w.level = 3
        projs = w.get_projectiles(100, 200)
        assert len(projs) == 5
        assert all(p.get("shiny") for p in projs)

    def test_levels_additive(self):
        w = SpreadShot()
        prev = 0
        for lv in range(1, 4):
            w.level = lv
            count = len(w.get_projectiles(100, 200))
            assert count >= prev
            prev = count


class _FakeGame:
    GAME_WIDTH = 1280

class TestLaserCannon:
    def test_always_one_beam(self):
        w = LaserCannon()
        for lv in range(1, w.max_level + 1):
            w.level = lv
            assert len(w.get_projectiles(100, 200, game=_FakeGame())) == 1

    def test_beam_is_piercing_and_fullbeam(self):
        w = LaserCannon()
        p = w.get_projectiles(100, 200, game=_FakeGame())[0]
        assert p["piercing"] is True
        assert p["fullbeam"] is True

    def test_beam_spans_screen(self):
        w = LaserCannon()
        p = w.get_projectiles(100, 200, game=_FakeGame())[0]
        assert p["width"] >= _FakeGame.GAME_WIDTH - 100

    def test_beam_stationary(self):
        w = LaserCannon()
        p = w.get_projectiles(100, 200, game=_FakeGame())[0]
        assert p["dx"] == 0

    def test_beam_has_lifetime(self):
        w = LaserCannon()
        p = w.get_projectiles(100, 200, game=_FakeGame())[0]
        assert p["lifetime"] > 0

    def test_higher_level_beefier(self):
        w = LaserCannon()
        heights = []
        lifetimes = []
        for lv in range(1, w.max_level + 1):
            w.level = lv
            p = w.get_projectiles(100, 200, game=_FakeGame())[0]
            heights.append(p["height"])
            lifetimes.append(p["lifetime"])
        assert heights == sorted(heights)
        assert lifetimes == sorted(lifetimes)
        assert heights[-1] > heights[0]

    def test_level3_shiny(self):
        w = LaserCannon()
        w.level = 3
        p = w.get_projectiles(100, 200, game=_FakeGame())[0]
        assert p.get("shiny") is True

    def test_not_shiny_before_max(self):
        w = LaserCannon()
        w.level = 2
        p = w.get_projectiles(100, 200, game=_FakeGame())[0]
        assert not p.get("shiny", False)


class TestHomingMissile:
    def test_level1_single(self):
        w = HomingMissile()
        projs = w.get_projectiles(100, 200)
        assert len(projs) == 1
        assert projs[0]["homing"] is True

    def test_level2_adds_missiles(self):
        w = HomingMissile()
        w.level = 2
        projs = w.get_projectiles(100, 200)
        assert len(projs) == 3
        assert all(p["homing"] for p in projs)

    def test_level3_adds_more_and_shiny(self):
        w = HomingMissile()
        w.level = 3
        projs = w.get_projectiles(100, 200)
        assert len(projs) == 5
        assert all(p["shiny"] for p in projs)
        assert all(p["homing"] for p in projs)

    def test_levels_additive(self):
        w = HomingMissile()
        prev = len(w.get_projectiles(100, 200))
        for _ in range(w.max_level - 1):
            w.upgrade()
            cur = len(w.get_projectiles(100, 200))
            assert cur >= prev
            prev = cur

    def test_damage_is_2(self):
        w = HomingMissile()
        for lv in range(1, w.max_level + 1):
            w.level = lv
            for p in w.get_projectiles(100, 200):
                assert p["damage"] == 2

    def test_default_weapon_damage_is_1(self):
        for cls in [StraightCannon, SpreadShot]:
            w = cls()
            for p in w.get_projectiles(100, 200):
                assert p.get("damage", 1) == 1


class TestUpgradeMechanics:
    def test_upgrade_returns_true_when_not_max(self):
        w = StraightCannon()
        assert w.upgrade() is True
        assert w.level == 2

    def test_upgrade_returns_false_at_max(self):
        w = StraightCannon()
        w.level = w.max_level
        assert w.upgrade() is False

    def test_is_max_level(self):
        w = StraightCannon()
        assert not w.is_max_level()
        w.level = w.max_level
        assert w.is_max_level()

    def test_secondary_weapons_list(self):
        assert len(SECONDARY_WEAPONS) == 3
        for cls in SECONDARY_WEAPONS:
            assert cls.max_level == 3

    def test_weapon_colors_distinct(self):
        all_cls = [StraightCannon] + SECONDARY_WEAPONS
        colors = [cls.color for cls in all_cls]
        assert len(set(colors)) == len(colors)

    def test_all_weapons_return_dicts(self):
        for cls in [StraightCannon] + SECONDARY_WEAPONS:
            w = cls()
            for spec in w.get_projectiles(100, 200):
                assert isinstance(spec, dict)
                assert "x" in spec and "y" in spec

    def test_max_level_always_shiny(self):
        for cls in [StraightCannon] + SECONDARY_WEAPONS:
            w = cls()
            w.level = w.max_level
            for p in w.get_projectiles(100, 200):
                assert p.get("shiny") is True
