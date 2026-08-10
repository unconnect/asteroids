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
