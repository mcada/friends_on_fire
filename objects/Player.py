import pygame, os

from objects.Projectile import Projectile

PLAYER_WIDTH, PLAYER_HEIGHT = 80, 35


class Player:
    def __init__(self, game):
        self.game = game
        self.load_sprites()
        self.position_x, self.position_y = 100, self.game.GAME_HEIGHT / 2
        self.current_frame, self.last_frame_update = 0, 0
        self.player_speed = 200
        self.attack_speed = 0.5
        self.weapon_cooldown = 0

    def update(self, delta_time, actions):
        # Get the direction from inputs
        direction_x = actions["right"] - actions["left"]
        direction_y = actions["down"] - actions["up"]
        # Update the position
        self.position_x += self.player_speed * delta_time * direction_x
        self.position_y += self.player_speed * delta_time * direction_y
        # Animate the sprite
        self.animate(delta_time, direction_x, direction_y)
        # Update weapon cooldown
        self.weapon_cooldown -= delta_time

        # Shoot
        if actions["space"]:
            if self.weapon_cooldown <= 0:
                self.game.projectiles.add(
                    Projectile(
                        "crimson",
                        self.position_x + PLAYER_WIDTH,
                        self.position_y + PLAYER_HEIGHT / 2,
                        self.game,
                    )
                )
                self.weapon_cooldown = self.attack_speed

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
            pygame.transform.scale(
                pygame.image.load(
                    os.path.join(self.sprite_dir, "ship_0.png")
                ).convert_alpha(),
                (PLAYER_WIDTH, PLAYER_HEIGHT),
            )
        )

        for i in range(1, 4):
            self.flames.append(
                pygame.transform.scale(
                    pygame.image.load(
                        os.path.join(self.sprite_dir, "ship_flames_" + str(i) + ".png")
                    ).convert_alpha(),
                    (PLAYER_WIDTH, PLAYER_HEIGHT),
                )
            )

        # Set the default frames to facing front
        self.curr_image = self.stationary[0]
        self.curr_anim_list = self.stationary
