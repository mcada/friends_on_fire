import os, sys, json, math, random, array as _array, pygame
from states.title import Title
from objects.Player import Player

BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
SCORES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scores.json")
CONTROLS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "controls.json")
MAX_SCORES = 10
MAX_PLAYERS = 3

BINDABLE_ACTIONS = [
    ("left", "Move Left"),
    ("right", "Move Right"),
    ("up", "Move Up"),
    ("down", "Move Down"),
    ("fire", "Fire"),
    ("secondary", "Secondary Weapon"),
    ("cycle_weapon", "Cycle Weapon"),
]

PLAYER_BINDINGS = [
    {
        "left": [pygame.K_a], "right": [pygame.K_d],
        "up": [pygame.K_w], "down": [pygame.K_s],
        "fire": [pygame.K_SPACE],
        "secondary": [pygame.K_LSHIFT, pygame.K_e],
        "cycle_weapon": [pygame.K_q],
    },
    {
        "left": [pygame.K_LEFT], "right": [pygame.K_RIGHT],
        "up": [pygame.K_UP], "down": [pygame.K_DOWN],
        "fire": [pygame.K_RSHIFT],
        "secondary": [pygame.K_RCTRL],
        "cycle_weapon": [pygame.K_SLASH],
    },
    {
        "left": [pygame.K_KP4], "right": [pygame.K_KP6],
        "up": [pygame.K_KP8], "down": [pygame.K_KP5],
        "fire": [pygame.K_KP0],
        "secondary": [pygame.K_KP1],
        "cycle_weapon": [pygame.K_KP2],
    },
]

ALWAYS_RESERVED = {pygame.K_RETURN, pygame.K_ESCAPE}


def _key_label(keys):
    """Human-readable label for a list of key codes."""
    if not keys:
        return "---"
    return ", ".join(pygame.key.name(k).upper() for k in keys)


def _move_label(bindings):
    """Compact label for the four movement keys."""
    parts = []
    for a in ("left", "right", "up", "down"):
        for k in bindings.get(a, []):
            n = pygame.key.name(k).upper()
            if n not in parts:
                parts.append(n)
    return "".join(parts) if len(parts) <= 5 else "/".join(parts)


