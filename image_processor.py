import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import cv2
import traceback
import sys

from ascii_art_generator import ASCIIArtGenerator

class ImageProcessor:
    """
    Advanced image processing class with debugging capabilities.
    """

    def __init__(self):
        """Initialize the image processor with default settings."""
        self.image = None
        self.original = None
        self.debug_mode = True  # Enable debug output

    def debug_print(self, message):
        """Print debug messages if debug mode is enabled."""
        if self.debug_mode:
            print(f"DEBUG [ImageProcessor]: {message}")

    def load(self, image_path):
        """Load an image from file with error tracing."""
        try:
            self.debug_print(f"Loading image from {image_path}")
            self.image = Image.open(image_path)
            self.original = self.image.copy()
            self.debug_print(f"Image loaded successfully: {self.image.format}, {self.image.size}, {self.image.mode}")
            return self
        except FileNotFoundError:
            self.debug_print(f"File not found: {image_path}")
            raise FileNotFoundError(f"Image file not found: {image_path}")
        except Exception as e:
            self.debug_print(f"Error loading image: {e}")
            traceback.print_exc()
            raise ValueError(f"Could not open file as image: {e}")

    def from_pil_image(self, pil_image):
        """Use an existing PIL image."""
        try:
            self.debug_print(f"Creating from PIL image: {pil_image.size}, {pil_image.mode}")
            self.image = pil_image.copy()
            self.original = pil_image.copy()
            return self
        except Exception as e:
            self.debug_print(f"Error creating from PIL image: {e}")
            traceback.print_exc()
            raise

    def reset(self):
        """Reset to the original image."""
        try:
            self.debug_print("Resetting to original image")
            if self.original:
                self.image = self.original.copy()
            else:
                self.debug_print("Warning: No original image to reset to")
            return self
        except Exception as e:
            self.debug_print(f"Error resetting image: {e}")
            traceback.print_exc()
            raise

    def resize(self, width, height=None, method=Image.LANCZOS):
        """Resize the image."""
        try:
            if height is None:
                height = ASCIIArtGenerator.calculate_auto_height(width, self.image)

            self.debug_print(f"Resizing image from {self.image.size} to ({width}, {height})")
            self.image = self.image.resize((width, height), method)
            self.debug_print(f"Resized image: {self.image.size}, {self.image.mode}")
            return self
        except Exception as e:
            self.debug_print(f"Error resizing image: {e}")
            traceback.print_exc()
            raise

    def to_grayscale(self):
        """Convert the image to grayscale."""
        try:
            self.debug_print(f"Converting image from {self.image.mode} to grayscale")
            self.image = self.image.convert("L")
            self.debug_print(f"Converted to grayscale: {self.image.mode}")
            return self
        except Exception as e:
            self.debug_print(f"Error converting to grayscale: {e}")
            traceback.print_exc()
            raise

    def adjust_contrast(self, factor=1.5):
        """Adjust the image contrast."""
        try:
            self.debug_print(f"Adjusting contrast with factor {factor}")
            self.image = ASCIIArtGenerator.apply_contrast(self.image, factor)
            return self
        except Exception as e:
            self.debug_print(f"Error adjusting contrast: {e}")
            traceback.print_exc()
            raise

    def adjust_brightness(self, factor=1.2):
        """Adjust the image brightness."""
        try:
            self.debug_print(f"Adjusting brightness with factor {factor}")
            self.image = ASCIIArtGenerator.apply_brightness(self.image, factor)
            return self
        except Exception as e:
            self.debug_print(f"Error adjusting brightness: {e}")
            traceback.print_exc()
            raise

    def adjust_sharpness(self, factor=1.5):
        """Adjust the image sharpness."""
        try:
            self.debug_print(f"Adjusting sharpness with factor {factor}")
            enhancer = ImageEnhance.Sharpness(self.image)
            self.image = enhancer.enhance(factor)
            return self
        except Exception as e:
            self.debug_print(f"Error adjusting sharpness: {e}")
            traceback.print_exc()
            raise

    def invert(self):
        """Invert the image colors."""
        try:
            self.debug_print("Inverting image colors")
            self.image = ASCIIArtGenerator.apply_invert(self.image)
            return self
        except Exception as e:
            self.debug_print(f"Error inverting image: {e}")
            traceback.print_exc()
            raise

    def apply_dithering(self):
        """Apply Floyd-Steinberg dithering."""
        try:
            self.debug_print("Applying dithering")
            self.image = ASCIIArtGenerator.apply_dither(self.image)
            return self
        except Exception as e:
            self.debug_print(f"Error applying dithering: {e}")
            traceback.print_exc()
            raise

    def detect_edges(self, mode="standard"):
        """Apply edge detection to emphasize outlines."""
        try:
            self.debug_print(f"Detecting edges with mode: {mode}")

            # Make sure image is in grayscale mode for edge detection
            if self.image.mode != 'L':
                self.debug_print(f"Converting image from {self.image.mode} to grayscale for edge detection")
                self.image = self.image.convert('L')

            if mode == "standard":
                # PIL's built-in edge filter
                self.debug_print("Using PIL FIND_EDGES filter")
                self.image = self.image.filter(ImageFilter.FIND_EDGES)

            elif mode == "sobel" or mode == "canny":
                # Convert PIL image to OpenCV format
                self.debug_print("Converting PIL image to numpy array")
                img_array = np.array(self.image)
                self.debug_print(f"Array shape: {img_array.shape}, dtype: {img_array.dtype}")

                # Ensure the array has the right type
                img_array = img_array.astype(np.uint8)

                if mode == "sobel":
                    self.debug_print("Applying Sobel edge detection")
                    # Apply Sobel edge detection
                    sobelx = cv2.Sobel(img_array, cv2.CV_64F, 1, 0, ksize=3)
                    sobely = cv2.Sobel(img_array, cv2.CV_64F, 0, 1, ksize=3)

                    # Compute magnitude of gradient
                    self.debug_print("Computing gradient magnitude")
                    # Use np.hypot for safer computation
                    magnitude = np.hypot(sobelx, sobely)

                    # Scale to 0-255 and convert to uint8
                    self.debug_print("Scaling magnitude to 0-255")
                    magnitude = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

                    # Convert back to PIL
                    self.debug_print(f"Converting back to PIL image, array shape: {magnitude.shape}, dtype: {magnitude.dtype}")
                    self.image = Image.fromarray(magnitude)

                else:  # Canny
                    self.debug_print("Applying Canny edge detection")
                    try:
                        edges = cv2.Canny(img_array, 100, 200)
                        self.debug_print(f"Canny output shape: {edges.shape}, dtype: {edges.dtype}")
                        # Convert back to PIL
                        self.image = Image.fromarray(edges)
                    except Exception as e:
                        self.debug_print(f"Error in Canny edge detection: {e}")
                        # Fallback to standard edge detection
                        self.debug_print("Falling back to standard edge detection")
                        self.image = self.image.filter(ImageFilter.FIND_EDGES)

            self.debug_print("Edge detection completed")
            return self

        except Exception as e:
            self.debug_print(f"Error detecting edges: {e}")
            traceback.print_exc()
            # Try to recover by falling back to the original image
            self.debug_print("Falling back to original image due to error")
            if self.original:
                self.image = self.original.copy()
            raise

    def apply_histogram_equalization(self):
        """Apply histogram equalization."""
        try:
            self.debug_print("Applying histogram equalization")

            # Ensure image is grayscale
            if self.image.mode != 'L':
                self.debug_print(f"Converting image from {self.image.mode} to grayscale")
                self.image = self.image.convert('L')

            # Convert to numpy array
            img_array = np.array(self.image)
            self.debug_print(f"Array shape: {img_array.shape}, dtype: {img_array.dtype}")

            # Ensure the array has the right type
            img_array = img_array.astype(np.uint8)

            # Apply equalization
            self.debug_print("Applying equalizeHist")
            img_array = cv2.equalizeHist(img_array)

            # Convert back to PIL
            self.debug_print("Converting back to PIL image")
            self.image = Image.fromarray(img_array)
            return self
        except Exception as e:
            self.debug_print(f"Error applying histogram equalization: {e}")
            traceback.print_exc()
            raise

    def apply_unsharp_mask(self, radius=2, amount=1.5):
        """Apply unsharp mask filter."""
        try:
            self.debug_print(f"Applying unsharp mask with radius={radius}, amount={amount}")
            percent = amount * 100
            self.debug_print(f"Using percent={percent}")
            self.image = self.image.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent))
            return self
        except Exception as e:
            self.debug_print(f"Error applying unsharp mask: {e}")
            traceback.print_exc()
            raise

    def apply_adaptive_thresholding(self, block_size=11, c=2):
        """Apply adaptive thresholding."""
        try:
            self.debug_print(f"Applying adaptive thresholding with block_size={block_size}, c={c}")

            # Ensure grayscale
            if self.image.mode != 'L':
                self.debug_print(f"Converting image from {self.image.mode} to grayscale")
                self.image = self.image.convert('L')

            # Convert to OpenCV format
            img_array = np.array(self.image)
            self.debug_print(f"Array shape: {img_array.shape}, dtype: {img_array.dtype}")

            # Ensure the array has the right type
            img_array = img_array.astype(np.uint8)

            # Ensure block_size is odd
            if block_size % 2 == 0:
                block_size += 1
                self.debug_print(f"Adjusted block_size to {block_size} to ensure it's odd")

            # Apply adaptive thresholding
            self.debug_print("Applying adaptiveThreshold")
            try:
                result = cv2.adaptiveThreshold(
                    img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, block_size, c
                )
                self.debug_print(f"Thresholding result shape: {result.shape}, dtype: {result.dtype}")

                # Convert back to PIL
                self.debug_print("Converting back to PIL image")
                self.image = Image.fromarray(result)
            except Exception as e:
                self.debug_print(f"Error in adaptiveThreshold: {e}")
                raise

            return self
        except Exception as e:
            self.debug_print(f"Error applying adaptive thresholding: {e}")
            traceback.print_exc()
            raise

    def get_processed_image(self):
        """Get the processed image."""
        try:
            self.debug_print(f"Returning processed image: {self.image.size}, {self.image.mode}")
            return self.image.copy()
        except Exception as e:
            self.debug_print(f"Error getting processed image: {e}")
            traceback.print_exc()
            raise

    def save(self, output_path):
        """Save the processed image to file."""
        try:
            self.debug_print(f"Saving image to {output_path}")
            self.image.save(output_path)
            self.debug_print("Image saved successfully")
            return True
        except Exception as e:
            self.debug_print(f"Error saving image: {e}")
            traceback.print_exc()
            return False
