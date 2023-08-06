import pygame, os
from states.state import State

# from states.pause_menu import PauseMenu


class Game_World(State):
    def __init__(self, game):
        State.__init__(self, game)
        self.player = Player(self.game)
        self.background = pygame.image.load(
            os.path.join(self.game.assets_dir, "bg.jpeg")
        )

    def update(self, delta_time, actions):
        # Check if the game was paused
        # if actions["start"]:
        #     new_state = PauseMenu(self.game)
        #     new_state.enter_state()
        self.player.update(delta_time, actions)
        pass

    def render(self, display):
        display.blit(self.background, (0, 0))
        self.player.render(display)


class Player:
    def __init__(self, game):
        self.game = game
        self.load_sprites()
        self.position_x, self.position_y = 100, self.game.GAME_HEIGHT / 2
        self.current_frame, self.last_frame_update = 0, 0
        self.player_speed = 200

    def update(self, delta_time, actions):
        # Get the direction from inputs
        direction_x = actions["right"] - actions["left"]
        direction_y = actions["down"] - actions["up"]
        # Update the position
        self.position_x += self.player_speed * delta_time * direction_x
        self.position_y += self.player_speed * delta_time * direction_y
        # Animate the sprite
        self.animate(delta_time, direction_x, direction_y)

    def render(self, display):
        display.blit(self.curr_image, (self.position_x, self.position_y))

    def animate(self, delta_time, direction_x, direction_y):
        # Compute how much time has passed since the frame last updated
        self.last_frame_update += delta_time

        # If a direction was pressed, use the appropriate list of frames according to direction
        if direction_x or direction_y:
            self.curr_anim_list = self.flames
        else:
            self.curr_anim_list = self.stationary

        # Advance the animation if enough time has elapsed
        if self.last_frame_update > 0.15:
            self.last_frame_update = 0
            self.current_frame = (self.current_frame + 1) % len(self.curr_anim_list)
            self.curr_image = self.curr_anim_list[self.current_frame]

    def load_sprites(self):
        # Get the diretory with the player sprites
        self.sprite_dir = os.path.join(self.game.sprite_dir, "ship")
        self.stationary, self.flames = (
            [],
            [],
        )
        # Load in the frames for each direction
        self.stationary.append(
            pygame.image.load(os.path.join(self.sprite_dir, "ship_0.png"))
        )

        for i in range(1, 4):
            self.flames.append(
                pygame.image.load(
                    os.path.join(self.sprite_dir, "ship_flames_" + str(i) + ".png")
                )
            )

        # Set the default frames to facing front
        self.curr_image = self.stationary[0]
        self.curr_anim_list = self.stationary
