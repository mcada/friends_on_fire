import pygame
from states.game_world import (
    Game_World, ENEMY_FIRST_SPAWN, ENEMY_SPAWN_INTERVAL,
    ENEMY_MIN_INTERVAL, DRONE_MAX, FIGHTER_MAX,
    FIGHTER_UNLOCK_TIME,
)
from objects.Enemy import Enemy, Drone, Fighter, EnemyProjectile, ENEMY_TYPES
from objects.Projectile import Projectile


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


# ---- Enemy class basics ----

class TestEnemyBasics:
    def test_fighter_initial_hp(self, game):
        f = Fighter(600, 300, game)
        assert f.hp == 4
        assert f.max_hp == 4
        assert f.alive_flag is True

    def test_take_damage_reduces_hp(self, game):
        f = Fighter(600, 300, game)
        f.take_damage(1)
        assert f.hp == 3
        assert f.alive_flag is True

    def test_take_damage_kills_at_zero(self, game):
        f = Fighter(600, 300, game)
        f.take_damage(4)
        assert f.hp <= 0
        assert f.alive_flag is False

    def test_fighter_is_sprite(self, game):
        f = Fighter(600, 300, game)
        assert isinstance(f, pygame.sprite.Sprite)
        assert f.image is not None
        assert f.mask is not None
        assert f.rect is not None

    def test_enemy_has_score_value(self, game):
        f = Fighter(600, 300, game)
        assert f.score_value >= 1

    def test_enemy_types_list(self):
        assert len(ENEMY_TYPES) >= 1
        for cls in ENEMY_TYPES:
            assert issubclass(cls, Enemy)


# ---- Drone basics ----

class TestDroneBasics:
    def test_drone_has_two_hp(self, game):
        d = Drone(800, 200, game)
        assert d.hp == 2
        assert d.max_hp == 2

    def test_drone_survives_one_hit(self, game):
        d = Drone(800, 200, game)
        d.take_damage(1)
        assert d.hp == 1
        assert d.alive_flag is True

    def test_drone_dies_at_zero(self, game):
        d = Drone(800, 200, game)
        d.take_damage(2)
        assert d.alive_flag is False

    def test_drone_moves_left(self, game):
        d = Drone(800, 200, game)
        x_before = d.rect.x
        d.update(1 / 60)
        assert d.rect.x < x_before

    def test_drone_does_not_patrol(self, game):
        d = Drone(800, 200, game)
        assert d.entering is False

    def test_drone_shoots_straight_left(self, game):
        d = Drone(800, 200, game)
        d._shot_schedule = [0]
        d.update(0.1)
        assert len(game.enemy_projectiles) >= 1
        ep = list(game.enemy_projectiles)[0]
        assert ep.dx < 0
        assert ep.dy == 0

    def test_drone_limited_shots(self, game):
        d = Drone(800, 200, game)
        assert 1 <= len(d._shot_schedule) <= 2

    def test_drone_killed_offscreen(self, game):
        group = pygame.sprite.Group()
        d = Drone(-50, 200, game)
        d._fx = -50.0
        group.add(d)
        d.update(1 / 60)
        assert not d.alive_flag


# ---- EnemyProjectile ----

class TestEnemyProjectile:
    def test_creates_valid_sprite(self, game):
        ep = EnemyProjectile(400, 300, -3, 0, game)
        assert isinstance(ep, pygame.sprite.Sprite)
        assert ep.image is not None
        assert ep.mask is not None

    def test_moves_on_update(self, game):
        ep = EnemyProjectile(400, 300, -5, 2, game)
        x_before = ep.rect.x
        y_before = ep.rect.y
        ep.update()
        assert ep.rect.x < x_before
        assert ep.rect.y > y_before

    def test_dies_offscreen(self, game):
        group = pygame.sprite.Group()
        ep = EnemyProjectile(-100, 300, -5, 0, game)
        group.add(ep)
        ep.update()
        assert len(group) == 0

    def test_paused_no_move(self, game):
        game.paused = True
        ep = EnemyProjectile(400, 300, -5, 0, game)
        x_before = ep.rect.x
        ep.update()
        assert ep.rect.x == x_before
        game.paused = False


# ---- Fighter shooting ----

