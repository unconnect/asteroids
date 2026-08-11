# Playable Asteroids + Web Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the boot.dev Asteroids exercise into a finished game playable at `https://asteroids.nikolasreuber.de`, downloadable as native binaries, shipped by pushing a `v*` tag.

**Architecture:** Game rules move into a rendering-free `gamestate.py` so they are unit-testable; the game loop becomes `async` so the same source runs on desktop under `asyncio.run()` and in the browser under pygbag/WASM. CI builds the WASM bundle on x86, copies it into an `nginx:alpine` image built for `linux/arm64`, pushes to GHCR, and pokes a Portainer webhook.

**Tech Stack:** Python 3.12, pygame 2.6.1, pytest, pygbag, PyInstaller, Docker buildx, nginx, GitHub Actions, SWAG, Portainer.

**Spec:** `docs/superpowers/specs/2026-08-10-playable-and-deploy-design.md`

## Global Constraints

- Python **3.12** everywhere — `.python-version`, `pyproject.toml` `requires-python`, and CI. pygbag's browser runtime is 3.12; a mismatch means the browser build diverges from what the tests exercise.
- **`gamestate.py` must never import a pygame rendering API.** It may import `constants` and stdlib only. This is what keeps the rules testable headless.
- **No `sys.exit()` anywhere.** It is fatal in the browser. The game loop exits by falling out of its `while` condition.
- **`asyncio.run(main())` at module level**, not inside `if __name__ == "__main__":` — pygbag expects the bare call.
- **No asset files.** All drawing is vector primitives; all text uses `pygame.font.Font(None, size)`. Do not introduce image or sound files — they change the pygbag packaging story.
- Tests run headless: `SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy`.
- Container image: `ghcr.io/unconnect/asteroids`. Container/service name `asteroids` on the external `swag_default` network.
- Commit after every task. Never commit a red test suite.

---

### Task 1: Test infrastructure and Python 3.12

Establishes the headless test harness everything else depends on, and moves the project to the version pygbag requires.

**Files:**
- Modify: `.python-version`
- Modify: `pyproject.toml`
- Create: `conftest.py`
- Create: `tests/test_circleshape.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: a working `uv run pytest` command; `conftest.py` at repo root which places the repo root on `sys.path` so tests can `import circleshape` etc. directly

- [ ] **Step 1: Set the Python version**

Replace the entire contents of `.python-version` with:

```
3.12
```

- [ ] **Step 2: Update `pyproject.toml`**

Replace the whole file with:

```toml
[project]
name = "asteroids"
version = "0.1.0"
description = "Classic Asteroids, playable in the browser and on the desktop"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "pygame==2.6.1",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pygbag>=0.9.2",
    "pyinstaller>=6.10",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Create `conftest.py` at the repo root**

This must live at the **repo root**, not in `tests/`. Its presence there makes pytest put the repo root on `sys.path`, so `import gamestate` works without a package layout. Setting the SDL env vars here guarantees they are set before pygame is imported by any test.

```python
import os

# Must run before pygame is imported anywhere: forces headless SDL so tests
# work in CI with no display or sound device.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest


@pytest.fixture(scope="session", autouse=True)
def _pygame_session():
    """Init pygame once per test session.

    Player.update() calls pygame.key.get_pressed(), which needs the video
    subsystem. Keeping this beside the dummy SDL env vars means every test
    file works standalone, rather than only when collected alongside another
    file that happened to init pygame first.
    """
    pygame.init()
    yield
    pygame.quit()
```

The `import pygame` must stay **below** the `os.environ.setdefault` calls. Above
them, the dummy driver would not be in effect when pygame initialises its video
subsystem, and CI would try to open a real display.

- [ ] **Step 4: Sync the environment**

Run: `uv sync --all-groups`
Expected: resolves and installs pygame, pytest, pygbag, pyinstaller against Python 3.12.

- [ ] **Step 5: Write the failing test**

Create `tests/test_circleshape.py`:

```python
import pygame

from circleshape import CircleShape


def make(x, y, radius):
    return CircleShape(x, y, radius)


def test_overlapping_circles_collide():
    a = make(0, 0, 10)
    b = make(5, 0, 10)
    assert a.collision(b) is True


def test_distant_circles_do_not_collide():
    a = make(0, 0, 10)
    b = make(100, 0, 10)
    assert a.collision(b) is False


def test_exactly_touching_circles_do_not_collide():
    # Distance == sum of radii. The implementation uses a strict >, so
    # circles that only graze are not a hit.
    a = make(0, 0, 10)
    b = make(20, 0, 10)
    assert a.collision(b) is False


def test_collision_is_symmetric():
    a = make(0, 0, 30)
    b = make(25, 0, 10)
    assert a.collision(b) == b.collision(a)


def test_new_shape_starts_at_rest():
    shape = make(3, 4, 10)
    assert shape.position == pygame.Vector2(3, 4)
    assert shape.velocity == pygame.Vector2(0, 0)
```

- [ ] **Step 6: Run the tests**

Run: `uv run pytest -v`
Expected: **5 passed.** These test existing behaviour, so they should pass immediately — that is the point. If they fail, the harness is misconfigured, and that must be fixed before any other task.

- [ ] **Step 7: Commit**

```bash
git add .python-version pyproject.toml uv.lock conftest.py tests/test_circleshape.py
git commit -m "test: add headless pytest harness and move to Python 3.12"
```

---

### Task 2: Screen wrap and off-screen culling

Adds the two geometry helpers every moving object needs. Pure math, no game rules.

**Files:**
- Modify: `circleshape.py`
- Modify: `tests/test_circleshape.py`

**Interfaces:**
- Consumes: `CircleShape` from Task 1
- Produces: `CircleShape.wrap() -> None` and `CircleShape.is_off_screen(margin: float) -> bool`, used by Tasks 4 and 5

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_circleshape.py`:

```python
from constants import SCREEN_HEIGHT, SCREEN_WIDTH


def test_wrap_leaves_centred_shape_alone():
    shape = make(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 20)
    shape.wrap()
    assert shape.position == pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)


def test_wrap_left_edge_to_right():
    shape = make(-21, 300, 20)
    shape.wrap()
    assert shape.position.x == SCREEN_WIDTH + 20


def test_wrap_right_edge_to_left():
    shape = make(SCREEN_WIDTH + 21, 300, 20)
    shape.wrap()
    assert shape.position.x == -20


def test_wrap_top_edge_to_bottom():
    shape = make(300, -21, 20)
    shape.wrap()
    assert shape.position.y == SCREEN_HEIGHT + 20


