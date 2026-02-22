import pytest
import pygame
from states.game_world import Game_World
from objects.Rocks import Rock, BASIC, CLUSTER, IRON


def _enter_game_world(game):
    gw = Game_World(game)
    gw.enter_state()
    return gw


def _no_actions():
    return {
        "left": False, "right": False, "up": False, "down": False,
        "action1": False, "action2": False, "start": False, "space": False,
        "escape": False, "secondary": False,
    }


def test_rocks_spawn_after_interval(game):
    gw = _enter_game_world(game)
    actions = _no_actions()
    for _ in range(65):
        gw.update(1 / 60, actions)
    assert len(game.rocks) > 0


def test_spawn_interval_decreases(game):
    gw = _enter_game_world(game)
    initial = gw.rock_spawn_interval
    actions = _no_actions()
    gw.rock_spawn_timer = gw.rock_spawn_interval
    gw.update(1 / 60, actions)
    assert gw.rock_spawn_interval < initial


def test_spawn_interval_has_minimum(game):
    gw = _enter_game_world(game)
    gw.rock_spawn_interval = 0.45
    gw.rock_spawn_timer = 0.45
    actions = _no_actions()
    gw.update(1 / 60, actions)
    assert gw.rock_spawn_interval >= 0.45


def test_game_over_on_collision(game):
    gw = _enter_game_world(game)
    p = game.player
    p.position_x, p.position_y = 200, 200
    center_x = int(p.position_x) + 40
    center_y = int(p.position_y) + 17
    rock = Rock(center_x, center_y, 45, 35, game)
    game.rocks.add(rock)
    actions = _no_actions()
    gw.update(1 / 60, actions)
    assert gw.game_over is True


def test_game_over_requires_keypress(game):
    gw = _enter_game_world(game)
    gw.game_over = True
    stack_size = len(game.state_stack)
    actions = _no_actions()
    for _ in range(120):
        gw.update(1 / 60, actions)
    assert len(game.state_stack) == stack_size, "Should not auto-dismiss"


def test_game_over_dismisses_on_space(game):
    gw = _enter_game_world(game)
    gw.game_over = True
    actions = _no_actions()
    actions["space"] = True
    gw.update(1 / 60, actions)
    assert game.state_stack[-1] is not gw


def test_kill_count_increments(game):
    gw = _enter_game_world(game)
    assert gw.asteroids_killed == 0

    from objects.Projectile import Projectile

    rock = Rock(300, 300, 30, 30, game)
    game.rocks.add(rock)
    proj = Projectile("crimson", rock.rect.centerx, rock.rect.centery, game)
    game.projectiles.add(proj)

    actions = _no_actions()
    gw.update(1 / 60, actions)
    assert gw.asteroids_killed >= 1


def test_high_score_updates(game):
    game.high_scores = []
    gw = _enter_game_world(game)
    gw.elapsed_time = 10.0
    gw.asteroids_killed = 5
    gw.game_over = False

    p = game.player
    p.position_x, p.position_y = 200, 200
    center_x = int(p.position_x) + 40
    center_y = int(p.position_y) + 17
    rock = Rock(center_x, center_y, 45, 35, game)
    game.rocks.add(rock)

    actions = _no_actions()
    gw.update(1 / 60, actions)

    assert len(game.high_scores) == 1
    assert game.high_scores[0]["time"] == 10
    assert game.high_scores[0]["kills"] == 5


def test_elapsed_time_advances(game):
    gw = _enter_game_world(game)
    actions = _no_actions()
    gw.update(0.5, actions)
    assert gw.elapsed_time == pytest.approx(0.5, abs=0.01)


# ---- iron asteroid HP in combat ----

def test_iron_survives_single_shot(game):
    gw = _enter_game_world(game)
    from objects.Projectile import Projectile

    rock = Rock(300, 300, 45, 45, game, rock_type=IRON)
    game.rocks.add(rock)
    proj = Projectile("crimson", rock.rect.centerx, rock.rect.centery, game)
    game.projectiles.add(proj)

    actions = _no_actions()
    gw.update(1 / 60, actions)
    assert rock.hp == 2
    assert rock.alive()