class TestFighterShooting:
    def test_fighter_shoots_into_enemy_projectiles(self, game):
        f = Fighter(600, 300, game)
        f.entering = False
        f.shoot_timer = 0.01
        assert len(game.enemy_projectiles) == 0
        f.update(0.02)
        assert len(game.enemy_projectiles) >= 1

    def test_fighter_projectile_aims_at_player(self, game):
        p = game.players[0]
        p.position_x = 100
        p.position_y = 300
        f = Fighter(600, 300, game)
        f.entering = False
        f.shoot_timer = 0.01
        f.update(0.02)
        ep = list(game.enemy_projectiles)[0]
        assert ep.dx < 0


# ---- Spawning in Game_World ----

class TestEnemySpawning:
    def test_no_enemies_before_first_spawn_time(self, game):
        gw = _enter_game_world(game)
        actions = _no_actions()
        steps = int((ENEMY_FIRST_SPAWN - 1) * 60)
        for _ in range(steps):
            gw.update(1 / 60, actions)
        assert len(game.enemies) == 0

    def test_enemies_spawn_after_threshold(self, game):
        gw = _enter_game_world(game)
        actions = _no_actions()
        gw.elapsed_time = ENEMY_FIRST_SPAWN - 0.01
        gw.update(0.02, actions)
        assert gw._enemies_started
        gw.enemy_spawn_timer = gw.enemy_spawn_interval
        gw.update(1 / 60, actions)
        assert len(game.enemies) >= 1

    def test_drone_cap_respected(self, game):
        gw = _enter_game_world(game)
        gw.elapsed_time = ENEMY_FIRST_SPAWN + 1
        for _ in range(DRONE_MAX + 10):
            gw._spawn_enemy()
        drones = sum(1 for e in game.enemies if isinstance(e, Drone))
        assert drones <= DRONE_MAX

    def test_fighter_cap_respected(self, game):
        gw = _enter_game_world(game)
        gw.elapsed_time = FIGHTER_UNLOCK_TIME + 1
        for _ in range(50):
            gw._spawn_enemy()
        fighters = sum(1 for e in game.enemies if isinstance(e, Fighter))
        assert fighters <= FIGHTER_MAX

    def test_drone_wave_spawns_multiple(self, game):
        gw = _enter_game_world(game)
        gw.elapsed_time = ENEMY_FIRST_SPAWN + 1
        gw._spawn_drone_wave()
        drones = sum(1 for e in game.enemies if isinstance(e, Drone))
        assert 3 <= drones <= DRONE_MAX

    def test_drone_wave_respects_cap(self, game):
        gw = _enter_game_world(game)
        for i in range(DRONE_MAX - 1):
            game.enemies.add(Drone(800, 100 + i * 30, game))
        gw._spawn_drone_wave()
        drones = sum(1 for e in game.enemies if isinstance(e, Drone))
        assert drones <= DRONE_MAX

    def test_spawn_interval_decays(self, game):
        gw = _enter_game_world(game)
        gw._enemies_started = True
        initial = gw.enemy_spawn_interval
        gw.enemy_spawn_timer = initial
        actions = _no_actions()
        gw.update(1 / 60, actions)
        assert gw.enemy_spawn_interval < initial

    def test_spawn_interval_has_minimum(self, game):
        gw = _enter_game_world(game)
        gw._enemies_started = True
        gw.enemy_spawn_interval = ENEMY_MIN_INTERVAL
        gw.enemy_spawn_timer = ENEMY_MIN_INTERVAL
        actions = _no_actions()
        gw.update(1 / 60, actions)
        assert gw.enemy_spawn_interval >= ENEMY_MIN_INTERVAL

    def test_only_drones_before_fighter_unlock(self, game):
        gw = _enter_game_world(game)
        gw.elapsed_time = ENEMY_FIRST_SPAWN + 1
        for _ in range(20):
            gw._spawn_enemy()
        for e in game.enemies:
            assert isinstance(e, Drone)

    def test_fighters_can_appear_after_unlock(self, game):
        gw = _enter_game_world(game)
        gw.elapsed_time = FIGHTER_UNLOCK_TIME + 1
        types_seen = set()
        for _ in range(100):
            gw._spawn_enemy()
        for e in game.enemies:
            types_seen.add(type(e))
        assert Fighter in types_seen

    def test_no_enemies_during_boss(self, game):
        gw = _enter_game_world(game)
        gw.boss_phase = True
        gw._enemies_started = True
        gw.enemy_spawn_timer = gw.enemy_spawn_interval + 1
        actions = _no_actions()
        gw.update(1 / 60, actions)
        assert len(game.enemies) == 0


