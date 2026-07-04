import argparse
import os
import sys
from collections import Counter
from PIL import Image, ImageOps, ImageEnhance
import numpy as np
import traceback

from glyph_profiles import build_glyph_profiles, darkest_avg_ink, darkest_subcell_ink, GRID_COLS, GRID_ROWS
from glyphset_narrow import NARROW_GLYPHS

class ASCIIArtGenerator:
    """
    A class to convert images to ASCII art with debugging capabilities.
    """

    # Character sets from low to high density
    CHAR_SETS = {
        'basic': ' .:-=+*#%@',  # Simple 10-character set
        'standard': ' .`^",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$', # Detailed set
        'blocks': ' ░▒▓█',  # Unicode blocks
        'custom': ' .",:;!~+-xmo*#W&8%B@$'  # Mid-level detail
    }

    def __init__(self, char_set='standard', width=100, height=None,
                contrast=1.0, brightness=1.0, gamma=1.0, invert=False, dither=False,
                debug=True, shape_aware=False, ink_ceiling=None):
        """Initialize the ASCII Art generator with debugging capabilities."""
        self.width = width
        self.height = height
        self.contrast = contrast
        self.brightness = brightness
        # Gamma curve applied after brightness/contrast -- unlike those
        # (uniform shifts/scales), gamma reshapes shadows vs. highlights
        # differently: output = (input/255)**gamma. gamma<1 lifts shadows
        # disproportionately; gamma>1 crushes them further. 1.0 = no-op.
        # See optimize_gamma_for_diversity()/apply_gamma().
        self.gamma = gamma
        self.invert = invert
        self.dither = dither
        self.debug_mode = debug
        # When True, characters are chosen by matching a sub-cell glyph
        # shape profile instead of averaging the cell to one brightness
        # value -- see glyph_profiles.py and TODO.md items 2/3. Currently
        # always matches against the narrow (95-char) glyph pool.
        self.shape_aware = shape_aware
        # Optional ink-density fraction (0-1) to use as the image's black
        # point -- see apply_ink_ceiling(). None disables this step. Pass
        # glyph_profiles.darkest_avg_ink()/darkest_subcell_ink() for the two
        # experimental presets.
        self.ink_ceiling = ink_ceiling
        # Populated by _map_pixels_to_ascii_profiled(): overall %, and
        # (matched, total) sub-cell counts it was computed from. None until
        # a shape-aware conversion has run at least once.
        self.last_accuracy = None
        self.last_accuracy_detail = None
        # Populated by _finalize_ascii_image() on every conversion (either
        # mode): count of distinct glyphs used, and normalized Shannon
        # entropy of their usage frequency (0-100%, where 100% would be
        # every glyph in the pool used equally often). See _compute_diversity().
        self.last_diversity_unique_count = None
        self.last_diversity_pct = None

        # Set character set
        if char_set in self.CHAR_SETS:
            self.chars = self.CHAR_SETS[char_set]
        else:
            self.debug_print(f"Warning: Character set '{char_set}' not found. Using 'standard'.")
            self.chars = self.CHAR_SETS['standard']

    def debug_print(self, message):
        """Print debug messages if debug mode is enabled."""
        if self.debug_mode:
            print(f"DEBUG [ASCIIArtGenerator]: {message}")

    # Character-cell width/height correction factor for monospace output.
    # Measured from Courier New (see font-compair/measure_ratios.py, which
    # reads exact glyph corner coordinates out of reference SVGs): a Courier
    # New cell is 2.1428x taller than it is wide, so we shrink the naive
    # aspect-ratio height by 1/2.1428 to compensate.
    CHAR_CELL_CORRECTION = 1 / 2.1428

    # Ink-density tolerance (same 0-1 scale as glyph_profiles' grids) for
    # counting a sampled sub-cell as "matching" its chosen glyph's profile
    # at that grid position -- see _map_pixels_to_ascii_profiled's accuracy
    # scoring. 0.15 is a starting point (~15 percentage points of ink), not
    # a measured value.
    SUBCELL_MATCH_TOLERANCE = 0.15

    @staticmethod
    def calculate_auto_height(width, image):
        """Calculate output height from an image's aspect ratio.

        Applies CHAR_CELL_CORRECTION to account for terminal/monospace
        character cells being taller than they are wide. This is the single
        source of truth for that correction factor -- other pipelines
        (GUI) should call this rather than re-deriving it.
        """
        aspect_ratio = image.height / image.width
        return int(width * aspect_ratio * ASCIIArtGenerator.CHAR_CELL_CORRECTION)

    @staticmethod
    def apply_contrast(image, factor):
        """Adjust image contrast by the given factor."""
        return ImageEnhance.Contrast(image).enhance(factor)

    @staticmethod
    def apply_brightness(image, factor):
        """Adjust image brightness by the given factor."""
        return ImageEnhance.Brightness(image).enhance(factor)

    @staticmethod
    def apply_gamma(image, gamma):
        """Apply a gamma curve: output = 255 * (input/255)**gamma.

        Unlike apply_brightness (a uniform multiply) or apply_ink_ceiling (a
        linear floor-and-stretch), this reshapes shadows and highlights by
        different amounts -- gamma<1 lifts shadows much more than
        highlights, gamma>1 does the opposite. That extra degree of freedom
        is what lets optimize_gamma_for_diversity() route pixel values into
        the parts of ink-space the glyph pool actually covers, beating what
        a single flat brightness value can achieve (see TODO.md).
        """
        arr = np.array(image, dtype=np.float64) / 255.0
        arr = np.power(arr, gamma)
        return Image.fromarray((arr * 255.0).clip(0, 255).astype(np.uint8))

    @staticmethod
    def apply_invert(image):
        """Invert image tones."""
        return ImageOps.invert(image)

    @staticmethod
    def apply_dither(image):
        """Apply Floyd-Steinberg dithering, returning a grayscale image."""
        image = image.convert('1', dither=Image.FLOYDSTEINBERG)
        return image.convert('L')

    @staticmethod
    def apply_ink_ceiling(image, target_ink):
        """Raise the image's black point so its darkest pixel needs no more
        than `target_ink` ink density to represent.

        No glyph can render arbitrarily dark (see glyph_profiles.py --
        darkest_avg_ink()/darkest_subcell_ink()), so without this, cells in a
        very dark image region all ask for more ink than any glyph provides,
        and the matcher just picks whichever available glyph is closest --
        often flickering between near-ties. This linearly stretches
        [current_min, current_max] to [255*(1-target_ink), 255], preserving
        contrast and highlights and only moving the floor.
        """
        arr = np.array(image, dtype=np.float64)
        current_min, current_max = arr.min(), arr.max()
        if current_max <= current_min:
            return image
        target_floor = 255.0 * (1.0 - target_ink)
        arr = target_floor + (arr - current_min) * (255.0 - target_floor) / (current_max - current_min)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    def _preprocess_image(self, image):
        """Preprocess the image with sizing and adjustments."""
        try:
            # Calculate height to maintain aspect ratio if not specified
            if self.height is None:
                self.height = self.calculate_auto_height(self.width, image)
                self.debug_print(f"Auto-calculated height: {self.height}")

            # Resize image. In shape-aware mode we need GRID_COLS x GRID_ROWS
            # source pixels per output character (not just one), so profile
            # matching has real sub-cell detail to compare against.
            if self.shape_aware:
                target_size = (self.width * GRID_COLS, self.height * GRID_ROWS)
            else:
                target_size = (self.width, self.height)
            self.debug_print(f"Resizing image from {image.size} to {target_size}")
            image = image.resize(target_size, Image.LANCZOS)

            # Convert to grayscale
            self.debug_print(f"Converting image from {image.mode} to grayscale")
            image = image.convert("L")

            # Apply contrast adjustment
            if self.contrast != 1.0:
                self.debug_print(f"Adjusting contrast with factor {self.contrast}")
                image = self.apply_contrast(image, self.contrast)

            # Apply brightness adjustment
            if self.brightness != 1.0:
                self.debug_print(f"Adjusting brightness with factor {self.brightness}")
                image = self.apply_brightness(image, self.brightness)

            # Apply gamma curve
            if self.gamma != 1.0:
                self.debug_print(f"Applying gamma curve, gamma={self.gamma}")
                image = self.apply_gamma(image, self.gamma)

            # Invert if requested
            if self.invert:
                self.debug_print("Inverting image colors")
                image = self.apply_invert(image)

            # Apply dithering if requested
            if self.dither:
                self.debug_print("Applying dithering")
                image = self.apply_dither(image)

            # Raise the black point to the glyph pool's achievable ceiling,
            # if requested -- see apply_ink_ceiling().
            if self.ink_ceiling is not None:
                self.debug_print(f"Applying ink ceiling correction, target_ink={self.ink_ceiling}")
                image = self.apply_ink_ceiling(image, self.ink_ceiling)

            self.debug_print(f"Preprocessing complete: {image.size}, {image.mode}")
            return image

        except Exception as e:
            self.debug_print(f"Error in preprocessing: {e}")
            traceback.print_exc()
            raise

    def _map_pixels_to_ascii(self, image):
        """Map each pixel to an ASCII character with detailed debugging."""
        try:
            # Get pixel data as a numpy array
            self.debug_print("Converting image to numpy array")
            pixels = np.array(image)
            self.debug_print(f"Pixel array shape: {pixels.shape}, dtype: {pixels.dtype}")

            # Print some array statistics to help diagnose issues
            self.debug_print(f"Array min: {pixels.min()}, max: {pixels.max()}, mean: {pixels.mean():.2f}")

            # Create empty ASCII image
            ascii_image = []

            # Map each pixel to a character
            self.debug_print("Mapping pixels to ASCII characters")
            for row_idx, row in enumerate(pixels):
                ascii_row = []
                for col_idx, pixel_value in enumerate(row):
                    try:
                        # Ensure pixel_value is a scalar
                        if isinstance(pixel_value, np.ndarray):
                            self.debug_print(f"Found array at position [{row_idx},{col_idx}]: {pixel_value}")
                            # Try to get single value from array
                            if pixel_value.size == 1:
                                pixel_value = pixel_value.item()
                                self.debug_print(f"Converted to scalar: {pixel_value}")
                            else:
                                # Take first element or average if multiple values
                                pixel_value = pixel_value[0] if pixel_value.size > 0 else 0
                                self.debug_print(f"Taking first element: {pixel_value}")

                        # Map the value (0-255) to an index in the character set
                        # Normalize pixel value to be between 0-255
                        if isinstance(pixel_value, (int, float, np.number)):
                            if pixel_value < 0 or pixel_value > 255:
                                pixel_value = np.clip(pixel_value, 0, 255)
                                self.debug_print(f"Clipped pixel value to range [0,255]: {pixel_value}")

                            char_idx = int(int(pixel_value) * (len(self.chars) - 1) / 255)
                            # Ensure index is within bounds
                            char_idx = max(0, min(char_idx, len(self.chars) - 1))
                            ascii_row.append(self.chars[char_idx])
                        else:
                            self.debug_print(f"Unexpected pixel value type at [{row_idx},{col_idx}]: {type(pixel_value)}")
                            # Fallback to middle character
                            middle_idx = len(self.chars) // 2
                            ascii_row.append(self.chars[middle_idx])

                    except Exception as e:
                        self.debug_print(f"Error processing pixel at [{row_idx},{col_idx}]: {e}")
                        self.debug_print(f"Pixel value: {pixel_value}, type: {type(pixel_value)}")
                        # Use a fallback character (space)
                        ascii_row.append(' ')

                ascii_image.append(ascii_row)

            self.debug_print(f"ASCII conversion complete: {len(ascii_image)} rows, {len(ascii_image[0]) if ascii_image else 0} columns")
            return ascii_image

        except Exception as e:
            self.debug_print(f"Error in pixel mapping: {e}")
            traceback.print_exc()
            raise

    def _map_pixels_to_ascii_profiled(self, image):
        """Map each output character by nearest-matching a glyph shape profile.

        Downsamples every GRID_ROWS x GRID_COLS block of the (already
        oversized, see _preprocess_image) source image to the same grid
        shape the glyph profiles use, then picks whichever glyph's profile
        is closest by squared distance. See glyph_profiles.py.
        """
        try:
            pixels = np.array(image, dtype=np.float64)
            out_height = pixels.shape[0] // GRID_ROWS
            out_width = pixels.shape[1] // GRID_COLS
            self.debug_print(
                f"Profiled mapping: {out_width}x{out_height} characters, "
                f"{GRID_COLS}x{GRID_ROWS} grid each, pool size {len(NARROW_GLYPHS)}"
            )

            profiles = build_glyph_profiles(NARROW_GLYPHS)
            chars = list(profiles.keys())
            profile_matrix = np.stack([profiles[c].ravel() for c in chars])

            ink = 1.0 - (pixels / 255.0)

            ascii_image = []
            matched_subcells = 0
            total_subcells = 0
            for row_idx in range(out_height):
                ascii_row = []
                r0 = row_idx * GRID_ROWS
                for col_idx in range(out_width):
                    c0 = col_idx * GRID_COLS
                    block = ink[r0:r0 + GRID_ROWS, c0:c0 + GRID_COLS].ravel()
                    distances = np.sum((profile_matrix - block) ** 2, axis=1)
                    best = int(np.argmin(distances))
                    ascii_row.append(chars[best])

                    # Accuracy: how many of this cell's sub-cell rectangles
                    # ended up within tolerance of the glyph we actually
                    # picked -- see SUBCELL_MATCH_TOLERANCE.
                    diff = np.abs(profile_matrix[best] - block)
                    matched_subcells += int(np.count_nonzero(diff <= self.SUBCELL_MATCH_TOLERANCE))
                    total_subcells += diff.size
                ascii_image.append(ascii_row)

            self.last_accuracy = 100.0 * matched_subcells / total_subcells if total_subcells else 0.0
            self.last_accuracy_detail = (matched_subcells, total_subcells)
            self.debug_print(
                f"Profiled ASCII conversion complete: {len(ascii_image)} rows, "
                f"accuracy {self.last_accuracy:.2f}% ({matched_subcells}/{total_subcells} sub-cells within tolerance {self.SUBCELL_MATCH_TOLERANCE})"
            )
            return ascii_image

        except Exception as e:
            self.debug_print(f"Error in profiled pixel mapping: {e}")
            traceback.print_exc()
            raise

    def optimize_brightness(self, image, low=0.3, high=3.0, coarse_steps=13, fine_steps=9):
        """Search for the brightness multiplier that maximizes shape-aware accuracy.

        Coarse-to-fine grid search rather than a gradient-free method like
        golden-section search: accuracy as a function of brightness isn't
        guaranteed unimodal (discrete character assignment can introduce
        small local bumps as the winning glyph flips), so a plain grid is
        more robust to that, for a similar total evaluation count.

        Expensive: each candidate brightness re-runs the full preprocessing
        + shape-aware matching pipeline over the whole image (that's
        `coarse_steps + fine_steps` full conversions, ~22 by default). Sets
        self.brightness to the best value found and returns
        (best_brightness, best_accuracy). Requires shape_aware=True, since
        accuracy is only defined for that path.
        """
        if not self.shape_aware:
            raise ValueError("optimize_brightness requires shape_aware=True (accuracy is only defined for shape-aware matching)")

        def evaluate(brightness):
            self.brightness = brightness
            processed = self._preprocess_image(image.copy())
            self._map_pixels_to_ascii_profiled(processed)
            return self.last_accuracy

        coarse_candidates = np.linspace(low, high, coarse_steps)
        results = [(b, evaluate(b)) for b in coarse_candidates]
        best_b, best_acc = max(results, key=lambda r: r[1])
        self.debug_print(f"optimize_brightness coarse pass: best={best_b:.3f} accuracy={best_acc:.2f}%")

        idx = int(np.argmin(np.abs(coarse_candidates - best_b)))
        lo = coarse_candidates[max(idx - 1, 0)]
        hi = coarse_candidates[min(idx + 1, len(coarse_candidates) - 1)]
        fine_candidates = np.linspace(lo, hi, fine_steps)
        results += [(b, evaluate(b)) for b in fine_candidates]
        best_b, best_acc = max(results, key=lambda r: r[1])
        self.debug_print(f"optimize_brightness fine pass: best={best_b:.3f} accuracy={best_acc:.2f}%")

        self.brightness = best_b
        return best_b, best_acc

    def optimize_for_diversity(self, image, low=0.3, high=3.0, coarse_steps=13, fine_steps=9):
        """Search for the brightness multiplier that maximizes output glyph diversity.

        Unlike accuracy (see optimize_brightness's docstring for why that
        objective is a dead end -- either gameable or trivially maximized by
        doing nothing), diversity has a genuine interior optimum: too dark
        and nearly every cell collapses onto whichever few glyphs are
        closest to the unreachable-dark end; too bright and cells collapse
        toward blank/near-blank glyphs. A good middle ground spreads usage
        across many glyphs instead. Same coarse-to-fine grid search
        structure as optimize_brightness; same cost profile. Returns
        (best_brightness, best_diversity_pct).
        """
        if not self.shape_aware:
            raise ValueError("optimize_for_diversity requires shape_aware=True (accuracy/diversity are only tracked for shape-aware matching)")

        def evaluate(brightness):
            self.brightness = brightness
            processed = self._preprocess_image(image.copy())
            ascii_image = self._map_pixels_to_ascii_profiled(processed)
            self._finalize_ascii_image(ascii_image)
            return self.last_diversity_pct

        coarse_candidates = np.linspace(low, high, coarse_steps)
        results = [(b, evaluate(b)) for b in coarse_candidates]
        best_b, best_div = max(results, key=lambda r: r[1])
        self.debug_print(f"optimize_for_diversity coarse pass: best={best_b:.3f} diversity={best_div:.2f}%")

        idx = int(np.argmin(np.abs(coarse_candidates - best_b)))
        lo = coarse_candidates[max(idx - 1, 0)]
        hi = coarse_candidates[min(idx + 1, len(coarse_candidates) - 1)]
        fine_candidates = np.linspace(lo, hi, fine_steps)
        results += [(b, evaluate(b)) for b in fine_candidates]
        best_b, best_div = max(results, key=lambda r: r[1])
        self.debug_print(f"optimize_for_diversity fine pass: best={best_b:.3f} diversity={best_div:.2f}%")

        self.brightness = best_b
        return best_b, best_div

    def optimize_gamma_for_diversity(self, image, low=0.05, high=3.0, coarse_steps=13, fine_steps=9):
        """Search for the gamma value that maximizes output glyph diversity.

        Same objective as optimize_for_diversity(), but searches the gamma
        curve (apply_gamma()) instead of a flat brightness multiplier. A
        curve reshapes shadows vs. highlights unevenly, which empirically
        reaches a higher diversity peak than any single brightness value can
        (~54% vs. ~48% on the reference photo -- see TODO.md and
        experiments/). Confirmed to have a genuine interior optimum (around
        gamma~0.17 on that photo) rather than running away to a degenerate
        boundary. Same coarse-to-fine grid search structure and cost profile
        as optimize_for_diversity. Returns (best_gamma, best_diversity_pct).
        """
        if not self.shape_aware:
            raise ValueError("optimize_gamma_for_diversity requires shape_aware=True (accuracy/diversity are only tracked for shape-aware matching)")

        def evaluate(gamma):
            self.gamma = gamma
            processed = self._preprocess_image(image.copy())
            ascii_image = self._map_pixels_to_ascii_profiled(processed)
            self._finalize_ascii_image(ascii_image)
            return self.last_diversity_pct

        coarse_candidates = np.linspace(low, high, coarse_steps)
        results = [(g, evaluate(g)) for g in coarse_candidates]
        best_g, best_div = max(results, key=lambda r: r[1])
        self.debug_print(f"optimize_gamma_for_diversity coarse pass: best={best_g:.3f} diversity={best_div:.2f}%")

        idx = int(np.argmin(np.abs(coarse_candidates - best_g)))
        lo = coarse_candidates[max(idx - 1, 0)]
        hi = coarse_candidates[min(idx + 1, len(coarse_candidates) - 1)]
        fine_candidates = np.linspace(lo, hi, fine_steps)
        results += [(g, evaluate(g)) for g in fine_candidates]
        best_g, best_div = max(results, key=lambda r: r[1])
        self.debug_print(f"optimize_gamma_for_diversity fine pass: best={best_g:.3f} diversity={best_div:.2f}%")

        self.gamma = best_g
        return best_g, best_div

    def _compute_diversity(self, ascii_image, pool_size):
        """Count distinct glyphs used and their usage evenness.

        Returns (unique_count, normalized_entropy_pct). Normalized entropy
        is Shannon entropy of the glyph-usage frequency distribution divided
        by log2(pool_size) -- 100% would mean every glyph in the available
        pool was used equally often; a single repeated glyph is 0%.
        """
        flat = [char for row in ascii_image for char in row]
        counts = Counter(flat)
        total = len(flat)
        unique_count = len(counts)
        if total == 0 or pool_size <= 1:
            return unique_count, 0.0
        probs = np.array(list(counts.values()), dtype=np.float64) / total
        entropy = -np.sum(probs * np.log2(probs))
        max_entropy = np.log2(pool_size)
        return unique_count, 100.0 * entropy / max_entropy

    def _finalize_ascii_image(self, ascii_image):
        """Compute diversity stats and join the character grid into the final string."""
        pool_size = len(NARROW_GLYPHS) if self.shape_aware else len(self.chars)
        self.last_diversity_unique_count, self.last_diversity_pct = self._compute_diversity(ascii_image, pool_size)
        return '\n'.join([''.join(row) for row in ascii_image])

    def convert_image(self, input_path):
        """Convert an image file to ASCII art with error handling."""
        try:
            # Check if file exists
            if not os.path.exists(input_path):
                self.debug_print(f"Input file not found: {input_path}")
                raise FileNotFoundError(f"Input file not found: {input_path}")

            # Open the image
            try:
                self.debug_print(f"Opening image: {input_path}")
                image = Image.open(input_path)
                self.debug_print(f"Image opened: {image.format}, {image.size}, {image.mode}")
            except Exception as e:
                self.debug_print(f"Error opening image: {e}")
                raise ValueError(f"Could not open file as image: {e}")

            # Preprocess the image
            processed_image = self._preprocess_image(image)

            # Convert to ASCII
            if self.shape_aware:
                ascii_image = self._map_pixels_to_ascii_profiled(processed_image)
            else:
                ascii_image = self._map_pixels_to_ascii(processed_image)

            # Join the characters into a string
            self.debug_print("Joining ASCII characters into final string")
            ascii_art = self._finalize_ascii_image(ascii_image)

            return ascii_art

        except Exception as e:
            self.debug_print(f"Error converting image: {e}")
            traceback.print_exc()
            raise

    def direct_convert(self, image):
        """Convert a PIL image directly to ASCII art with error handling."""
        try:
            self.debug_print(f"Direct converting PIL image: {image.size}, {image.mode}")

            # Preprocess the image
            processed_image = self._preprocess_image(image)

            # Convert to ASCII
            if self.shape_aware:
                ascii_image = self._map_pixels_to_ascii_profiled(processed_image)
            else:
                ascii_image = self._map_pixels_to_ascii(processed_image)

            # Join the characters into a string
            ascii_art = self._finalize_ascii_image(ascii_image)

            return ascii_art

        except Exception as e:
            self.debug_print(f"Error in direct conversion: {e}")
            traceback.print_exc()
            raise

    def save_to_file(self, ascii_art, output_path):
        """Save the ASCII art to a file."""
        try:
            self.debug_print(f"Saving ASCII art to {output_path}")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(ascii_art)
            self.debug_print("ASCII art saved successfully")
            return True
        except Exception as e:
            self.debug_print(f"Error saving ASCII art to file: {e}")
            traceback.print_exc()
            return False

    @staticmethod
    def preview(ascii_art):
        """Print the ASCII art to the console."""
        print(ascii_art)


