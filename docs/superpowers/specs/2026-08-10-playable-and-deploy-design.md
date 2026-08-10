# Asteroids: Playable Game + Web Deployment

**Date:** 2026-08-10
**Status:** Approved design, pending implementation plan

## Goal

Turn the boot.dev Asteroids exercise into a finished, playable game that anyone can
play at `https://asteroids.nikolasreuber.de`, and that can also be downloaded as a
native executable for macOS, Windows, and Linux. Pushing a `v*` tag builds and ships
everything.

## Non-goals

Deliberately excluded to keep scope single-plan sized:

- Sound effects, music, title screen, particle effects
- Persistent or online high scores
- Touch or gamepad input
- Multiple levels or wave structure
- Code signing / notarization of desktop binaries

---

## Part 1: Game

### 1.1 Architecture

Three concerns split out of `main.py` so game rules are testable without a display:

| File | Responsibility | Depends on |
|---|---|---|
| `gamestate.py` *(new)* | Score, lives, phase, difficulty curve | `constants` only — **no pygame rendering** |
| `hud.py` *(new)* | Draws score, ships remaining, game-over overlay | `pygame`, `gamestate` |
| `main.py` *(rewritten)* | Async loop, events, collisions, wiring | everything |

`gamestate.py` imports no rendering APIs. That is what makes the scoring, life, and
difficulty rules directly unit-testable.

### 1.2 `gamestate.py`

```python
class Phase(Enum):
    PLAYING
    GAME_OVER

class GameState:
    score: int
    lives: int
    phase: Phase

    def reset() -> None                      # score=0, lives=PLAYER_LIVES, phase=PLAYING
    def award(asteroid_radius: int) -> int   # adds points, returns points awarded
    def lose_life() -> bool                  # decrements; returns True if now GAME_OVER
    @property
    def spawn_interval() -> float            # current difficulty
```

### 1.3 Scoring

Classic Asteroids values — smaller rocks are worth more, rewarding follow-through:

| Asteroid | Radius | Points |
|---|---|---|
| Large | 60 | 20 |
| Medium | 40 | 50 |
| Small | 20 | 100 |

Implemented as a lookup keyed on `radius // ASTEROID_MIN_RADIUS`, so it stays correct
if `ASTEROID_KINDS` changes. An unknown radius returns 0 rather than raising.

### 1.4 Lives and respawn

3 ships. On collision the player loses one and respawns at screen center with **2
seconds of invulnerability**, blinking at 10 Hz (`draw()` skips on alternate 0.05s
windows). Without the grace period the player rematerializes inside the same asteroid
and immediately loses the next life too.

Invulnerability is a `Player.invuln_timer` float, decremented in `update()`. While
`invuln_timer > 0`, `main.py` skips the player/asteroid collision check entirely.

At 0 lives the phase becomes `GAME_OVER`. **`sys.exit()` is removed** (`main.py:50`) —
it is fatal in the browser.

### 1.5 Screen wrap and culling

**The player wraps. Asteroids do not.**

This is a deliberate divergence from arcade Asteroids. `AsteroidField` spawns
continuously every 0.8s (`asteroidfield.py:41`) rather than in finite waves. If
asteroids also wrapped, nothing would ever leave the playfield and the screen would
saturate into an unwinnable state within roughly a minute. Difficulty instead comes
from the spawn interval tightening (§1.6).

Two methods on `CircleShape`:

```python
def wrap(self) -> None
    # position.x < -radius        -> SCREEN_WIDTH + radius
    # position.x > SCREEN_WIDTH+r -> -radius       (same for y)

def is_off_screen(self, margin: float) -> bool
```

- `Player.update()` calls `wrap()`.
- `Asteroid.update()` culls itself via `is_off_screen(ASTEROID_CULL_MARGIN)`.
- `Shot.update()` culls itself via `is_off_screen(SHOT_RADIUS)`.

`ASTEROID_CULL_MARGIN = ASTEROID_MAX_RADIUS * 2` (120). **This must exceed the spawn
margin** — asteroids spawn at exactly `ASTEROID_MAX_RADIUS` outside the edge
(`asteroidfield.py:10-28`), so a smaller cull margin would destroy every asteroid on
the frame it spawns.

Culling also fixes an existing leak: asteroids and missed shots are currently never
removed from their sprite groups and accumulate for the lifetime of the process.

### 1.6 Difficulty ramp

Linear interpolation from starting interval to floor, clamped:

```python
t = min(1.0, score / DIFFICULTY_MAX_SCORE)
spawn_interval = SPAWN_RATE_START + (SPAWN_RATE_MIN - SPAWN_RATE_START) * t
```

