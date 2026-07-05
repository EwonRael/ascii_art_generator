"""End-to-end tests against a real reference photo.

The synthetic fixtures in test_ascii_art_generator.py (solid colors, a
horizontal gradient) are good for isolating specific behavior but can't
exercise real photographic detail -- gradients, edges, fine texture --
which is exactly what the shape-aware matching (glyph_profiles.py) cares
about. tests/fixtures/lenna.jpg is the classic "Lenna" image, a standard
reference photo used throughout image processing.
"""

import os
import sys

import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ascii_art_generator import ASCIIArtGenerator
from glyphset_narrow import NARROW_GLYPHS

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'lenna.jpg')


@pytest.fixture
def reference_image():
    """Load the real reference photo."""
    return Image.open(FIXTURE_PATH)


class TestPlainConversion:
    """The existing brightness-only mapping, run against a real photo."""

    def test_produces_expected_dimensions(self, reference_image):
        gen = ASCIIArtGenerator(width=40, shape_aware=False, debug=False)
        art = gen.direct_convert(reference_image)
        lines = art.split('\n')
        assert len(lines) == gen.height
        assert all(len(line) == 40 for line in lines)

    def test_only_uses_configured_char_set(self, reference_image):
        gen = ASCIIArtGenerator(width=40, char_set='basic', shape_aware=False, debug=False)
        art = gen.direct_convert(reference_image)
        assert set(art) <= set(gen.chars) | {'\n'}

    def test_deterministic(self, reference_image):
        gen = ASCIIArtGenerator(width=40, shape_aware=False, debug=False)
        assert gen.direct_convert(reference_image) == gen.direct_convert(reference_image)


class TestShapeAwareConversion:
    """The sub-character glyph-profile matching, run against a real photo."""

    def test_produces_expected_dimensions(self, reference_image):
        gen = ASCIIArtGenerator(width=40, shape_aware=True, debug=False)
        art = gen.direct_convert(reference_image)
        lines = art.split('\n')
        assert len(lines) == gen.height
        assert all(len(line) == 40 for line in lines)

    def test_only_uses_narrow_glyph_pool(self, reference_image):
        gen = ASCIIArtGenerator(width=40, shape_aware=True, debug=False)
        art = gen.direct_convert(reference_image)
        assert set(art) <= set(NARROW_GLYPHS) | {'\n'}

    def test_deterministic(self, reference_image):
        gen = ASCIIArtGenerator(width=40, shape_aware=True, debug=False)
        assert gen.direct_convert(reference_image) == gen.direct_convert(reference_image)

    def test_differs_from_plain_mapping(self, reference_image):
        """Shape-aware matching should pick a genuinely different result, not just reproduce brightness mapping."""
        plain = ASCIIArtGenerator(width=40, shape_aware=False, debug=False).direct_convert(reference_image)
        shaped = ASCIIArtGenerator(width=40, shape_aware=True, debug=False).direct_convert(reference_image)
        assert plain != shaped
