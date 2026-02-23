import pytest
from objects.Boss import (
    Boss, BossProjectile, BossLaser, BOSS_BASE_HP,
    HIT_COOLDOWN, INVULN_PHASE_DURATION,
    PATROL_LEFT_RATIO, PATROL_RIGHT_RATIO, PATROL_SPEED,
    LASER_CHARGE_DURATION, LASER_ACTIVE_DURATION,
    LASER_MAX_CONCURRENT,
)
from states.game_world import Game_World, LEVEL_DURATION, BOSS_COUNTDOWN


def _no_actions():
    return {
        "left": False, "right": False, "up": False, "down": False,
        "action1": False, "action2": False, "start": False, "space": False,
        "escape": False, "secondary": False,
    }


def _enter_gw(game, mode="endless", level_num=0):
    gw = Game_World(game, game_mode=mode, level_num=level_num)
    gw.enter_state()
    return gw


# ---- Boss entity ----

def test_boss_initial_hp(game):
    boss = Boss(game, attack_level=1, hp_override=20)
    assert boss.hp == 20
    assert boss.alive_flag is True


def test_boss_takes_damage(game):
    boss = Boss(game, attack_level=1, hp_override=10)
    assert boss.take_damage(1) is True
    assert boss.hp == 9


def test_boss_hit_cooldown(game):
    boss = Boss(game, attack_level=1, hp_override=10)
    boss.take_damage(1)
    assert boss.is_invulnerable is True
    assert boss.take_damage(1) is False
    assert boss.hp == 9


def test_boss_hit_cooldown_expires(game):
    boss = Boss(game, attack_level=1, hp_override=10)
    boss.entering = False
    boss.take_damage(1)
    boss.update(HIT_COOLDOWN + 0.01)
    assert boss.hit_cooldown == 0
    assert boss.take_damage(1) is True
    assert boss.hp == 8


def test_boss_invuln_phase_at_threshold(game):
    boss = Boss(game, attack_level=1, hp_override=4)
    boss.entering = False
    boss.take_damage(1)
    assert boss.invuln_timer == INVULN_PHASE_DURATION


def test_boss_dies_at_zero_hp(game):
    boss = Boss(game, attack_level=1, hp_override=1)
    boss.take_damage(1)
    assert boss.hp == 0
    assert boss.alive_flag is False


def test_boss_projectile_moves(game):
    bp = BossProjectile(400, 300, -3, 0, game, destroyable=True)
    start_x = bp.rect.x
    bp.update()
    assert bp.rect.x < start_x


def test_boss_projectile_killed_offscreen(game):
    bp = BossProjectile(-50, 300, -3, 0, game)
    bp.update()
    assert not bp.alive()


def test_destroyable_boss_projectile(game):
    bp = BossProjectile(400, 300, -3, 0, game, destroyable=True)
    assert bp.destroyable is True


def test_indestructible_boss_projectile(game):
    bp = BossProjectile(400, 300, -3, 0, game, destroyable=False)
    assert bp.destroyable is False


def test_laser_projectile_dimensions(game):
    bp = BossProjectile(400, 300, -5, 0, game, destroyable=False,
                        width=220, height=14, color=(200, 0, 200))
    assert bp.rect.width == 220
    assert bp.rect.height == 14
    assert bp.destroyable is False


# ---- BossLaser (stream-based) ----

def test_boss_laser_starts_charging(game):
    boss = Boss(game, attack_level=2, hp_override=20)
    boss.entering = False
    laser = BossLaser(boss, 0, game)
    assert laser.phase == "charging"
    assert not laser.active
    assert not laser.done


def test_boss_laser_transitions_to_active(game):
    boss = Boss(game, attack_level=2, hp_override=20)
    boss.entering = False
    boss.rect.x = 600
    laser = BossLaser(boss, 0, game)
    laser.update(LASER_CHARGE_DURATION + 0.01)
    assert laser.phase == "active"
    assert laser.active


def test_boss_laser_emits_segments_when_active(game):
    boss = Boss(game, attack_level=2, hp_override=20)
    boss.entering = False
    boss.rect.x = 600
    laser = BossLaser(boss, 0, game)
    assert len(laser.segments) == 0
    laser.update(LASER_CHARGE_DURATION + 0.01)
    laser.update(0.1)
    assert len(laser.segments) > 0


