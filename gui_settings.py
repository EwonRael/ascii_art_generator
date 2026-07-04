"""
GUI settings panel for the ASCII Art Generator.

Contains functions to create and manage all settings widgets (ASCII options,
image processing, advanced settings) and their associated toggle/update callbacks.
"""

import os
import tkinter as tk
from tkinter import ttk
from PIL import Image

from ascii_art_generator import ASCIIArtGenerator


def create_settings_panel(app, parent):
    """Create the settings panel with all controls."""
    # File selection
    file_frame = ttk.Frame(parent)
    file_frame.pack(fill=tk.X, padx=5, pady=5)

    ttk.Label(file_frame, text="Image:").pack(side=tk.LEFT, padx=5)
    app.file_path_var = tk.StringVar()
    ttk.Entry(file_frame, textvariable=app.file_path_var, width=30).pack(side=tk.LEFT, padx=5)
    ttk.Button(file_frame, text="Browse...", command=app._load_image).pack(side=tk.LEFT, padx=5)

    # Settings notebook
    notebook = ttk.Notebook(parent)
    notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    ascii_frame = ttk.Frame(notebook)
    notebook.add(ascii_frame, text="ASCII Settings")

    img_frame = ttk.Frame(notebook)
    notebook.add(img_frame, text="Image Processing")

    adv_frame = ttk.Frame(notebook)
    notebook.add(adv_frame, text="Advanced")

    _create_ascii_settings(app, ascii_frame)
    _create_image_processing(app, img_frame)
    _create_advanced_settings(app, adv_frame)

    # Action buttons
    btn_frame = ttk.Frame(parent)
    btn_frame.pack(fill=tk.X, padx=5, pady=10)

    ttk.Button(btn_frame, text="Generate Preview", command=app._generate_preview).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Generate Full", command=app._generate_full).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Save As...", command=app._save_ascii_art).pack(side=tk.RIGHT, padx=5)


def _create_ascii_settings(app, parent):
    """Create controls for basic ASCII conversion settings."""
    width_frame = ttk.Frame(parent)
    width_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(width_frame, text="Width:").pack(side=tk.LEFT, padx=5)
    app.width_var = tk.IntVar()
    ttk.Spinbox(width_frame, from_=20, to=500, textvariable=app.width_var, width=5).pack(side=tk.LEFT, padx=5)

    height_frame = ttk.Frame(parent)
    height_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(height_frame, text="Height:").pack(side=tk.LEFT, padx=5)
    app.height_var = tk.IntVar()
    app.height_spinbox = ttk.Spinbox(height_frame, from_=0, to=500, textvariable=app.height_var, width=5)
    app.height_spinbox.pack(side=tk.LEFT, padx=5)
    app.auto_height_var = tk.BooleanVar()
    ttk.Checkbutton(height_frame, text="Auto (maintain aspect ratio)",
                    variable=app.auto_height_var,
                    command=lambda: toggle_height_auto(app)).pack(side=tk.LEFT, padx=5)

    char_frame = ttk.Frame(parent)
    char_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(char_frame, text="Character Set:").pack(side=tk.LEFT, padx=5)
    app.char_set_var = tk.StringVar()
    char_combo = ttk.Combobox(char_frame, textvariable=app.char_set_var, width=15)
    char_combo['values'] = ('basic', 'standard', 'blocks', 'custom')
    char_combo.pack(side=tk.LEFT, padx=5)

    invert_frame = ttk.Frame(parent)
    invert_frame.pack(fill=tk.X, padx=5, pady=5)
    app.invert_var = tk.BooleanVar()
    ttk.Checkbutton(invert_frame, text="Invert Colors", variable=app.invert_var).pack(side=tk.LEFT, padx=5)
    app.dither_var = tk.BooleanVar()
    ttk.Checkbutton(invert_frame, text="Apply Dithering", variable=app.dither_var).pack(side=tk.LEFT, padx=20)


