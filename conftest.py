import os

# Must run before pygame is imported anywhere: forces headless SDL so tests
# work in CI with no display or sound device.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
