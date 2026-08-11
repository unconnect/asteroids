#!/usr/bin/env bash
# Build a fully self-hosted pygbag/WebAssembly bundle in build/web/.
#
# pygbag's own `--build` only produces index.html/favicon.png/<app>.apk/<app>.tar.gz.
# The actual CPython-for-WASM interpreter, its stdlib+pygame-ce data, and the
# terminal/xterm.js support files it depends on are NOT shipped in the pygbag
# pip package and are NOT downloaded by `pygbag --build` -- they are normally
# fetched by the *browser*, at run time, from pygame-web.github.io. That is a
# hard runtime dependency on a third-party host, which defeats self-hosting.
#
# This script instead builds with the runtime cdn pointed at the local site
# root ("./") and then mirrors every file the loader (pythons.js) actually
# requests into build/web/, so the deployed site has zero external hosts.
#
# The exact file list below was derived by reading pythons.js/vtx.js/index.html
# source (not guessed, not taken from a single browser trace) -- see
# .superpowers/sdd/2026-08-10-playable-and-deploy/task-9-report.md for the
# full derivation and reasoning for every entry (and every deliberate
# exclusion, e.g. vt.js and the sixel image worker, which our config never
# loads).
#
# Usage: scripts/build_web.sh
# Run from anywhere; always operates on the repo root. Idempotent: safe to
# re-run, and works from a clean checkout (only prerequisite is `uv` and
# network access to pygame-web.github.io).

set -euo pipefail

# ---------------------------------------------------------------------------
# Pin the exact pygbag runtime version this script mirrors. This must match
# the `pygbag` version installed via uv (see pyproject.toml/uv.lock) -- pygbag
# embeds this same version string into its default --cdn URL. Bump it
# deliberately, together with the pygbag dependency, never automatically:
# an unpinned "latest" here would let an upstream change silently alter what
# gets deployed to production.
PYGBAG_VERSION="0.9.3"
# ---------------------------------------------------------------------------

CDN_VERSIONED="https://pygame-web.github.io/cdn/${PYGBAG_VERSION}"
# A few files (vtx.js, vt.js, and everything under vt/) are NOT versioned --
# they live one directory above the version-pinned path on the CDN. Confirmed
# by curling both locations: the versioned path 404s, the root path 200s.
CDN_ROOT="https://pygame-web.github.io/cdn"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BUILD_WEB="$REPO_ROOT/build/web"
FETCH_CACHE="$REPO_ROOT/build/.pygbag-fetch-cache"

CURL="curl -fsSL --retry 3"
# -f: turn HTTP errors (404 etc.) into a non-zero exit instead of writing the
#     error-page body to the destination file. This is the exact check that
#     would have caught a zero-byte/error-page file being written silently.

mkdir -p "$FETCH_CACHE" "$BUILD_WEB"

echo "==> [1/4] Fetching build-time template + icon (used only to render index.html)"
$CURL -o "$FETCH_CACHE/default.tmpl" "$CDN_VERSIONED/default.tmpl"
$CURL -o "$FETCH_CACHE/favicon.png" "$CDN_VERSIONED/favicon.png"

echo "==> [2/4] Building pygbag bundle with cdn pointed at same-origin ('./')"
uv run pygbag --build \
    --cdn "./" \
    --template "$FETCH_CACHE/default.tmpl" \
    --icon "$FETCH_CACHE/favicon.png" \
    main.py

echo "==> [3/4] Mirroring the WASM runtime files the browser loader requests"
mkdir -p "$BUILD_WEB/cpython312" "$BUILD_WEB/vt"

# Root-level files: sit next to index.html because config.cdn == "./" and
# pythons.js resolves "../vtx.js" relative to its OWN (root-level) location,
# which browsers clamp back to root when there's nowhere higher to go.
$CURL -o "$BUILD_WEB/pythons.js"   "$CDN_VERSIONED/pythons.js"
$CURL -o "$BUILD_WEB/empty.html"   "$CDN_VERSIONED/empty.html"
# empty.ogg: fetched by feat_snd()'s autoplay/user-media-engagement unlock
# trick on non-Safari browsers whenever ume_block is set (pygbag's default).
$CURL -o "$BUILD_WEB/empty.ogg"    "$CDN_VERSIONED/empty.ogg"
# cpythonrc.py: fetched by VM.postrun() as `${cdn}cpythonrc.py`.
$CURL -o "$BUILD_WEB/cpythonrc.py" "$CDN_VERSIONED/cpythonrc.py"
# vtx.js: NOT under the version path -- see CDN_ROOT note above.
$CURL -o "$BUILD_WEB/vtx.js"       "$CDN_ROOT/vtx.js"

