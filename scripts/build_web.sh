#!/usr/bin/env bash
# Build the pygbag/WebAssembly browser bundle in build/web/ using the stock,
# unmodified pygbag CDN build.
#
# ---------------------------------------------------------------------------
# History: an earlier version of this script tried to self-host the runtime
# by pointing `--cdn` at the local site root and mirroring pythons.js, the
# xterm.js terminal, and the CPython-for-WASM interpreter into build/web/.
# That looked complete by every static check (no external URLs anywhere in
# the built files) but did NOT work in a real browser: pygame-ce itself is
# fetched at runtime by Python code running *inside* the WASM interpreter, as
# a wheel from a URL built from a hardcoded default ("http://localhost:8000/
# cdn/...") that `--cdn` never touches, and the package index it resolves
# against ("index-0.9.3-cp312.json") is still requested straight from
# pygame-web.github.io regardless of what `--cdn` says. Those two fetches
# happen from inside the running interpreter, not from anything present in
# build/web/ on disk, so no static scan of the built files could have caught
# them. The wheel URL in particular resolves to pygbag's hardcoded
# dev-server default, "http://localhost:8000/cdn/...", regardless of what
# --cdn was set to; in a real deployment with nothing listening on :8000,
# the browser console shows net::ERR_CONNECTION_REFUSED for that request and
# the game never finishes loading pygame_ce. Self-hosting pygbag 0.9.3's
# runtime is not achievable without reverse-engineering and repackaging its
# Python-level package resolution, which is out of scope.
#
# Decision: ship the stock pygbag CDN build. The deployed site has a real,
# documented runtime dependency on pygame-web.github.io (loader JS, terminal
# JS, the CPython-for-WASM interpreter, and the pygame-ce wheel are all
# fetched by the browser/interpreter from that host at play time). That's
# recorded in the README as a known dependency, per the original task-9
# brief's own fallback plan for exactly this situation.
# ---------------------------------------------------------------------------
#
# Usage: scripts/build_web.sh
# Run from anywhere; always operates on the repo root. Idempotent: safe to
# re-run, and works from a clean checkout (only prerequisite is `uv`;
# pygbag.ini keeps the build from walking into .venv/tests/docs/etc, which is
# required for `pygbag --build` to succeed at all from this repo's layout).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BUILD_WEB="$REPO_ROOT/build/web"

echo "==> Building pygbag bundle (stock CDN build, no local overrides)"
uv run python -m pygbag --build main.py

echo "==> Verifying build/web/ (fail loudly on anything missing or empty)"

apk=$(find "$BUILD_WEB" -maxdepth 1 -name "*.apk" 2>/dev/null | head -n1)

required=(
    "index.html"
    "favicon.png"
)

status=0

if [ -z "$apk" ]; then
    echo "FAIL: no .apk game archive found in $BUILD_WEB" >&2
    status=1
else
    required+=("$(basename "$apk")")
fi

for f in "${required[@]}"; do
    path="$BUILD_WEB/$f"
    if [ ! -f "$path" ]; then
        echo "FAIL: missing required file: $f" >&2
        status=1
        continue
    fi
    size=$(wc -c < "$path" | tr -d ' ')
    if [ "$size" -eq 0 ]; then
        echo "FAIL: required file is zero bytes: $f" >&2
        status=1
        continue
    fi
    printf 'OK   %-30s %10d bytes\n' "$f" "$size"
done

if [ -n "$apk" ] && ! grep -q "$(basename "$apk")" "$BUILD_WEB/index.html" 2>/dev/null; then
    echo "FAIL: index.html does not reference the game archive $(basename "$apk")" >&2
    status=1
else
    echo "OK   index.html references $(basename "$apk")"
fi

zero_byte="$(find "$BUILD_WEB" -type f -size 0 2>/dev/null || true)"
if [ -n "$zero_byte" ]; then
    echo "FAIL: zero-byte file(s) found under $BUILD_WEB:" >&2
    echo "$zero_byte" >&2
    status=1
fi

if [ "$status" -ne 0 ]; then
    echo "==> build_web.sh: VERIFICATION FAILED" >&2
    exit 1
fi

total_size="$(du -sh "$BUILD_WEB" | cut -f1)"
echo "==> build_web.sh: OK -- $total_size total in $BUILD_WEB"
echo "==> NOTE: this bundle depends on pygame-web.github.io at runtime (loader JS,"
echo "    CPython-for-WASM interpreter, and the pygame-ce wheel are all fetched by"
echo "    the browser/interpreter at play time). See README for details."
