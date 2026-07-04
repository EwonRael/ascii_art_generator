"""Unit tests for glyph diversity scoring and the diversity-maximizing search."""

import os
import sys

import pytest
from PIL import Image
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ascii_art_generator import ASCIIArtGenerator
from glyphset_narrow import NARROW_GLYPHS


class TestDiversityScoring:
    def test_none_before_any_conversion(self):
        gen = ASCIIArtGenerator(width=10, shape_aware=True, debug=False)
        assert gen.last_diversity_unique_count is None
        assert gen.last_diversity_pct is None

    def test_tracked_in_plain_mode_too(self):
        """Unlike accuracy, diversity is meaningful for the brightness-only path too."""
        gen = ASCIIArtGenerator(width=20, shape_aware=False, debug=False)
        gradient = np.zeros((50, 100, 3), dtype=np.uint8)
        for x in range(100):
            gradient[:, x, :] = int(x * 255 / 99)
        gen.direct_convert(Image.fromarray(gradient))
        assert gen.last_diversity_unique_count is not None
        assert gen.last_diversity_pct is not None

    def test_flat_image_collapses_to_zero_diversity(self):
        """A single flat color maps every cell to the same glyph -- the degenerate floor."""
        gen = ASCIIArtGenerator(width=10, shape_aware=True, debug=False)
        img = Image.new("RGB", (30, 30), color=(128, 128, 128))
        gen.direct_convert(img)
        assert gen.last_diversity_unique_count == 1
        assert gen.last_diversity_pct == 0.0

    def test_bounds(self):
        gen = ASCIIArtGenerator(width=20, shape_aware=True, debug=False)
        img = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'lenna.jpg'))
        gen.direct_convert(img)
        assert 1 <= gen.last_diversity_unique_count <= len(NARROW_GLYPHS)
        assert 0.0 <= gen.last_diversity_pct <= 100.0


class TestDiversityOptimization:
    def test_requires_shape_aware(self):
        gen = ASCIIArtGenerator(width=10, shape_aware=False, debug=False)
        img = Image.new("RGB", (30, 30), color=(128, 128, 128))
        with pytest.raises(ValueError):
            gen.optimize_for_diversity(img)

    def test_finds_a_valid_brightness_and_applies_it(self):
        gen = ASCIIArtGenerator(width=12, shape_aware=True, debug=False)
        img = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'lenna.jpg'))
        best_brightness, best_diversity = gen.optimize_for_diversity(img, coarse_steps=5, fine_steps=3)
        assert 0.3 <= best_brightness <= 3.0
        assert 0.0 <= best_diversity <= 100.0
        assert gen.brightness == best_brightness

    def test_beats_the_unadjusted_baseline_on_a_real_photo(self):
        """The whole point: a real photo's default (brightness=1.0) rendering is
        too dark for this glyph pool, so the optimizer should find something
        with higher diversity than doing nothing."""
        img = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'lenna.jpg'))

        baseline = ASCIIArtGenerator(width=20, shape_aware=True, debug=False)
        baseline.direct_convert(img.copy())
        baseline_diversity = baseline.last_diversity_pct

        gen = ASCIIArtGenerator(width=20, shape_aware=True, debug=False)
        _, best_diversity = gen.optimize_for_diversity(img.copy())
        assert best_diversity > baseline_diversity


class TestGammaOptimization:
    def test_requires_shape_aware(self):
        gen = ASCIIArtGenerator(width=10, shape_aware=False, debug=False)
        img = Image.new("RGB", (30, 30), color=(128, 128, 128))
        with pytest.raises(ValueError):
            gen.optimize_gamma_for_diversity(img)

    def test_finds_a_valid_gamma_and_applies_it(self):
        gen = ASCIIArtGenerator(width=12, shape_aware=True, debug=False)
        img = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'lenna.jpg'))
        best_gamma, best_diversity = gen.optimize_gamma_for_diversity(img, coarse_steps=5, fine_steps=3)
        assert 0.05 <= best_gamma <= 3.0
        assert 0.0 <= best_diversity <= 100.0
        assert gen.gamma == best_gamma

    def test_beats_flat_brightness_optimization_on_a_real_photo(self):
        """The whole point: a gamma curve reshapes shadows/highlights unevenly,
        reaching a higher diversity peak than any single flat brightness
        multiplier can (see TODO.md / experiments/)."""
        img = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'lenna.jpg'))

        brightness_gen = ASCIIArtGenerator(width=20, shape_aware=True, debug=False)
        _, brightness_best = brightness_gen.optimize_for_diversity(img.copy())

        gamma_gen = ASCIIArtGenerator(width=20, shape_aware=True, debug=False)
        _, gamma_best = gamma_gen.optimize_gamma_for_diversity(img.copy())

        assert gamma_best > brightness_best
