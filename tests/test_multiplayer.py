import pytest
import pygame
from states.game_world import Game_World
from objects.Rocks import Rock, BASIC
from objects.Player import (
    PLAYER_CENTER_OFFSET_X, PLAYER_CENTER_OFFSET_Y, MAX_LIVES,
)


def _no_actions():
    return {
        "left": False, "right": False, "up": False, "down": False,
        "action1": False, "action2": False,
        "start": False, "space": False, "escape": False,
        "secondary": False, "cycle_weapon": False, "toggle_autofire": False,
    }


def _enter_game_world(game, num_players=2):
    game.num_players = num_players
    gw = Game_World(game)
    gw.enter_state()
    return gw


# ---- player setup ----

def test_setup_creates_correct_player_count(game):
    game.setup_players(3)
    assert len(game.players) == 3
    for i, p in enumerate(game.players):
        assert p.index == i


def test_two_players_have_different_y(game):
    gw = _enter_game_world(game, 2)
    p1, p2 = game.players
    assert abs(p1.position_y - p2.position_y) > 50


def test_three_players_spread_evenly(game):
    gw = _enter_game_world(game, 3)
    ys = [p.position_y for p in game.players]
    assert ys[0] < ys[1] < ys[2]


def test_players_have_independent_weapons(game):
    gw = _enter_game_world(game, 2)
    from objects.Weapon import SpreadShot
    game.players[0].set_secondary(SpreadShot)
    assert game.players[0].secondary is not None
    assert game.players[1].secondary is None


def test_players_have_independent_lives(game):
    gw = _enter_game_world(game, 2)
    game.players[0].lives = 1
    assert game.players[1].lives == MAX_LIVES


# ---- death and survival ----

def test_game_continues_when_one_player_dies(game):
    gw = _enter_game_world(game, 2)
    p1 = game.players[0]
    p1.lives = 1
    p1.position_x, p1.position_y = 200, 200
    cx = int(p1.position_x) + PLAYER_CENTER_OFFSET_X
    cy = int(p1.position_y) + PLAYER_CENTER_OFFSET_Y
    rock = Rock(cx, cy, 45, 35, game)
    game.rocks.add(rock)
    actions = _no_actions()
    gw.update(1 / 60, actions)
    assert p1.alive is False
    assert gw.game_over is False


def test_game_over_when_all_players_die(game):
    gw = _enter_game_world(game, 2)
    for p in game.players:
        p.lives = 1
        p.position_x, p.position_y = 200, 200
    cx = int(game.players[0].position_x) + PLAYER_CENTER_OFFSET_X
    cy = int(game.players[0].position_y) + PLAYER_CENTER_OFFSET_Y
    rock = Rock(cx, cy, 60, 60, game, dx=0)
    game.rocks.add(rock)
    actions = _no_actions()
    gw.update(1 / 60, actions)
    assert gw.game_over is True


def test_dead_player_not_updated(game):
    gw = _enter_game_world(game, 2)
    p2 = game.players[1]
    p2.alive = False
    old_x = p2.position_x
    actions = _no_actions()
    actions["right"] = True
    p2.update(1 / 60, actions)
    assert p2.position_x > old_x


# ---- boss resurrection ----

def test_boss_defeat_resurrects_dead_player(game):
    gw = _enter_game_world(game, 2)
    p1, p2 = game.players
    p2.alive = False
    p2.lives = 0

    from objects.Boss import Boss
    gw.boss = Boss(game, attack_level=1, hp_override=1)
    gw.boss_phase = True
    gw.boss.entering = False
    gw.boss.alive_flag = True

    gw.boss.hp = 0
    gw.boss.alive_flag = False
    gw._on_boss_defeated()

    assert p2.alive is True
    assert p2.lives == MAX_LIVES


def test_boss_defeat_refreshes_all_lives(game):
    gw = _enter_game_world(game, 2)
    p1, p2 = game.players
    p1.lives = 1
    p2.lives = 2

    from objects.Boss import Boss
    gw.boss = Boss(game, attack_level=1, hp_override=1)
    gw.boss_phase = True
    gw.boss.entering = False
    gw.boss.alive_flag = False
    gw._on_boss_defeated()

    assert p1.lives == MAX_LIVES
    assert p2.lives == MAX_LIVES


# ---- per-player input ----

def test_per_player_actions_are_independent(game):
    assert len(game.player_actions) >= 2
    game.player_actions[0]["left"] = True
    assert game.player_actions[1]["left"] is False


def test_player_count_selection(game):
    game.num_players = 3
    gw = _enter_game_world(game, 3)
    assert len(game.players) == 3


# ---- pickup competition ----

def test_closest_player_collects_pickup(game):
    gw = _enter_game_world(game, 2)
    from objects.Pickup import UpgradePickup
    p1, p2 = game.players
    p1.position_x, p1.position_y = 100, 100
    p2.position_x, p2.position_y = 500, 500

    pickup = UpgradePickup(
        int(p1.position_x) + PLAYER_CENTER_OFFSET_X,
        int(p1.position_y) + PLAYER_CENTER_OFFSET_Y,
        None, game,
    )
    game.pickups.add(pickup)
    actions = _no_actions()
    gw.update(1 / 60, actions)
    assert p1.primary.level == 2
    assert p2.primary.level == 1
