import pygame
from objects.Rocks import Rock, BASIC, CLUSTER, IRON


# ---- basic asteroid (default) ----

def test_moves_left(game):
    rock = Rock(500, 300, 30, 30, game)
    start_x = rock.rect.x
    rock.update()
    assert rock.rect.x < start_x


def test_moves_at_correct_speed(game):
    rock = Rock(500, 300, 30, 30, game)
    start_x = rock.rect.x
    rock.update()
    assert rock.rect.x == start_x - 3


def test_killed_when_offscreen(game):
    group = pygame.sprite.Group()
    rock = Rock(-10, 300, 5, 5, game)
    group.add(rock)
    rock.update()
    assert len(group) == 0


def test_stays_alive_when_onscreen(game):
    group = pygame.sprite.Group()
    rock = Rock(500, 300, 30, 30, game)
    group.add(rock)
    rock.update()
    assert len(group) == 1


def test_has_mask(game):
    rock = Rock(500, 300, 30, 30, game)
    assert rock.mask is not None
    assert rock.mask.count() > 0


def test_basic_hp_is_one(game):
    rock = Rock(500, 300, 30, 30, game)
    assert rock.hp == 1
    assert rock.rock_type == BASIC


# ---- cluster asteroid ----

def test_cluster_hp_is_one(game):
    rock = Rock(500, 300, 50, 50, game, rock_type=CLUSTER)
    assert rock.hp == 1
    assert rock.rock_type == CLUSTER


# ---- iron asteroid ----

def test_iron_hp_is_three(game):
    rock = Rock(500, 300, 45, 45, game, rock_type=IRON)
    assert rock.hp == 3
    assert rock.rock_type == IRON


def test_iron_survives_one_hit(game):
    rock = Rock(500, 300, 45, 45, game, rock_type=IRON)
    rock.take_damage(1)
    assert rock.hp == 2


def test_iron_dies_after_three_hits(game):
    rock = Rock(500, 300, 45, 45, game, rock_type=IRON)
    rock.take_damage(3)
    assert rock.hp <= 0


def test_iron_visual_changes_on_damage(game):
    rock = Rock(500, 300, 45, 45, game, rock_type=IRON)
    pixels_before = pygame.image.tostring(rock.image, "RGBA")
    rock.take_damage(1)
    pixels_after = pygame.image.tostring(rock.image, "RGBA")
    assert pixels_before != pixels_after


# ---- fragment movement ----

def test_fragment_with_dy_moves_diagonally(game):
    rock = Rock(500, 300, 15, 15, game, dx=-4, dy=3)
    start_x, start_y = rock.rect.x, rock.rect.y
    rock.update()
    assert rock.rect.x == start_x - 4
    assert rock.rect.y == start_y + 3


def test_fragment_killed_offscreen_bottom(game):
    group = pygame.sprite.Group()
    rock = Rock(400, game.GAME_HEIGHT + 60, 15, 15, game, dx=-3, dy=2)
    group.add(rock)
    rock.update()
    assert len(group) == 0