def test_wrap_bottom_edge_to_top():
    shape = make(300, SCREEN_HEIGHT + 21, 20)
    shape.wrap()
    assert shape.position.y == -20


def test_wrap_preserves_the_other_axis():
    shape = make(-21, 137, 20)
    shape.wrap()
    assert shape.position.y == 137


def test_is_off_screen_false_just_inside_margin():
    shape = make(-49, 300, 20)
    assert shape.is_off_screen(50) is False


def test_is_off_screen_true_just_outside_margin():
    shape = make(-51, 300, 20)
    assert shape.is_off_screen(50) is True


def test_is_off_screen_checks_all_four_sides():
    margin = 50
    assert make(300, -51, 20).is_off_screen(margin) is True
    assert make(300, SCREEN_HEIGHT + 51, 20).is_off_screen(margin) is True
    assert make(SCREEN_WIDTH + 51, 300, 20).is_off_screen(margin) is True
    assert make(-51, 300, 20).is_off_screen(margin) is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_circleshape.py -v`
Expected: FAIL — `AttributeError: 'CircleShape' object has no attribute 'wrap'`

- [ ] **Step 3: Implement the helpers**

In `circleshape.py`, add the import at the top of the file, below `import pygame`:

```python
from constants import SCREEN_HEIGHT, SCREEN_WIDTH
```

Then add these two methods to `CircleShape`, after `collision()`:

```python
    def wrap(self):
        """Teleport to the opposite edge once fully off-screen.

        The radius offset means the shape reappears just outside the far edge
        rather than popping into view at the boundary.
        """
        if self.position.x < -self.radius:
            self.position.x = SCREEN_WIDTH + self.radius
        elif self.position.x > SCREEN_WIDTH + self.radius:
            self.position.x = -self.radius

        if self.position.y < -self.radius:
            self.position.y = SCREEN_HEIGHT + self.radius
        elif self.position.y > SCREEN_HEIGHT + self.radius:
            self.position.y = -self.radius

    def is_off_screen(self, margin):
        """True once the shape is further than `margin` outside the playfield."""
        return (
            self.position.x < -margin
            or self.position.x > SCREEN_WIDTH + margin
            or self.position.y < -margin
            or self.position.y > SCREEN_HEIGHT + margin
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -v`
Expected: **14 passed.**

- [ ] **Step 5: Commit**

```bash
git add circleshape.py tests/test_circleshape.py
git commit -m "feat: add screen wrap and off-screen detection to CircleShape"
```

---

### Task 3: Constants and `gamestate.py`

The heart of the game rules, deliberately free of any rendering dependency.

**Files:**
- Modify: `constants.py`
- Create: `gamestate.py`
- Create: `tests/test_gamestate.py`

**Interfaces:**
- Consumes: `constants`
- Produces:
  - `Phase.PLAYING`, `Phase.GAME_OVER` (enum members)
  - `GameState()` with attributes `score: int`, `lives: int`, `phase: Phase`
  - `GameState.reset() -> None`
  - `GameState.award(asteroid_radius: float) -> int` (returns points added)
  - `GameState.lose_life() -> bool` (returns True if now GAME_OVER)
  - `GameState.spawn_interval -> float` (property)
  - New constants consumed by Tasks 4, 5, 6, 7, 8

- [ ] **Step 1: Update `constants.py`**

Replace the whole file with:

```python
# Colors
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)

# Screen
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_COLOR = COLOR_BLACK

# Asteroid
ASTEROID_MIN_RADIUS = 20
ASTEROID_KINDS = 3
ASTEROID_MAX_RADIUS = ASTEROID_MIN_RADIUS * ASTEROID_KINDS

# Asteroids spawn ASTEROID_MAX_RADIUS outside the edge, so the cull margin
# MUST be larger than that or every asteroid dies on the frame it spawns.
ASTEROID_CULL_MARGIN = ASTEROID_MAX_RADIUS * 2

# Classic arcade scoring: smaller rocks are worth more.
# Keyed by radius // ASTEROID_MIN_RADIUS.
ASTEROID_SCORE = {1: 100, 2: 50, 3: 20}

# Difficulty: spawn interval falls linearly from START to MIN as the score
# climbs to DIFFICULTY_MAX_SCORE, then stays at MIN.
SPAWN_RATE_START = 0.8
SPAWN_RATE_MIN = 0.25
DIFFICULTY_MAX_SCORE = 5000

# Player
PLAYER_RADIUS = 20
PLAYER_SPEED = 200
PLAYER_TURN_SPEED = 300
PLAYER_SHOT_SPEED = 500
PLAYER_SHOOT_COOLDOWN = 0.3
PLAYER_LIVES = 3
PLAYER_INVULN_TIME = 2.0
PLAYER_BLINK_HZ = 10

# Shot
SHOT_RADIUS = 5

# HUD
HUD_FONT_SIZE = 28
HUD_TITLE_SIZE = 72
HUD_MARGIN = 20
```

Note `ASTEROID_SPAWN_RATE` is **gone** — it is replaced by `SPAWN_RATE_START` and the difficulty curve. Task 6 updates its only consumer (`asteroidfield.py`).

- [ ] **Step 2: Write the failing tests**

Create `tests/test_gamestate.py`:

```python
import pytest

from constants import (
    DIFFICULTY_MAX_SCORE,
    PLAYER_LIVES,
    SPAWN_RATE_MIN,
    SPAWN_RATE_START,
)
from gamestate import GameState, Phase


def test_new_game_starts_playing_with_full_lives():
    state = GameState()
    assert state.score == 0
    assert state.lives == PLAYER_LIVES
    assert state.phase is Phase.PLAYING


@pytest.mark.parametrize(
    "radius, expected",
    [(20, 100), (40, 50), (60, 20)],
)
def test_award_gives_classic_arcade_points(radius, expected):
    state = GameState()
    assert state.award(radius) == expected
    assert state.score == expected


def test_award_accumulates():
    state = GameState()
    state.award(60)
    state.award(20)
    assert state.score == 120


def test_award_for_unknown_radius_scores_nothing():
    state = GameState()
    assert state.award(999) == 0
    assert state.score == 0


def test_lose_life_decrements_without_ending_the_game():
    state = GameState()
    assert state.lose_life() is False
    assert state.lives == PLAYER_LIVES - 1
    assert state.phase is Phase.PLAYING


def test_game_over_on_the_last_life():
    state = GameState()
    for _ in range(PLAYER_LIVES - 1):
        state.lose_life()
    assert state.lose_life() is True
    assert state.lives == 0
    assert state.phase is Phase.GAME_OVER