def test_boss_laser_segments_move_left(game):
    boss = Boss(game, attack_level=2, hp_override=20)
    boss.entering = False
    boss.rect.x = 600
    laser = BossLaser(boss, 0, game)
    laser.update(LASER_CHARGE_DURATION + 0.01)
    laser.update(0.05)
    first_x = laser.segments[0][0]
    laser.update(0.05)
    assert laser.segments[0][0] < first_x


def test_boss_laser_fades_after_active(game):
    boss = Boss(game, attack_level=2, hp_override=20)
    boss.entering = False
    boss.rect.x = 600
    laser = BossLaser(boss, 0, game)
    laser.update(LASER_CHARGE_DURATION + 0.01)
    laser.update(LASER_ACTIVE_DURATION + 0.01)
    assert laser.phase == "fading"
    assert laser.active


def test_boss_laser_done_when_segments_gone(game):
    boss = Boss(game, attack_level=2, hp_override=20)
    boss.entering = False
    boss.rect.x = 600
    laser = BossLaser(boss, 0, game)
    laser.update(LASER_CHARGE_DURATION + 0.01)
    laser.update(LASER_ACTIVE_DURATION + 0.01)
    for _ in range(300):
        laser.update(0.05)
    assert laser.done


def test_boss_laser_sweep_creates_one_or_two(game):
    boss = Boss(game, attack_level=2, hp_override=20)
    boss.entering = False
    boss._attack_laser_sweep()
    assert 1 <= len(boss.boss_lasers) <= 2


def test_boss_laser_cross_creates_one_or_two(game):
    boss = Boss(game, attack_level=2, hp_override=20)
    boss.entering = False
    boss._attack_laser_cross()
    assert 1 <= len(boss.boss_lasers) <= 2


def test_boss_laser_max_concurrent(game):
    boss = Boss(game, attack_level=2, hp_override=20)
    boss.entering = False
    boss._attack_laser_sweep()
    boss._attack_laser_sweep()
    assert len(boss.boss_lasers) <= LASER_MAX_CONCURRENT


def test_boss_laser_sweep_offsets_have_gaps(game):
    boss = Boss(game, attack_level=2, hp_override=20)
    boss.entering = False
    boss._attack_laser_sweep()
    offsets = sorted(l.offset_y for l in boss.boss_lasers)
    from objects.Boss import LASER_BEAM_RADIUS
    for i in range(len(offsets) - 1):
        gap = offsets[i + 1] - offsets[i] - LASER_BEAM_RADIUS * 2
        assert gap >= 35, f"Gap {gap}px too small for player (35px)"


def test_boss_lasers_cleaned_after_lifecycle(game):
    boss = Boss(game, attack_level=2, hp_override=20)
    boss.entering = False
    boss.rect.x = 600
    boss.base_y = float(boss.rect.centery)
    boss.attack_timer = 9999
    boss._attack_laser_sweep()
    assert len(boss.boss_lasers) >= 1
    boss.update(LASER_CHARGE_DURATION + 0.01)
    boss.attack_timer = 9999
    boss.update(LASER_ACTIVE_DURATION + 0.01)
    boss.attack_timer = 9999
    for _ in range(300):
        boss.update(0.05)
        boss.attack_timer = 9999
    assert len(boss.boss_lasers) == 0


# ---- Boss movement ----

def test_boss_patrols_left_and_right(game):
    boss = Boss(game, attack_level=1, hp_override=50)
    boss.entering = False
    boss.rect.x = boss.patrol_right
    boss.patrol_dir = -1
    boss.base_y = float(boss.rect.centery)

    boss.update(0.5)
    after_left = boss.rect.x
    assert after_left < boss.patrol_right

    boss.rect.x = boss.patrol_left
    boss.update(0.016)
    assert boss.patrol_dir == 1


def test_boss_patrol_reverses_at_right(game):
    boss = Boss(game, attack_level=1, hp_override=50)
    boss.entering = False
    boss.rect.x = boss.patrol_right + 1
    boss.patrol_dir = 1
    boss.base_y = float(boss.rect.centery)
    boss.update(0.016)
    assert boss.patrol_dir == -1


# ---- Boss shield visual (no flicker) ----

def test_boss_invuln_uses_shield_not_flicker(game):
    boss = Boss(game, attack_level=1, hp_override=4)
    boss.entering = False
    boss.take_damage(1)
    assert boss.invuln_timer > 0
    boss.update(0.1)
    assert boss.image is not None
    assert not hasattr(boss, 'invuln_flash')


# ---- Boss attack pools ----

