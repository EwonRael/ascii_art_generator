"""
ASCII Art Generator -- Tkinter GUI Application.

Provides ASCIIArtApp, a full-featured GUI for converting images to ASCII art.
Settings panel logic is delegated to gui_settings module.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk

from ascii_art_generator import ASCIIArtGenerator
from image_processor import ImageProcessor
import gui_settings


class ASCIIArtApp(tk.Tk):
    """
    GUI application for the ASCII Art Generator.

    Provides a user-friendly interface for loading images, customizing
    conversion parameters, previewing results, and saving ASCII art.
    """

    def __init__(self):
        """Initialize the application."""
        super().__init__()

        self.title("ASCII Art Generator")
        self.geometry("1200x800")
        self.minsize(800, 600)

        # Internal state
        self.input_image_path = None
        self.output_path = None
        self.ascii_result = None
        self.processor = ImageProcessor()
        self.current_preview = None

        # Build UI
        self._create_menu()
        self._create_main_layout()
        self._setup_bindings()
        self._set_default_values()

        # Style
        self.style = ttk.Style()
        self.style.configure("TButton", padding=6)
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0")

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready. Load an image to begin.")
        self.status_bar = ttk.Label(self, textvariable=self.status_var,
                                    relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _create_menu(self):
        """Create the application menu."""
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Image", command=self._load_image)
        file_menu.add_command(label="Save ASCII Art", command=self._save_ascii_art)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Instructions", command=self._show_instructions)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _create_main_layout(self):
        """Create the main application layout."""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        settings_frame = ttk.LabelFrame(main_frame, text="Settings")
        settings_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)

        preview_frame = ttk.LabelFrame(main_frame, text="Preview")
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        gui_settings.create_settings_panel(self, settings_frame)
        self._create_preview_panel(preview_frame)

    def _create_preview_panel(self, parent):
        """Create the preview panel with tabs for original image and ASCII result."""
        self.preview_notebook = ttk.Notebook(parent)
        self.preview_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.original_frame = ttk.Frame(self.preview_notebook)
        self.preview_notebook.add(self.original_frame, text="Original Image")

        self.ascii_frame = ttk.Frame(self.preview_notebook)
        self.preview_notebook.add(self.ascii_frame, text="ASCII Result")

        self.image_canvas = tk.Canvas(self.original_frame, bg="white")
        self.image_canvas.pack(fill=tk.BOTH, expand=True)

        self.ascii_text = scrolledtext.ScrolledText(self.ascii_frame, wrap=tk.NONE)
        self.ascii_text.pack(fill=tk.BOTH, expand=True)
        self.ascii_text.config(font=('Courier', 10))

    # ------------------------------------------------------------------
    # Bindings and defaults
    # ------------------------------------------------------------------

    def _setup_bindings(self):
        """Set up event bindings."""
        self.width_var.trace_add("write", lambda *a: gui_settings.update_auto_height(self))
        self.enhance_edges_var.trace_add("write", lambda *a: gui_settings.toggle_edge_mode(self))
        self.char_set_var.trace_add("write", lambda *a: gui_settings.update_custom_chars(self))
        self.unsharp_mask_var.trace_add("write", lambda *a: gui_settings.toggle_unsharp_params(self))
        self.adaptive_thresh_var.trace_add("write", lambda *a: gui_settings.toggle_thresh_params(self))

    def _set_default_values(self):
        """Set default values for all settings."""
        gui_settings.set_default_values(self)

    # ------------------------------------------------------------------
    # Image loading
    # ------------------------------------------------------------------

    def _load_image(self):
        """Load an image from file."""
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff"),
                ("All files", "*.*"),
            ],
        )
        if file_path:
            try:
                self.input_image_path = file_path
                self.file_path_var.set(file_path)
                self._display_original_image(file_path)
                gui_settings.update_auto_height(self)
                self.status_var.set(f"Image loaded: {os.path.basename(file_path)}")
                self.preview_notebook.select(0)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")
                self.status_var.set("Error loading image.")

    def _display_original_image(self, file_path):
        """Display the original image in the canvas."""
        try:
            self.image_canvas.delete("all")
            image = Image.open(file_path)
            self.image_canvas.update()

            canvas_width = self.image_canvas.winfo_width()
            canvas_height = self.image_canvas.winfo_height()
            img_width, img_height = image.size

            scale_width = canvas_width / img_width if img_width > canvas_width else 1
            scale_height = canvas_height / img_height if img_height > canvas_height else 1
            scale = min(scale_width, scale_height)

            if scale < 1:
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                image = image.resize((new_width, new_height), Image.LANCZOS)

            self.current_preview = ImageTk.PhotoImage(image)
            self.image_canvas.create_image(
                canvas_width // 2, canvas_height // 2,
                image=self.current_preview, anchor=tk.CENTER,
            )
        except Exception as e:
            print(f"Error displaying image: {e}")
            self.image_canvas.create_text(
                self.image_canvas.winfo_width() // 2,
                self.image_canvas.winfo_height() // 2,
                text=f"Error displaying image: {e}", fill="red",
            )

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    # Busy-cursor names to try, in order. "wait" only exists on Windows;
    # X11/Tk uses "watch" for the hourglass-style cursor, and "spinning"
    # is a further fallback seen on some Tk builds.
    _BUSY_CURSORS = ("watch", "wait", "spinning")

    def _set_busy_cursor(self, busy):
        """Set (or clear) a busy cursor without crashing on unsupported names."""
        if not busy:
            self.config(cursor="")
            return
        for name in self._BUSY_CURSORS:
            try:
                self.config(cursor=name)
                return
            except tk.TclError:
                continue

    def _generate_preview(self):
        """Generate a preview of the ASCII art with reduced settings."""
        if not self.input_image_path:
            messagebox.showwarning("Warning", "No image loaded. Please load an image first.")
            return

        preview_width = min(80, self.width_var.get())
        if self.auto_height_var.get():
            with Image.open(self.input_image_path) as img:
                preview_height = ASCIIArtGenerator.calculate_auto_height(preview_width, img)
        else:
            preview_height = min(40, self.height_var.get())

        try:
            self._set_busy_cursor(True)
            self.update()
            self._generate_ascii_art(preview_width, preview_height)
            self.preview_notebook.select(1)
            self.status_var.set(f"Preview generated ({preview_width}x{preview_height} characters).")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate preview: {e}")
            self.status_var.set("Error generating preview.")
        finally:
            self._set_busy_cursor(False)

    def _generate_full(self):
        """Generate full ASCII art with all settings."""
        if not self.input_image_path:
            messagebox.showwarning("Warning", "No image loaded. Please load an image first.")
            return
        try:
            self._set_busy_cursor(True)
            self.update()
            threading.Thread(target=self._threaded_generation, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start generation: {e}")
            self.status_var.set("Error starting generation.")
            self._set_busy_cursor(False)

    def _threaded_generation(self):
        """Generate ASCII art in a separate thread to keep UI responsive."""
        try:
            width = self.width_var.get()
            height = None if self.auto_height_var.get() else self.height_var.get()
            self._generate_ascii_art(width, height)
            self.after(0, self._update_ui_after_generation)
        except Exception as e:
            self.after(0, lambda: self._show_generation_error(str(e)))

    def _update_ui_after_generation(self):
        """Update UI after successful generation."""
        self.preview_notebook.select(1)
        self.status_var.set("ASCII art generated successfully.")
        self._set_busy_cursor(False)

    def _show_generation_error(self, error_msg):
        """Show error message after failed generation."""
        messagebox.showerror("Generation Error", f"Failed to generate ASCII art: {error_msg}")
        self.status_var.set("Error generating ASCII art.")
        self._set_busy_cursor(False)

    def _generate_ascii_art(self, width, height):
        """Generate ASCII art with the specified dimensions."""
        if not self.input_image_path:
            raise ValueError("No image loaded")

        self.processor = ImageProcessor()
        self.processor.load(self.input_image_path)
        self.processor.resize(width, height)

        if self.sharpness_var.get() != 1.0:
            self.processor.adjust_sharpness(self.sharpness_var.get())
        if self.contrast_var.get() != 1.0:
            self.processor.adjust_contrast(self.contrast_var.get())
        if self.brightness_var.get() != 1.0:
            self.processor.adjust_brightness(self.brightness_var.get())
        if self.hist_equal_var.get():
            self.processor.apply_histogram_equalization()
        if self.enhance_edges_var.get():
            self.processor.detect_edges(self.edge_mode_var.get())
        if self.unsharp_mask_var.get():
            self.processor.apply_unsharp_mask(
                radius=self.unsharp_radius_var.get(), amount=self.unsharp_amount_var.get()
            )
        if self.adaptive_thresh_var.get():
            self.processor.apply_adaptive_thresholding(
                block_size=self.thresh_block_var.get(), c=self.thresh_c_var.get()
            )
        if self.invert_var.get():
            self.processor.invert()
        if self.dither_var.get():
            self.processor.apply_dithering()

        processed_img = self.processor.get_processed_image()

        char_set = self.char_set_var.get()
        if char_set == "custom":
            ASCIIArtGenerator.CHAR_SETS['custom'] = self.custom_chars_var.get()

        generator = ASCIIArtGenerator(
            char_set=char_set, width=width, height=height,
            contrast=1.0, brightness=1.0,
        )

        ascii_image = generator._map_pixels_to_ascii(processed_img)
        result = '\n'.join([''.join(row) for row in ascii_image])
        self.ascii_result = result

        self.ascii_text.config(state=tk.NORMAL)
        self.ascii_text.delete(1.0, tk.END)
        self.ascii_text.insert(1.0, result)
        self.ascii_text.config(state=tk.DISABLED)
        self.ascii_text.config(font=('Courier', self.font_size_var.get()))

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save_ascii_art(self):
        """Save generated ASCII art to file."""
        if not self.ascii_result:
            messagebox.showwarning("Warning", "No ASCII art has been generated yet.")
            return

        output_format = self.output_format_var.get()

        if output_format == "Text":
            file_path = filedialog.asksaveasfilename(
                title="Save ASCII Art", defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            )
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(self.ascii_result)
                    self.status_var.set(f"ASCII art saved to: {os.path.basename(file_path)}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save file: {e}")

        elif output_format == "HTML":
            file_path = filedialog.asksaveasfilename(
                title="Save ASCII Art as HTML", defaultextension=".html",
                filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
            )
            if file_path:
                try:
                    html_content = (
                        "<!DOCTYPE html>\n<html>\n<head>\n"
                        '<meta charset="UTF-8">\n<title>ASCII Art</title>\n'
                        "<style>pre { font-family: monospace; font-size: 10px; "
                        "line-height: 1.0; white-space: pre; }</style>\n"
                        "</head>\n<body>\n<pre>"
                        f"{self.ascii_result}</pre>\n</body>\n</html>"
                    )
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    self.status_var.set(f"ASCII art saved as HTML to: {os.path.basename(file_path)}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save HTML file: {e}")

        elif output_format == "Image":
            file_path = filedialog.asksaveasfilename(
                title="Save ASCII Art as Image", defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            )
            if file_path:
                try:
                    self.ascii_text.update()
                    x = self.ascii_text.winfo_rootx()
                    y = self.ascii_text.winfo_rooty()
                    w = self.ascii_text.winfo_width()
                    h = self.ascii_text.winfo_height()
                    img = ImageTk.PhotoImage(Image.grab((x, y, x + w, y + h)))
                    img._image.save(file_path)
                    self.status_var.set(f"ASCII art saved as image to: {os.path.basename(file_path)}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save image: {e}")

    # ------------------------------------------------------------------
    # Help dialogs
    # ------------------------------------------------------------------

    def _show_instructions(self):
        """Show application instructions."""
        instructions = (
            "ASCII Art Generator - Instructions\n\n"
            "1. Getting Started:\n"
            "   - Click 'File > Open Image' or 'Browse...' to load an image\n"
            "   - Adjust settings in the different tabs\n"
            "   - Click 'Generate Preview' for a quick low-resolution result\n"
            "   - Click 'Generate Full' for the complete ASCII art\n\n"
            "2. ASCII Settings:\n"
            "   - Width/Height: Number of characters in the output\n"
            "   - Character Set: Different character collections\n"
            "   - Invert Colors: Reverse dark and light values\n"
            "   - Apply Dithering: Add texture for detail\n\n"
            "3. Image Processing:\n"
            "   - Contrast/Brightness/Sharpness: Adjust image properties\n"
            "   - Enhance Edges: Highlight edges\n"
            "   - Histogram Equalization: Improve contrast range\n"
            "   - Unsharp Mask: Enhance edges while preserving appearance\n\n"
            "4. Advanced Settings:\n"
            "   - Preview Font: Change display font size\n"
            "   - Output Format: Save as text, HTML, or image\n"
            "   - Custom Characters: Define your own density map\n"
            "   - Adaptive Thresholding: Better detail in varied lighting\n\n"
            "5. Tips:\n"
            "   - Use high-contrast images for best results\n"
            "   - Experiment with different character sets\n"
            "   - Small contrast changes can dramatically improve results\n"
        )
        dialog = tk.Toplevel(self)
        dialog.title("Instructions")
        dialog.geometry("600x500")
        dialog.transient(self)
        dialog.grab_set()
        text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(1.0, instructions)
        text.config(state=tk.DISABLED)
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)

    def _show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About ASCII Art Generator",
            "ASCII Art Generator v1.0\n\n"
            "A tool for converting images to ASCII art with extensive customization.\n\n"
            "Features: Multiple character sets, image processing, preview/full modes,\n"
            "save as text/HTML/image.\n\n"
            "Built with Python, Tkinter, PIL, and OpenCV.",
        )


if __name__ == "__main__":
    app = ASCIIArtApp()
    app.mainloop()
