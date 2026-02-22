import pygame
from states.game_world import Game_World, BASE_UPGRADE_CHANCE, UPGRADE_CHANCE_DECAY
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
    assert game.player.primary.level == 1
    gw._apply_upgrade(_make_pickup(None, game))
    assert game.player.primary.level == 2


def test_primary_upgrade_max(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    game.player.primary.level = game.player.primary.max_level
    gw._apply_upgrade(_make_pickup(None, game))
    assert "MAX" in gw.upgrade_msg


# ---- secondary weapon pickups ----

def test_secondary_pickup_equips_weapon(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    assert game.player.secondary is None
    gw._apply_upgrade(_make_pickup(SpreadShot, game))
    assert isinstance(game.player.secondary, SpreadShot)


def test_secondary_same_type_upgrades(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    game.player.set_secondary(SpreadShot)
    assert game.player.secondary.level == 1
    gw._apply_upgrade(_make_pickup(SpreadShot, game))
    assert game.player.secondary.level == 2


def test_secondary_different_type_switches(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    game.player.set_secondary(SpreadShot)
    gw._apply_upgrade(_make_pickup(LaserCannon, game))
    assert isinstance(game.player.secondary, LaserCannon)


def test_secondary_first_pickup_is_level_1(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    game.player.set_secondary(SpreadShot)
    gw._apply_upgrade(_make_pickup(LaserCannon, game))
    assert isinstance(game.player.secondary, LaserCannon)
    assert game.player.secondary.level == 1


def test_secondary_switch_back_levels_up(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    game.player.set_secondary(SpreadShot)
    gw._apply_upgrade(_make_pickup(LaserCannon, game))
    assert game.player.secondary.level == 1
    gw._apply_upgrade(_make_pickup(SpreadShot, game))
    assert isinstance(game.player.secondary, SpreadShot)
    assert game.player.secondary.level == 2


def test_secondary_level_remembered(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    game.player.set_secondary(SpreadShot)
    game.player.upgrade_secondary()
    assert game.player.secondary.level == 2
    game.player.set_secondary(LaserCannon)
    assert isinstance(game.player.secondary, LaserCannon)
    game.player.set_secondary(SpreadShot)
    assert game.player.secondary.level == 2


def test_upgrade_count_increments(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    assert gw.upgrade_count == 0
    gw._apply_upgrade(_make_pickup(None, game))
    assert gw.upgrade_count == 1
    gw._apply_upgrade(_make_pickup(SpreadShot, game))
    assert gw.upgrade_count == 2


def test_upgrade_message_set(game):
    gw = Game_World(game)
    gw.game.state_stack.append(gw)
    gw._apply_upgrade(_make_pickup(None, game))
    assert gw.upgrade_msg_timer > 0
    assert gw.upgrade_msg != ""


def test_pickup_type_distribution():
    """random_pickup_type should return None or a secondary weapon class."""
    gw_cls = Game_World
    results = {None: 0}
    for cls in SECONDARY_WEAPONS:
        results[cls] = 0
    import random
    random.seed(42)
    for _ in range(1000):
        t = gw_cls._random_pickup_type()
        assert t is None or t in SECONDARY_WEAPONS
        results[t] += 1
    assert results[None] > 100
    for cls in SECONDARY_WEAPONS:
        assert results[cls] > 100