def test_attack_pool_tier_1_has_entries(game):
    boss = Boss(game, attack_level=1)
    assert len(boss._ATTACK_POOLS[1]) >= 2


def test_attack_pool_all_4_tiers_exist(game):
    boss = Boss(game, attack_level=4)
    for tier in range(1, 5):
        assert tier in boss._ATTACK_POOLS
        assert len(boss._ATTACK_POOLS[tier]) >= 1


def test_attack_pool_methods_exist(game):
    boss = Boss(game, attack_level=4)
    for tier, names in boss._ATTACK_POOLS.items():
        for name in names:
            assert hasattr(boss, f"_attack_{name}"), f"Missing _attack_{name}"


# ---- Boss spawning in game_world ----

def _trigger_boss(gw):
    """Trigger boss spawn and advance past the countdown."""
    actions = _no_actions()
    gw.elapsed_time = LEVEL_DURATION - 0.1
    gw.update(0.2, actions)
    assert gw.boss_phase is True
    if gw.boss is None:
        gw.update(BOSS_COUNTDOWN + 0.1, actions)


def test_boss_spawns_in_level_at_duration(game):
    gw = _enter_gw(game, mode="level", level_num=1)
    _trigger_boss(gw)
    assert gw.boss is not None
    assert gw.boss_phase is True


def test_boss_spawns_in_endless_at_interval(game):
    gw = _enter_gw(game, mode="endless")
    _trigger_boss(gw)
    assert gw.boss is not None
    assert gw.boss_phase is True


def test_boss_hp_scales_with_level(game):
    gw = _enter_gw(game, mode="level", level_num=3)
    assert gw._boss_hp() == BOSS_BASE_HP + 20


def test_boss_attack_level_matches_game_level(game):
    gw = _enter_gw(game, mode="level", level_num=2)
    assert gw._boss_attack_level() == 2


def test_level_won_on_boss_defeat(game):
    gw = _enter_gw(game, mode="level", level_num=1)
    _trigger_boss(gw)
    assert gw.boss is not None
    actions = _no_actions()
    gw.boss.hp = 0
    gw.boss.alive_flag = False
    gw.update(0.01, actions)
    assert gw.level_won is True


def test_endless_continues_after_boss(game):
    gw = _enter_gw(game, mode="endless")
    _trigger_boss(gw)
    assert gw.boss is not None
    actions = _no_actions()
    gw.boss.hp = 0
    gw.boss.alive_flag = False
    gw.update(0.01, actions)
    assert gw.boss is None
    assert gw.boss_phase is False
    assert gw.level_won is False


def test_boss_challenge_spawns_immediately(game):
    gw = _enter_gw(game, mode="boss_challenge")
    actions = _no_actions()
    gw.update(0.01, actions)
    assert gw.boss is not None
    assert gw.boss_phase is True


def test_boss_challenge_full_attack_level(game):
    gw = _enter_gw(game, mode="boss_challenge")
    assert gw._boss_attack_level() == 4


def test_boss_challenge_full_hp(game):
    gw = _enter_gw(game, mode="boss_challenge")
    assert gw._boss_hp() == BOSS_BASE_HP + 30


def test_boss_challenge_no_rocks(game):
    gw = _enter_gw(game, mode="boss_challenge")
    actions = _no_actions()
    for _ in range(120):
        gw.update(1 / 60, actions)
    asteroid_rocks = [r for r in game.rocks if r.rect.x > game.GAME_WIDTH]
    assert len(asteroid_rocks) == 0


def test_boss_challenge_win_on_defeat(game):
    gw = _enter_gw(game, mode="boss_challenge")
    actions = _no_actions()
    gw.update(0.01, actions)
    assert gw.boss is not None
    gw.boss.hp = 0
    gw.boss.alive_flag = False
    gw.update(0.01, actions)
    assert gw.level_won is True


def test_no_rocks_spawn_during_boss(game):
    gw = _enter_gw(game, mode="endless")
    actions = _no_actions()
    gw.elapsed_time = LEVEL_DURATION + 1
    gw.update(0.01, actions)
    assert gw.boss_phase is True
    rocks_before = len(game.rocks)
    for _ in range(60):
        gw.rock_spawn_timer = gw.rock_spawn_interval + 1
        gw.update(1 / 60, actions)
    rock_spawned_by_game = len([r for r in game.rocks
                                 if r.rect.x > game.GAME_WIDTH])
    assert rock_spawned_by_game == 0 or gw.boss_phase