# vtx.js itself imports xterm.js + the image addon from
# `config.cdn + "../vt/"`, which with config.cdn == "./" also collapses to
# the site root's vt/ subdirectory.
$CURL -o "$BUILD_WEB/vt/xterm.css"            "$CDN_ROOT/vt/xterm.css"
$CURL -o "$BUILD_WEB/vt/xterm.js"             "$CDN_ROOT/vt/xterm.js"
$CURL -o "$BUILD_WEB/vt/xterm-addon-image.js" "$CDN_ROOT/vt/xterm-addon-image.js"

# The actual CPython-for-WASM interpreter + stdlib + pygame-ce build
# (~20 MB). locateFile() in pythons.js fetches these as
# `${cdn}cpython312/${path}`.
$CURL -o "$BUILD_WEB/cpython312/main.js"   "$CDN_VERSIONED/cpython312/main.js"
$CURL -o "$BUILD_WEB/cpython312/main.wasm" "$CDN_VERSIONED/cpython312/main.wasm"
$CURL -o "$BUILD_WEB/cpython312/main.data" "$CDN_VERSIONED/cpython312/main.data"

# Deliberately NOT fetched (documented, not an oversight):
#   - vt.js: sibling of vtx.js, only loaded when the template's data-os
#     config selects the plain "vt" terminal instead of "vtx". Our
#     default.tmpl always requests "vtx" (data-os="vtx,snd,gui"), so vt.js
#     is dead code for this build.
#   - xtermjsixel/xterm-addon-image-worker.js: referenced by pythons.js as an
#     addon URL, but returns 404 from the CDN under every path tried (site
#     root, vt/, and the version path), AND xterm-addon-image.js (54 KB,
#     downloaded above) contains no `Worker(` call anywhere that would ever
#     dereference that URL -- it is unreachable dead configuration, broken
#     upstream, not something we can mirror because no real copy exists.
#   - browserfs.min.js: also 404s from the CDN under every path tried.
#     pythons.js has its own comment confirming this ("was browserfs,
#     removed must be fully provided from template" -- but the template
#     provides a reference to a file nobody ships). It's a plain, non-async
#     <script src> tag (unlike the awaited dynamic imports above), so a
#     failed load doesn't block boot -- but rather than ship a fake 0-byte
#     stand-in for a file that doesn't exist anywhere, we remove the dead
#     tag from index.html below.

echo "==> [4/4] Removing dead browserfs.min.js <script> tag from index.html"
sed -i.bak '/browserfs\.min\.js/d' "$BUILD_WEB/index.html"
rm -f "$BUILD_WEB/index.html.bak"

echo "==> Verifying build/web/ (fail loudly on anything missing or empty)"

apk=$(find "$BUILD_WEB" -maxdepth 1 -name "*.apk" | head -n1)
targz=$(find "$BUILD_WEB" -maxdepth 1 -name "*.tar.gz" | head -n1)

required=(
    "index.html"
    "favicon.png"
    "pythons.js"
    "empty.html"
    "empty.ogg"
    "cpythonrc.py"
    "vtx.js"
    "vt/xterm.css"
    "vt/xterm.js"
    "vt/xterm-addon-image.js"
    "cpython312/main.js"
    "cpython312/main.wasm"
    "cpython312/main.data"
)

status=0

if [ -z "$apk" ]; then
    echo "FAIL: no .apk game archive found in $BUILD_WEB" >&2
    status=1
else
    required+=("$(basename "$apk")")
fi

if [ -z "$targz" ]; then
    echo "FAIL: no .tar.gz game archive found in $BUILD_WEB" >&2
    status=1
else
    required+=("$(basename "$targz")")
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

external_urls="$(grep -oE 'https?://[^"'"'"']+' "$BUILD_WEB/index.html" || true)"
if [ -n "$external_urls" ]; then
    echo "FAIL: external URL(s) still present in index.html:" >&2
    echo "$external_urls" >&2
    status=1
else
    echo "OK   index.html references no external hosts"
fi

if [ "$status" -ne 0 ]; then
    echo "==> build_web.sh: VERIFICATION FAILED" >&2
    exit 1
fi

total_size="$(du -sh "$BUILD_WEB" | cut -f1)"
echo "==> build_web.sh: OK -- $total_size total in $BUILD_WEB"
