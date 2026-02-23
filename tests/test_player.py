from objects.Player import (
    PLAYER_HEIGHT, CANNON_PAD,
    SEC_READY, SEC_ACTIVE, SEC_COOLDOWN,
    SECONDARY_CYCLE, SECONDARY_ACTIVE_PER_LEVEL,
)
from objects.Weapon import SpreadShot, LaserCannon


def test_moves_right(game, actions):
    p = game.players[0]
    start_x = p.position_x
    actions["right"] = True
    p.update(1 / 60, actions)
    assert p.position_x > start_x


def test_moves_left(game, actions):
    p = game.players[0]
    p.position_x = 200
    start_x = p.position_x
    actions["left"] = True
    p.update(1 / 60, actions)
    assert p.position_x < start_x


def test_moves_up(game, actions):
    p = game.players[0]
    p.position_y = 200
    start_y = p.position_y
    actions["up"] = True
    p.update(1 / 60, actions)
    assert p.position_y < start_y


def test_moves_down(game, actions):
    p = game.players[0]
    p.position_y = 200
    start_y = p.position_y
    actions["down"] = True
    p.update(1 / 60, actions)
    assert p.position_y > start_y


def test_bounded_left(game, actions):
    p = game.players[0]
    p.position_x = 0
    actions["left"] = True
    p.update(1 / 60, actions)
    assert p.position_x >= 0


def test_bounded_right(game, actions):
    p = game.players[0]
    max_x = game.GAME_WIDTH * 4 / 5
    p.position_x = max_x
    actions["right"] = True
    p.update(1 / 60, actions)
    assert p.position_x <= max_x


def test_bounded_top(game, actions):
    p = game.players[0]
    p.position_y = 0
    actions["up"] = True
    p.update(1 / 60, actions)
    assert p.position_y >= 0


def test_bounded_bottom(game, actions):
    p = game.players[0]
    max_y = game.GAME_HEIGHT - p.curr_image.get_height()
    p.position_y = max_y
    actions["down"] = True
    p.update(1 / 60, actions)
    assert p.position_y <= max_y


def test_shoot_creates_projectile(game, actions):
    game.projectiles.empty()
    p = game.players[0]
    p.primary_cooldown = 0
    actions["space"] = True
    p.update(1 / 60, actions)
    assert len(game.projectiles) == 1


def test_primary_cooldown_prevents_rapid_fire(game, actions):
    game.projectiles.empty()
    p = game.players[0]
    p.primary_cooldown = 0
    actions["space"] = True
    p.update(1 / 60, actions)
    p.update(1 / 60, actions)
    assert len(game.projectiles) == 1


def test_primary_cooldown_expires(game, actions):
    game.projectiles.empty()
    p = game.players[0]
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
    assert game.players[0].mask is not None
    assert game.players[0].mask.count() > 0


# ---- secondary weapon tests ----

def test_no_secondary_by_default(game):
    assert game.players[0].secondary is None


def test_set_secondary_equips_weapon(game):
    game.players[0].set_secondary(SpreadShot)
    assert isinstance(game.players[0].secondary, SpreadShot)


def test_secondary_makes_sprite_taller(game):
    p = game.players[0]
    base_h = p.curr_image.get_height()
    p.set_secondary(SpreadShot)
    assert p.curr_image.get_height() == base_h + CANNON_PAD


def test_secondary_activates_on_key(game, actions):
    """Pressing secondary key transitions from READY to ACTIVE."""
    p = game.players[0]
    p.set_secondary(SpreadShot)
    assert p.sec_state == SEC_READY
    actions["secondary"] = True
    p.update(1 / 60, actions)
    assert p.sec_state == SEC_ACTIVE


def test_secondary_fires_during_active(game, actions):
    """Secondary auto-fires during ACTIVE state."""
    game.projectiles.empty()
    p = game.players[0]
    p.set_secondary(SpreadShot)
    actions["secondary"] = True
    p.update(1 / 60, actions)
    sec_projs = len(game.projectiles) - (1 if actions.get("space") else 0)
    assert sec_projs >= 1


def test_secondary_active_duration_scales_with_level(game):
    p = game.players[0]
    p.set_secondary(SpreadShot)
    assert p._sec_active_duration() == 1 * SECONDARY_ACTIVE_PER_LEVEL
    p.upgrade_secondary()
    assert p._sec_active_duration() == 2 * SECONDARY_ACTIVE_PER_LEVEL


def test_secondary_enters_cooldown_after_active(game, actions):
    """After active time expires, enters COOLDOWN."""
    p = game.players[0]
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
    p = game.players[0]
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
    p = game.players[0]
    p.set_secondary(SpreadShot)
    while p.upgrade_secondary():
        pass
    assert p._sec_cooldown_duration() >= 1.0


