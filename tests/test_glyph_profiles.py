"""Unit tests for glyph shape profiling (see TODO.md items 2/3)."""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glyph_profiles import build_glyph_profiles, GRID_COLS, GRID_ROWS


def test_profile_shape():
    """Every profile is a (GRID_ROWS, GRID_COLS) ink-density grid in [0, 1]."""
    profiles = build_glyph_profiles()
    for char, grid in profiles.items():
        assert grid.shape == (GRID_ROWS, GRID_COLS)
        assert grid.min() >= 0.0
        assert grid.max() <= 1.0


def test_space_is_blank():
    """The space character should have no ink anywhere in its grid."""
    profiles = build_glyph_profiles()
    assert np.allclose(profiles[' '], 0.0)


def test_underscore_is_bottom_heavy():
    """'_' should carry its ink in the bottom row, not the top."""
    profiles = build_glyph_profiles()
    grid = profiles['_']
    top_half = grid[:GRID_ROWS // 2]
    bottom_half = grid[GRID_ROWS // 2:]
    assert bottom_half.sum() > top_half.sum()
    assert top_half.sum() == 0.0


def test_quote_is_top_heavy():
    """'\"' should carry its ink near the top, not the bottom."""
    profiles = build_glyph_profiles()
    grid = profiles['"']
    top_half = grid[:GRID_ROWS // 2]
    bottom_half = grid[GRID_ROWS // 2:]
    assert top_half.sum() > bottom_half.sum()
    assert bottom_half.sum() == 0.0


def test_underscore_and_quote_differ_more_than_brightness_alone_would_suggest():
    """Two glyphs with similar average brightness should still be distinguishable by shape."""
    profiles = build_glyph_profiles()
    underscore, quote = profiles['_'], profiles['"']
    # Their per-cell shapes should be clearly distinct even though both are
    # light, low-ink glyphs overall.
    assert not np.allclose(underscore, quote, atol=0.05)
