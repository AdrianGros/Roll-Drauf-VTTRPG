"""S10: unit tests for vtt/play/vision.py's raycasting/classification
engine. Pure geometry -- no Flask app, no DB -- so these run instantly and
pin the actual visibility math directly, independent of the REST/socket
plumbing tested elsewhere.
"""

from collections import namedtuple

from vtt.play.vision import calculate_visible_cells, cell_of, visible_token_ids

Wall = namedtuple("Wall", ["x0", "y0", "x1", "y1", "sight"], defaults=["normal"])
Light = namedtuple(
    "Light", ["x", "y", "bright_radius", "dim_radius", "light_type", "provides_vision"],
    defaults=["light", True],
)
Token = namedtuple("Token", ["id", "x", "y"])

GRID = 50


class TestBasicVisibility:
    def test_origin_cell_is_always_visible(self):
        visible = calculate_visible_cells(100, 100, None, [], [], GRID)
        assert cell_of(100, 100, GRID) in visible

    def test_unlimited_sight_sees_a_far_cell_with_no_obstructions(self):
        visible = calculate_visible_cells(0, 0, None, [], [], GRID, ray_count=90)
        far_cell = cell_of(2000, 0, GRID)
        assert far_cell in visible

    def test_finite_sight_range_does_not_see_beyond_it(self):
        visible = calculate_visible_cells(0, 0, 100, [], [], GRID, ray_count=90)
        near_cell = cell_of(50, 0, GRID)
        far_cell = cell_of(2000, 0, GRID)
        assert near_cell in visible
        assert far_cell not in visible


class TestWallBlocking:
    def test_a_wall_blocks_sight_to_the_far_side(self):
        # Vertical wall at x=100 spanning the whole ray fan's plausible
        # y-range; token at origin looking toward +x must not see past it.
        wall = Wall(x0=100, y0=-500, x1=100, y1=500)
        visible = calculate_visible_cells(0, 0, None, [wall], [], GRID, ray_count=360)
        near_cell = cell_of(80, 0, GRID)
        far_cell = cell_of(300, 0, GRID)
        assert near_cell in visible
        assert far_cell not in visible

    def test_sight_none_wall_does_not_block(self):
        wall = Wall(x0=100, y0=-500, x1=100, y1=500, sight="none")
        visible = calculate_visible_cells(0, 0, None, [wall], [], GRID, ray_count=360)
        assert cell_of(300, 0, GRID) in visible

    def test_limited_and_proximity_walls_block_like_normal_this_slice(self):
        # Apply decision documented in vision.py / SceneWall: full
        # Foundry semantics for "limited"/"proximity" are deferred: they
        # block fully, same as "normal", until a later slice refines it.
        for sight_value in ("limited", "proximity"):
            wall = Wall(x0=100, y0=-500, x1=100, y1=500, sight=sight_value)
            visible = calculate_visible_cells(0, 0, None, [wall], [], GRID, ray_count=360)
            assert cell_of(300, 0, GRID) not in visible, f"{sight_value} wall should block like normal"


class TestLightExtendsVision:
    def test_a_light_lets_a_short_sighted_token_see_further_toward_it(self):
        # Token has only 50 units of natural sight, but a light sits at
        # distance 300 with a 150 radius -- the light should let the
        # token see cells within the light's reach, not just its own.
        light = Light(x=300, y=0, bright_radius=150, dim_radius=150)
        visible = calculate_visible_cells(0, 0, 50, [], [light], GRID, ray_count=360)
        lit_cell = cell_of(280, 0, GRID)
        assert lit_cell in visible

    def test_a_light_that_does_not_provide_vision_does_not_extend_sight(self):
        light = Light(x=300, y=0, bright_radius=150, dim_radius=150, provides_vision=False)
        visible = calculate_visible_cells(0, 0, 50, [], [light], GRID, ray_count=360)
        assert cell_of(280, 0, GRID) not in visible

    def test_a_wall_still_blocks_even_toward_a_light(self):
        wall = Wall(x0=100, y0=-500, x1=100, y1=500)
        light = Light(x=300, y=0, bright_radius=150, dim_radius=150)
        visible = calculate_visible_cells(0, 0, 50, [wall], [light], GRID, ray_count=360)
        assert cell_of(280, 0, GRID) not in visible


class TestDarknessExcludes:
    def test_darkness_source_removes_cells_from_visibility(self):
        darkness = Light(x=100, y=0, bright_radius=60, dim_radius=60, light_type="darkness")
        visible = calculate_visible_cells(0, 0, None, [], [darkness], GRID, ray_count=360)
        dark_cell = cell_of(100, 0, GRID)
        far_cell = cell_of(500, 0, GRID)
        assert dark_cell not in visible
        assert far_cell in visible, "darkness must not blank out unrelated distant cells"


class TestVisibleTokenIds:
    def test_returns_only_tokens_within_the_visible_set(self):
        wall = Wall(x0=100, y0=-500, x1=100, y1=500)
        near_token = Token(id=1, x=50, y=0)
        far_token = Token(id=2, x=300, y=0)
        ids = visible_token_ids(0, 0, None, [wall], [], [near_token, far_token], GRID, ray_count=360)
        assert ids == [1]
