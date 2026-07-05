# ASCII Engine Rework — TODO

Personal core-engine rework backlog. Not implementing yet — planning only.

## 1. Standardize the font
**Decided (2026-07-04): Courier's measured metrics are the reference**, both as a number and as
a bundled file.
- The character-cell width/height ratio (2.1428, from `font-compair/measure_ratios.py` reading
  exact glyph corners out of reference SVGs) is live in `ascii_art_generator.py` as
  `ASCIIArtGenerator.CHAR_CELL_CORRECTION`.
- For actual glyph-outline rasterization (items 2/3 below), **`ciour/texgyrecursor-regular.otf`**
  (+ italic/bold/bold-italic) is bundled — TeX Gyre Cursor, GUST e-Foundry's freely-licensed
  (GUST Font License / LPPL) metric-compatible clone of Courier, the same font served by the
  LaTeX Font Catalogue's "Courier" entry. We aren't using Microsoft's actual Courier New file
  since it's a proprietary Monotype font that can't be redistributed — but the letterform shapes
  and the "Courier" name are public domain, so a freely-licensed rendering of them is fine to
  bundle. See `ciour/README.md` for provenance/license details.

## 2. Image-to-font sub-character-aware comparison algorithm
**Glyph pools done (2026-07-04):** `glyphset_narrow.py` (`NARROW_GLYPHS`, the 95 printable
ASCII chars) and `glyphset_expanded.py` (`EXPANDED_GLYPHS`, 649 chars total) are checked in.
The expanded set was later grown from an initial 131-char draft to ~all of
`ciour/texgyrecursor-regular.otf`'s usable coverage (673 mapped codepoints minus 25
combining-mark/format/duplicate-space entries that can't stand alone in a cell) --
Latin-1, Latin Extended-A/B, Latin Extended Additional, Greek, general punctuation,
currency, letterlike symbols, arrows, math operators, and a handful of ligatures/misc.
Every character was verified against the font's cmap with fontTools *and* confirmed to
render non-blank via `PIL.ImageFont.getmask().getbbox()`.

**Important limitation found:** TeX Gyre Cursor has no box-drawing (U+2500 block), no
block-element (U+2580 block), and almost no geometric-shape glyphs -- can't be added at
any size. Rendered ink-density measurement (not just Unicode-category guessing) also
shows this font has no genuinely "dark" glyph: the heaviest available (₩ ₦ ¶ № Ŋ Æ Ǽ Ħ Ḫ Ṃ
Œ...) top out around 21% pixel coverage in a cell -- nowhere near a solid block. If the
accuracy-comparison work (item 3) ever needs a true "black" output cell, this font can't
provide one; either swap in a font with block elements or lean on the backlogged Braille
dot-matrix mode (which needs no font rasterization at all).

Build an algorithm that compares an image region to a candidate font glyph with sub-character
(sub-cell) awareness — i.e. matching on a sampled brightness/shape grid within the cell, not
just a single averaged pixel value. Basis for real glyph-shape-based character selection instead
of a hand-guessed density string.

**Done (2026-07-04):** `glyph_profiles.py` renders each glyph (`NARROW_GLYPHS` only for now, per
plan) from `ciour/texgyrecursor-regular.otf` into a cell standardized to the *measured terminal*
aspect ratio (`CHAR_CELL_CORRECTION`'s 2.1428, not the font's own, noticeably squarer,
ascent/descent box), then downsamples with `Image.BOX` to a `GRID_COLS=3 x GRID_ROWS=6` grid —
3 wide by the user's own call, 6 tall from `round(3 * 2.1428)` (whatever makes each cell closest
to square, per the user's spec). Downsampling via resize, rather than manually slicing the glyph
into equal rectangles, is what sidesteps the "glyph pixel dimensions don't divide evenly" problem
raised during planning — the same resize step is later reused on the source image, so profile
grids and sampled grids are always built the same way. Verified both by unit test
(`tests/test_glyph_profiles.py`) and by eye: `_` is bottom-heavy, `"`/`'` are top-heavy, `.` sits
low, `-`/`o` sit mid-cell — the shape distinctions this feature exists to capture. Cached via
`lru_cache`.

## 3. Rewrite ASCII generation to use sub-character awareness
Rework `_map_pixels_to_ascii()` (and the duplicate CLI/GUI preprocessing pipelines feeding it)
to sample a sub-cell grid per output character and nearest-match it against the profiles/algorithm
from item 2, instead of one-pixel-per-character brightness mapping.

