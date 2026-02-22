import os, sys, json, math, random, array as _array, pygame
from states.title import Title
from objects.Player import Player

BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
SCORES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scores.json")
MAX_SCORES = 10


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.GAME_WIDTH, self.GAME_HEIGHT = 1280, 600
        self.game_canvas = pygame.Surface((self.GAME_WIDTH, self.GAME_HEIGHT))
        self.screen = pygame.display.set_mode((self.GAME_WIDTH, self.GAME_HEIGHT))
        pygame.display.set_caption("Friends on Fire!")
        self.running, self.playing = True, True
        self.actions = {
            "left": False,
            "right": False,
            "up": False,
            "down": False,
            "action1": False,
            "action2": False,
            "start": False,
            "space": False,
            "escape": False,
            "secondary": False,
            "cycle_weapon": False,
            "toggle_autofire": False,
        }
        self.delta_time = 0
        self.paused = False
        self.active_game_world = None
        self.state_stack = []
        self.clock = pygame.time.Clock()
        self.load_assets()
        self.load_states()
        self.projectiles = pygame.sprite.Group()
        self.rocks = pygame.sprite.Group()
        self.pickups = pygame.sprite.Group()
        self.player = Player(self)
        self.high_scores = self.load_scores()

    def game_loop(self):
        while self.playing:
            self.get_delta_time()
            self.get_events()
            self.update()
            self.render()

    def get_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.playing = False
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_a, pygame.K_LEFT):
                    self.actions["left"] = True
                if event.key in (pygame.K_d, pygame.K_RIGHT):
                    self.actions["right"] = True
                if event.key in (pygame.K_w, pygame.K_UP):
                    self.actions["up"] = True
                if event.key in (pygame.K_s, pygame.K_DOWN):
                    self.actions["down"] = True
                if event.key == pygame.K_p:
                    self.actions["action1"] = True
                if event.key == pygame.K_o:
                    self.actions["action2"] = True
                if event.key == pygame.K_RETURN:
                    self.actions["start"] = True
                if event.key == pygame.K_SPACE:
                    self.actions["space"] = True
                    self.actions["toggle_autofire"] = True
                if event.key == pygame.K_ESCAPE:
                    self.actions["escape"] = True
                if event.key in (pygame.K_LSHIFT, pygame.K_e):
                    self.actions["secondary"] = True
                if event.key == pygame.K_q:
                    self.actions["cycle_weapon"] = True

            if event.type == pygame.KEYUP:
                if event.key in (pygame.K_a, pygame.K_LEFT):
                    self.actions["left"] = False
                if event.key in (pygame.K_d, pygame.K_RIGHT):
                    self.actions["right"] = False
                if event.key in (pygame.K_w, pygame.K_UP):
                    self.actions["up"] = False
                if event.key in (pygame.K_s, pygame.K_DOWN):
                    self.actions["down"] = False
                if event.key == pygame.K_p:
                    self.actions["action1"] = False
                if event.key == pygame.K_o:
                    self.actions["action2"] = False
                if event.key == pygame.K_RETURN:
                    self.actions["start"] = False
                if event.key == pygame.K_SPACE:
                    self.actions["space"] = False
                if event.key == pygame.K_ESCAPE:
                    self.actions["escape"] = False
                if event.key in (pygame.K_LSHIFT, pygame.K_e):
                    self.actions["secondary"] = False

    def update(self):
        self.state_stack[-1].update(self.delta_time, self.actions)
        if getattr(self.state_stack[-1], "game_over", False):
            return
        self.projectiles.update()
        self.pickups.update()
        self.player.update(self.delta_time, self.actions)

    def render(self):
        self.state_stack[-1].render(self.game_canvas)

        if self.is_gameplay_active():
            self.rocks.draw(self.game_canvas)
            self.pickups.draw(self.game_canvas)
            self.projectiles.draw(self.game_canvas)
            self.player.render(self.game_canvas)
            gw = self.active_game_world
            if gw and gw.boss and gw.boss.alive_flag:
                gw.boss.draw(self.game_canvas)

        self.screen.blit(self.game_canvas, (0, 0))
        pygame.display.flip()

    def is_gameplay_active(self):
        gw = self.active_game_world
        return gw is not None and not gw.game_over and not gw.level_won

    def get_delta_time(self):
        self.delta_time = self.clock.tick(60) / 1000.0

    def draw_text(self, surface, text, color, x, y):
        text_surface = self.font.render(text, True, color)
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
        text_surface = self.get_font(size).render(text, True, color)
        text_rect = text_surface.get_rect()
        text_rect.center = (x, y)
        surface.blit(text_surface, text_rect)

    def load_assets(self):
        self.assets_dir = os.path.join(BASE_DIR, "assets")
        self.sprite_dir = os.path.join(self.assets_dir, "sprites")
        self.sound_dir = os.path.join(self.assets_dir, "sounds")
        self._font_cache = {}
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
        if name in self.weapon_sounds:
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
        self.active_game_world = None
        self.paused = False
        while len(self.state_stack) > 1:
            self.state_stack.pop()
        self.play_music("menu")
        self.reset_keys()

    def reset_keys(self):
        for action in self.actions:
            self.actions[action] = False


if __name__ == "__main__":
    game_instance = Game()
    while game_instance.running:
        game_instance.game_loop()