def test_lives_never_go_negative():
    state = GameState()
    for _ in range(PLAYER_LIVES + 5):
        state.lose_life()
    assert state.lives == 0


def test_reset_restores_a_fresh_game():
    state = GameState()
    state.award(60)
    for _ in range(PLAYER_LIVES):
        state.lose_life()
    state.reset()
    assert state.score == 0
    assert state.lives == PLAYER_LIVES
    assert state.phase is Phase.PLAYING


def test_spawn_interval_starts_slow():
    assert GameState().spawn_interval == pytest.approx(SPAWN_RATE_START)


def test_spawn_interval_reaches_the_floor_at_max_score():
    state = GameState()
    state.score = DIFFICULTY_MAX_SCORE
    assert state.spawn_interval == pytest.approx(SPAWN_RATE_MIN)


def test_spawn_interval_is_clamped_beyond_max_score():
    state = GameState()
    state.score = DIFFICULTY_MAX_SCORE * 10
    assert state.spawn_interval == pytest.approx(SPAWN_RATE_MIN)


def test_spawn_interval_decreases_monotonically():
    state = GameState()
    previous = state.spawn_interval
    for score in range(0, DIFFICULTY_MAX_SCORE, 250):
        state.score = score
        assert state.spawn_interval <= previous
        previous = state.spawn_interval


def test_gamestate_does_not_pull_in_a_display():
    # gamestate must stay rendering-free so the rules test headless.
    # Walk the imports rather than scanning the source text: a substring
    # check also matches docstrings and comments, so a module explaining
    # why it avoids pygame would fail its own test.
    import ast
    import inspect

    import gamestate

    tree = ast.parse(inspect.getsource(gamestate))
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "pygame" not in imported_roots
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_gamestate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gamestate'`

- [ ] **Step 4: Implement `gamestate.py`**

```python
from enum import Enum, auto

from constants import (
    ASTEROID_MIN_RADIUS,
    ASTEROID_SCORE,
    DIFFICULTY_MAX_SCORE,
    PLAYER_LIVES,
    SPAWN_RATE_MIN,
    SPAWN_RATE_START,
)


class Phase(Enum):
    PLAYING = auto()
    GAME_OVER = auto()


class GameState:
    """Score, lives and difficulty. Deliberately free of pygame.

    Keeping the rules separate from rendering is what lets them be tested
    without a display, and keeps the game loop readable.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.score = 0
        self.lives = PLAYER_LIVES
        self.phase = Phase.PLAYING

    def award(self, asteroid_radius):
        """Add points for destroying an asteroid; returns the points added."""
        kind = int(asteroid_radius) // ASTEROID_MIN_RADIUS
        points = ASTEROID_SCORE.get(kind, 0)
        self.score += points
        return points

    def lose_life(self):
        """Spend a life. Returns True if that was the last one."""
        self.lives = max(0, self.lives - 1)
        if self.lives == 0:
            self.phase = Phase.GAME_OVER
        return self.phase is Phase.GAME_OVER

    @property
    def spawn_interval(self):
        """Seconds between asteroid spawns, tightening as the score climbs."""
        progress = min(1.0, self.score / DIFFICULTY_MAX_SCORE)
        return SPAWN_RATE_START + (SPAWN_RATE_MIN - SPAWN_RATE_START) * progress
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest -v`
Expected: all pass (14 from Tasks 1–2, plus 15 here).

- [ ] **Step 6: Commit**

```bash
git add constants.py gamestate.py tests/test_gamestate.py
git commit -m "feat: add GameState with scoring, lives and difficulty curve"
```

---

### Task 4: Asteroid and shot culling

Stops asteroids and missed shots accumulating forever, and verifies the spawn/cull margin interaction.

**Files:**
- Modify: `asteroid.py`
- Modify: `shot.py`
- Create: `tests/test_asteroid.py`
- Create: `tests/test_shot.py`

**Interfaces:**
- Consumes: `CircleShape.is_off_screen` (Task 2), `ASTEROID_CULL_MARGIN` (Task 3)
- Produces: `Asteroid.update()` and `Shot.update()` self-cull; `Asteroid.split()` behaviour pinned by tests

- [ ] **Step 1: Write the failing tests**

Create `tests/test_asteroid.py`:

```python
import pygame

from asteroid import Asteroid
from asteroidfield import AsteroidField
from constants import (
    ASTEROID_CULL_MARGIN,
    ASTEROID_MAX_RADIUS,
    ASTEROID_MIN_RADIUS,
)


def make_group():
    """Asteroids auto-add to Asteroid.containers; give them a scratch group."""
    group = pygame.sprite.Group()
    Asteroid.containers = (group,)
    return group


def test_update_moves_by_velocity():
    make_group()
    asteroid = Asteroid(100, 100, ASTEROID_MIN_RADIUS)
    asteroid.velocity = pygame.Vector2(10, 20)
    asteroid.update(1.0)
    assert asteroid.position == pygame.Vector2(110, 120)


def test_asteroid_far_off_screen_is_culled():
    group = make_group()
    asteroid = Asteroid(-ASTEROID_CULL_MARGIN - 100, 300, ASTEROID_MIN_RADIUS)
    asteroid.update(0.0)
    assert len(group) == 0


def test_asteroid_on_screen_survives():
    group = make_group()
    asteroid = Asteroid(640, 360, ASTEROID_MIN_RADIUS)
    asteroid.update(0.0)
    assert len(group) == 1


def test_asteroid_at_its_spawn_position_is_not_culled():
    # Regression guard: asteroids spawn exactly ASTEROID_MAX_RADIUS outside
    # the edge. If the cull margin were <= that, every asteroid would be
    # destroyed on the frame it spawned and the game would be silently empty.
    group = make_group()
    for _, place in AsteroidField.edges:
        position = place(0.5)
        asteroid = Asteroid(position.x, position.y, ASTEROID_MAX_RADIUS)
        asteroid.update(0.0)
    assert len(group) == len(AsteroidField.edges)


def test_split_of_smallest_asteroid_spawns_nothing():
    group = make_group()
    asteroid = Asteroid(640, 360, ASTEROID_MIN_RADIUS)
    asteroid.velocity = pygame.Vector2(10, 0)
    asteroid.split()
    assert len(group) == 0


def test_split_of_large_asteroid_spawns_two_smaller_ones():
    group = make_group()
    asteroid = Asteroid(640, 360, ASTEROID_MAX_RADIUS)
    asteroid.velocity = pygame.Vector2(10, 0)
    asteroid.split()

    children = list(group)
    assert len(children) == 2
    for child in children:
        assert child.radius == ASTEROID_MAX_RADIUS - ASTEROID_MIN_RADIUS
        assert child.position == pygame.Vector2(640, 360)


def test_split_children_move_faster_and_diverge():
    group = make_group()
    asteroid = Asteroid(640, 360, ASTEROID_MAX_RADIUS)
    asteroid.velocity = pygame.Vector2(10, 0)
    asteroid.split()

    first, second = list(group)
    assert first.velocity.length() > asteroid.velocity.length()
    assert second.velocity.length() > asteroid.velocity.length()
    assert first.velocity != second.velocity
```

