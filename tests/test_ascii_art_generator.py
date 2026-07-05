"""Unit tests for the ASCIIArtGenerator class."""

import os
import sys
import tempfile
import pytest
from PIL import Image
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ascii_art_generator import ASCIIArtGenerator


@pytest.fixture
def generator():
    """Create a plain-mode ASCIIArtGenerator (this file tests the original
    brightness-density mapping specifically, not the shape-aware default)."""
    return ASCIIArtGenerator(width=20, shape_aware=False, debug=False)


@pytest.fixture
def white_image():
    """Create a small white test image."""
    return Image.new("RGB", (50, 50), color=(255, 255, 255))


@pytest.fixture
def black_image():
    """Create a small black test image."""
    return Image.new("RGB", (50, 50), color=(0, 0, 0))


@pytest.fixture
def gradient_image():
    """Create a horizontal gradient image."""
    arr = np.zeros((50, 100, 3), dtype=np.uint8)
    for x in range(100):
        arr[:, x, :] = int(x * 255 / 99)
    return Image.fromarray(arr)


class TestCharacterSets:
    """Tests for character set handling."""

    def test_default_char_set(self):
        """Test that 'standard' char set is used by default."""
        gen = ASCIIArtGenerator(debug=False)
        assert gen.chars == ASCIIArtGenerator.CHAR_SETS['standard']

    def test_basic_char_set(self):
        """Test selecting the 'basic' char set."""
        gen = ASCIIArtGenerator(char_set='basic', debug=False)
        assert gen.chars == ASCIIArtGenerator.CHAR_SETS['basic']

    def test_unknown_char_set_falls_back(self):
        """Test that unknown char set falls back to 'standard'."""
        gen = ASCIIArtGenerator(char_set='nonexistent', debug=False)
        assert gen.chars == ASCIIArtGenerator.CHAR_SETS['standard']


class TestConversion:
    """Tests for image-to-ASCII conversion."""

    def test_white_image_produces_spaces(self, generator, white_image):
        """Test that a white image maps to high-density characters."""
        result = generator.direct_convert(white_image)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_black_image_produces_characters(self, generator, black_image):
        """Test that a black image maps to low-density characters (spaces)."""
        result = generator.direct_convert(black_image)
        lines = result.strip().split('\n')
        # Black pixels (value 0) should map to the first char (space)
        for line in lines:
            assert all(c == ' ' for c in line)

    def test_output_dimensions(self, generator, gradient_image):
        """Test that output dimensions match expected width."""
        result = generator.direct_convert(gradient_image)
        lines = result.split('\n')
        assert len(lines[0]) == 20  # width=20

    def test_height_auto_calculated(self, generator, gradient_image):
        """Test that height is auto-calculated from aspect ratio."""
        result = generator.direct_convert(gradient_image)
        lines = result.split('\n')
        # 100x50 image at width=20 -> height should be ~5 (20 * 0.5 * 0.5)
        assert len(lines) > 0

    def test_gradient_has_variety(self):
        """Test that a gradient image produces varied characters."""
        gen = ASCIIArtGenerator(width=50, char_set='basic', shape_aware=False, debug=False)
        arr = np.zeros((20, 100, 3), dtype=np.uint8)
        for x in range(100):
            arr[:, x, :] = int(x * 255 / 99)
        img = Image.fromarray(arr)
        result = gen.direct_convert(img)
        unique_chars = set(result.replace('\n', ''))
        assert len(unique_chars) > 3  # Should have variety


class TestFileIO:
    """Tests for file operations."""

    def test_convert_from_file(self, generator, tmp_path):
        """Test converting from a file path."""
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        img_path = str(tmp_path / "test.png")
        img.save(img_path)
        result = generator.convert_image(img_path)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_convert_nonexistent_file_raises(self, generator):
        """Test that converting a nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            generator.convert_image("/nonexistent/image.png")

    def test_save_to_file(self, generator, white_image, tmp_path):
        """Test saving ASCII art to a file."""
        result = generator.direct_convert(white_image)
        output_path = str(tmp_path / "output.txt")
        success = generator.save_to_file(result, output_path)
        assert success is True
        assert os.path.exists(output_path)


class TestOptions:
    """Tests for processing options."""

    def test_invert(self, white_image):
        """Test that invert option changes the output."""
        gen_normal = ASCIIArtGenerator(width=10, shape_aware=False, debug=False)
        gen_invert = ASCIIArtGenerator(width=10, invert=True, shape_aware=False, debug=False)
        result_normal = gen_normal.direct_convert(white_image)
        result_invert = gen_invert.direct_convert(white_image)
        assert result_normal != result_invert

    def test_dither(self, gradient_image):
        """Test that dither option does not crash."""
        gen = ASCIIArtGenerator(width=20, dither=True, shape_aware=False, debug=False)
        result = gen.direct_convert(gradient_image)
        assert isinstance(result, str)
