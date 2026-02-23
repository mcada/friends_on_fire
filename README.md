# Friends on Fire!

A side-scrolling space shooter built with Pygame. Fly solo or team up with up to 3 players in local co-op, blast through asteroids and enemy ships, collect weapon upgrades, and take on multi-phase bosses.

## Quick Start

Requires **Python 3.10+** and **Pygame 2.6+**.

```bash
git clone <repo-url>
cd friends_on_fire
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python Game.py
```

### Building a Standalone Executable

A PyInstaller spec is included for distribution:

```bash
pip install pyinstaller
pyinstaller FriendsOnFire.spec
```

## Game Modes

| Mode | Description |
|------|-------------|
| **Endless** | Survive as long as you can. Difficulty ramps up over time. Boss appears every 120 s. |
| **Level 1-3** | Survive 120 seconds per level with increasing asteroid and enemy difficulty, then defeat the boss. |
| **Boss Challenge** | Skip straight to a full-power boss fight. No asteroids. |
| **Testing** | Endless mode with all weapons pre-equipped and shield active. |

## Players & Ships

1-3 players on a single keyboard. Each player gets their own ship, weapons, lives, and shield.

| Ship | Style | Notes |
|------|-------|-------|
| Viper (P1) | White, PNG sprite | Classic look |
| Arrow (P2) | Red, procedurally generated | Sleek interceptor |
| Titan (P3) | Yellow, procedurally generated | Heavy gunship |

## Controls

Controls are fully rebindable per player from the Controls menu. Defaults:

| Action | Player 1 | Player 2 | Player 3 |
|--------|----------|----------|----------|
| Move | W / A / S / D | Arrow keys | Numpad 8 / 4 / 5 / 6 |
| Fire (also toggles auto-fire) | Space | Right Shift | Numpad 0 |
| Activate secondary | Left Shift / E | Right Ctrl | Numpad 1 |
| Cycle secondary weapon | Q | / | Numpad 2 |
| Pause | Escape or Enter | | |

## Weapons

### Primary -- Straight Cannon

Always equipped. Upgrades through 5 levels via gold pickups, adding more projectiles and spread at each tier.

### Secondary Weapons

Obtained from colored pickups. You can carry all three and cycle between them. Each has 3 upgrade levels and operates on an activate/cooldown cycle -- higher levels extend the active firing window. Background weapons continue their cooldown timers even when not selected.

| Weapon | Color | Behaviour |
|--------|-------|-----------|
| **Pulse Spread** | Orchid | Fires pulse orbs that auto-aim at nearby targets |
| **Laser Cannon** | Lime | Screen-spanning beam that pierces through all enemies |
| **Homing Missile** | Orange | Missiles that track and chase targets |

## Enemies

| Enemy | HP | Behaviour |
|-------|-----|-----------|
| **Drone** | 2 | Flies across the screen, fires 1-2 straight shots on a schedule |
| **Fighter** | 4 | Patrols on the right side, fires aimed shots at the nearest player |

Enemies begin spawning at 30 s. Fighters unlock at 55 s. Drones can arrive in formation waves (V, line, or diagonal patterns).

## Boss

The boss appears after surviving 120 seconds (or immediately in Boss Challenge mode). It features:

- **Invulnerability phases** at 75%, 50%, and 25% HP with a shield bubble
- **4 tiers of attacks** that unlock based on encounter number / level:
  - *Tier 1:* Aimed burst, shotgun fan, wall-with-gap (destroyable projectiles)
  - *Tier 2:* Laser sweep, laser cross (indestructible beams)
  - *Tier 3:* Rock barrage (throws asteroids)
  - *Tier 4:* Spiral storm, ring pulse (overwhelming bullet patterns)
- Defeating the boss in Endless mode revives all players and schedules the next boss

## Asteroids

| Type | HP | Special |
|------|-----|---------|
| **Basic** | 1 | Standard asteroid |
| **Cluster** | 1 | Splits into 2-3 smaller fragments on destruction |
| **Iron** | 3 | Metallic look, shows damage cracks as HP drops |

## Pickups

- **Weapon Upgrades** -- drop from destroyed asteroids with decreasing probability (to prevent over-powering). Can be primary (gold) or secondary (colored).
- **Shields** -- one-hit protection with a pity system that increases drop chance the longer you go without one.

## Mechanics

- **Lives:** 3 per player. Taking a hit grants brief invulnerability. Losing all lives removes that player. Game over when all players are dead.
- **Shields:** Absorb one hit before breaking. Shown as a pulsing bubble around the ship.
- **Auto-fire:** Pressing fire toggles auto-fire so you can focus on dodging.
- **Mask-based collision:** Pixel-accurate hit detection for all objects.
- **Particle effects:** Explosions on asteroid/enemy/player destruction.
- **High scores:** Top 10 scores saved locally, ranked by kills then survival time.

## Running Tests

```bash
pip install pytest
pytest
```

## Project Structure

```
friends_on_fire/
├── Game.py                  # Entry point, game loop, input, audio, bindings
├── requirements.txt         # pygame>=2.6
├── FriendsOnFire.spec       # PyInstaller build spec
├── controls.json            # Saved key bindings (per player)
├── scores.json              # High score data
├── assets/
│   ├── bg.jpeg              # Background image
│   ├── sprites/             # Ship, asteroid, ammo sprites
│   ├── enemies/             # Enemy sprites
│   └── sounds/              # SFX + music tracks
├── objects/
│   ├── Player.py            # Player ship, movement, weapons, rendering
│   ├── Weapon.py            # Weapon base + StraightCannon, SpreadShot, LaserCannon, HomingMissile
│   ├── Projectile.py        # All projectile types (straight, pulse, beam, missile, homing)
│   ├── Rocks.py             # Asteroid types (Basic, Cluster, Iron)
│   ├── Enemy.py             # Drone, Fighter enemy ships
│   ├── Boss.py              # Boss with multi-phase attacks
│   ├── Pickup.py            # Weapon upgrade and shield pickups
│   └── ships.py             # Procedural ship sprite generators (Arrow, Titan)
├── states/
│   ├── state.py             # Base State class
│   ├── title.py             # Main menu
│   ├── player_select.py     # Player count selection (1-3)
│   ├── level_select.py      # Game mode selection
│   ├── game_world.py        # Core gameplay, spawning, collisions, HUD
│   ├── controls.py          # Key rebinding screen
│   ├── pause_menu.py        # Pause overlay
│   └── scoreboard.py        # High score display
└── tests/                   # pytest suite (13 test modules)
```
