"""S10: vision/Fog-of-War calculation.

Pure geometry -- no Flask, no DB session, no imports from vtt.models --
so this module is trivially unit-testable and reusable from routes.py,
socket_handlers.py, and tests without any app context.

Apply decision (research doc §12, deferred to this module rather than a
second migration): the full Foundry model computes light-to-cell line of
sight separately from token-to-cell line of sight, which needs one
raycast pass PER LIGHT plus one per token -- real complexity for a first
pass explicitly scoped to "start with raycasting, defer advanced
algorithms" (§12 Q7). This engine instead does ONE raycast pass per
token (token -> map edge, blocked by walls) and then classifies each
unobstructed cell by distance:

  - within the token's own sight_range (or unlimited if None): visible.
  - else, within reach of a vision-providing "light" source's radius
    (straight-line distance from the token, not a second raycast from the
    light): visible. Interpretation: "if you can look toward a lit spot
    with nothing blocking the view, you see it, even past your own
    natural range."
  - Darkness sources are simpler still: any cell within a "darkness"
    source's radius is excluded from visibility outright, regardless of
    the above (a flat exclusion zone, not full priority-based blending).

This is a documented simplification, not the full Foundry model -- walls
still fully gate what a token can perceive at all; only the "how far do I
see" question is simplified. A future slice can replace the per-light
distance check with a real light->cell raycast without changing this
module's public contract (calculate_visible_cells).
"""

from __future__ import annotations

import math

DEFAULT_RAY_COUNT = 180
# Cap so a misconfigured/unlimited-sight token on a huge map can't make a
# single recalculation pathologically expensive (§10 performance risk).
MAX_EFFECTIVE_RANGE = 4000


def cell_of(x: float, y: float, grid_size: int) -> tuple[int, int]:
    size = max(1, grid_size)
    return (int(math.floor(x / size)), int(math.floor(y / size)))


def _segment_intersection_fraction(ox, oy, dx, dy, x0, y0, x1, y1):
    """Fraction (0..1) along ray (ox,oy)->(ox+dx,oy+dy) where it crosses
    segment (x0,y0)-(x1,y1), or None if they don't cross within the ray."""
    ex, ey = x1 - x0, y1 - y0
    denom = dx * ey - dy * ex
    if abs(denom) < 1e-9:
        return None
    t = ((x0 - ox) * ey - (y0 - oy) * ex) / denom
    u = ((x0 - ox) * dy - (y0 - oy) * dx) / denom
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return t
    return None


def _blocking_walls(walls):
    return [w for w in walls if getattr(w, "sight", "normal") != "none"]


def _raycast_unobstructed(origin_x, origin_y, max_range, walls, ray_count=DEFAULT_RAY_COUNT):
    """Cast `ray_count` rays out to `max_range`, stopped by the nearest
    sight-blocking wall. Returns a list of (cell_x, cell_y, distance)
    sample points along each ray's unobstructed portion (distance from
    origin, world units) -- distance lets the caller apply per-token
    sight_range / per-light-radius classification without re-raycasting.
    """
    blocking = _blocking_walls(walls)
    samples = []
    if ray_count <= 0 or max_range <= 0:
        return samples
    for i in range(ray_count):
        angle = 2 * math.pi * i / ray_count
        dx, dy = math.cos(angle), math.sin(angle)
        nearest_t = 1.0
        for wall in blocking:
            t = _segment_intersection_fraction(
                origin_x, origin_y, dx * max_range, dy * max_range,
                wall.x0, wall.y0, wall.x1, wall.y1)
            if t is not None and t < nearest_t:
                nearest_t = t
        distance = max_range * nearest_t
        # Sample every half-grid-cell along the unobstructed ray so no
        # cell along a long clear sightline gets skipped.
        step_count = max(1, int(distance / 16))
        for step in range(step_count + 1):
            sample_distance = distance * step / step_count
            samples.append((
                origin_x + dx * sample_distance,
                origin_y + dy * sample_distance,
                sample_distance,
            ))
    return samples


def calculate_visible_cells(
    origin_x: float,
    origin_y: float,
    sight_range,
    walls,
    lights,
    grid_size: int,
    ray_count: int = DEFAULT_RAY_COUNT,
) -> set[tuple[int, int]]:
    """Grid cells visible from (origin_x, origin_y).

    sight_range=None means unlimited natural sight (still wall-blocked).
    walls/lights are any objects with the attributes SceneWall/SceneLight
    expose (duck-typed so plain namedtuples work in tests, no DB needed).
    """
    vision_lights = [
        light for light in lights
        if getattr(light, "provides_vision", True)
        and getattr(light, "light_type", "light") == "light"
        and (getattr(light, "bright_radius", 0) or getattr(light, "dim_radius", 0))
    ]
    darkness_sources = [
        light for light in lights
        if getattr(light, "light_type", "light") == "darkness"
        and (getattr(light, "bright_radius", 0) or getattr(light, "dim_radius", 0))
    ]

    effective_range = sight_range if sight_range is not None else MAX_EFFECTIVE_RANGE
    for light in vision_lights:
        radius = max(getattr(light, "bright_radius", 0) or 0, getattr(light, "dim_radius", 0) or 0)
        light_distance = math.hypot(getattr(light, "x", origin_x) - origin_x,
                                     getattr(light, "y", origin_y) - origin_y)
        effective_range = max(effective_range, min(light_distance + radius, MAX_EFFECTIVE_RANGE))
    effective_range = min(effective_range, MAX_EFFECTIVE_RANGE)

    samples = _raycast_unobstructed(origin_x, origin_y, effective_range, walls, ray_count)

    visible: set[tuple[int, int]] = {cell_of(origin_x, origin_y, grid_size)}
    for x, y, distance in samples:
        within_own_sight = sight_range is None or distance <= sight_range
        within_a_light = any(
            math.hypot(getattr(light, "x", 0) - x, getattr(light, "y", 0) - y)
                <= max(getattr(light, "bright_radius", 0) or 0, getattr(light, "dim_radius", 0) or 0)
            for light in vision_lights
        )
        if within_own_sight or within_a_light:
            visible.add(cell_of(x, y, grid_size))

    if darkness_sources:
        dark_cells = set()
        for light in darkness_sources:
            radius = max(getattr(light, "bright_radius", 0) or 0, getattr(light, "dim_radius", 0) or 0)
            lx, ly = getattr(light, "x", 0), getattr(light, "y", 0)
            for cx, cy in list(visible):
                world_x, world_y = (cx + 0.5) * grid_size, (cy + 0.5) * grid_size
                if math.hypot(lx - world_x, ly - world_y) <= radius:
                    dark_cells.add((cx, cy))
        visible -= dark_cells

    return visible


def visible_token_ids(origin_x, origin_y, sight_range, walls, lights, tokens, grid_size, ray_count=DEFAULT_RAY_COUNT):
    """Convenience wrapper: which of `tokens` (objects with id/x/y) fall
    inside the visible-cells set computed from (origin_x, origin_y)."""
    visible_cells = calculate_visible_cells(origin_x, origin_y, sight_range, walls, lights, grid_size, ray_count)
    result = []
    for token in tokens:
        if cell_of(token.x, token.y, grid_size) in visible_cells:
            result.append(token.id)
    return result
