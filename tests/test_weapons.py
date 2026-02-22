from objects.Weapon import (
    Weapon, StraightCannon, SpreadShot, LaserCannon, SECONDARY_WEAPONS,
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


class TestLaserCannon:
    def test_level1_single_beam(self):
        w = LaserCannon()
        projs = w.get_projectiles(100, 200)
        assert len(projs) == 1
        assert projs[0]["piercing"] is True

    def test_level2_adds_beams(self):
        w = LaserCannon()
        w.level = 2
        projs = w.get_projectiles(100, 200)
        assert len(projs) == 3
        assert all(p["piercing"] for p in projs)

    def test_level3_adds_more_and_shiny(self):
        w = LaserCannon()
        w.level = 3
        projs = w.get_projectiles(100, 200)
        assert len(projs) == 5
        assert all(p.get("shiny") for p in projs)
        assert projs[0]["width"] > 60

    def test_levels_additive(self):
        w = LaserCannon()
        prev = 0
        for lv in range(1, 4):
            w.level = lv
            count = len(w.get_projectiles(100, 200))
            assert count >= prev
            prev = count


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
        assert len(SECONDARY_WEAPONS) == 2
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
