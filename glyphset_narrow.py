"""Narrow glyph pool for sub-character profiling (see TODO.md items 2/3).

Standard printable ASCII (0x20-0x7E) -- the 95 characters on any US
keyboard. Straight ' and " only; no directional/curly quotes and no
other typographic extras. This is the safe baseline pool: guaranteed
to exist in essentially any font, including ones far more limited
than the bundled ciour/texgyrecursor-*.otf.

Distinct from ASCIIArtGenerator.CHAR_SETS (ascii_art_generator.py),
which are hand-ordered density strings used for direct brightness
mapping today. This pool is raw material for the future glyph-shape
profiling system, not a drop-in replacement for CHAR_SETS.
"""

NARROW_GLYPHS = ''.join(chr(c) for c in range(0x20, 0x7F))