**Initial version done (2026-07-04):** added additively rather than replacing the existing path
yet — a `shape_aware=False` constructor flag / `--shape-aware` CLI flag on `ASCIIArtGenerator`.
When on, `_preprocess_image` resizes to `width*GRID_COLS x height*GRID_ROWS` (instead of
`width x height`) so there's real sub-cell detail to sample, and the new
`_map_pixels_to_ascii_profiled()` nearest-matches each block against the item-2 profiles by
squared distance. Default brightness-only path is byte-for-byte unchanged (verified). GUI is not
wired up to this yet. Matches against `NARROW_GLYPHS` only, as planned.

**Limitation observed, ties back to item 2's font-limitation note:** in flat/solid dark image
regions, output gets visually noisy — flickers between several similarly-inky characters
(`%`, `B`, `8`, `$`, `@`...) cell-to-cell instead of settling on one, because no narrow-pool
glyph gets anywhere close to the target's near-1.0 ink density (font tops out ~21% coverage), so
squared-distance ranking among the closest-available options is sensitive to minor shape noise.
Not a bug in the matching logic — a real gap that switching to the expanded glyph pool, or item 4
(warp/contrast tuning), may need to address if flat-region fidelity matters.

**Promoted to the default (2026-07-04):** after a long round of experimentation (see
`experiments/README.txt` for the full trail), `shape_aware=True` is now `ASCIIArtGenerator`'s
constructor default, and the CLI's no-flags default runs the full best-known recipe automatically:
- `match_sharpness()` boosts sharpness (PIL `ImageEnhance.Sharpness`) to hit
  `ASCIIArtGenerator.IDEAL_SHARPNESS` (2132.39, Laplacian variance measured from a reference photo
  the user hand-picked as "ideal" -- baked in as a number per their explicit request, not a
  dependency on that file, since it's an untracked fixture that's already been deleted by accident
  more than once).
- `optimize_gamma_for_diversity()` then searches a gamma curve to maximize glyph diversity (see
  below for why diversity, not accuracy).
- The original plain brightness-density mapping is still available via `--simple` (also skips both
  auto-searches; individual `--gamma`/`--sharpness`/etc. flags still apply on top of either mode).

**Key finding along the way: accuracy is a dead end as a search target, diversity works.**
Tried auto-searching brightness/ink-ceiling to maximize a per-cell "accuracy" score (`last_accuracy`,
tolerance-based sub-cell match rate against glyph profiles). Confirmed via `experiments/sweep_*`
that this is a dead end *either way* you score it: scored against the same adjusted image being
searched, it's gameable (the search just brightens toward blank, since blank trivially matches
everywhere); scored against the true unadjusted image instead, it's monotonic the other way --
converges to "don't touch the image" as best, since any deviation from truth necessarily scores
worse against truth by construction. Kept as a reported diagnostic only (`--optimize-brightness`),
never trust it as a search objective. **Diversity** (`last_diversity_pct`/`last_diversity_unique_count`,
normalized Shannon entropy of glyph usage) has a genuine interior optimum instead -- too dark
collapses onto a few "closest available dark" glyphs, too bright collapses toward blank, a good
middle ground spreads usage across many glyphs. `optimize_for_diversity()` (brightness) and
`optimize_gamma_for_diversity()` (gamma curve, empirically better -- a curve reshapes shadows/
highlights unevenly instead of just shifting everything) both target this instead.

Diversity isn't perfectly reliable either, though: blending edge-detection into the source image
(both an additive-darken overlay and a straight 50/50 crossfade, using the three edge modes
already in `image_processor.py`) *raised* diversity numbers further still but the user's own
eyeball verdict was that every edge variant looked *less* legible than the plain gamma-diversity
result -- crossfade in particular just homogenizes flat regions into one repeated glyph, high
entropy but low information. Lesson: diversity is a good signal for steering away from degenerate
collapse, but stops being trustworthy once comparing already-reasonable candidates -- look at the
render too.

## 4. Image warp/skew optimization algorithm
Create an algorithm that modifies the source image (skewing/stretching) to try to maximize the
accuracy score from item 2/3 — i.e. automatically search over geometric transforms of the input
to find the one that yields the best ASCII match. This is fully algorithmic/automatic — no manual
user-driven warp control (no drag handles or interactive UI).

---

## Backlog (deferred, lower priority, not scoped yet)
- ~~Fix the character-cell aspect ratio properly~~ — done: replaced the guessed `0.5` height
  multiplier with `ASCIIArtGenerator.CHAR_CELL_CORRECTION` (1/2.1428, measured from Courier New).
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