def _create_image_processing(app, parent):
    """Create controls for image preprocessing settings."""
    # Contrast
    contrast_frame = ttk.Frame(parent)
    contrast_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(contrast_frame, text="Contrast:").pack(side=tk.LEFT, padx=5)
    app.contrast_var = tk.DoubleVar()
    ttk.Scale(contrast_frame, from_=0.1, to=3.0, variable=app.contrast_var,
              orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    ttk.Label(contrast_frame, textvariable=app.contrast_var).pack(side=tk.LEFT, padx=5)

    # Brightness
    brightness_frame = ttk.Frame(parent)
    brightness_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(brightness_frame, text="Brightness:").pack(side=tk.LEFT, padx=5)
    app.brightness_var = tk.DoubleVar()
    ttk.Scale(brightness_frame, from_=0.1, to=3.0, variable=app.brightness_var,
              orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    ttk.Label(brightness_frame, textvariable=app.brightness_var).pack(side=tk.LEFT, padx=5)

    # Sharpness
    sharpness_frame = ttk.Frame(parent)
    sharpness_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(sharpness_frame, text="Sharpness:").pack(side=tk.LEFT, padx=5)
    app.sharpness_var = tk.DoubleVar()
    ttk.Scale(sharpness_frame, from_=0.1, to=5.0, variable=app.sharpness_var,
              orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    ttk.Label(sharpness_frame, textvariable=app.sharpness_var).pack(side=tk.LEFT, padx=5)

    # Edge enhancement
    edge_frame = ttk.Frame(parent)
    edge_frame.pack(fill=tk.X, padx=5, pady=5)
    app.enhance_edges_var = tk.BooleanVar()
    ttk.Checkbutton(edge_frame, text="Enhance Edges", variable=app.enhance_edges_var).pack(side=tk.LEFT, padx=5)
    app.edge_mode_var = tk.StringVar()
    app._edge_combo = ttk.Combobox(edge_frame, textvariable=app.edge_mode_var, width=10, state="readonly")
    app._edge_combo['values'] = ('standard', 'sobel', 'canny')
    app._edge_combo.pack(side=tk.LEFT, padx=5)

    # Histogram equalization
    hist_frame = ttk.Frame(parent)
    hist_frame.pack(fill=tk.X, padx=5, pady=5)
    app.hist_equal_var = tk.BooleanVar()
    ttk.Checkbutton(hist_frame, text="Apply Histogram Equalization", variable=app.hist_equal_var).pack(side=tk.LEFT, padx=5)

    # Unsharp mask
    unsharp_frame = ttk.Frame(parent)
    unsharp_frame.pack(fill=tk.X, padx=5, pady=5)
    app.unsharp_mask_var = tk.BooleanVar()
    ttk.Checkbutton(unsharp_frame, text="Apply Unsharp Mask", variable=app.unsharp_mask_var).pack(side=tk.LEFT, padx=5)

    app.unsharp_radius_var = tk.DoubleVar()
    app.unsharp_amount_var = tk.DoubleVar()

    unsharp_params_frame = ttk.Frame(parent)
    unsharp_params_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(unsharp_params_frame, text="Radius:").pack(side=tk.LEFT, padx=5)
    app._unsharp_radius_spin = ttk.Spinbox(unsharp_params_frame, from_=0.5, to=5.0, increment=0.5,
                                            textvariable=app.unsharp_radius_var, width=5)
    app._unsharp_radius_spin.pack(side=tk.LEFT, padx=5)
    ttk.Label(unsharp_params_frame, text="Amount:").pack(side=tk.LEFT, padx=5)
    app._unsharp_amount_spin = ttk.Spinbox(unsharp_params_frame, from_=0.5, to=3.0, increment=0.1,
                                            textvariable=app.unsharp_amount_var, width=5)
    app._unsharp_amount_spin.pack(side=tk.LEFT, padx=5)


def _create_advanced_settings(app, parent):
    """Create controls for advanced settings."""
    font_frame = ttk.Frame(parent)
    font_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(font_frame, text="Preview Font:").pack(side=tk.LEFT, padx=5)
    app.font_size_var = tk.IntVar()
    ttk.Spinbox(font_frame, from_=4, to=24, textvariable=app.font_size_var, width=5).pack(side=tk.LEFT, padx=5)

    format_frame = ttk.Frame(parent)
    format_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(format_frame, text="Output Format:").pack(side=tk.LEFT, padx=5)
    app.output_format_var = tk.StringVar()
    format_combo = ttk.Combobox(format_frame, textvariable=app.output_format_var, width=10, state="readonly")
    format_combo['values'] = ('Text', 'HTML', 'Image')
    format_combo.pack(side=tk.LEFT, padx=5)

    custom_frame = ttk.Frame(parent)
    custom_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(custom_frame, text="Custom Characters:").pack(anchor=tk.W, padx=5, pady=2)
    app.custom_chars_var = tk.StringVar()
    ttk.Entry(custom_frame, textvariable=app.custom_chars_var, width=40).pack(padx=5, pady=2, fill=tk.X)
    ttk.Label(custom_frame, text="(From darkest to lightest)").pack(anchor=tk.W, padx=5, pady=2)

    thresh_frame = ttk.Frame(parent)
    thresh_frame.pack(fill=tk.X, padx=5, pady=5)
    app.adaptive_thresh_var = tk.BooleanVar()
    ttk.Checkbutton(thresh_frame, text="Apply Adaptive Thresholding",
                    variable=app.adaptive_thresh_var).pack(side=tk.LEFT, padx=5)

    thresh_params_frame = ttk.Frame(parent)
    thresh_params_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Label(thresh_params_frame, text="Block Size:").pack(side=tk.LEFT, padx=5)
    app.thresh_block_var = tk.IntVar()
    app._thresh_block_spin = ttk.Spinbox(thresh_params_frame, from_=3, to=51, increment=2,
                                          textvariable=app.thresh_block_var, width=5)
    app._thresh_block_spin.pack(side=tk.LEFT, padx=5)
    ttk.Label(thresh_params_frame, text="Constant:").pack(side=tk.LEFT, padx=5)
    app.thresh_c_var = tk.IntVar()
    app._thresh_c_spin = ttk.Spinbox(thresh_params_frame, from_=0, to=10,
                                      textvariable=app.thresh_c_var, width=5)
    app._thresh_c_spin.pack(side=tk.LEFT, padx=5)

    reset_frame = ttk.Frame(parent)
    reset_frame.pack(fill=tk.X, padx=5, pady=10)
    ttk.Button(reset_frame, text="Reset to Defaults", command=app._set_default_values).pack(side=tk.RIGHT, padx=5)


# --- Toggle and update callbacks ---


def toggle_height_auto(app, *args):
    """Enable/disable height input based on auto-height checkbox."""
    if app.auto_height_var.get():
        app.height_spinbox.configure(state="disabled")
        update_auto_height(app)
    else:
        app.height_spinbox.configure(state="normal")


def toggle_edge_mode(app, *args):
    """Enable/disable edge mode combobox based on edge enhancement checkbox."""
    if hasattr(app, '_edge_combo'):
        if app.enhance_edges_var.get():
            app._edge_combo.configure(state="readonly")
        else:
            app._edge_combo.configure(state="disabled")


def toggle_unsharp_params(app, *args):
    """Enable/disable unsharp mask parameters based on checkbox."""
    state = "normal" if app.unsharp_mask_var.get() else "disabled"
    if hasattr(app, '_unsharp_radius_spin'):
        app._unsharp_radius_spin.configure(state=state)
    if hasattr(app, '_unsharp_amount_spin'):
        app._unsharp_amount_spin.configure(state=state)


def toggle_thresh_params(app, *args):
    """Enable/disable threshold parameters based on checkbox."""
    state = "normal" if app.adaptive_thresh_var.get() else "disabled"
    if hasattr(app, '_thresh_block_spin'):
        app._thresh_block_spin.configure(state=state)
    if hasattr(app, '_thresh_c_spin'):
        app._thresh_c_spin.configure(state=state)


def update_custom_chars(app, *args):
    """Update custom characters field when char set changes."""
    if app.char_set_var.get() != "custom":
        try:
            char_set = ASCIIArtGenerator.CHAR_SETS.get(app.char_set_var.get())
            if char_set:
                app.custom_chars_var.set(char_set)
        except Exception as e:
            print(f"Error updating custom chars: {e}")


def update_auto_height(app, *args):
    """Update height based on width and aspect ratio if auto-height is enabled."""
    if hasattr(app, 'auto_height_var') and app.auto_height_var.get():
        if app.input_image_path and os.path.exists(app.input_image_path):
            try:
                with Image.open(app.input_image_path) as img:
                    height = ASCIIArtGenerator.calculate_auto_height(app.width_var.get(), img)
                    app.height_var.set(height)
            except Exception as e:
                print(f"Error calculating auto height: {e}")


def set_default_values(app):
    """Set default values for all settings."""
    app.width_var.set(100)
    app.height_var.set(50)
    app.auto_height_var.set(True)
    toggle_height_auto(app)

    app.char_set_var.set("standard")
    app.invert_var.set(False)
    app.dither_var.set(False)

    app.contrast_var.set(1.0)
    app.brightness_var.set(1.0)
    app.sharpness_var.set(1.0)

    app.enhance_edges_var.set(False)
    app.edge_mode_var.set("standard")
    toggle_edge_mode(app)

    app.hist_equal_var.set(False)

    app.unsharp_mask_var.set(False)
    app.unsharp_radius_var.set(2.0)
    app.unsharp_amount_var.set(1.5)
    toggle_unsharp_params(app)

    app.font_size_var.set(10)
    app.output_format_var.set("Text")
    app.custom_chars_var.set(" .`^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$")
    app.adaptive_thresh_var.set(False)
    app.thresh_block_var.set(11)
    app.thresh_c_var.set(2)
    toggle_thresh_params(app)