`AsteroidField` receives the `GameState` in its constructor and reads
`state.spawn_interval` each update, replacing the `ASTEROID_SPAWN_RATE` constant.

### 1.7 New constants

```python
PLAYER_LIVES = 3
PLAYER_INVULN_TIME = 2.0
PLAYER_BLINK_HZ = 10

ASTEROID_CULL_MARGIN = ASTEROID_MAX_RADIUS * 2
ASTEROID_SCORE = {1: 100, 2: 50, 3: 20}   # keyed by radius // MIN_RADIUS

SPAWN_RATE_START = 0.8
SPAWN_RATE_MIN = 0.25
DIFFICULTY_MAX_SCORE = 5000

HUD_FONT_SIZE = 28
HUD_TITLE_SIZE = 72
```

### 1.8 Game loop

```python
async def main():
    pygame.init()
    ...
    state = GameState()
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if state.phase is Phase.GAME_OVER and event.key == pygame.K_r:
                    start_new_game(...)

        if state.phase is Phase.PLAYING:
            # update, collide, score
        # draw world + HUD (or overlay)

        pygame.display.flip()
        dt = clock.tick(60) / 1000
        await asyncio.sleep(0)      # yields to the browser event loop

asyncio.run(main())
```

`start_new_game()` empties all sprite groups, calls `state.reset()`, and constructs a
fresh `Player` and `AsteroidField`. It is used for both first start and restart, so
there is exactly one code path that establishes a playable world.

On `GAME_OVER` the world freezes (no updates) and the overlay draws over the last
frame.

Also fixed: `AsteroidField.containers = (updatable)` (`main.py:29`) is not a tuple —
it becomes `(updatable,)`.

---

## Part 2: Browser build

pygbag compiles the game to WebAssembly. Required source changes are exactly the
async loop (§1.8) and removing `sys.exit()` — both harmless on desktop, where
`asyncio.run()` executes the identical loop. **One codebase serves both targets with
no conditional branching.**

The game draws entirely with vector primitives and uses pygame's built-in font
(`pygame.font.Font(None, size)`), so there are **no asset files** to bundle.

`.python-version` moves `3.9` → `3.12` to match pygbag's browser runtime. No code in
the project is version-specific. `pyproject.toml` `requires-python` updates to match.

Build command, producing `build/web/`:

```bash
python -m pygbag --build main.py
```

---

## Part 3: Container and proxy

### 3.1 Dockerfile

The pygbag bundle is built in CI **before** the image build, so the Dockerfile is a
static-file copy:

```dockerfile
FROM nginx:alpine
COPY build/web /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

This is a deliberate performance decision. Running pygbag inside an `arm64` image
build on an x86 runner would execute the whole Python toolchain under QEMU emulation
and take many minutes. Copying pre-built static files makes the arm64 build a file
copy.

### 3.2 nginx config

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    include /etc/nginx/mime.types;
    types {
        application/wasm  wasm;
        application/octet-stream  apk;
    }

    gzip on;
    gzip_min_length 1024;
    gzip_types application/wasm application/javascript text/html text/css
               application/json application/octet-stream;

    add_header Cross-Origin-Opener-Policy   same-origin;
    add_header Cross-Origin-Embedder-Policy require-corp;

    location / { try_files $uri $uri/ /index.html; }
}
```

Two points to **verify during implementation rather than assume**:

1. `application/wasm` — browsers refuse to stream-compile WASM served as
   `octet-stream`. Recent `nginx:alpine` mime.types already maps `.wasm`; the explicit
   `types` block is belt-and-braces. Because a nested `types` block can override rather
   than extend the included map, the built image must be smoke-tested with
   `curl -I .../*.wasm` to confirm both `.wasm` and ordinary `.js`/`.css` still resolve
   correctly.
2. COOP/COEP headers are pygbag's documented recommendation (they enable
   `SharedArrayBuffer`). If they turn out to break loading in this configuration,
   remove them — pygbag functions without threading.

gzip takes the Python runtime from roughly 10 MB to roughly 3 MB over the wire.

### 3.3 Deployment files

Conventions taken from the user's existing `trackfoundry` deployment on the Pi, which
these files mirror exactly.

`deploy/docker-compose.yml` — Portainer stack:

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

`deploy/asteroids.subdomain.conf` — SWAG proxy conf, following the standard
linuxserver template (`## Version 2023/05/31`) with all auth includes left commented:

