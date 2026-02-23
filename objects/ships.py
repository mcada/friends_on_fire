"""Procedural ship sprite generators.

Each builder returns (stationary_frames, flame_frames) -- lists of
pygame.Surface at PLAYER_WIDTH x PLAYER_HEIGHT, ready for the Player
sprite compositing pipeline.

Ship 0 ("Viper")  : loaded from PNG assets -- not built here.
Ship 1 ("Arrow")  : red interceptor -- sleek, angular, fast-looking.
Ship 2 ("Titan")  : yellow gunship  -- wide, armored, heavy-looking.
"""

import pygame
import math

SHIP_W, SHIP_H = 80, 35
CY = SHIP_H // 2


def _exhaust(surf, x, y_top, y_bot, length, brightness=0.85):
    """Draw a triangular engine exhaust flame with inner core."""
    mid = (y_top + y_bot) // 2
    outer = [(x, y_top), (x - length, mid), (x, y_bot)]
    glow = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(glow, (255, 160, 40, int(130 * brightness)), outer)
    surf.blit(glow, (0, 0))
    il = int(length * 0.55)
    ih = max(1, (y_bot - y_top) // 3)
    inner = [(x, mid - ih), (x - il, mid), (x, mid + ih)]
    core = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(core, (255, 255, 200, int(210 * brightness)), inner)
    surf.blit(core, (0, 0))


# ---------------------------------------------------------------------------
#  Ship 1 -- "Arrow" (red interceptor)
# ---------------------------------------------------------------------------

_ARROW_BODY_COLOR = (175, 35, 35)
_ARROW_HIGHLIGHT = (225, 75, 75)
_ARROW_WING = (135, 25, 25)
_ARROW_WING_EDGE = (95, 18, 18)
_ARROW_COCKPIT = (80, 185, 255)
_ARROW_COCKPIT_HI = (155, 225, 255)
_ARROW_ENGINE = (60, 60, 72)
_ARROW_ENGINE_HI = (105, 105, 115)

_ARROW_EXHAUST_LENS = [18, 26, 13]


def _build_arrow_frame(flame_len=0):
    surf = pygame.Surface((SHIP_W, SHIP_H), pygame.SRCALPHA)
    cy = CY

    body = [
        (74, cy), (56, cy - 9), (22, cy - 8),
        (12, cy - 5), (12, cy + 5),
        (22, cy + 8), (56, cy + 9),
    ]
    pygame.draw.polygon(surf, _ARROW_BODY_COLOR, body)

    stripe = [
        (70, cy - 1), (22, cy - 3), (14, cy - 1),
        (14, cy + 1), (22, cy + 3), (70, cy + 1),
    ]
    pygame.draw.polygon(surf, _ARROW_HIGHLIGHT, stripe)

    for sign, wy in [(-1, 1), (1, SHIP_H - 2)]:
        wing = [
            (40, cy + sign * 8), (24, wy), (14, wy), (14, cy + sign * 5),
        ]
        pygame.draw.polygon(surf, _ARROW_WING, wing)
        pygame.draw.polygon(surf, _ARROW_WING_EDGE, wing, 1)

    pygame.draw.ellipse(surf, _ARROW_COCKPIT, (57, cy - 4, 10, 8))
    pygame.draw.ellipse(surf, _ARROW_COCKPIT_HI, (59, cy - 2, 6, 4))

    for ey in [cy - 4, cy + 2]:
        pygame.draw.rect(surf, _ARROW_ENGINE, (8, ey, 6, 3))
        pygame.draw.rect(surf, _ARROW_ENGINE_HI, (9, ey + 1, 4, 1))

    if flame_len > 0:
        _exhaust(surf, 9, cy - 5, cy - 1, flame_len)
        _exhaust(surf, 9, cy + 1, cy + 5, flame_len)

    return surf


def build_arrow():
    stationary = [_build_arrow_frame(0)]
    flames = [_build_arrow_frame(fl) for fl in _ARROW_EXHAUST_LENS]
    return stationary, flames


# ---------------------------------------------------------------------------
#  Ship 2 -- "Titan" (yellow gunship)
# ---------------------------------------------------------------------------

_TITAN_BODY = (195, 170, 40)
_TITAN_ARMOR = (165, 145, 30)
_TITAN_DARK = (130, 110, 20)
_TITAN_HIGHLIGHT = (225, 205, 70)
_TITAN_COCKPIT = (70, 200, 185)
_TITAN_COCKPIT_HI = (130, 240, 220)
_TITAN_ENGINE = (100, 88, 28)
_TITAN_ENGINE_HI = (145, 130, 55)

_TITAN_EXHAUST_LENS = [20, 29, 14]


def _build_titan_frame(flame_len=0):
    surf = pygame.Surface((SHIP_W, SHIP_H), pygame.SRCALPHA)
    cy = CY

    body = [
        (72, cy - 4), (75, cy), (72, cy + 4),
        (50, cy + 10), (15, cy + 10),
        (10, cy + 7), (10, cy - 7),
        (15, cy - 10), (50, cy - 10),
    ]
    pygame.draw.polygon(surf, _TITAN_BODY, body)

    pygame.draw.line(surf, _TITAN_HIGHLIGHT, (68, cy), (18, cy), 1)
    pygame.draw.line(surf, _TITAN_DARK, (50, cy - 9), (50, cy + 9), 1)

    plate_t = [(48, cy - 10), (18, cy - 10), (14, cy - 14), (42, cy - 14)]
    pygame.draw.polygon(surf, _TITAN_ARMOR, plate_t)
    pygame.draw.polygon(surf, _TITAN_DARK, plate_t, 1)

    plate_b = [(48, cy + 10), (18, cy + 10), (14, cy + 14), (42, cy + 14)]
    pygame.draw.polygon(surf, _TITAN_ARMOR, plate_b)
    pygame.draw.polygon(surf, _TITAN_DARK, plate_b, 1)

    pygame.draw.polygon(surf, _TITAN_COCKPIT,
                         [(66, cy - 3), (71, cy), (66, cy + 3), (58, cy)])
    pygame.draw.polygon(surf, _TITAN_COCKPIT_HI,
                         [(64, cy - 1), (68, cy), (64, cy + 1), (60, cy)])

    for ey in [cy - 8, cy + 5]:
        pygame.draw.rect(surf, _TITAN_ENGINE, (6, ey, 8, 4))
        pygame.draw.rect(surf, _TITAN_ENGINE_HI, (7, ey + 1, 6, 2))

    if flame_len > 0:
        _exhaust(surf, 7, cy - 9, cy - 4, flame_len, 0.9)
        _exhaust(surf, 7, cy + 4, cy + 9, flame_len, 0.9)

    return surf


def build_titan():
    stationary = [_build_titan_frame(0)]
    flames = [_build_titan_frame(fl) for fl in _TITAN_EXHAUST_LENS]
    return stationary, flames


# ---------------------------------------------------------------------------
#  Registry -- used by Player to look up designs by ship_id.
# ---------------------------------------------------------------------------

SHIP_DESIGNS = [
    {"id": 0, "name": "Viper",  "color": (255, 255, 255), "builder": None},
    {"id": 1, "name": "Arrow",  "color": (255, 100, 100), "builder": build_arrow},
    {"id": 2, "name": "Titan",  "color": (255, 220, 80),  "builder": build_titan},
]