def binding_labels_for(bindings):
    """Build a PLAYER_BINDING_LABELS-style dict from a bindings dict."""
    return {
        "move": _move_label(bindings),
        "fire": _key_label(bindings.get("fire", [])),
        "secondary": _key_label(bindings.get("secondary", [])),
        "cycle": _key_label(bindings.get("cycle_weapon", [])),
    }


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.GAME_WIDTH, self.GAME_HEIGHT = 1280, 600
        self.screen = pygame.display.set_mode((self.GAME_WIDTH, self.GAME_HEIGHT))
        self.game_canvas = self.screen
        pygame.display.set_caption("Friends on Fire!")
        self.running, self.playing = True, True
        self.actions = self._make_menu_actions()
        self.num_players = 1
        self.player_actions = [self._make_player_actions() for _ in range(MAX_PLAYERS)]
        self.last_keydown = None
        self.delta_time = 0
        self.paused = False
        self.active_game_world = None
        self.state_stack = []
        self.clock = pygame.time.Clock()
        self.load_assets()
        self.all_bindings = self._load_bindings()
        self._build_key_maps()
        self.load_states()
        self.projectiles = pygame.sprite.Group()
        self.rocks = pygame.sprite.Group()
        self.pickups = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.enemy_projectiles = pygame.sprite.Group()
        self.players = [Player(self, index=0)]
        self.high_scores = self.load_scores()

    @staticmethod
    def _make_menu_actions():
        return {
            "left": False, "right": False, "up": False, "down": False,
            "action1": False, "action2": False,
            "start": False, "space": False, "escape": False,
            "secondary": False, "cycle_weapon": False, "toggle_autofire": False,
        }

    @staticmethod
    def _make_player_actions():
        return {
            "left": False, "right": False, "up": False, "down": False,
            "space": False, "secondary": False,
            "cycle_weapon": False, "toggle_autofire": False,
        }

    def setup_players(self, n):
        self.num_players = n
        self.players = [Player(self, index=i) for i in range(n)]

    def game_loop(self):
        while self.playing:
            self.get_delta_time()
            self.get_events()
            self.update()
            self.render()

    def get_events(self):
        self.last_keydown = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.playing = False
                self.running = False
            if event.type == pygame.KEYDOWN:
                self.last_keydown = event.key
                for action in self._menu_key_down_map.get(event.key, ()):
                    self.actions[action] = True
                for i, kmap in enumerate(self._player_key_down_maps):
                    for action in kmap.get(event.key, ()):
                        self.player_actions[i][action] = True
            if event.type == pygame.KEYUP:
                for action in self._menu_key_up_map.get(event.key, ()):
                    self.actions[action] = False
                for i, kmap in enumerate(self._player_key_up_maps):
                    for action in kmap.get(event.key, ()):
                        self.player_actions[i][action] = False

    def update(self):
        if not self.state_stack:
            return
        self.state_stack[-1].update(self.delta_time, self.actions)
        if getattr(self.state_stack[-1], "game_over", False):
            return
        self.projectiles.update()
        self.enemy_projectiles.update()
        self.pickups.update()
        for i, player in enumerate(self.players):
            if player.alive:
                player.update(self.delta_time, self.player_actions[i])

    def render(self):
        if not self.state_stack:
            return
        self.state_stack[-1].render(self.game_canvas)

        if self.is_gameplay_active():
            from objects.Rocks import BLACKHOLE
            for rock in self.rocks:
                if rock.rock_type == BLACKHOLE:
                    rock.draw_blackhole_effects(self.game_canvas)
            self.rocks.draw(self.game_canvas)
            self.pickups.draw(self.game_canvas)
            self.projectiles.draw(self.game_canvas)
            self.enemy_projectiles.draw(self.game_canvas)
            for enemy in self.enemies:
                enemy.draw(self.game_canvas)
            for player in self.players:
                if player.alive:
                    player.render(self.game_canvas)
            gw = self.active_game_world
            if gw and gw.boss and gw.boss.alive_flag:
                gw.boss.draw(self.game_canvas)
            if gw:
                for p in gw.particles:
                    p.draw(self.game_canvas)

        pygame.display.flip()

    def is_gameplay_active(self):
        gw = self.active_game_world
        return gw is not None and not gw.game_over and not gw.level_won

    def get_delta_time(self):
        self.delta_time = self.clock.tick(60) / 1000.0

    def draw_text(self, surface, text, color, x, y):
        key = (text, color, 30)
        text_surface = self._text_cache.get(key)
        if text_surface is None:
            text_surface = self.font.render(text, True, color)
            self._text_cache[key] = text_surface
        text_rect = text_surface.get_rect()
        text_rect.center = (x, y)
        surface.blit(text_surface, text_rect)

    def get_font(self, size):
        font = self._font_cache.get(size)
        if font is None:
            font = pygame.font.SysFont("comicsans", size)
            self._font_cache[size] = font
        return font

    def draw_text_sized(self, surface, text, color, x, y, size):
        key = (text, color, size)
        text_surface = self._text_cache.get(key)
        if text_surface is None:
            text_surface = self.get_font(size).render(text, True, color)
            self._text_cache[key] = text_surface
        text_rect = text_surface.get_rect()
        text_rect.center = (x, y)
        surface.blit(text_surface, text_rect)

    def load_assets(self):
        self.assets_dir = os.path.join(BASE_DIR, "assets")
        self.sprite_dir = os.path.join(self.assets_dir, "sprites")
        self.sound_dir = os.path.join(self.assets_dir, "sounds")
        self.background = pygame.image.load(
            os.path.join(self.assets_dir, "bg.jpeg")
        ).convert()
        self._font_cache = {}
        self._text_cache = {}
        self.font = self.get_font(30)
        self.load_sounds()

    def load_sounds(self):
        self.sounds = {}
        for name in ("death", "powerup"):
            path = os.path.join(self.sound_dir, f"{name}.wav")
            if os.path.exists(path):
                self.sounds[name] = pygame.mixer.Sound(path)
            else:
                self.sounds[name] = None
        self.shoot_sounds = []
        self.explosion_sounds = []
        self.weapon_sounds = {}
        for i in range(1, 4):
            for prefix, target in (("shoot", self.shoot_sounds), ("explosion", self.explosion_sounds)):
                path = os.path.join(self.sound_dir, f"{prefix}_{i}.wav")
                if os.path.exists(path):
                    target.append(pygame.mixer.Sound(path))
        for weapon_prefix in ("spread", "laser", "missile"):
            group = []
            for i in range(1, 4):
                path = os.path.join(self.sound_dir, f"{weapon_prefix}_{i}.wav")
                if os.path.exists(path):
                    group.append(pygame.mixer.Sound(path))
            if group:
                self.weapon_sounds[weapon_prefix] = group
        self.weapon_sounds["spread"] = self._generate_swing_sounds()
        self.music_paths = {
            "menu": os.path.join(self.sound_dir, "menu_music.mp3"),
            "game": os.path.join(self.sound_dir, "game_music.ogg"),
            "boss": os.path.join(self.sound_dir, "boss_music.wav"),
        }

    def _generate_swing_sounds(self):
        """Generate 3 lightsaber-swing variations for the spread weapon."""
        variants = [
            (0.32, 190, 580, 150),
            (0.28, 220, 680, 170),
            (0.36, 160, 500, 130),
        ]
        sounds = []
        for dur, base, peak, end in variants:
            snd = self._synth_swing(dur, base, peak, end)
            if snd:
                sounds.append(snd)
        return sounds or self.weapon_sounds.get("spread", [])

    @staticmethod
    def _synth_swing(duration, base_freq, peak_freq, end_freq):
        mixer_init = pygame.mixer.get_init()
        if not mixer_init:
            return None
        sample_rate, _, channels = mixer_init
        num_samples = int(sample_rate * duration)
        buf = _array.array('h')
        phase = 0.0
        for i in range(num_samples):
            t = i / sample_rate
            p = t / duration
            if p < 0.22:
                freq = base_freq + (peak_freq - base_freq) * (p / 0.22)
            else:
                freq = peak_freq - (peak_freq - end_freq) * ((p - 0.22) / 0.78)
            phase += 2 * math.pi * freq / sample_rate
            tone = (math.sin(phase) * 0.40
                    + math.sin(phase * 2) * 0.18
                    + math.sin(phase * 3) * 0.07
                    + math.sin(phase * 5.02) * 0.04)
            noise = (random.random() * 2 - 1) * 0.06
            if p < 0.06:
                env = p / 0.06
            elif p > 0.65:
                env = (1.0 - p) / 0.35
            else:
                env = 1.0
            val = int(max(-1.0, min(1.0, (tone + noise) * env * 0.85)) * 32000)
            for _ in range(channels):
                buf.append(val)
        return pygame.mixer.Sound(buffer=buf)

    def play_boss_death_sound(self):
        """Layer all explosion sounds at staggered volumes for an epic boom."""
        for i, snd in enumerate(self.explosion_sounds):
            ch = pygame.mixer.find_channel()
            if ch:
                ch.set_volume(1.0 - i * 0.15)
                ch.play(snd)

    def play_sound(self, name):
        if name == "shoot":
            if self.shoot_sounds:
                random.choice(self.shoot_sounds).play()
            return
        if name == "explosion":
            if self.explosion_sounds:
                random.choice(self.explosion_sounds).play()
            return
        if self.weapon_sounds.get(name):
            random.choice(self.weapon_sounds[name]).play()
            return
        sound = self.sounds.get(name)
        if sound:
            sound.play()

    def play_music(self, name, loops=-1, volume=0.8):
        path = self.music_paths.get(name)
        if path and os.path.exists(path):
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops)

    def stop_music(self):
        pygame.mixer.music.stop()

    def stop_all_sounds(self):
        pygame.mixer.stop()

    @staticmethod
    def default_bindings(player_idx=None):
        if player_idx is not None:
            return {k: list(v) for k, v in PLAYER_BINDINGS[player_idx].items()}
        return [{k: list(v) for k, v in b.items()} for b in PLAYER_BINDINGS]

    def reserved_keys_for(self, player_idx):
        """Keys that cannot be used by player_idx (belong to other players)."""
        reserved = set(ALWAYS_RESERVED)
        for i, bindings in enumerate(self.all_bindings):
            if i == player_idx:
                continue
            for keys in bindings.values():
                reserved.update(keys)
        return reserved

    def get_binding_labels(self):
        """Build display labels for all players from current bindings."""
        return [binding_labels_for(b) for b in self.all_bindings]

    @staticmethod
    def _bindings_to_key_maps(bindings):
        """Build key->action maps for a single player's bindings."""
        down, up = {}, {}
        for action, keys in bindings.items():
            for key in keys:
                if action == "fire":
                    down.setdefault(key, []).append("space")
                    down.setdefault(key, []).append("toggle_autofire")
                    up.setdefault(key, []).append("space")
                elif action == "cycle_weapon":
                    down.setdefault(key, []).append("cycle_weapon")
                else:
                    down.setdefault(key, []).append(action)
                    up.setdefault(key, []).append(action)
        return down, up

    def _build_key_maps(self):
        """Build per-player key maps and a combined menu key map."""
        all_bindings = self.all_bindings

        self._player_key_down_maps = []
        self._player_key_up_maps = []
        for b in all_bindings:
            d, u = self._bindings_to_key_maps(b)
            self._player_key_down_maps.append(d)
            self._player_key_up_maps.append(u)

        menu_down, menu_up = {}, {}
        for b in all_bindings:
            for action in ("left", "right", "up", "down"):
                for key in b.get(action, []):
                    menu_down.setdefault(key, []).append(action)
                    menu_up.setdefault(key, []).append(action)
            for key in b.get("fire", []):
                menu_down.setdefault(key, []).append("space")
                menu_up.setdefault(key, []).append("space")
        for key, action in [
            (pygame.K_RETURN, "start"), (pygame.K_ESCAPE, "escape"),
        ]:
            menu_down.setdefault(key, []).append(action)
            menu_up.setdefault(key, []).append(action)
        self._menu_key_down_map = menu_down
        self._menu_key_up_map = menu_up

    def _load_bindings(self):
        defaults = self.default_bindings()
        if not os.path.exists(CONTROLS_FILE):
            return defaults
        try:
            with open(CONTROLS_FILE, "r") as f:
                data = json.load(f)

            if "player_0" in data:
                result = []
                for i in range(MAX_PLAYERS):
                    pdata = data.get(f"player_{i}", {})
                    bindings = {}
                    for action, key_names in pdata.items():
                        if action in defaults[i]:
                            bindings[action] = [
                                pygame.key.key_code(n) for n in key_names
                            ]
                    for action, keys in defaults[i].items():
                        if action not in bindings:
                            bindings[action] = list(keys)
                    result.append(bindings)
                return result

            bindings = {}
            for action, key_names in data.items():
                if action in defaults[0]:
                    bindings[action] = [
                        pygame.key.key_code(n) for n in key_names
                    ]
            for action, keys in defaults[0].items():
                if action not in bindings:
                    bindings[action] = list(keys)
            return [bindings] + defaults[1:]
        except (json.JSONDecodeError, IOError, ValueError, KeyError,
                TypeError, AttributeError):
            return defaults

    def save_bindings(self):
        data = {}
        for i, bindings in enumerate(self.all_bindings):
            data[f"player_{i}"] = {
                action: [pygame.key.name(k) for k in keys]
                for action, keys in bindings.items()
            }
        try:
            with open(CONTROLS_FILE, "w") as f:
                json.dump(data, f)
        except IOError:
            pass

    def load_states(self):
        self.title_screen = Title(self)
        self.state_stack.append(self.title_screen)

    def load_scores(self):
        if os.path.exists(SCORES_FILE):
            try:
                with open(SCORES_FILE, "r") as f:
                    return json.load(f)[:MAX_SCORES]
            except (json.JSONDecodeError, IOError):
                pass
        return []

    def save_score(self, time_alive, kills):
        self.high_scores.append({"time": time_alive, "kills": kills})
        self.high_scores.sort(key=lambda s: (s["kills"], s["time"]), reverse=True)
        self.high_scores = self.high_scores[:MAX_SCORES]
        try:
            with open(SCORES_FILE, "w") as f:
                json.dump(self.high_scores, f)
        except IOError:
            pass

    def return_to_menu(self):
        self.rocks.empty()
        self.projectiles.empty()
        self.pickups.empty()
        self.enemies.empty()
        self.enemy_projectiles.empty()
        self.active_game_world = None
        self.paused = False
        while len(self.state_stack) > 1:
            self.state_stack.pop()
        self.play_music("menu")
        self.reset_keys()

    def reset_keys(self):
        for action in self.actions:
            self.actions[action] = False
        for pa in self.player_actions:
            for action in pa:
                pa[action] = False


if __name__ == "__main__":
    game_instance = Game()
    while game_instance.running:
        game_instance.game_loop()