def main():
    """Main function to run the ASCII art generator from command line."""
    parser = argparse.ArgumentParser(description='Convert images to ASCII art')

    # Required argument
    parser.add_argument('input', help='Input image file path')

    # Optional arguments
    parser.add_argument('-o', '--output', help='Output file path (default: ascii_art.txt)', default='ascii_art.txt')
    parser.add_argument('-w', '--width', type=int, help='Width of ASCII art in characters (default: 100)', default=100)
    parser.add_argument('-H', '--height', type=int, help='Height of ASCII art in characters (auto if not specified)')
    parser.add_argument('-c', '--char-set', choices=['basic', 'standard', 'blocks', 'custom'],
                       help='Character set to use (default: standard)', default='standard')
    parser.add_argument('--contrast', type=float, help='Contrast adjustment (default: 1.0)', default=1.0)
    parser.add_argument('--brightness', type=float, help='Brightness adjustment (default: 1.0)', default=1.0)
    parser.add_argument('--gamma', type=float, help='Gamma curve, applied after brightness (default: 1.0, no-op; <1 lifts shadows)', default=1.0)
    parser.add_argument('--invert', action='store_true', help='Invert the image')
    parser.add_argument('--dither', action='store_true', help='Apply dithering for better detail')
    parser.add_argument('--shape-aware', action='store_true',
                       help='Match characters by sub-cell glyph shape profile instead of average brightness (narrow glyph pool only, experimental)')
    parser.add_argument('--ink-ceiling', choices=['none', 'glyph-avg', 'subcell'], default='none',
                       help="Raise the image's black point to what the glyph pool can actually render: "
                            "'glyph-avg' targets the darkest glyph's overall average ink, 'subcell' targets "
                            "the darkest single sub-cell rectangle (experimental, see TODO.md)")
    parser.add_argument('--optimize-brightness', action='store_true',
                       help='Search for the brightness value that maximizes shape-aware match accuracy -- '
                            'NOTE: this objective is a known dead end (see TODO.md), kept for reference/comparison '
                            '(requires --shape-aware; expensive -- re-runs the full pipeline ~22 times)')
    parser.add_argument('--optimize-diversity', action='store_true',
                       help='Search for the brightness value that maximizes output glyph diversity -- has a '
                            'genuine interior optimum, unlike --optimize-brightness '
                            '(requires --shape-aware; expensive -- re-runs the full pipeline ~22 times)')
    parser.add_argument('--optimize-gamma-diversity', action='store_true',
                       help='Search for the gamma curve that maximizes output glyph diversity -- reshapes '
                            'shadows/highlights unevenly instead of shifting everything uniformly, reaching a '
                            'higher diversity peak than --optimize-diversity on the reference photo '
                            '(requires --shape-aware; expensive -- re-runs the full pipeline ~22 times)')
    parser.add_argument('--preview', action='store_true', help='Preview the ASCII art in console')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')

    args = parser.parse_args()

    ink_ceiling = None
    if args.ink_ceiling == 'glyph-avg':
        ink_ceiling = darkest_avg_ink()
    elif args.ink_ceiling == 'subcell':
        ink_ceiling = darkest_subcell_ink()

    optimize_flags = [args.optimize_brightness, args.optimize_diversity, args.optimize_gamma_diversity]
    if any(optimize_flags) and not args.shape_aware:
        parser.error("--optimize-brightness/--optimize-diversity/--optimize-gamma-diversity require --shape-aware")
    if sum(optimize_flags) > 1:
        parser.error("--optimize-brightness, --optimize-diversity, and --optimize-gamma-diversity are mutually exclusive")

    try:
        # Create generator with specified parameters
        generator = ASCIIArtGenerator(
            char_set=args.char_set,
            width=args.width,
            height=args.height,
            contrast=args.contrast,
            brightness=args.brightness,
            gamma=args.gamma,
            invert=args.invert,
            dither=args.dither,
            debug=args.debug,
            shape_aware=args.shape_aware,
            ink_ceiling=ink_ceiling
        )

        # Search for the best brightness/gamma before the real conversion, if requested
        if args.optimize_brightness:
            best_brightness, best_accuracy = generator.optimize_brightness(Image.open(args.input))
            print(f"Optimized brightness: {best_brightness:.3f} (accuracy {best_accuracy:.2f}%)")
        elif args.optimize_diversity:
            best_brightness, best_diversity = generator.optimize_for_diversity(Image.open(args.input))
            print(f"Optimized brightness: {best_brightness:.3f} (diversity {best_diversity:.2f}%)")
        elif args.optimize_gamma_diversity:
            best_gamma, best_diversity = generator.optimize_gamma_for_diversity(Image.open(args.input))
            print(f"Optimized gamma: {best_gamma:.3f} (diversity {best_diversity:.2f}%)")

        # Convert image to ASCII
        ascii_art = generator.convert_image(args.input)

        # Save to file
        if generator.save_to_file(ascii_art, args.output):
            print(f"ASCII art saved to {args.output}")

        # Shape-aware runs always report their match accuracy, headless or not
        if generator.last_accuracy is not None:
            matched, total = generator.last_accuracy_detail
            print(f"Accuracy: {generator.last_accuracy:.2f}% ({matched}/{total} sub-cells within tolerance {ASCIIArtGenerator.SUBCELL_MATCH_TOLERANCE})")

        # Diversity is tracked for both modes, and always reported
        if generator.last_diversity_pct is not None:
            print(f"Diversity: {generator.last_diversity_pct:.2f}% ({generator.last_diversity_unique_count} distinct glyphs used)")

        # Preview if requested
        if args.preview:
            print("\nPreview:")
            generator.preview(ascii_art)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
