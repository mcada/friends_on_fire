from objects.Player import (
    PLAYER_HEIGHT, CANNON_PAD,
    SEC_READY, SEC_ACTIVE, SEC_COOLDOWN,
    SECONDARY_CYCLE, SECONDARY_ACTIVE_PER_LEVEL,
)
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


def test_secondary_activates_on_key(game, actions):
    """Pressing secondary key transitions from READY to ACTIVE."""
    p = game.player
    p.set_secondary(SpreadShot)
    assert p.sec_state == SEC_READY
    actions["secondary"] = True
    p.update(1 / 60, actions)
    assert p.sec_state == SEC_ACTIVE


def test_secondary_fires_during_active(game, actions):
    """Secondary auto-fires during ACTIVE state."""
    game.projectiles.empty()
    p = game.player
    p.set_secondary(SpreadShot)
    actions["secondary"] = True
    p.update(1 / 60, actions)
    sec_projs = len(game.projectiles) - (1 if actions.get("space") else 0)
    assert sec_projs >= 1


def test_secondary_active_duration_scales_with_level(game):
    p = game.player
    p.set_secondary(SpreadShot)
    assert p._sec_active_duration() == 1 * SECONDARY_ACTIVE_PER_LEVEL
    p.upgrade_secondary()
    assert p._sec_active_duration() == 2 * SECONDARY_ACTIVE_PER_LEVEL


def test_secondary_enters_cooldown_after_active(game, actions):
    """After active time expires, enters COOLDOWN."""
    p = game.player
    p.set_secondary(SpreadShot)
    actions["secondary"] = True
    p.update(0.01, actions)
    assert p.sec_state == SEC_ACTIVE
    actions["secondary"] = False
    active_dur = p._sec_active_duration()
    p.update(active_dur + 0.1, actions)
    assert p.sec_state == SEC_COOLDOWN


def test_secondary_returns_to_ready_after_cooldown(game, actions):
    """After cooldown expires, returns to READY."""
    p = game.player
    p.set_secondary(SpreadShot)
    actions["secondary"] = True
    p.update(0.01, actions)
    actions["secondary"] = False
    active_dur = p._sec_active_duration()
    p.update(active_dur + 0.1, actions)
    assert p.sec_state == SEC_COOLDOWN
    cd_dur = p._sec_cooldown_duration()
    p.update(cd_dur + 0.1, actions)
    assert p.sec_state == SEC_READY


def test_secondary_cooldown_min_1s(game):
    """At max level, cooldown should be at least 1 second."""
    p = game.player
    p.set_secondary(SpreadShot)
    while p.upgrade_secondary():
        pass
    assert p._sec_cooldown_duration() >= 1.0


def test_primary_fires_independently_of_secondary(game, actions):
    """Primary fires on space even when secondary is on cooldown."""
    game.projectiles.empty()
    p = game.player
    p.set_secondary(SpreadShot)
    p.sec_state = SEC_COOLDOWN
    p.sec_state_timer = 5.0
    p.primary_cooldown = 0
    actions["space"] = True
    p.update(1 / 60, actions)
    assert len(game.projectiles) == 1


def test_secondary_does_not_fire_on_space(game, actions):
    """Space alone does not activate secondary."""
    game.projectiles.empty()
    p = game.player
    p.set_secondary(SpreadShot)
    p.primary_cooldown = 0
    actions["space"] = True
    p.update(1 / 60, actions)
    assert len(game.projectiles) == 1


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
