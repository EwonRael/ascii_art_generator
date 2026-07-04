import argparse
import os
import sys
from PIL import Image, ImageOps, ImageEnhance
import numpy as np
import traceback

from glyph_profiles import build_glyph_profiles, GRID_COLS, GRID_ROWS
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
                contrast=1.0, brightness=1.0, invert=False, dither=False,
                debug=True, shape_aware=False):
        """Initialize the ASCII Art generator with debugging capabilities."""
        self.width = width
        self.height = height
        self.contrast = contrast
        self.brightness = brightness
        self.invert = invert
        self.dither = dither
        self.debug_mode = debug
        # When True, characters are chosen by matching a sub-cell glyph
        # shape profile instead of averaging the cell to one brightness
        # value -- see glyph_profiles.py and TODO.md items 2/3. Currently
        # always matches against the narrow (95-char) glyph pool.
        self.shape_aware = shape_aware

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
    def apply_invert(image):
        """Invert image tones."""
        return ImageOps.invert(image)

    @staticmethod
    def apply_dither(image):
        """Apply Floyd-Steinberg dithering, returning a grayscale image."""
        image = image.convert('1', dither=Image.FLOYDSTEINBERG)
        return image.convert('L')

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

            # Invert if requested
            if self.invert:
                self.debug_print("Inverting image colors")
                image = self.apply_invert(image)

            # Apply dithering if requested
            if self.dither:
                self.debug_print("Applying dithering")
                image = self.apply_dither(image)

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
            for row_idx in range(out_height):
                ascii_row = []
                r0 = row_idx * GRID_ROWS
                for col_idx in range(out_width):
                    c0 = col_idx * GRID_COLS
                    block = ink[r0:r0 + GRID_ROWS, c0:c0 + GRID_COLS].ravel()
                    distances = np.sum((profile_matrix - block) ** 2, axis=1)
                    ascii_row.append(chars[int(np.argmin(distances))])
                ascii_image.append(ascii_row)

            self.debug_print(f"Profiled ASCII conversion complete: {len(ascii_image)} rows")
            return ascii_image

        except Exception as e:
            self.debug_print(f"Error in profiled pixel mapping: {e}")
            traceback.print_exc()
            raise

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
            ascii_art = '\n'.join([''.join(row) for row in ascii_image])

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
            ascii_art = '\n'.join([''.join(row) for row in ascii_image])

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
    parser.add_argument('--invert', action='store_true', help='Invert the image')
    parser.add_argument('--dither', action='store_true', help='Apply dithering for better detail')
    parser.add_argument('--shape-aware', action='store_true',
                       help='Match characters by sub-cell glyph shape profile instead of average brightness (narrow glyph pool only, experimental)')
    parser.add_argument('--preview', action='store_true', help='Preview the ASCII art in console')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')

    args = parser.parse_args()

    try:
        # Create generator with specified parameters
        generator = ASCIIArtGenerator(
            char_set=args.char_set,
            width=args.width,
            height=args.height,
            contrast=args.contrast,
            brightness=args.brightness,
            invert=args.invert,
            dither=args.dither,
            debug=args.debug,
            shape_aware=args.shape_aware
        )

        # Convert image to ASCII
        ascii_art = generator.convert_image(args.input)

        # Save to file
        if generator.save_to_file(ascii_art, args.output):
            print(f"ASCII art saved to {args.output}")

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
