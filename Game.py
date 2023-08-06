import os, time, pygame
from states.title import Title


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.GAME_WIDTH, self.GAME_HEIGHT = 1280, 600
        self.game_canvas = pygame.Surface((self.GAME_WIDTH, self.GAME_HEIGHT))
        self.screen = pygame.display.set_mode((self.GAME_WIDTH, self.GAME_HEIGHT))
        self.running, self.playing = True, True
        self.actions = {
            "left": False,
            "right": False,
            "up": False,
            "down": False,
            "action1": False,
            "action2": False,
            "start": False,
        }
        self.delta_time, self.previous_time = 0, 0
        self.state_stack = []
        self.load_assets()
        self.load_states()

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
                if event.key == pygame.K_ESCAPE:
                    self.playing = False
                    self.running = False
                if event.key == pygame.K_a:
                    self.actions["left"] = True
                if event.key == pygame.K_d:
                    self.actions["right"] = True
                if event.key == pygame.K_w:
                    self.actions["up"] = True
                if event.key == pygame.K_s:
                    self.actions["down"] = True
                if event.key == pygame.K_p:
                    self.actions["action1"] = True
                if event.key == pygame.K_o:
                    self.actions["action2"] = True
                if event.key == pygame.K_RETURN:
                    self.actions["start"] = True

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_a:
                    self.actions["left"] = False
                if event.key == pygame.K_d:
                    self.actions["right"] = False
                if event.key == pygame.K_w:
                    self.actions["up"] = False
                if event.key == pygame.K_s:
                    self.actions["down"] = False
                if event.key == pygame.K_p:
                    self.actions["action1"] = False
                if event.key == pygame.K_o:
                    self.actions["action2"] = False
                if event.key == pygame.K_RETURN:
                    self.actions["start"] = False

    def update(self):
        self.state_stack[-1].update(self.delta_time, self.actions)

    def render(self):
        self.state_stack[-1].render(self.game_canvas)
        # Render current state to the screen
        self.screen.blit(
            self.game_canvas,
            (0, 0),
        )
        pygame.display.flip()

    def get_delta_time(self):
        now = time.time()
        self.delta_time = now - self.previous_time
        self.previous_time = now

    def draw_text(self, surface, text, color, x, y):
        text_surface = self.font.render(text, True, color)
        # text_surface.set_colorkey((0,0,0))
        text_rect = text_surface.get_rect()
        text_rect.center = (x, y)
        surface.blit(text_surface, text_rect)

    def load_assets(self):
        # Create pointers to directories
        self.assets_dir = os.path.join("assets")
        self.sprite_dir = os.path.join(self.assets_dir, "sprites")
        self.font = pygame.font.SysFont("comicsans", 30)

    def load_states(self):
        self.title_screen = Title(self)
        self.state_stack.append(self.title_screen)


if __name__ == "__main__":
    game_instance = Game()
    while game_instance.running:
        game_instance.game_loop()