Create `tests/test_shot.py`:

```python
import pygame

from constants import SCREEN_WIDTH
from shot import Shot


def make_group():
    group = pygame.sprite.Group()
    Shot.containers = (group,)
    return group


def test_update_moves_by_velocity():
    make_group()
    shot = Shot(100, 100)
    shot.velocity = pygame.Vector2(0, 50)
    shot.update(2.0)
    assert shot.position == pygame.Vector2(100, 200)


def test_shot_that_leaves_the_screen_is_culled():
    group = make_group()
    shot = Shot(SCREEN_WIDTH - 10, 300)
    shot.velocity = pygame.Vector2(500, 0)
    shot.update(1.0)
    assert len(group) == 0


def test_shot_on_screen_survives():
    group = make_group()
    shot = Shot(640, 360)
    shot.velocity = pygame.Vector2(0, 100)
    shot.update(0.1)
    assert len(group) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_asteroid.py tests/test_shot.py -v`
Expected: the culling tests FAIL (sprites survive because nothing kills them). The movement and split tests should already pass.

- [ ] **Step 3: Implement culling in `asteroid.py`**

Change the import line to include the new constant, then update `update()`:

```python
    def update(self, dt):
        self.position += self.velocity * dt
        # Asteroids do not wrap: the field spawns continuously, so wrapping
        # would saturate the screen. They leave and are reclaimed instead.
        if self.is_off_screen(ASTEROID_CULL_MARGIN):
            self.kill()
```

`asteroid.py` uses `from constants import *`, so `ASTEROID_CULL_MARGIN` is already in scope — no import change needed.

- [ ] **Step 4: Implement culling in `shot.py`**

```python
    def update(self, dt):
        self.position += self.velocity * dt
        if self.is_off_screen(SHOT_RADIUS):
            self.kill()
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add asteroid.py shot.py tests/test_asteroid.py tests/test_shot.py
git commit -m "fix: cull off-screen asteroids and shots instead of leaking them"
```

---

### Task 5: Player wrap, invulnerability and respawn

**Files:**
- Modify: `player.py`
- Create: `tests/test_player.py`

**Interfaces:**
- Consumes: `CircleShape.wrap` (Task 2); `PLAYER_INVULN_TIME`, `PLAYER_BLINK_HZ` (Task 3)
- Produces:
  - `Player.invuln_timer: float`
  - `Player.is_invulnerable -> bool` (property)
  - `Player.is_visible() -> bool`
  - `Player.respawn() -> None`
  - `Player.update()` now decrements `cooldown_timer` itself (Task 8 removes the duplicate from the loop)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_player.py`:

```python
import pygame
import pytest