def test_primary_fires_independently_of_secondary(game, actions):
    """Primary fires on space even when secondary is on cooldown."""
    game.projectiles.empty()
    p = game.players[0]
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
    p = game.players[0]
    p.set_secondary(SpreadShot)
    p.primary_cooldown = 0
    actions["space"] = True
    p.update(1 / 60, actions)
    assert len(game.projectiles) == 1


def test_laser_fires_slower_than_spread(game):
    assert LaserCannon.fire_rate > SpreadShot.fire_rate


def test_upgrade_secondary(game):
    p = game.players[0]
    p.set_secondary(SpreadShot)
    assert p.secondary.level == 1
    assert p.upgrade_secondary() is True
    assert p.secondary.level == 2


def test_secondary_level_remembered_on_switch(game):
    p = game.players[0]
    p.set_secondary(SpreadShot)
    p.upgrade_secondary()
    assert p.secondary.level == 2
    p.set_secondary(LaserCannon)
    assert isinstance(p.secondary, LaserCannon)
    assert p.secondary.level == 1
    p.set_secondary(SpreadShot)
    assert p.secondary.level == 2


def test_secondary_mask_updates(game):
    p = game.players[0]
    base_count = p.mask.count()
    p.set_secondary(SpreadShot)
    assert p.mask.count() > base_count


# ---- weapon cycling + background state ticking ----

def _equip_two_weapons(game):
    """Helper: equip SpreadShot then LaserCannon, ending with Laser selected."""
    p = game.players[0]
    p.set_secondary(SpreadShot)
    p.set_secondary(LaserCannon)
    return p


def test_cycle_saves_active_state(game, actions):
    """Cycling away from a firing weapon saves SEC_ACTIVE in sec_weapon_states."""
    p = game.players[0]
    p.set_secondary(SpreadShot)
    p.set_secondary(LaserCannon)

    p._cycle_secondary()
    assert isinstance(p.secondary, SpreadShot)

    actions["secondary"] = True
    p.update(0.01, actions)
    assert p.sec_state == SEC_ACTIVE
    actions["secondary"] = False

    p._cycle_secondary()
    assert isinstance(p.secondary, LaserCannon)

    saved = p.sec_weapon_states[SpreadShot]
    assert saved["state"] == SEC_ACTIVE
    assert saved["timer"] > 0


def test_background_active_timer_ticks_down(game, actions):
    """A non-selected weapon in SEC_ACTIVE has its timer decreased each frame."""
    p = _equip_two_weapons(game)
    p._cycle_secondary()
    assert isinstance(p.secondary, SpreadShot)

    actions["secondary"] = True
    p.update(0.01, actions)
    actions["secondary"] = False

    p._cycle_secondary()
    assert isinstance(p.secondary, LaserCannon)
    timer_before = p.sec_weapon_states[SpreadShot]["timer"]

    p.update(0.5, actions)
    timer_after = p.sec_weapon_states[SpreadShot]["timer"]
    assert timer_after < timer_before


def test_background_active_transitions_to_cooldown(game, actions):
    """A non-selected weapon's SEC_ACTIVE expires into SEC_COOLDOWN."""
    p = _equip_two_weapons(game)
    p._cycle_secondary()
    assert isinstance(p.secondary, SpreadShot)

    actions["secondary"] = True
    p.update(0.01, actions)
    actions["secondary"] = False

    active_dur = p._sec_active_duration()

    p._cycle_secondary()
    assert isinstance(p.secondary, LaserCannon)
    assert p.sec_weapon_states[SpreadShot]["state"] == SEC_ACTIVE

    p.update(active_dur + 1.0, actions)
    assert p.sec_weapon_states[SpreadShot]["state"] == SEC_COOLDOWN
    assert p.sec_weapon_states[SpreadShot]["timer"] > 0


def test_background_cooldown_reaches_ready(game, actions):
    """A non-selected weapon transitions ACTIVE -> COOLDOWN -> READY."""
    p = _equip_two_weapons(game)
    p._cycle_secondary()

    actions["secondary"] = True
    p.update(0.01, actions)
    actions["secondary"] = False

    p._cycle_secondary()

    p.update(SECONDARY_CYCLE + 1.0, actions)
    p.update(SECONDARY_CYCLE + 1.0, actions)
    assert p.sec_weapon_states[SpreadShot]["state"] == SEC_READY


def test_non_selected_ready_stays_ready(game, actions):
    """A non-selected weapon in SEC_READY stays SEC_READY after ticking."""
    p = _equip_two_weapons(game)
    assert p.sec_weapon_states.get(SpreadShot, {}).get("state") == SEC_READY

    p.update(1.0, actions)
    ws = p.sec_weapon_states.get(SpreadShot, {"state": SEC_READY})
    assert ws["state"] == SEC_READY
