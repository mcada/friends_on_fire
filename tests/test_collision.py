import pygame


def test_mask_collision_more_precise_than_rect():
    """Rects overlap but actual pixels don't -- mask should report no collision."""
    # Surface with pixels only in the left half
    left = pygame.Surface((20, 20), pygame.SRCALPHA)
    left.fill((255, 0, 0, 255), pygame.Rect(0, 0, 10, 20))

    # Surface with pixels only in the right half
    right = pygame.Surface((20, 20), pygame.SRCALPHA)
    right.fill((0, 255, 0, 255), pygame.Rect(10, 0, 10, 20))

    rect_a = left.get_rect(topleft=(0, 0))
    rect_b = right.get_rect(topleft=(5, 0))

    assert rect_a.colliderect(rect_b), "Rects should overlap"

    mask_a = pygame.mask.from_surface(left)
    mask_b = pygame.mask.from_surface(right)
    offset = (rect_b.x - rect_a.x, rect_b.y - rect_a.y)
    assert mask_a.overlap(mask_b, offset) is None, "Masks should not overlap"


def test_mask_collision_detects_real_overlap():
    """When pixels actually overlap, mask reports a hit."""
    surf_a = pygame.Surface((20, 20), pygame.SRCALPHA)
    surf_a.fill((255, 0, 0, 255))

    surf_b = pygame.Surface((20, 20), pygame.SRCALPHA)
    surf_b.fill((0, 255, 0, 255))

    mask_a = pygame.mask.from_surface(surf_a)
    mask_b = pygame.mask.from_surface(surf_b)

    assert mask_a.overlap(mask_b, (5, 5)) is not None


def test_near_miss_with_shapes():
    """Pixels on opposite edges of their surfaces; rects overlap in the empty middle."""
    a = pygame.Surface((40, 20), pygame.SRCALPHA)
    pygame.draw.rect(a, (255, 255, 255, 255), (0, 0, 5, 20))

    b = pygame.Surface((40, 20), pygame.SRCALPHA)
    pygame.draw.rect(b, (255, 255, 255, 255), (35, 0, 5, 20))

    rect_a = a.get_rect(topleft=(0, 0))
    rect_b = b.get_rect(topleft=(10, 0))

    assert rect_a.colliderect(rect_b), "Rects should overlap"

    mask_a = pygame.mask.from_surface(a)
    mask_b = pygame.mask.from_surface(b)
    offset = (rect_b.x - rect_a.x, rect_b.y - rect_a.y)
    assert mask_a.overlap(mask_b, offset) is None, "Shapes should not overlap"