from constants import (
    PLAYER_BLINK_HZ,
    PLAYER_INVULN_TIME,
    PLAYER_RADIUS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from player import Player


def make_player(x=SCREEN_WIDTH / 2, y=SCREEN_HEIGHT / 2):
    group = pygame.sprite.Group()
    Player.containers = (group,)
    return Player(x, y)


def test_player_spawns_invulnerable():
    player = make_player()
    assert player.is_invulnerable is True
    assert player.invuln_timer == PLAYER_INVULN_TIME


def test_invulnerability_expires():
    player = make_player()
    player.invuln_timer = 0.01
    player.update(0.5)
    assert player.is_invulnerable is False


def test_visible_when_not_invulnerable():
    player = make_player()
    player.invuln_timer = 0
    assert player.is_visible() is True


def test_blinks_while_invulnerable():
    player = make_player()
    seen = set()
    # Sample a full blink cycle; both states must occur.
    for step in range(PLAYER_BLINK_HZ * 2):
        player.invuln_timer = PLAYER_INVULN_TIME - step / (PLAYER_BLINK_HZ * 2)
        seen.add(player.is_visible())
    assert seen == {True, False}

    # The set check above catches a stuck blink but not an inverted one:
    # flipping the parity leaves {True, False} unchanged. Pin actual values
    # against the spec formula. These four t values cover both parities.
    for t in (2.0, 1.95, 1.9, 1.85):
        player.invuln_timer = t
        assert player.is_visible() is (int(t * PLAYER_BLINK_HZ) % 2 == 0)


def test_respawn_recentres_and_grants_grace():
    player = make_player(10, 10)
    player.rotation = 123
    player.velocity = pygame.Vector2(50, 50)
    player.invuln_timer = 0

    player.respawn()

    assert player.position == pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    assert player.velocity == pygame.Vector2(0, 0)
    assert player.rotation == 0
    assert player.invuln_timer == PLAYER_INVULN_TIME


def test_update_wraps_the_player():
    player = make_player(-PLAYER_RADIUS - 5, 300)
    player.update(0.0)
    assert player.position.x == SCREEN_WIDTH + PLAYER_RADIUS


def test_update_ticks_down_the_shoot_cooldown():
    player = make_player()
    player.cooldown_timer = 0.3
    player.update(0.1)
    assert player.cooldown_timer == pytest.approx(0.2)


def test_triangle_has_three_points():
    player = make_player()
    assert len(player.triangle()) == 3
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_player.py -v`
Expected: FAIL — `AttributeError: 'Player' object has no attribute 'is_invulnerable'`

- [ ] **Step 3: Rewrite `player.py`**

Replace the whole file with:

```python
import pygame

from circleshape import CircleShape
from constants import *
from shot import Shot


class Player(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, radius=PLAYER_RADIUS)
        self.rotation = 0
        self.cooldown_timer = 0
        # Spawn with grace so the player is not killed by whatever is already
        # on screen before they can react.
        self.invuln_timer = PLAYER_INVULN_TIME

    @property
    def is_invulnerable(self):
        return self.invuln_timer > 0

    def is_visible(self):
        """Blink while invulnerable so the grace period is legible."""
        if not self.is_invulnerable:
            return True
        return int(self.invuln_timer * PLAYER_BLINK_HZ) % 2 == 0

    def respawn(self):
        self.position = pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        self.velocity = pygame.Vector2(0, 0)
        self.rotation = 0
        self.invuln_timer = PLAYER_INVULN_TIME

    # Define a triangle
    def triangle(self):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        right = pygame.Vector2(0, 1).rotate(self.rotation + 90) * self.radius / 1.5
        a = self.position + forward * self.radius
        b = self.position - forward * self.radius - right
        c = self.position - forward * self.radius + right
        return [a, b, c]

    def draw(self, screen):
        if self.is_visible():
            pygame.draw.polygon(screen, COLOR_WHITE, self.triangle(), 2)

    def rotate(self, dt):
        self.rotation += PLAYER_TURN_SPEED * dt

    def update(self, dt):
        self.cooldown_timer -= dt
        self.invuln_timer -= dt

        keys = pygame.key.get_pressed()

        # Classic WASD movement
        if keys[pygame.K_a]:
            self.rotate(dt)
        if keys[pygame.K_d]:
            self.rotate(-dt)
        if keys[pygame.K_w]:
            self.move(dt)
        if keys[pygame.K_s]:
            self.move(-dt)
        if keys[pygame.K_SPACE]:
            self.shoot()

        self.wrap()

    def move(self, dt):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        self.position += forward * PLAYER_SPEED * dt

    def shoot(self):
        if self.cooldown_timer <= 0:
            shot = Shot(self.position.x, self.position.y)
            # Create and rotate its velocity vector in the player's direction
            shot.velocity = pygame.Vector2(0, 1).rotate(self.rotation)
            # Scale up the velocity vector to move fast
            shot.velocity *= PLAYER_SHOT_SPEED
            # Set shot cooldown timer
            self.cooldown_timer = PLAYER_SHOOT_COOLDOWN
```

Note `pygame.key.get_pressed()` requires video init. The session-scoped autouse fixture in `conftest.py` (Task 1) covers this for every test file — do **not** add a bare `pygame.init()` to `tests/test_player.py`. A module-level init there is a process-global side effect with no teardown, and it leaves the other test files passing only when collected in the same run as this one.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add player.py tests/test_player.py
git commit -m "feat: add player wrap, respawn and spawn invulnerability"
```

---

### Task 6: Difficulty-driven asteroid spawning

**Files:**
- Modify: `asteroidfield.py`
- Create: `tests/test_asteroidfield.py`

**Interfaces:**
- Consumes: `GameState.spawn_interval` (Task 3)
- Produces: `AsteroidField(state)` — **constructor signature changes**, Task 8 must pass the state

- [ ] **Step 1: Write the failing test**

Create `tests/test_asteroidfield.py`:

```python
import pygame

from asteroid import Asteroid
from asteroidfield import AsteroidField
from constants import DIFFICULTY_MAX_SCORE, SPAWN_RATE_START
from gamestate import GameState


def make_field(state):
    field_group = pygame.sprite.Group()
    asteroid_group = pygame.sprite.Group()
    AsteroidField.containers = (field_group,)
    Asteroid.containers = (asteroid_group,)
    return AsteroidField(state), asteroid_group


def test_no_spawn_before_the_interval_elapses():
    state = GameState()
    field, asteroids = make_field(state)
    field.update(SPAWN_RATE_START / 2)
    assert len(asteroids) == 0


def test_spawns_once_the_interval_elapses():
    state = GameState()
    field, asteroids = make_field(state)
    field.update(SPAWN_RATE_START + 0.01)
    assert len(asteroids) == 1


def test_spawned_asteroid_is_moving():
    state = GameState()
    field, asteroids = make_field(state)
    field.update(SPAWN_RATE_START + 0.01)
    assert list(asteroids)[0].velocity.length() > 0


def test_high_score_spawns_faster():
    state = GameState()
    state.score = DIFFICULTY_MAX_SCORE
    field, asteroids = make_field(state)
    # This dt would not have been enough at the starting interval.
    field.update(state.spawn_interval + 0.01)
    assert len(asteroids) == 1
    assert state.spawn_interval < SPAWN_RATE_START
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_asteroidfield.py -v`
Expected: FAIL — `TypeError: AsteroidField.__init__() takes 1 positional argument but 2 were given`

- [ ] **Step 3: Update `asteroidfield.py`**

Change `__init__` and `update`:

```python
    def __init__(self, state):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.state = state
        self.spawn_timer = 0.0
```

```python
    def update(self, dt):
        self.spawn_timer += dt
        # Interval shortens as the score climbs — this is the difficulty ramp.
        if self.spawn_timer > self.state.spawn_interval:
            self.spawn_timer = 0
```

The rest of `update()` is unchanged.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add asteroidfield.py tests/test_asteroidfield.py
git commit -m "feat: drive asteroid spawn rate from the difficulty curve"
```

---

### Task 7: HUD and game-over overlay

**Files:**
- Create: `hud.py`
- Create: `tests/test_hud.py`

**Interfaces:**
- Consumes: `GameState` (Task 3)
- Produces:
  - `draw_hud(screen, font, state) -> None`
  - `draw_game_over(screen, title_font, font, state) -> None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_hud.py`. These are smoke tests — they render onto an off-screen surface and assert something was actually drawn, which catches crashes and blank output without asserting on exact pixels.

```python
import pygame
import pytest

from constants import COLOR_BLACK, HUD_FONT_SIZE, HUD_TITLE_SIZE, SCREEN_HEIGHT, SCREEN_WIDTH
from gamestate import GameState, Phase
from hud import draw_game_over, draw_hud


@pytest.fixture
def surface():
    pygame.init()
    pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.fill(COLOR_BLACK)
    return screen


def has_non_black_pixels(screen):
    return pygame.transform.average_color(screen)[:3] != (0, 0, 0)


def test_draw_hud_puts_something_on_screen(surface):
    font = pygame.font.Font(None, HUD_FONT_SIZE)
    state = GameState()
    state.award(60)
    draw_hud(surface, font, state)
    assert has_non_black_pixels(surface)


def test_draw_game_over_puts_something_on_screen(surface):
    font = pygame.font.Font(None, HUD_FONT_SIZE)
    title_font = pygame.font.Font(None, HUD_TITLE_SIZE)
    state = GameState()
    state.phase = Phase.GAME_OVER
    draw_game_over(surface, title_font, font, state)
    assert has_non_black_pixels(surface)


def test_game_over_overlay_dims_the_playfield(surface):
    # The overlay must be translucent, not opaque: the frozen playfield
    # should still be faintly visible behind it.
    surface.fill((255, 255, 255))
    before = pygame.transform.average_color(surface)[:3]

    font = pygame.font.Font(None, HUD_FONT_SIZE)
    title_font = pygame.font.Font(None, HUD_TITLE_SIZE)
    state = GameState()
    state.phase = Phase.GAME_OVER
    draw_game_over(surface, title_font, font, state)

    after = pygame.transform.average_color(surface)[:3]
    assert after < before          # dimmed
    assert after != (0, 0, 0)      # but not blacked out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_hud.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'hud'`

- [ ] **Step 3: Implement `hud.py`**

```python
import pygame

from constants import (
    COLOR_WHITE,
    HUD_MARGIN,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)


def draw_hud(screen, font, state):
    """Score on the left, remaining ships on the right."""
    score = font.render(f"SCORE {state.score}", True, COLOR_WHITE)
    screen.blit(score, (HUD_MARGIN, HUD_MARGIN))

    ships = font.render(f"SHIPS {state.lives}", True, COLOR_WHITE)
    screen.blit(ships, (SCREEN_WIDTH - ships.get_width() - HUD_MARGIN, HUD_MARGIN))


def draw_game_over(screen, title_font, font, state):
    """Dim the frozen playfield and prompt for a restart."""
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    _blit_centred(screen, title_font.render("GAME OVER", True, COLOR_WHITE), -60)
    _blit_centred(screen, font.render(f"SCORE {state.score}", True, COLOR_WHITE), 20)
    _blit_centred(
        screen, font.render("press R to play again", True, COLOR_WHITE), 70
    )


def _blit_centred(screen, surface, y_offset):
    rect = surface.get_rect(
        center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + y_offset)
    )
    screen.blit(surface, rect)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add hud.py tests/test_hud.py
git commit -m "feat: add score/ships HUD and game-over overlay"
```

---

### Task 8: Async game loop and restart

Wires everything together. After this task the game is fully playable on the desktop.

**Files:**
- Modify: `main.py` (full rewrite)
- Create: `game.py`
- Create: `tests/test_game.py`

**Interfaces:**
- Consumes: everything from Tasks 2–7
- Produces: a runnable game; the async loop shape pygbag requires

> **Amended during execution.** `start_new_game` and `handle_collisions` live in
> `game.py`, not `main.py`, which imports them. They are display-free, but
> `asyncio.run(main())` at module level makes `main.py` unimportable, so keeping
> them there left the project's most integration-heavy logic reachable by no test.
> `tests/test_game.py` now covers respawn polarity in both directions,
> one-shot-one-asteroid, pre-split scoring, and the restart teardown. The code
> block below shows both functions inline for readability; put them in `game.py`.

- [ ] **Step 1: Rewrite `main.py`**

Replace the whole file with:

```python
import asyncio

import pygame

from asteroid import Asteroid
from asteroidfield import AsteroidField
from constants import *
from gamestate import GameState, Phase
from hud import draw_game_over, draw_hud
from player import Player
from shot import Shot


def start_new_game(state, groups):
    """Clear the world and build a fresh one.

    Used for both first start and restart, so there is exactly one code path
    that produces a playable game.
    """
    for group in groups:
        group.empty()
    state.reset()
    player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    AsteroidField(state)
    return player


def handle_collisions(state, player, asteroids, shots):
    """Resolve shot hits and player impacts for one frame.

    Returns the player, respawned if they were hit and had a life left.
    """
    for asteroid in list(asteroids):
        for shot in list(shots):
            if shot.collision(asteroid):
                state.award(asteroid.radius)
                asteroid.split()
                shot.kill()
                break

    if player.is_invulnerable:
        return player

    for asteroid in list(asteroids):
        if asteroid.collision(player):
            if not state.lose_life():
                player.respawn()
            break
    return player


async def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Asteroids")

    clock = pygame.time.Clock()
    dt = 0

    font = pygame.font.Font(None, HUD_FONT_SIZE)
    title_font = pygame.font.Font(None, HUD_TITLE_SIZE)

    updatable = pygame.sprite.Group()
    drawable = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots = pygame.sprite.Group()
    groups = (updatable, drawable, asteroids, shots)

    # Automatically add all instances of the classes to groups
    Player.containers = (updatable, drawable)
    Asteroid.containers = (asteroids, updatable, drawable)
    AsteroidField.containers = (updatable,)
    Shot.containers = (shots, updatable, drawable)

    state = GameState()
    player = start_new_game(state, groups)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if state.phase is Phase.GAME_OVER and event.key == pygame.K_r:
                    player = start_new_game(state, groups)

        screen.fill(SCREEN_COLOR)

        if state.phase is Phase.PLAYING:
            updatable.update(dt)
            player = handle_collisions(state, player, asteroids, shots)

        for drawable_instance in drawable:
            drawable_instance.draw(screen)

        draw_hud(screen, font, state)
        if state.phase is Phase.GAME_OVER:
            draw_game_over(screen, title_font, font, state)

        pygame.display.flip()

        # Cap the step so a browser tab that regains focus after being
        # throttled cannot deliver one multi-second frame: that would
        # teleport sprites through each other without a collision test and
        # burn the whole invulnerability grace in a single decrement.
        dt = min(clock.tick(60) / 1000, MAX_FRAME_TIME)

        # Yields to the browser event loop under pygbag. On the desktop this
        # is a no-op that costs nothing.
        await asyncio.sleep(0)

    pygame.quit()


asyncio.run(main())
```

Three things changed deliberately and must not be reverted:

1. `sys.exit()` is gone — it is fatal in the browser.
2. `asyncio.run(main())` is at module level, **not** under `if __name__ == "__main__":` — pygbag expects the bare call.
3. `AsteroidField.containers = (updatable,)` is now a real tuple. It was `(updatable)` before, which is just the group itself.

- [ ] **Step 2: Run the test suite**

Run: `uv run pytest -v`
Expected: all pass. `main.py` is not imported by tests (importing it would start the game), so this confirms nothing else regressed.

- [ ] **Step 3: Play it**

Run: `uv run python main.py`

Verify by hand, and do not proceed until all of these hold:

- WASD moves and turns; space shoots with a cooldown
- Flying off any edge wraps you to the opposite side
- The ship blinks for ~2 seconds after spawning and cannot be killed during it
- Shooting a large asteroid splits it and the score increases by 20; the medium pieces give 50; the small ones 100
- Hitting an asteroid drops SHIPS by one and recentres the ship
- After three hits the overlay appears, the world freezes, and **R** starts a fresh game with score 0 and 3 ships
- Asteroids that fly off the edge do not come back
- Closing the window exits cleanly with no traceback

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: async game loop with lives, scoring and restart"
```

---

### Task 9: pygbag web build

**Files:**
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `main.py` from Task 8
- Produces: `build/web/` containing the browser bundle, consumed by Tasks 10 and 12

- [ ] **Step 1: Build the bundle**

Run: `uv run pygbag --build main.py`
Expected: completes and writes `build/web/`.

- [ ] **Step 2: Inspect what was produced**

Run: `ls -la build/web && grep -o 'https://[^"'"'"']*' build/web/index.html | sort -u`

**This step decides the next one.** pygbag's default template may load the CPython WASM runtime from the `pygame-web.github.io` CDN rather than bundling it. Record which it is:

- **No external URLs** → the bundle is self-contained. Skip Step 3.
- **External URLs present** → the deployed site depends on a third-party CDN at runtime. Do Step 3.

- [ ] **Step 3: Self-host the runtime, if Step 2 found external URLs**

Check the available options first: `uv run pygbag --help | grep -i -e cdn -e archive`

pygbag exposes a flag for pointing at an alternative runtime location (`--cdn`). Re-run the build with the runtime served from the same origin, then copy the runtime archive into `build/web/` so nginx serves it. Verify by repeating Step 2's `grep` and confirming no external hosts remain.

If self-hosting cannot be made to work, that is an acceptable outcome — record it in the README as a known runtime dependency on the pygame-web CDN and move on. Do not block the pipeline on it.

- [ ] **Step 4: Play it in a browser**

Run: `uv run pygbag main.py`

This serves on `http://localhost:8000`. Open it and confirm the same checklist from Task 8 Step 3 passes in the browser. Pay particular attention to:

- The page does not freeze (proves `await asyncio.sleep(0)` is doing its job)
- The browser console shows no errors
- Space bar does not scroll the page while playing
- Game over and **R** to restart both work

- [ ] **Step 5: Confirm `build/` stays out of git**

`.gitignore` already contains `build/`. Verify with `git status --short` that no build output is staged. If `dist/` is not listed, add it now — PyInstaller writes there in Task 11.

- [ ] **Step 6: Commit**

```bash
git add .gitignore
git commit -m "chore: keep build and dist output out of git"
```

---

### Task 10: nginx container

**Files:**
- Create: `docker/Dockerfile`
- Create: `docker/nginx.conf`
- Create: `.dockerignore`

**Interfaces:**
- Consumes: `build/web/` from Task 9
- Produces: an image serving the game on port 80, consumed by Tasks 11 and 12

- [ ] **Step 1: Create `docker/nginx.conf`**

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Browsers refuse to stream-compile WASM served as octet-stream.
    types {
        application/wasm          wasm;
        application/octet-stream  apk;
        text/html                 html;
        text/css                  css;
        application/javascript    js;
        image/png                 png;
        image/svg+xml             svg;
        application/json          json;
    }
    default_type application/octet-stream;

    # The Python runtime is ~10MB raw, ~3MB gzipped.
    gzip on;
    gzip_min_length 1024;
    gzip_types application/wasm application/javascript text/html text/css
               application/json application/octet-stream;

    # Recommended by pygbag; enables SharedArrayBuffer.
    add_header Cross-Origin-Opener-Policy   same-origin;
    add_header Cross-Origin-Embedder-Policy require-corp;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

The `types` block lists the common types explicitly rather than relying on
`include /etc/nginx/mime.types` plus an override, because a nested `types` block
**replaces** the inherited map rather than extending it. Step 4 verifies this.

- [ ] **Step 2: Create `docker/Dockerfile`**

```dockerfile
# The pygbag bundle is built in CI before this image, so this is a pure
# static-file copy. Building pygbag inside an arm64 image would run the whole
# Python toolchain under QEMU emulation and take many minutes.
FROM nginx:alpine

COPY build/web /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

- [ ] **Step 3: Create `.dockerignore`**

`build/` must **not** be listed here — it is the payload.

```
.git
.github
.idea
.venv
__pycache__/
dist/
docs/
tests/
*.md
uv.lock
conftest.py
```

- [ ] **Step 4: Build and smoke-test locally**

```bash
uv run pygbag --build main.py
docker build -f docker/Dockerfile -t asteroids:test .
docker run -d --rm -p 8088:80 --name asteroids-smoke asteroids:test
```

Then check the content types actually served:

```bash
curl -sI http://localhost:8088/ | grep -i content-type
curl -s http://localhost:8088/ -o /dev/null -w '%{http_code}\n'
for f in $(ls build/web); do
  echo -n "$f -> "
  curl -sI "http://localhost:8088/$f" | grep -i '^content-type' || echo MISSING
done
```

Expected: `/` is `text/html`; any `.wasm` file is `application/wasm`; `.js` is
`application/javascript`; **nothing that should be typed comes back as
`application/octet-stream` unexpectedly.** If `.js` or `.css` regressed, the `types`
block is wrong — fix it before moving on.

- [ ] **Step 5: Play it from the container**

Open `http://localhost:8088` and run the Task 8 Step 3 checklist once more. Then:

```bash
docker stop asteroids-smoke
```

If the game fails to load here but worked in Task 9 Step 4, the most likely cause is
the COOP/COEP headers. Comment them out, rebuild, retest — pygbag works without
`SharedArrayBuffer`.

- [ ] **Step 6: Commit**

```bash
git add docker/Dockerfile docker/nginx.conf .dockerignore
git commit -m "feat: serve the web build from an nginx container"
```

---

### Task 11: Release pipeline

**Files:**
- Create: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: the test suite, `main.py`, `docker/Dockerfile`
- Produces: a GitHub Release with three binaries, and `ghcr.io/unconnect/asteroids:latest` deployed to the Pi

- [ ] **Step 1: Create `.github/workflows/release.yml`**

```yaml
name: Release

on:
  push:
    tags: ['v*']
  workflow_dispatch:

permissions:
  contents: write
  packages: write

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv python install 3.12
      - run: uv sync --all-groups
      - run: uv run pytest -v
        env:
          SDL_VIDEODRIVER: dummy
          SDL_AUDIODRIVER: dummy

  desktop:
    needs: test
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: ubuntu-latest
            artifact: asteroids-linux
          - os: windows-latest
            artifact: asteroids-windows
          - os: macos-latest
            artifact: asteroids-macos
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv python install 3.12
      - run: uv sync --all-groups

      - name: Build binary (Linux)
        if: matrix.os == 'ubuntu-latest'
        run: |
          uv run pyinstaller --onefile --name asteroids main.py
          mv dist/asteroids dist/asteroids-linux

      - name: Build binary (Windows)
        if: matrix.os == 'windows-latest'
        run: |
          uv run pyinstaller --onefile --windowed --name asteroids main.py
          mv dist/asteroids.exe dist/asteroids-windows.exe

      - name: Build binary (macOS)
        if: matrix.os == 'macos-latest'
        run: |
          uv run pyinstaller --onefile --windowed --name Asteroids main.py
          hdiutil create -volname Asteroids -srcfolder dist/Asteroids.app \
            -ov -format UDZO dist/asteroids-macos.dmg

      - uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.artifact }}
          path: |
            dist/asteroids-linux
            dist/asteroids-windows.exe
            dist/asteroids-macos.dmg
          if-no-files-found: ignore

  release:
    needs: desktop
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: artifacts
          pattern: asteroids-*
          merge-multiple: true
      - uses: softprops/action-gh-release@v2
        with:
          files: artifacts/*
          generate_release_notes: true

  web:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv python install 3.12
      - run: uv sync --all-groups
      - run: uv run pygbag --build main.py
      - uses: actions/upload-artifact@v4
        with:
          name: web
          path: build/web

  docker:
    needs: web
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: web
          path: build/web

      - uses: docker/setup-qemu-action@v3
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=ref,event=tag
            type=raw,value=latest

      - uses: docker/build-push-action@v6
        with:
          context: .
          file: docker/Dockerfile
          platforms: linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}

      - name: Trigger Portainer redeploy
        run: curl -fsS -X POST "${{ secrets.PORTAINER_WEBHOOK_URL }}"
```

- [ ] **Step 2: Verify the PyInstaller build works locally first**

Do not debug packaging inside CI. Run the command for your own platform:

Run: `uv run pyinstaller --onefile --windowed --name Asteroids main.py`
Then: `./dist/Asteroids.app/Contents/MacOS/Asteroids` (macOS) or `./dist/asteroids` (Linux)
Expected: the game window opens and plays.

`--windowed` is omitted on Linux, where it has no effect.

- [ ] **Step 3: Commit and push the workflow**

```bash
git add .github/workflows/release.yml
git commit -m "ci: build desktop binaries and deploy the web build on tag"
git push
```

- [ ] **Step 4: Dry-run the workflow**

Trigger it manually from the Actions tab (`workflow_dispatch`) **before** tagging.
Expected: `test`, `desktop`, and `web` all go green. `release` will be skipped or fail
harmlessly without a tag; `docker` will push a `latest` image.

**Ordering note:** the final `curl` to the Portainer webhook will fail at this point
unless the Pi-side setup from Task 12 Step 5 is already done and the
`PORTAINER_WEBHOOK_URL` secret exists. That failure is expected on a first dry run and
does not indicate a problem with the build — everything before it is what this step is
checking. Either do Task 12 Step 5 first, or ignore that one red step for now.

Fix anything else red here rather than after tagging.

---

### Task 12: Deployment files and documentation

**Files:**
- Create: `deploy/docker-compose.yml`
- Create: `deploy/asteroids.subdomain.conf`
- Modify: `README.md`

**Interfaces:**
- Consumes: the image from Task 11
- Produces: the two files the user installs on the Pi

- [ ] **Step 1: Create `deploy/docker-compose.yml`**

Mirrors the existing `trackfoundry` stack exactly.

```yaml
services:
  asteroids:
    image: ghcr.io/unconnect/asteroids:latest
    container_name: asteroids
    restart: unless-stopped
    networks:
      - swag_default

networks:
  swag_default:
    external: true
```

- [ ] **Step 2: Create `deploy/asteroids.subdomain.conf`**

```nginx
## Version 2023/05/31

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    server_name asteroids.nikolasreuber.de;

    include /config/nginx/ssl.conf;

    client_max_body_size 0;

    location / {
        include /config/nginx/proxy.conf;
        include /config/nginx/resolver.conf;

        set $upstream_app asteroids;
        set $upstream_port 80;
        set $upstream_proto http;
        proxy_pass $upstream_proto://$upstream_app:$upstream_port;
    }
}
```

- [ ] **Step 3: Write `README.md`**

`README.md` is currently empty. Write it covering:

- What the game is and the play URL `https://asteroids.nikolasreuber.de`
- Controls: **W/S** thrust, **A/D** rotate, **Space** shoot, **R** restart after game over
- Scoring table: large 20, medium 50, small 100
- Download links pointing at the GitHub Releases page, with an explicit note that
  binaries are **unsigned**: macOS requires right-click → Open to get past Gatekeeper,
  Windows requires "More info" → "Run anyway" past SmartScreen
- Local development: `uv sync --all-groups`, `uv run python main.py`, `uv run pytest`
- Local web build: `uv run pygbag main.py`
- Deployment: push a `v*` tag; the Action builds binaries, publishes the image, and
  pokes the Portainer webhook. Note that `deploy/asteroids.subdomain.conf` is
  installed by hand into SWAG's `proxy-confs/` directory and is not deployed by the
  pipeline
- Whatever Task 9 Step 2/3 concluded about the pygame-web CDN dependency

- [ ] **Step 4: Commit**

```bash
git add deploy/ README.md
git commit -m "docs: add deployment files and README"
```

- [ ] **Step 5: Install on the Pi (manual, by the user)**

1. Copy `deploy/asteroids.subdomain.conf` into SWAG's `proxy-confs/` directory
2. Create the `asteroids` stack in Portainer from `deploy/docker-compose.yml`
3. Copy that stack's webhook URL into the repo secret `PORTAINER_WEBHOOK_URL`
4. Add the `asteroids` DNS record in Cloudflare
5. Restart SWAG so it picks up the new proxy conf

- [ ] **Step 6: Ship it**

```bash
git tag v1.0.0
git push --tags
```

Then verify, in order:

- The Actions run goes green end to end
- The GitHub Release has all three binaries attached
- `ghcr.io/unconnect/asteroids:latest` exists in the repo's Packages
- The Portainer stack shows a recent redeploy
- `https://asteroids.nikolasreuber.de` loads and plays

If the site 502s, SWAG cannot resolve the container: confirm it joined
`swag_default` and that `container_name` is exactly `asteroids`.

---

## Verification checklist

Before calling this done:

- [ ] `uv run pytest -v` passes with no failures or errors
- [ ] `uv run python main.py` is playable, and every item in Task 8 Step 3 holds
- [ ] `uv run pygbag main.py` is playable in a local browser with a clean console
- [ ] The Docker image serves `.wasm` as `application/wasm` and `.js` as `application/javascript`
- [ ] A tag push produces a green Actions run, a Release with three binaries, and a live site