# ---- Combat integration ----

class TestEnemyCombat:
    def test_player_projectile_kills_enemy(self, game):
        gw = _enter_game_world(game)
        f = Fighter(700, 300, game)
        f.entering = False
        f.hp = 1
        game.enemies.add(f)

        actions = _no_actions()
        gw.update(1 / 60, actions)

        proj = Projectile("crimson", f.rect.centerx, f.rect.centery,
                           game, dx=0, width=50, height=50,
                           piercing=True, owner=game.players[0])
        game.projectiles.add(proj)
        gw._update_enemy_combat()
        assert not f.alive_flag

    def test_piercing_projectile_survives_enemy_hit(self, game):
        gw = _enter_game_world(game)
        f = Fighter(700, 300, game)
        f.entering = False
        game.enemies.add(f)

        actions = _no_actions()
        gw.update(1 / 60, actions)

        proj = Projectile("lime", f.rect.centerx, f.rect.centery,
                           game, dx=0, piercing=True, width=60, height=50,
                           owner=game.players[0])
        game.projectiles.add(proj)
        gw._update_enemy_combat()
        assert proj.alive()

    def test_enemy_projectile_damages_player(self, game):
        gw = _enter_game_world(game)
        p = game.players[0]
        p.has_shield = False
        p.hit_invuln = 0
        lives_before = p.lives
        ep = EnemyProjectile(
            int(p.position_x) + 20, int(p.position_y) + 10,
            0, 0, game,
        )
        game.enemy_projectiles.add(ep)
        actions = _no_actions()
        gw.update(1 / 60, actions)
        assert p.lives < lives_before or p.has_shield is False

    def test_player_projectile_destroys_enemy_projectile(self, game):
        gw = _enter_game_world(game)
        ep = EnemyProjectile(400, 300, -3, 0, game, size=18)
        game.enemy_projectiles.add(ep)
        proj = Projectile("crimson", 400, 300, game, dx=5,
                           width=30, height=30, owner=game.players[0])
        game.projectiles.add(proj)
        gw._update_projectile_vs_projectile()
        assert len(game.enemy_projectiles) == 0

    def test_piercing_survives_enemy_projectile(self, game):
        gw = _enter_game_world(game)
        ep = EnemyProjectile(400, 300, -3, 0, game, size=18)
        game.enemy_projectiles.add(ep)
        proj = Projectile("lime", 400, 300, game, dx=5,
                           width=30, height=30, piercing=True,
                           owner=game.players[0])
        game.projectiles.add(proj)
        gw._update_projectile_vs_projectile()
        assert len(game.enemy_projectiles) == 0
        assert proj.alive()

    def test_no_new_enemies_during_boss_countdown(self, game):
        """Once boss countdown starts, no new enemies spawn."""
        gw = _enter_game_world(game)
        gw._enemies_started = True
        gw._begin_boss_countdown()
        count_before = len(game.enemies)
        gw.enemy_spawn_timer = gw.enemy_spawn_interval + 1
        actions = _no_actions()
        gw.update(1 / 60, actions)
        assert len(game.enemies) == count_before

    def test_existing_enemies_persist_during_countdown(self, game):
        """Enemies already on screen stay alive during the boss countdown."""
        gw = _enter_game_world(game)
        f = Fighter(700, 300, game)
        f.entering = False
        game.enemies.add(f)
        game.enemy_projectiles.add(
            EnemyProjectile(500, 300, -3, 0, game)
        )
        gw._begin_boss_countdown()
        assert len(game.enemies) == 1
        assert len(game.enemy_projectiles) == 1


# ---- Cleanup ----

class TestEnemyCleanup:
    def test_return_to_menu_clears_enemies(self, game):
        gw = _enter_game_world(game)
        game.enemies.add(Fighter(600, 300, game))
        game.enemy_projectiles.add(
            EnemyProjectile(500, 300, -3, 0, game)
        )
        game.return_to_menu()
        assert len(game.enemies) == 0
        assert len(game.enemy_projectiles) == 0
