"""Sub-character glyph shape profiles (see TODO.md items 2/3).

Renders each candidate glyph from the bundled font onto a cell standardized
to the *measured terminal* character-cell aspect ratio (see
ASCIIArtGenerator.CHAR_CELL_CORRECTION, 2.1428) rather than the font's own
ascent/descent box, which is noticeably squarer. The cell is then
downsampled to a small grid of ink-density values. Comparing an image
region's downsampled grid against these profiles is what lets character
selection respond to *where* within a cell the dark/light parts of a glyph
sit (e.g. top-heavy vs. bottom-heavy), not just its average brightness.
"""

import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from glyphset_narrow import NARROW_GLYPHS

FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ciour', 'texgyrecursor-regular.otf')

# 3 columns wide; rows chosen so each cell is as close to square as possible
# given the measured terminal char-cell ratio (ASCIIArtGenerator.
# CHAR_CELL_CORRECTION -- 2.1428 tall-per-wide): round(3 * 2.1428) == 6.
GRID_COLS = 3
GRID_ROWS = 6

# Font point size used for rendering before downsampling -- large enough
# that the downsample below is a real antialiased average rather than a
# handful of blocky source pixels.
_RENDER_SIZE = 200

# Same ratio as ASCIIArtGenerator.CHAR_CELL_CORRECTION's reciprocal (kept as
# a literal here to avoid a circular import between the two modules).
_CHAR_CELL_RATIO = 2.1428


@lru_cache(maxsize=None)
def build_glyph_profiles(glyphs=NARROW_GLYPHS, font_path=FONT_PATH, cols=GRID_COLS, rows=GRID_ROWS):
    """Render each character in `glyphs` and reduce it to a (rows, cols) ink-density grid.

    Returns a dict mapping each character to a numpy array of shape
    (rows, cols) with values in [0, 1], where 1.0 is fully dark (ink) and
    0.0 is background. Cached -- rendering is deterministic for a given
    (glyphs, font_path, cols, rows) combination.
    """
    font = ImageFont.truetype(font_path, _RENDER_SIZE)
    ascent, descent = font.getmetrics()
    natural_h = ascent + descent
    cell_w = font.getlength('M')  # monospace: every glyph shares one advance width

    # Standardize to the measured terminal cell ratio, then center the
    # glyph's natural ink box in the extra vertical padding -- the same
    # role a terminal's line-height leading plays.
    cell_h = round(cell_w * _CHAR_CELL_RATIO)
    pad_top = (cell_h - natural_h) // 2

    profiles = {}
    for char in glyphs:
        canvas = Image.new('L', (round(cell_w), cell_h), color=255)
        draw = ImageDraw.Draw(canvas)
        draw.text((0, pad_top), char, font=font, fill=0, anchor='la')
        cell = canvas.resize((cols, rows), Image.BOX)
        ink = 1.0 - (np.asarray(cell, dtype=np.float64) / 255.0)
        profiles[char] = ink
    return profiles
