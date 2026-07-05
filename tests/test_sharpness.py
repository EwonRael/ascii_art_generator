"""Unit tests for sharpness measurement and reference-matching.

Only tests/fixtures/lenna.jpg is depended on here -- it's the one fixture
committed to git. lenna-50.jpg (the user's hand-picked "ideal sharpness"
reference) is not committed and has already been deleted once by accident,
which is exactly why match_sharpness() bakes its measured value in as
IDEAL_SHARPNESS rather than requiring the file. Tests against the real file
are separated out and skipped if it's missing.
"""

import os
import sys

import pytest
from PIL import Image, ImageEnhance

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ascii_art_generator import ASCIIArtGenerator

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
LENNA_50 = os.path.join(FIXTURES, 'lenna-50.jpg')


class TestMeasureSharpness:
    def test_sharpening_increases_measured_sharpness(self):
        """Laplacian variance should rise monotonically with the enhancement factor."""
        img = Image.open(os.path.join(FIXTURES, 'lenna.jpg'))
        base = ASCIIArtGenerator.measure_sharpness(img)
        sharpened = ImageEnhance.Sharpness(img).enhance(4.0)
        assert ASCIIArtGenerator.measure_sharpness(sharpened) > base

    def test_blurring_decreases_measured_sharpness(self):
        img = Image.open(os.path.join(FIXTURES, 'lenna.jpg'))
        base = ASCIIArtGenerator.measure_sharpness(img)
        blurred = ImageEnhance.Sharpness(img).enhance(0.0)
        assert ASCIIArtGenerator.measure_sharpness(blurred) < base


class TestMatchSharpness:
    """The baked-in-default path -- no external reference photo needed."""

    def test_converges_close_to_default_target(self):
        gen = ASCIIArtGenerator(width=10, debug=False)
        img = Image.open(os.path.join(FIXTURES, 'lenna.jpg'))
        best_factor, achieved, target = gen.match_sharpness(img)
        assert target == ASCIIArtGenerator.IDEAL_SHARPNESS
        assert abs(achieved - target) / target < 0.05

    def test_explicit_target_overrides_default(self):
        gen = ASCIIArtGenerator(width=10, debug=False)
        img = Image.open(os.path.join(FIXTURES, 'lenna.jpg'))
        best_factor, achieved, target = gen.match_sharpness(img, target_sharpness=900.0)
        assert target == 900.0
        assert abs(achieved - target) / target < 0.05

    def test_sets_self_sharpness_and_last_values(self):
        gen = ASCIIArtGenerator(width=10, debug=False)
        img = Image.open(os.path.join(FIXTURES, 'lenna.jpg'))
        best_factor, achieved, target = gen.match_sharpness(img)
        assert gen.sharpness == best_factor
        assert gen.last_sharpness_factor == best_factor
        assert gen.last_measured_sharpness == achieved
        assert gen.last_sharpness_target == target

    def test_matched_sharpness_is_actually_applied_during_conversion(self):
        """The factor found should get used automatically on the next conversion, not just stored."""
        # width=40, not 10 -- too small a grid and the sharpening difference
        # can wash out entirely after downsampling, making this flaky.
        gen = ASCIIArtGenerator(width=40, debug=False)
        img = Image.open(os.path.join(FIXTURES, 'lenna.jpg'))
        gen.match_sharpness(img.copy())
        assert gen.sharpness != 1.0

        plain_gen = ASCIIArtGenerator(width=40, debug=False)
        assert plain_gen.direct_convert(img.copy()) != gen.direct_convert(img.copy())


class TestMatchSharpnessToReference:
    """Convenience wrapper around match_sharpness() -- uses a synthetically
    sharpened image as the reference, so this doesn't depend on any specific
    external fixture file existing."""

    def test_converges_close_to_references_sharpness(self):
        gen = ASCIIArtGenerator(width=10, debug=False)
        img = Image.open(os.path.join(FIXTURES, 'lenna.jpg'))
        reference = ImageEnhance.Sharpness(img).enhance(5.0)
        best_factor, achieved, target = gen.match_sharpness_to_reference(img.copy(), reference)
        assert target == ASCIIArtGenerator.measure_sharpness(reference)
        assert abs(achieved - target) / target < 0.05


@pytest.mark.skipif(not os.path.exists(LENNA_50), reason="optional, not-committed reference fixture")
class TestAgainstRealReferenceFixture:
    """Extra confirmation against the user's own hand-picked reference photo,
    when present. Not required -- this file isn't committed to git."""

    def test_matches_the_real_reference_photo(self):
        gen = ASCIIArtGenerator(width=10, debug=False)
        img = Image.open(os.path.join(FIXTURES, 'lenna.jpg'))
        reference = Image.open(LENNA_50)
        best_factor, achieved, target = gen.match_sharpness_to_reference(img, reference)
        assert abs(achieved - target) / target < 0.05
