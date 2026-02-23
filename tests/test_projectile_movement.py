import math
import pygame
from objects.Projectile import Projectile


def test_straight_projectile_moves_right(game):
    p = Projectile("crimson", 100, 200, game, dx=8, dy=0)
    game.projectiles.add(p)
    start_x = p.rect.centerx
    p.update()
    assert p.rect.centerx == start_x + 8


def test_diagonal_projectile_moves(game):
    p = Projectile("cyan", 100, 200, game, dx=7, dy=-2)
    game.projectiles.add(p)
    start_x, start_y = p.rect.centerx, p.rect.centery
    p.update()
    assert p.rect.centerx == start_x + 7
    assert p.rect.centery == start_y - 2


def test_wave_projectile_oscillates(game):
    amp, freq = 20, 0.15
    p = Projectile("lime", 100, 300, game, dx=7, dy=0, wave=(amp, freq, 0))
    game.projectiles.add(p)
    ys = []
    for _ in range(50):
        p.update()
        ys.append(p.rect.centery)
    assert max(ys) > 300 and min(ys) < 300


def test_wave_counter_phase(game):
    """Two wave projectiles with pi offset should be at opposite positions."""
    p1 = Projectile("lime", 100, 300, game, dx=7, dy=0, wave=(20, 0.15, 0))
    p2 = Projectile("lime", 100, 300, game, dx=7, dy=0, wave=(20, 0.15, math.pi))
    game.projectiles.add(p1, p2)
    for _ in range(10):
        p1.update()
        p2.update()
    assert p1.rect.centery != p2.rect.centery


def test_projectile_killed_offscreen_right(game):
    p = Projectile("crimson", game.GAME_WIDTH - 2, 200, game, dx=8, dy=0)
    game.projectiles.add(p)
    for _ in range(10):
        p.update()
    assert not game.projectiles.has(p)


def test_diagonal_projectile_killed_offscreen_top(game):
    p = Projectile("cyan", 100, 5, game, dx=5, dy=-10)
    game.projectiles.add(p)
    for _ in range(20):
        p.update()
    assert not game.projectiles.has(p)


def test_piercing_projectile_has_flag(game):
    p = Projectile("lime", 100, 200, game, dx=10, width=60, height=6, piercing=True)
    assert p.piercing is True


def test_non_piercing_projectile_default(game):
    p = Projectile("crimson", 100, 200, game)
    assert p.piercing is False


def test_piercing_beam_visual_is_wider(game):
    beam = Projectile("lime", 100, 200, game, dx=10, width=60, height=6, piercing=True)
    bullet = Projectile("crimson", 100, 200, game)
    assert beam.rect.width > bullet.rect.width


def test_piercing_projectile_moves(game):
    p = Projectile("lime", 100, 200, game, dx=10, width=60, height=6, piercing=True)
    game.projectiles.add(p)
    start_x = p.rect.centerx
    p.update()
    assert p.rect.centerx == start_x + 10


def test_piercing_has_mask(game):
    p = Projectile("lime", 100, 200, game, dx=10, width=60, height=6, piercing=True)
    assert p.mask is not None
    assert p.mask.count() > 0


def test_shiny_projectile_larger(game):
    normal = Projectile("crimson", 100, 200, game)
    shiny = Projectile("crimson", 100, 200, game, shiny=True)
    assert shiny.rect.width > normal.rect.width
    assert shiny.rect.height > normal.rect.height


def test_shiny_beam_has_mask(game):
    p = Projectile("lime", 100, 200, game, dx=10, width=60, height=6, piercing=True, shiny=True)
    assert p.mask is not None
    assert p.mask.count() > 0


def test_homing_projectile_has_flag(game):
    p = Projectile("orange", 100, 200, game, dx=5, dy=-1, homing=True, width=14, height=8)
    assert p.homing is True
    assert p.mask is not None


def test_homing_missile_visual(game):
    p = Projectile("orange", 100, 200, game, dx=5, dy=0, homing=True, width=14, height=8)
    assert p.rect.width >= 14
    assert p.rect.height >= 8


def test_homing_ignores_rocks(game):
    """Missiles should fly straight past asteroids without locking on."""
    from objects.Rocks import Rock, BASIC
    rock = Rock(300, 300, 30, 30, game, rock_type=BASIC)
    game.rocks.add(rock)
    p = Projectile("orange", 100, 200, game, dx=5, dy=0, homing=True, width=14, height=8)
    game.projectiles.add(p)
    for _ in range(20):
        p.update()
    assert abs(p.dy) < 0.5


def test_homing_locks_onto_nearby_enemy(game):
    from objects.Enemy import Fighter
    enemy = Fighter(350, 250, game)
    enemy.entering = False
    game.enemies.add(enemy)
    p = Projectile("orange", 100, 200, game, dx=5, dy=0, homing=True, width=14, height=8)
    game.projectiles.add(p)
    for _ in range(20):
        p.update()
    assert p.dy > 0


def test_homing_flies_straight_when_enemy_out_of_range(game):
    from objects.Enemy import Fighter
    from objects.Projectile import HOMING_ACQUIRE_RANGE
    far_x = 100 + HOMING_ACQUIRE_RANGE + 200
    enemy = Fighter(far_x, 400, game)
    enemy.entering = False
    game.enemies.add(enemy)
    p = Projectile("orange", 100, 200, game, dx=5, dy=0, homing=True, width=14, height=8)
    game.projectiles.add(p)
    for _ in range(5):
        p.update()
    assert abs(p.dy) < 0.5


def test_homing_acquires_enemy_entering_range(game):
    """Missile flies straight then steers once an enemy enters range."""
    from objects.Enemy import Fighter
    from objects.Projectile import HOMING_ACQUIRE_RANGE
    enemy = Fighter(100 + HOMING_ACQUIRE_RANGE - 50, 350, game)
    enemy.entering = False
    game.enemies.add(enemy)
    p = Projectile("orange", 100, 200, game, dx=5, dy=0, homing=True, width=14, height=8)
    game.projectiles.add(p)
    for _ in range(20):
        p.update()
    assert p.dy > 0


def test_projectile_damage_attribute(game):
    p_default = Projectile("crimson", 100, 200, game)
    assert p_default.damage == 1
    p_custom = Projectile("orange", 100, 200, game, damage=2)
    assert p_custom.damage == 2
