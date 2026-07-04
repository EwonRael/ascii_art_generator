"""Unit tests for shape-aware accuracy scoring and brightness optimization."""

import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ascii_art_generator import ASCIIArtGenerator
from glyph_profiles import build_glyph_profiles, GRID_COLS, GRID_ROWS


def _image_from_profile(char):
    """Build the exact single-character source image a profile grid came from.

    profiles[char] is already a (GRID_ROWS, GRID_COLS) ink-density grid --
    exactly the pixel dimensions _preprocess_image would produce for a
    width=1, height=1 shape-aware conversion. Turning it directly back into
    a same-size grayscale image means the resize step in _preprocess_image
    is a no-op, so the matcher should reconstruct that glyph's profile
    almost exactly.
    """
    grid = build_glyph_profiles()[char]
    pixel_values = (255.0 * (1.0 - grid)).astype(np.uint8)
    return Image.fromarray(pixel_values, mode='L')


class TestAccuracyScoring:
    def test_none_before_any_shape_aware_conversion(self):
        gen = ASCIIArtGenerator(width=10, shape_aware=True, debug=False)
        assert gen.last_accuracy is None
        assert gen.last_accuracy_detail is None

    def test_stays_none_in_plain_mode(self):
        gen = ASCIIArtGenerator(width=10, shape_aware=False, debug=False)
        img = Image.new("RGB", (30, 30), color=(128, 128, 128))
        gen.direct_convert(img)
        assert gen.last_accuracy is None

    def test_bounds_and_consistency(self):
        gen = ASCIIArtGenerator(width=10, shape_aware=True, debug=False)
        img = Image.new("RGB", (30, 30), color=(128, 128, 128))
        gen.direct_convert(img)
        assert gen.last_accuracy is not None
        assert 0.0 <= gen.last_accuracy <= 100.0
        matched, total = gen.last_accuracy_detail
        assert 0 <= matched <= total
        assert total == gen.width * gen.height * GRID_COLS * GRID_ROWS

    def test_self_rendered_glyph_is_recovered_with_high_accuracy(self):
        """Feeding a glyph's own rendered profile back in should match itself almost exactly."""
        gen = ASCIIArtGenerator(width=1, height=1, shape_aware=True, debug=False)
        img = _image_from_profile('M')
        art = gen.direct_convert(img)
        assert art == 'M'
        assert gen.last_accuracy > 90.0


class TestBrightnessOptimization:
    def test_requires_shape_aware(self):
        gen = ASCIIArtGenerator(width=10, shape_aware=False, debug=False)
        img = Image.new("RGB", (30, 30), color=(128, 128, 128))
        with pytest.raises(ValueError):
            gen.optimize_brightness(img)

    def test_finds_a_valid_brightness_and_applies_it(self):
        gen = ASCIIArtGenerator(width=12, shape_aware=True, debug=False)
        img = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'lenna.jpg'))
        best_brightness, best_accuracy = gen.optimize_brightness(img, coarse_steps=5, fine_steps=3)
        assert 0.3 <= best_brightness <= 3.0
        assert 0.0 <= best_accuracy <= 100.0
        assert gen.brightness == best_brightness
