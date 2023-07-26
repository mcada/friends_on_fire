import pygame
import time
import random

from projectile import Projectile
from rocks import Rock

pygame.font.init()

WIDTH, HEIGHT = 1280, 600
FRAME_RATE = 60

PLAYER_WIDTH, PLAYER_HEIGHT = 60, 25
PLAYER_VELOCITY = 5

WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Friends on Fire!")

FONT = pygame.font.SysFont("comicsans", 30)

BG = pygame.transform.scale(pygame.image.load("bg.jpeg"), (WIDTH, HEIGHT))


def main_menu():
    WIN.blit(BG, (0, 0))

    menu_text = FONT.render("Press space to play, q to quit", 1, "grey")
    menu_rect = menu_text.get_rect(
        center=(
            HEIGHT / 2 - menu_text.get_height() / 2,
            WIDTH / 2 - menu_text.get_width() / 2,
        )
    )
    WIN.blit(menu_text, menu_rect)

    pygame.display.update()

    # TODO: Add buttons for play/game settings/control settings/multiplayer?!
    clock = pygame.time.Clock()

    while True:
        clock.tick(FRAME_RATE)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                break

        keys = pygame.key.get_pressed()
        if keys[pygame.K_q]:
            pygame.quit()
            break
        if keys[pygame.K_SPACE]:
            game_loop()
            # WIN.blit(BG, (0,0))
            WIN.blit(menu_text, menu_rect)
            pygame.display.update()


def main():
    # pygame setup
    # pygame.init()

    main_menu()
    # game_loop()


def draw(player, elapsed_time, rocks, projectiles):
    WIN.blit(BG, (0, 0))

    time_text = FONT.render(f"Time alive: {round(elapsed_time)} s", 1, "blue")
    WIN.blit(time_text, (WIDTH - 200, 10))

    rocks.update()
    rocks.draw(WIN)

    print(projectiles)
    print(rocks)

    projectiles.update()
    projectiles.draw(WIN)

    pygame.draw.rect(WIN, "green", player)

    pygame.display.update()


def game_loop():
    run = True

    player = pygame.Rect(30, HEIGHT / 2, PLAYER_WIDTH, PLAYER_HEIGHT)
    projectile_group = pygame.sprite.Group()
    rocks_group = pygame.sprite.Group()

    clock = pygame.time.Clock()
    start_time = time.time()
    elapsed_time = 0

    rocks_add_increment = 1000
    rocks_release_counter = 0

    hit = False

    while run:
        rocks_release_counter += clock.tick(FRAME_RATE)
        elapsed_time = time.time() - start_time

        # generate rocks if the time is right
        if rocks_release_counter > rocks_add_increment:
            for _ in range(3):
                rocks_group.add(
                    Rock(
                        "white",
                        WIDTH + random.randint(0, 200),
                        random.randint(25, HEIGHT - 25),
                        random.randint(5, 40),
                        random.randint(5, 30),
                    )
                )

            # spawn the rocks faster each time
            rocks_add_increment = max(200, rocks_add_increment - 25)
            # reset the timer
            rocks_release_counter = 0
            # this is crazy, get rid of it or die - btw. this is making the game lag - as all rocks suddenly move faster it seems like a lag/freeze
            # rocks_current_velocity = rocks_current_velocity * 1.01

        # poll for events
        # pygame.QUIT event means the user clicked X to close your window
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

        # player movement
        keys = pygame.key.get_pressed()
        if (
            keys[pygame.K_LEFT] or keys[pygame.K_a]
        ) and player.x - PLAYER_VELOCITY >= 0:
            player.x -= PLAYER_VELOCITY
        if (
            keys[pygame.K_RIGHT] or keys[pygame.K_d]
        ) and player.x + PLAYER_VELOCITY <= WIDTH - WIDTH / 5:
            player.x += PLAYER_VELOCITY
        if (keys[pygame.K_UP] or keys[pygame.K_w]) and player.y - PLAYER_VELOCITY >= 0:
            player.y -= PLAYER_VELOCITY
        if (
            keys[pygame.K_DOWN] or keys[pygame.K_s]
        ) and player.y + PLAYER_VELOCITY <= HEIGHT - PLAYER_HEIGHT:
            player.y += PLAYER_VELOCITY
        if keys[pygame.K_SPACE]:
            projectile_group.add(
                Projectile(
                    "crimson", player.x + PLAYER_WIDTH, player.y + PLAYER_HEIGHT / 2
                )
            )

        # check for collision with player
        for rock in rocks_group:
            if rock.rect.x <= player.x + PLAYER_WIDTH and player.colliderect(rock):
                # print("Removing a rock")
                rock.kill()
                hit = True
                break
            if pygame.sprite.spritecollide(rock, projectile_group, True):
                rock.kill()

        if hit:
            lost_text = FONT.render(f"You lost!", 1, "Red")
            WIN.blit(
                lost_text,
                (
                    WIDTH / 2 - lost_text.get_width() / 2,
                    HEIGHT / 2 - lost_text.get_height() / 2,
                ),
            )
            pygame.display.update()
            # pygame.time.delay(3000)
            break

        draw(player, elapsed_time, rocks_group, projectile_group)


if __name__ == "__main__":
    main()
