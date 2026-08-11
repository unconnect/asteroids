# Asteroids

A classic Asteroids clone, built with pygame. Playable in the browser (via the
pygame-ce-based pygbag/WASM runtime) or as a native desktop binary.

**Play now: https://asteroids.nikolasreuber.de**

## Controls

| Key | Action |
|-----|--------|
| `W` / `S` | Thrust forward / backward |
| `A` / `D` | Rotate left / right |
| `Space` | Shoot |
| `R` | Restart (after game over) |

## Scoring

Smaller rocks are worth more — they're harder to hit and closer to death when
they do:

| Asteroid size | Points |
|---------------|-------:|
| Large | 20 |
| Medium | 50 |
| Small | 100 |

## Downloads

Prebuilt binaries for Linux, Windows, and macOS are attached to each
[GitHub Release](https://github.com/unconnect/asteroids/releases).

**The binaries are unsigned.** Code signing costs money the project doesn't
spend (~$99/yr for an Apple developer certificate, ~$200/yr for a Windows
EV certificate), so both OSes will complain:

- **macOS**: Gatekeeper blocks the app on first launch. Right-click (or
  Control-click) the app and choose **Open**, instead of double-clicking.
  The macOS binary is built on `macos-latest` GitHub runners, which are
  Apple Silicon — the `.dmg` is **arm64-only**, it will not run on an Intel
  Mac.
- **Windows**: SmartScreen will say the app is unrecognized. Click **More
  info**, then **Run anyway**.

Neither of these is a sign the binary is broken or malicious — it's what
every unsigned executable gets from both OSes by default.

## Local development

```bash
uv sync --all-groups
uv run python main.py
```

Run the test suite (64 tests):

```bash
uv run pytest
```

## Local web build

Build the browser bundle with the project's build script, not a bare pygbag
invocation:

```bash
./scripts/build_web.sh
```

This wraps `pygbag --build main.py` and then verifies the output. A bare
`pygbag --build main.py` fails on this repo: pygbag has no notion of
`.gitignore` and walks into `.venv/`, where it chokes on a `.wav` file
bundled with pygame's own examples. `pygbag.ini` at the repo root tells it
to skip `.venv`, `tests/`, `docs/`, and a few other directories — it's
required for the build to work at all, so don't delete it.

To actually play the build locally:

```bash
uv run pygbag main.py
```

This starts a local dev server (default `http://localhost:8000`).

### Do not open it at `http://localhost:<port>`

This is the single most time-consuming gotcha in this project, so it's
stated plainly: **load the page at `http://127.0.0.1:<port>` or a real
domain — never the literal hostname `localhost`.**

pygbag's runtime startup script (`cpythonrc.py`) checks whether the page's
URL contains the literal substring `//localhost:`. If it does, it switches
into a "dev mode" that tries to resolve the `pygame-ce` wheel against
`http://localhost:8000/cdn/` — pygbag's own dev-server default — regardless
of where the page is actually being served from. If nothing is listening on
that port, the browser gets `ERR_CONNECTION_REFUSED`, the interpreter never
finishes booting, and the page just hangs on "Downloading..." forever with
no useful error on screen. `127.0.0.1` and any real hostname skip this
branch entirely and fetch the wheel from the real CDN, which is what you
want. This cost real hours to track down; don't repeat it.

### The page needs two clicks to start

This is normal pygbag behavior, not a bug: browsers won't let a page
autoplay audio/start a busy loop without a real user gesture. The first
click dismisses a "Loading, please wait…" screen; the second responds to a
"Ready to start! Please click/touch page" prompt. A first-time visitor who
doesn't click twice will think the page is broken — it isn't, it's waiting.

### The web build depends on pygame-web.github.io at runtime

The self-hosted Pi serves only the game itself — roughly 68 KB (`index.html`,
a favicon, and a small game-code archive). The rest — the ~20 MB
CPython-for-WASM interpreter, its standard library, and the `pygame-ce`
wheel — is fetched by the visitor's own browser directly from
`pygame-web.github.io` at play time. If that host is down or unreachable
from the visitor's network, the game will not load, independent of whether
the Pi itself is up.

Self-hosting this runtime was attempted and abandoned. Mirroring every
static asset pygbag's loader references is not enough: once the WASM
interpreter boots, Python code running *inside it* resolves the `pygame-ce`
wheel against a package index that is itself fetched straight from
`pygame-web.github.io`, and that resolution partly falls back to a
hardcoded `localhost:8000` dev-server URL that no static file mirror can
satisfy. This is a genuine, currently-unavoidable runtime dependency of the
web build, not an oversight — it's documented here rather than worked around.

## Deployment

Releases are cut by **publishing a GitHub Release** — from the Releases page,
or:

```bash
gh release create v1.0.0 --title "v1.0.0" --notes "What changed"
```

Creating the release creates its tag, so there is no separate `git tag` step.
A release left as a **draft** triggers nothing; the pipeline starts the moment
you publish, which means you can write the notes at your own pace.

Publishing triggers `.github/workflows/release.yml`, which:

1. Runs the test suite.
2. Builds desktop binaries for Linux, Windows, and macOS with PyInstaller and
   attaches them to the release you just published. Your release notes are
   never touched — the workflow only uploads assets.
3. Builds the web bundle (`scripts/build_web.sh`) and packages it into an
   `nginx:alpine`-based image, published to
   `ghcr.io/unconnect/asteroids:latest` (arm64, for the Raspberry Pi target).
4. Pokes a Portainer webhook to redeploy the running stack with the new
   image.

The same workflow also runs on every push to `main` and every pull request,
but only the test suite — the binary/image-building jobs (and the release
and redeploy steps) stay gated to a published release (or a manual
`workflow_dispatch` run, see below), so a PR never builds binaries, builds
or pushes an image, or touches GHCR.

The workflow also supports manual `workflow_dispatch` runs, useful for
dry-running most of the pipeline (tests, binary builds, image build/push)
without publishing anything. Three things stay release-only even on a
dispatch run: attaching binaries (there is no release to attach them to, so
that job doesn't run at all), moving the `latest` image tag that
`deploy/docker-compose.yml` pins, and the Portainer webhook. A dispatch run
still builds and pushes the image under a `sha-…` tag, so it genuinely
validates the build — it just cannot move `latest` or redeploy. A manual
"Run workflow" click, from any branch, can never touch the live site.

### `deploy/`

Two files live here for reference, mirroring the Pi's existing reverse-proxy
setup:

- `docker-compose.yml` — the stack definition used to create the `asteroids`
  service in Portainer. It joins the external `swag_default` network and
  pulls `ghcr.io/unconnect/asteroids:latest`.
- `asteroids.subdomain.conf` — the SWAG (nginx reverse proxy) config for
  `asteroids.nikolasreuber.de`.

Neither file is deployed by the pipeline. `asteroids.subdomain.conf` is
installed by hand into SWAG's `proxy-confs/` directory on the Pi, and the
Portainer stack is created once from `docker-compose.yml`; after that,
updates arrive via the webhook in step 4 above, not by re-copying these
files.