def test_iron_destroyed_after_enough_hits(game):
    gw = _enter_game_world(game)
    from objects.Projectile import Projectile

    rock = Rock(300, 300, 45, 45, game, rock_type=IRON)
    game.rocks.add(rock)

    actions = _no_actions()
    for _ in range(3):
        proj = Projectile("crimson", rock.rect.centerx, rock.rect.centery, game)
        game.projectiles.add(proj)
        gw.update(1 / 60, actions)

    assert not rock.alive()
    assert gw.asteroids_killed >= 1


# ---- cluster fragmentation ----

def test_cluster_spawns_fragments(game):
    gw = _enter_game_world(game)
    from objects.Projectile import Projectile

    rock = Rock(300, 300, 50, 50, game, rock_type=CLUSTER)
    game.rocks.add(rock)
    proj = Projectile("crimson", rock.rect.centerx, rock.rect.centery, game)
    game.projectiles.add(proj)

    actions = _no_actions()
    gw.update(1 / 60, actions)

    assert not rock.alive()
    assert len(game.rocks) >= 2


def test_cluster_fragments_are_basic(game):
    gw = _enter_game_world(game)
    from objects.Projectile import Projectile

    rock = Rock(300, 300, 50, 50, game, rock_type=CLUSTER)
    game.rocks.add(rock)
    proj = Projectile("crimson", rock.rect.centerx, rock.rect.centery, game)
    game.projectiles.add(proj)

    actions = _no_actions()
    gw.update(1 / 60, actions)

    for frag in game.rocks:
        assert frag.rock_type == BASIC


# ---- difficulty scaling ----

def test_early_game_all_basic(game):
    gw = _enter_game_world(game)
    gw.elapsed_time = 5
    import random
    random.seed(42)
    types = [gw._pick_asteroid_type() for _ in range(100)]
    assert all(t == BASIC for t in types)


def test_late_game_has_variety(game):
    gw = _enter_game_world(game)
    gw.elapsed_time = 120
    import random
    random.seed(42)
    types = [gw._pick_asteroid_type() for _ in range(200)]
    assert CLUSTER in types
    assert IRON in types
    assert BASIC in types


# ---- shield system ----

def test_first_kill_drops_shield(game):
    gw = _enter_game_world(game)
    from objects.Projectile import Projectile

    rock = Rock(300, 300, 30, 30, game)
    game.rocks.add(rock)
    proj = Projectile("crimson", rock.rect.centerx, rock.rect.centery, game)
    game.projectiles.add(proj)

    actions = _no_actions()
    gw.update(1 / 60, actions)

    shield_pickups = [p for p in game.pickups if p.pickup_type == "shield"]
    assert len(shield_pickups) == 1


def test_shield_absorbs_hit(game):
    gw = _enter_game_world(game)
    p = game.player
    p.has_shield = True
    p.position_x, p.position_y = 200, 200
    center_x = int(p.position_x) + 40
    center_y = int(p.position_y) + 17
    rock = Rock(center_x, center_y, 45, 35, game)
    game.rocks.add(rock)

    actions = _no_actions()
    gw.update(1 / 60, actions)

    assert gw.game_over is False
    assert p.has_shield is False


def test_shield_destroys_rock_on_hit(game):
    gw = _enter_game_world(game)
    p = game.player
    p.has_shield = True
    p.position_x, p.position_y = 200, 200
    center_x = int(p.position_x) + 40
    center_y = int(p.position_y) + 17
    rock = Rock(center_x, center_y, 45, 35, game)
    game.rocks.add(rock)

    actions = _no_actions()
    gw.update(1 / 60, actions)
    assert not rock.alive()


def test_no_shield_means_death(game):
    gw = _enter_game_world(game)
    p = game.player
    p.has_shield = False
    p.position_x, p.position_y = 200, 200
    center_x = int(p.position_x) + 40
    center_y = int(p.position_y) + 17
    rock = Rock(center_x, center_y, 45, 35, game)
    game.rocks.add(rock)

    actions = _no_actions()
    gw.update(1 / 60, actions)
    assert gw.game_over is True


def test_shield_pity_chance_grows(game):
    gw = _enter_game_world(game)
    base = gw._shield_chance()
    gw.kills_since_shield = 30
    assert gw._shield_chance() > base


def test_shield_no_drop_when_already_shielded(game):
    gw = _enter_game_world(game)
    game.player.has_shield = True
    gw.total_kills_ever = 1
    assert gw._should_spawn_shield() is False
