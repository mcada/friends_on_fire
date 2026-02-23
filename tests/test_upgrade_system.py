import pygame
from states.game_world import (Game_World, BASE_UPGRADE_CHANCE, UPGRADE_CHANCE_DECAY,
                               ENEMY_UPGRADE_CHANCE, ENEMY_SECONDARY_WEIGHT)
from objects.Weapon import StraightCannon, SpreadShot, LaserCannon, SECONDARY_WEAPONS


# ---- chance mechanics ----

def test_upgrade_chance_decreases_with_count(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    c0 = gw._upgrade_chance()
    gw.upgrade_count = 3
    assert gw._upgrade_chance() < c0


def test_upgrade_chance_never_zero(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    gw.upgrade_count = 100
    assert gw._upgrade_chance() > 0


def test_upgrade_chance_formula(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    gw.upgrade_count = 2
    expected = BASE_UPGRADE_CHANCE / (1 + 2 * UPGRADE_CHANCE_DECAY)
    assert abs(gw._upgrade_chance() - expected) < 1e-9


# ---- primary upgrades ----

def _make_pickup(weapon_cls, game):
    from objects.Pickup import UpgradePickup
    return UpgradePickup(400, 300, weapon_cls, game)


def test_primary_upgrade_increases_level(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    p = game.players[0]
    assert p.primary.level == 1
    gw._apply_upgrade(_make_pickup(None, game), p)
    assert p.primary.level == 2


def test_primary_upgrade_max(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    p = game.players[0]
    p.primary.level = p.primary.max_level
    gw._apply_upgrade(_make_pickup(None, game), p)
    assert "MAX" in gw.upgrade_msg


# ---- secondary weapon pickups ----

def test_secondary_pickup_equips_weapon(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    p = game.players[0]
    assert p.secondary is None
    gw._apply_upgrade(_make_pickup(SpreadShot, game), p)
    assert isinstance(p.secondary, SpreadShot)


def test_secondary_same_type_upgrades(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    p = game.players[0]
    p.set_secondary(SpreadShot)
    assert p.secondary.level == 1
    gw._apply_upgrade(_make_pickup(SpreadShot, game), p)
    assert p.secondary.level == 2


def test_secondary_different_type_switches(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    p = game.players[0]
    p.set_secondary(SpreadShot)
    gw._apply_upgrade(_make_pickup(LaserCannon, game), p)
    assert isinstance(p.secondary, LaserCannon)


def test_secondary_first_pickup_is_level_1(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    p = game.players[0]
    p.set_secondary(SpreadShot)
    gw._apply_upgrade(_make_pickup(LaserCannon, game), p)
    assert isinstance(p.secondary, LaserCannon)
    assert p.secondary.level == 1


def test_secondary_switch_back_levels_up(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    p = game.players[0]
    p.set_secondary(SpreadShot)
    gw._apply_upgrade(_make_pickup(LaserCannon, game), p)
    assert p.secondary.level == 1
    gw._apply_upgrade(_make_pickup(SpreadShot, game), p)
    assert isinstance(p.secondary, SpreadShot)
    assert p.secondary.level == 2


def test_secondary_level_remembered(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    game.players[0].set_secondary(SpreadShot)
    game.players[0].upgrade_secondary()
    assert game.players[0].secondary.level == 2
    game.players[0].set_secondary(LaserCannon)
    assert isinstance(game.players[0].secondary, LaserCannon)
    game.players[0].set_secondary(SpreadShot)
    assert game.players[0].secondary.level == 2


def test_upgrade_count_increments(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    p = game.players[0]
    assert gw.upgrade_count == 0
    gw._apply_upgrade(_make_pickup(None, game), p)
    assert gw.upgrade_count == 1
    gw._apply_upgrade(_make_pickup(SpreadShot, game), p)
    assert gw.upgrade_count == 2


def test_upgrade_message_set(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    p = game.players[0]
    gw._apply_upgrade(_make_pickup(None, game), p)
    assert gw.upgrade_msg_timer > 0
    assert gw.upgrade_msg != ""


def test_enemy_pickup_type_distribution():
    """Enemy drops should return None (primary) or a secondary weapon class."""
    gw_cls = Game_World
    results = {None: 0}
    for cls in SECONDARY_WEAPONS:
        results[cls] = 0
    import random
    random.seed(42)
    for _ in range(1000):
        t = gw_cls._random_enemy_pickup_type()
        assert t is None or t in SECONDARY_WEAPONS
        results[t] += 1
    assert results[None] > 50
    for cls in SECONDARY_WEAPONS:
        assert results[cls] > 50
