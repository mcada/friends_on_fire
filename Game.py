import os, json, random, pygame
from states.title import Title
from objects.Player import Player

SCORES_FILE = os.path.join(os.path.dirname(__file__), "scores.json")
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
        }
        self.delta_time = 0
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
                if event.key == pygame.K_ESCAPE:
                    self.actions["escape"] = True

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

        self.screen.blit(self.game_canvas, (0, 0))
        pygame.display.flip()

    def is_gameplay_active(self):
        from states.game_world import Game_World
        for s in self.state_stack:
            if isinstance(s, Game_World):
                return not s.game_over
        return False

    def get_delta_time(self):
        self.delta_time = self.clock.tick(60) / 1000.0

    def draw_text(self, surface, text, color, x, y):
        text_surface = self.font.render(text, True, color)
        text_rect = text_surface.get_rect()
        text_rect.center = (x, y)
        surface.blit(text_surface, text_rect)

    def draw_text_sized(self, surface, text, color, x, y, size):
        font = pygame.font.SysFont("comicsans", size)
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect()
        text_rect.center = (x, y)
        surface.blit(text_surface, text_rect)

    def load_assets(self):
        self.assets_dir = os.path.join("assets")
        self.sprite_dir = os.path.join(self.assets_dir, "sprites")
        self.sound_dir = os.path.join(self.assets_dir, "sounds")
        self.font = pygame.font.SysFont("comicsans", 30)
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
        for weapon_prefix in ("spread", "laser"):
            group = []
            for i in range(1, 4):
                path = os.path.join(self.sound_dir, f"{weapon_prefix}_{i}.wav")
                if os.path.exists(path):
                    group.append(pygame.mixer.Sound(path))
            if group:
                self.weapon_sounds[weapon_prefix] = group
        self.music_paths = {
            "menu": os.path.join(self.sound_dir, "menu_music.mp3"),
            "game": os.path.join(self.sound_dir, "game_music.ogg"),
        }

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
