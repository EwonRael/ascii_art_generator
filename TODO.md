# ASCII Engine Rework — TODO

Personal core-engine rework backlog. Not implementing yet — planning only.

## 1. Standardize the font
Pick a single font to use for algorithmic work (glyph profiling, accuracy scoring), separate
from the GUI's cosmetic preview font. Should be a bundled `.ttf` loaded via
`PIL.ImageFont.truetype(path)` (not an OS-installed font) to avoid "works on my machine" bugs.
Candidate: DejaVu Sans Mono, vendored into `assets/fonts/`. Not decided.

## 2. Image-to-font sub-character-aware comparison algorithm
Build an algorithm that compares an image region to a candidate font glyph with sub-character
(sub-cell) awareness — i.e. matching on a sampled brightness/shape grid within the cell, not
just a single averaged pixel value. Basis for real glyph-shape-based character selection instead
of a hand-guessed density string.

## 3. Rewrite ASCII generation to use sub-character awareness
Rework `_map_pixels_to_ascii()` (and the duplicate CLI/GUI preprocessing pipelines feeding it)
to sample a sub-cell grid per output character and nearest-match it against the profiles/algorithm
from item 2, instead of one-pixel-per-character brightness mapping.

## 4. Image warp/skew optimization algorithm
Create an algorithm that modifies the source image (skewing/stretching) to try to maximize the
accuracy score from item 2/3 — i.e. automatically search over geometric transforms of the input
to find the one that yields the best ASCII match. This is fully algorithmic/automatic — no manual
user-driven warp control (no drag handles or interactive UI).

---

## Backlog (deferred, lower priority, not scoped yet)
- Fix the character-cell aspect ratio properly: replace the guessed `0.5` height multiplier
  (hardcoded in both `ascii_art_generator.py` `_preprocess_image` and `gui_settings.py`
  `update_auto_height`) with a value measured from the standardized font (item 1).
- Possible **Braille dot-matrix character mode** (U+2800–U+28FF): each of the 256 Braille
  characters encodes an exact 2-wide × 4-tall grid of on/off dots — a known technique (e.g.
  `chafa --symbols=braille`) needing no profiling/matching, just direct bit math, giving higher
  effective resolution than any font-matched set.
- Character-pool scope question for profiling (item 2): curated symbol set (ASCII + common
  Unicode box/line-drawing glyphs, ~150-300 chars) vs. attempting the entire Unicode range
  (~150k code points, mostly blank/unrenderable — probably not worth it).
- Whether to unify the two duplicate CLI/GUI preprocessing pipelines into one shared pipeline
  (bigger refactor, less duplication) vs. patch each separately (less risk, mirrors the existing
  `0.5` hack situation).
- Warp implementation (item 4) should follow `ImageProcessor`'s existing chainable pattern (each
  method mutates `self.image`, returns `self`) — PIL supports the needed transforms natively:
  `Image.QUAD` (4-corner/perspective warp) for a first pass, `Image.MESH` (grid of independently
  warped pieces via `(dest_rect, src_quad)` pairs) as a higher-fidelity follow-up.

See `/home/owen/.claude/plans/starry-mixing-wilkinson.md` for fuller background notes (current
pipeline behavior, code entry points).