```nginx
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

Key conventions confirmed: containers join the external `swag_default` network,
`container_name` matches the service name and is what SWAG resolves as
`$upstream_app`, and images live at `ghcr.io/unconnect/<name>:latest`.

Note the proxy conf is a **file the user installs on the Pi** in SWAG's
`proxy-confs/` directory, not something the pipeline deploys. It lives in the repo for
reference and reproducibility.

---

## Part 4: Release pipeline

`.github/workflows/release.yml`, triggered on `push: tags: ['v*']`.

```
git tag v1.0.0 && git push --tags
   │
   ├─ test ────────── pytest, SDL_VIDEODRIVER=dummy
   │
   ├─ desktop ─────── ubuntu-latest  → asteroids-linux    ┐
   │   (matrix,        macos-latest   → Asteroids.dmg      ├→ GitHub Release
   │    needs: test)   windows-latest → asteroids.exe      ┘
   │
   └─ web ─────────── pygbag build → artifact
      (needs: test)        │
                           └─ docker ─ buildx --platform linux/arm64 → GHCR
                                          │
                                          └─ POST ${{ secrets.PORTAINER_WEBHOOK_URL }}
```

### 4.1 Jobs

| Job | Runner | Notes |
|---|---|---|
| `test` | ubuntu-latest | Gates everything below. |
| `desktop` | matrix: ubuntu / macos / windows | PyInstaller. No cross-compilation exists for Python packagers — each OS needs its own runner. Free and unlimited here because the repo is public. |
| `web` | ubuntu-latest | `pygbag --build`, uploads `build/web` as an artifact. |
| `release` | ubuntu-latest | `softprops/action-gh-release` attaches all three binaries. |
| `docker` | ubuntu-latest | Downloads the web artifact, `docker/build-push-action` for `linux/arm64` → GHCR, then POSTs the Portainer webhook. |

### 4.2 PyInstaller

No data files to bundle, so no `--add-data`:

- Linux/Windows: `pyinstaller --onefile --windowed --name asteroids main.py`
- macOS: same, then `hdiutil create -format UDZO` to produce a `.dmg` from the `.app`

Binaries are **unsigned**. macOS Gatekeeper will require right-click → Open, and
Windows SmartScreen will show a warning. The README documents this. Signing costs
$99/yr (Apple) and ~$200/yr (Windows) and is out of scope.

`macos-latest` is Apple Silicon, so the `.dmg` is arm64-only. If Intel Mac support is
ever wanted, add a `macos-13` matrix entry.

Linux binaries are built against `ubuntu-latest`'s glibc and will not run on
substantially older distributions. AppImage would solve this if it ever matters.

### 4.3 Secrets and permissions

| Name | Purpose |
|---|---|
| `PORTAINER_WEBHOOK_URL` | Repository secret. Already reachable from GitHub. |
| `GITHUB_TOKEN` | Built in. Needs `contents: write` (release) and `packages: write` (GHCR). |

---

## Part 5: Testing

`gamestate.py` has no rendering dependency, so the rules are directly testable. Tests
run headless in CI with `SDL_VIDEODRIVER=dummy`.

| Area | Cases |
|---|---|
| Scoring | Each of the three radii awards its documented value; unknown radius awards 0; score accumulates |
| Lives | Decrement; `GAME_OVER` at exactly 0; `reset()` restores 3 lives and clears score |
| Difficulty | Returns `SPAWN_RATE_START` at score 0; `SPAWN_RATE_MIN` at and beyond `DIFFICULTY_MAX_SCORE`; monotonically decreasing; never below the floor |
| Wrap | Each of the four edges wraps to the opposite side with the correct radius offset; a centered position is unchanged |
| Culling | `is_off_screen` is False just inside the margin, True just outside; **an asteroid at its spawn position is not immediately culled** |
| Split | Produces exactly 2 asteroids one size smaller; a minimum-radius asteroid produces 0 |
| Collision | Overlapping circles True; touching-exactly boundary; disjoint False |

The spawn-vs-cull margin case is called out explicitly because getting it wrong makes
the game silently unplayable — asteroids would vanish the instant they appear.

---

## Risks

| Risk | Mitigation |
|---|---|
| nginx `types` block overrides rather than extends the mime map, breaking `.js`/`.css` | Smoke-test the built image with `curl -I` on `.wasm`, `.js`, and `.css` before shipping |
| COOP/COEP headers break pygbag loading | Remove them; pygbag works without `SharedArrayBuffer` |
| Cloudflare proxy interferes with WASM content-type or caching | Explicit nginx `Content-Type` already set; test with the orange cloud in its final state |
| Pi 5 arm64 image mismatch | `buildx --platform linux/arm64` targets `aarch64` as confirmed |
| Deploy files don't match existing Pi conventions | Resolved — mirrored from the working `trackfoundry` stack (§3.3) |

## Open items

None blocking. Portainer webhook reachability was confirmed by the user on
2026-08-10.
