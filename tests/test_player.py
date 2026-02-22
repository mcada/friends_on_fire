from objects.Player import PLAYER_HEIGHT, CANNON_PAD
from objects.Weapon import SpreadShot, LaserCannon


def test_moves_right(game, actions):
    p = game.player
    start_x = p.position_x
    actions["right"] = True
    p.update(1 / 60, actions)
    assert p.position_x > start_x


def test_moves_left(game, actions):
    p = game.player
    p.position_x = 200
    start_x = p.position_x
    actions["left"] = True
    p.update(1 / 60, actions)
    assert p.position_x < start_x


def test_moves_up(game, actions):
    p = game.player
    p.position_y = 200
    start_y = p.position_y
    actions["up"] = True
    p.update(1 / 60, actions)
    assert p.position_y < start_y


def test_moves_down(game, actions):
    p = game.player
    p.position_y = 200
    start_y = p.position_y
    actions["down"] = True
    p.update(1 / 60, actions)
    assert p.position_y > start_y


def test_bounded_left(game, actions):
    p = game.player
    p.position_x = 0
    actions["left"] = True
    p.update(1 / 60, actions)
    assert p.position_x >= 0


def test_bounded_right(game, actions):
    p = game.player
    max_x = game.GAME_WIDTH * 4 / 5
    p.position_x = max_x
    actions["right"] = True
    p.update(1 / 60, actions)
    assert p.position_x <= max_x


def test_bounded_top(game, actions):
    p = game.player
    p.position_y = 0
    actions["up"] = True
    p.update(1 / 60, actions)
    assert p.position_y >= 0


def test_bounded_bottom(game, actions):
    p = game.player
    max_y = game.GAME_HEIGHT - p.curr_image.get_height()
    p.position_y = max_y
    actions["down"] = True
    p.update(1 / 60, actions)
    assert p.position_y <= max_y


def test_shoot_creates_projectile(game, actions):
    game.projectiles.empty()
    p = game.player
    p.primary_cooldown = 0
    actions["space"] = True
    p.update(1 / 60, actions)
    assert len(game.projectiles) == 1


def test_primary_cooldown_prevents_rapid_fire(game, actions):
    game.projectiles.empty()
    p = game.player
    p.primary_cooldown = 0
    actions["space"] = True
    p.update(1 / 60, actions)
    p.update(1 / 60, actions)
    assert len(game.projectiles) == 1


def test_primary_cooldown_expires(game, actions):
    game.projectiles.empty()
    p = game.player
    p.primary_cooldown = 0
    actions["space"] = True
    p.update(1 / 60, actions)
    actions["space"] = False
    for _ in range(35):
        p.update(1 / 60, actions)
    actions["space"] = True
    p.update(1 / 60, actions)
    assert len(game.projectiles) == 2


def test_has_mask(game):
    assert game.player.mask is not None
    assert game.player.mask.count() > 0


# ---- secondary weapon tests ----

def test_no_secondary_by_default(game):
    assert game.player.secondary is None


def test_set_secondary_equips_weapon(game):
    game.player.set_secondary(SpreadShot)
    assert isinstance(game.player.secondary, SpreadShot)


def test_secondary_makes_sprite_taller(game):
    p = game.player
    base_h = p.curr_image.get_height()
    p.set_secondary(SpreadShot)
    assert p.curr_image.get_height() == base_h + CANNON_PAD


def test_secondary_fires_on_first_press(game, actions):
    """Both cooldowns start at 0, so the very first shot fires both."""
    game.projectiles.empty()
    p = game.player
    p.set_secondary(SpreadShot)
    p.primary_cooldown = 0
    p.secondary_cooldown = 0
    actions["space"] = True
    p.update(1 / 60, actions)
    assert len(game.projectiles) == 2


def test_secondary_has_own_cooldown(game, actions):
    """After the first shot, secondary should be on its own longer cooldown."""
    game.projectiles.empty()
    p = game.player
    p.set_secondary(SpreadShot)
    p.primary_cooldown = 0
    p.secondary_cooldown = 0
    actions["space"] = True
    p.update(1 / 60, actions)
    assert p.secondary_cooldown > p.primary_cooldown


def test_primary_fires_without_secondary(game, actions):
    """After first volley, primary fires again while secondary is still cooling."""
    game.projectiles.empty()
    p = game.player
    p.set_secondary(SpreadShot)
    p.primary_cooldown = 0
    p.secondary_cooldown = 0
    actions["space"] = True
    p.update(1 / 60, actions)
    count_after_first = len(game.projectiles)

    actions["space"] = False
    for _ in range(35):
        p.update(1 / 60, actions)
    actions["space"] = True
    p.update(1 / 60, actions)
    assert len(game.projectiles) == count_after_first + 1


def test_laser_fires_slower_than_spread(game):
    assert LaserCannon.fire_rate > SpreadShot.fire_rate


def test_upgrade_secondary(game):
    p = game.player
    p.set_secondary(SpreadShot)
    assert p.secondary.level == 1
    assert p.upgrade_secondary() is True
    assert p.secondary.level == 2


def test_secondary_level_remembered_on_switch(game):
    p = game.player
    p.set_secondary(SpreadShot)
    p.upgrade_secondary()
    assert p.secondary.level == 2
    p.set_secondary(LaserCannon)
    assert isinstance(p.secondary, LaserCannon)
    assert p.secondary.level == 1
    p.set_secondary(SpreadShot)
    assert p.secondary.level == 2


def test_secondary_mask_updates(game):
    p = game.player
    base_count = p.mask.count()
    p.set_secondary(SpreadShot)
    assert p.mask.count() > base_count
