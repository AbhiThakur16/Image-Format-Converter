import os
import sys

import customtkinter as ctk

from tkinter import filedialog, messagebox

from PIL import Image, ImageOps

from psd_tools import PSDImage

from converter import (
    physical_size_to_pixels,
    print_preset_to_pixels,
    pixels_to_physical_size
)


# =========================================================
# APP SETTINGS
# =========================================================

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


SCREEN_PRESETS = {
    "HD - 1280 × 720": (1280, 720),
    "Full HD - 1920 × 1080": (1920, 1080),
    "2K - 2560 × 1440": (2560, 1440),
    "4K - 3840 × 2160": (3840, 2160)
}


# =========================================================
# IMAGE HELPERS
# =========================================================

def convert_to_rgb(image):

    if image.mode in ("RGBA", "LA"):

        rgba = image.convert("RGBA")

        background = Image.new(
            "RGB",
            rgba.size,
            "white"
        )

        background.paste(
            rgba,
            mask=rgba.getchannel("A")
        )

        return background

    if image.mode == "P":
        return image.convert("RGB")

    if image.mode != "RGB":
        return image.convert("RGB")

    return image


def apply_color_mode(image, color_mode):

    if color_mode == "Grayscale":
        return image.convert("L")

    return convert_to_rgb(image)


def get_resampling_filter(method):

    if method == "Fast - Bilinear":
        return Image.Resampling.BILINEAR

    if method == "Balanced - Bicubic":
        return Image.Resampling.BICUBIC

    return Image.Resampling.LANCZOS


def get_tiff_compression(name):

    mapping = {
        "LZW - Lossless": "tiff_lzw",
        "Deflate - Lossless": "tiff_adobe_deflate",
        "None - Uncompressed": "raw"
    }

    return mapping.get(
        name,
        "tiff_lzw"
    )


# =========================================================
# TARGET SIZE
# =========================================================

def calculate_target_size(
    original_size,
    size_mode,
    screen_preset,
    paper_size,
    orientation,
    custom_width,
    custom_height,
    custom_unit,
    dpi
):

    if size_mode == "Original Size":
        return original_size

    if size_mode == "Screen Resolution":

        return SCREEN_PRESETS[
            screen_preset
        ]

    if size_mode == "Print Preset":

        return print_preset_to_pixels(
            paper_size,
            orientation,
            dpi
        )

    if size_mode == "Custom Size":

        return physical_size_to_pixels(
            custom_width,
            custom_height,
            custom_unit,
            dpi
        )

    return original_size


# =========================================================
# RESIZE
# =========================================================

def resize_with_behavior(
    image,
    target_width,
    target_height,
    behavior,
    quality
):

    resample = get_resampling_filter(
        quality
    )

    original_width, original_height = (
        image.size
    )

    # FIT
    if behavior == "Fit":

        scale = min(
            target_width / original_width,
            target_height / original_height
        )

        new_width = max(
            1,
            round(original_width * scale)
        )

        new_height = max(
            1,
            round(original_height * scale)
        )

        return image.resize(
            (new_width, new_height),
            resample
        )

    # FILL & CROP
    if behavior == "Fill & Crop":

        return ImageOps.fit(
            image,
            (
                target_width,
                target_height
            ),
            method=resample,
            centering=(0.5, 0.5)
        )

    # STRETCH
    if behavior == "Stretch":

        return image.resize(
            (
                target_width,
                target_height
            ),
            resample
        )

    return image


# =========================================================
# QUALITY CHECK
# =========================================================

def get_quality_message(
    original_width,
    original_height,
    output_width,
    output_height
):

    scale = max(
        output_width / original_width,
        output_height / original_height
    )

    if scale >= 3:

        return (
            "⚠ High Upscaling",
            f"Image is being enlarged about {scale:.1f}×. "
            "Source detail may appear softer."
        )

    if scale >= 2:

        return (
            "⚠ Moderate Upscaling",
            "Significant enlargement detected. "
            "Lanczos quality is recommended."
        )

    if scale > 1:

        return (
            "ℹ Light Upscaling",
            "Small enlargement will be applied."
        )

    return (
        "✓ Good Quality",
        "No major upscaling issue detected."
    )


# =========================================================
# UNIQUE FILE NAME
# =========================================================

def unique_output_path(
    output_folder,
    base_name,
    extension
):

    output_path = os.path.join(
        output_folder,
        base_name + extension
    )

    if not os.path.exists(output_path):
        return output_path

    counter = 1

    while True:

        output_path = os.path.join(
            output_folder,
            f"{base_name}_{counter}{extension}"
        )

        if not os.path.exists(output_path):
            return output_path

        counter += 1


# =========================================================
# MAIN APPLICATION
# =========================================================

class ImageCraftDesktop(ctk.CTk):

    def __init__(self):

        super().__init__()

        self.title(
            "ImageCraft Pro Desktop"
        )

        self.geometry(
            "1380x900"
        )

        self.minsize(
            1150,
            760
        )

        self.selected_files = []

        self.preview_ctk_image = None

        self.output_folder = os.path.join(
            os.getcwd(),
            "output"
        )

        os.makedirs(
            self.output_folder,
            exist_ok=True
        )

        self.create_header()
        self.create_main_layout()
        self.create_settings_panel()
        self.create_workspace()

        self.refresh_controls()
        self.update_output_folder_label()


    # =====================================================
    # HEADER
    # =====================================================

    def create_header(self):

        header = ctk.CTkFrame(
            self,
            height=100,
            corner_radius=0,
            fg_color="#eef4ff"
        )

        header.pack(
            fill="x"
        )

        header.pack_propagate(
            False
        )

        ctk.CTkLabel(
            header,
            text="ImageCraft Pro",
            font=ctk.CTkFont(
                size=30,
                weight="bold"
            ),
            text_color="#172033"
        ).pack(
            pady=(16, 2)
        )

        ctk.CTkLabel(
            header,
            text=(
                "Professional Image Conversion, "
                "Print & Resolution Studio"
            ),
            font=ctk.CTkFont(
                size=14
            ),
            text_color="#52647a"
        ).pack()


    # =====================================================
    # MAIN LAYOUT
    # =====================================================

    def create_main_layout(self):

        self.main_frame = ctk.CTkFrame(
            self,
            fg_color="#f5f7fb",
            corner_radius=0
        )

        self.main_frame.pack(
            fill="both",
            expand=True
        )

        self.main_frame.grid_columnconfigure(
            0,
            weight=0
        )

        self.main_frame.grid_columnconfigure(
            1,
            weight=1
        )

        self.main_frame.grid_rowconfigure(
            0,
            weight=1
        )


    # =====================================================
    # SETTINGS PANEL
    # =====================================================

    def create_settings_panel(self):

        self.settings = (
            ctk.CTkScrollableFrame(
                self.main_frame,
                width=360,
                corner_radius=0,
                fg_color="#ffffff"
            )
        )

        self.settings.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 2),
            pady=0
        )


        ctk.CTkLabel(
            self.settings,
            text="🎛 Export Studio",
            font=ctk.CTkFont(
                size=23,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 4)
        )

        ctk.CTkLabel(
            self.settings,
            text="Configure professional export settings.",
            text_color="#6b7280"
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 18)
        )


        # -------------------------------------------------
        # FORMAT
        # -------------------------------------------------

        self.section_label(
            "File Format"
        )

        self.output_format = (
            ctk.CTkOptionMenu(
                self.settings,
                values=[
                    "TIFF",
                    "BMP",
                    "PDF",
                    "PSD"
                ],
                command=lambda value:
                    self.refresh_controls()
            )
        )

        self.output_format.set(
            "TIFF"
        )

        self.output_format.pack(
            fill="x",
            padx=20,
            pady=(4, 15)
        )


        # -------------------------------------------------
        # SIZE MODE
        # -------------------------------------------------

        self.size_frame = (
            ctk.CTkFrame(
                self.settings,
                fg_color="transparent"
            )
        )

        self.size_frame.pack(
            fill="x"
        )

        self.section_label(
            "📐 Size & Resolution",
            parent=self.size_frame
        )

        self.size_mode = (
            ctk.CTkOptionMenu(
                self.size_frame,
                values=[
                    "Original Size",
                    "Screen Resolution",
                    "Print Preset",
                    "Custom Size"
                ],
                command=lambda value:
                    self.refresh_controls()
            )
        )

        self.size_mode.set(
            "Original Size"
        )

        self.size_mode.pack(
            fill="x",
            padx=20,
            pady=(5, 8)
        )


        # SCREEN
        self.screen_frame = ctk.CTkFrame(
            self.size_frame,
            fg_color="transparent"
        )

        self.screen_preset = ctk.CTkOptionMenu(
            self.screen_frame,
            values=list(
                SCREEN_PRESETS.keys()
            )
        )

        self.screen_preset.set(
            "Full HD - 1920 × 1080"
        )

        self.screen_preset.pack(
            fill="x",
            padx=20,
            pady=5
        )


        # PRINT
        self.print_frame = ctk.CTkFrame(
            self.size_frame,
            fg_color="transparent"
        )

        self.paper_size = ctk.CTkOptionMenu(
            self.print_frame,
            values=[
                "A5",
                "A4",
                "A3",
                "A2"
            ]
        )

        self.paper_size.set(
            "A4"
        )

        self.paper_size.pack(
            fill="x",
            padx=20,
            pady=5
        )

        self.orientation = ctk.CTkOptionMenu(
            self.print_frame,
            values=[
                "Portrait",
                "Landscape"
            ]
        )

        self.orientation.set(
            "Portrait"
        )

        self.orientation.pack(
            fill="x",
            padx=20,
            pady=5
        )


        # CUSTOM
        self.custom_frame = ctk.CTkFrame(
            self.size_frame,
            fg_color="transparent"
        )

        self.custom_unit = ctk.CTkOptionMenu(
            self.custom_frame,
            values=[
                "Pixels",
                "Inches",
                "CM",
                "MM"
            ]
        )

        self.custom_unit.set(
            "Pixels"
        )

        self.custom_unit.pack(
            fill="x",
            padx=20,
            pady=5
        )

        dimensions = ctk.CTkFrame(
            self.custom_frame,
            fg_color="transparent"
        )

        dimensions.pack(
            fill="x",
            padx=20
        )

        self.custom_width = ctk.CTkEntry(
            dimensions,
            placeholder_text="Width"
        )

        self.custom_width.insert(
            0,
            "1920"
        )

        self.custom_width.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 4)
        )

        self.custom_height = ctk.CTkEntry(
            dimensions,
            placeholder_text="Height"
        )

        self.custom_height.insert(
            0,
            "1080"
        )

        self.custom_height.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(4, 0)
        )


        # -------------------------------------------------
        # RESIZE BEHAVIOUR
        # -------------------------------------------------

        self.resize_frame = ctk.CTkFrame(
            self.settings,
            fg_color="transparent"
        )

        self.resize_frame.pack(
            fill="x"
        )

        self.section_label(
            "↔ Resize Behaviour",
            parent=self.resize_frame
        )

        self.resize_behavior = (
            ctk.CTkOptionMenu(
                self.resize_frame,
                values=[
                    "Fit",
                    "Fill & Crop",
                    "Stretch"
                ]
            )
        )

        self.resize_behavior.set(
            "Fit"
        )

        self.resize_behavior.pack(
            fill="x",
            padx=20,
            pady=5
        )


        # -------------------------------------------------
        # DPI
        # -------------------------------------------------

        self.dpi_frame = ctk.CTkFrame(
            self.settings,
            fg_color="transparent"
        )

        self.dpi_frame.pack(
            fill="x"
        )

        self.section_label(
            "🖨 DPI Control",
            parent=self.dpi_frame
        )

        self.dpi_value = ctk.IntVar(
            value=300
        )

        self.dpi_label = ctk.CTkLabel(
            self.dpi_frame,
            text="300 DPI"
        )

        self.dpi_label.pack(
            pady=(2, 0)
        )

        self.dpi_slider = ctk.CTkSlider(
            self.dpi_frame,
            from_=72,
            to=600,
            number_of_steps=528,
            variable=self.dpi_value,
            command=self.update_dpi
        )

        self.dpi_slider.pack(
            fill="x",
            padx=20,
            pady=8
        )

        self.dpi_entry = ctk.CTkEntry(
            self.dpi_frame,
            width=100
        )

        self.dpi_entry.insert(
            0,
            "300"
        )

        self.dpi_entry.pack(
            pady=(0, 10)
        )

        self.dpi_entry.bind(
            "<Return>",
            self.sync_dpi_entry
        )

        self.dpi_entry.bind(
            "<FocusOut>",
            self.sync_dpi_entry
        )


        # -------------------------------------------------
        # COLOR
        # -------------------------------------------------

        self.color_frame = ctk.CTkFrame(
            self.settings,
            fg_color="transparent"
        )

        self.color_frame.pack(
            fill="x"
        )

        self.section_label(
            "🎨 Color Mode",
            parent=self.color_frame
        )

        self.color_mode = ctk.CTkOptionMenu(
            self.color_frame,
            values=[
                "RGB Color",
                "Grayscale"
            ]
        )

        self.color_mode.set(
            "RGB Color"
        )

        self.color_mode.pack(
            fill="x",
            padx=20,
            pady=5
        )


        # -------------------------------------------------
        # QUALITY
        # -------------------------------------------------

        self.quality_frame = ctk.CTkFrame(
            self.settings,
            fg_color="transparent"
        )

        self.quality_frame.pack(
            fill="x"
        )

        self.section_label(
            "✨ Resize Quality",
            parent=self.quality_frame
        )

        self.resize_quality = (
            ctk.CTkOptionMenu(
                self.quality_frame,
                values=[
                    "High Quality - Lanczos",
                    "Balanced - Bicubic",
                    "Fast - Bilinear"
                ]
            )
        )

        self.resize_quality.set(
            "High Quality - Lanczos"
        )

        self.resize_quality.pack(
            fill="x",
            padx=20,
            pady=5
        )


        # -------------------------------------------------
        # TIFF COMPRESSION
        # -------------------------------------------------

        self.compression_frame = (
            ctk.CTkFrame(
                self.settings,
                fg_color="transparent"
            )
        )

        self.compression_frame.pack(
            fill="x"
        )

        self.section_label(
            "📦 TIFF Compression",
            parent=self.compression_frame
        )

        self.tiff_compression = (
            ctk.CTkOptionMenu(
                self.compression_frame,
                values=[
                    "LZW - Lossless",
                    "Deflate - Lossless",
                    "None - Uncompressed"
                ]
            )
        )

        self.tiff_compression.set(
            "LZW - Lossless"
        )

        self.tiff_compression.pack(
            fill="x",
            padx=20,
            pady=(5, 20)
        )


    # =====================================================
    # WORKSPACE
    # =====================================================

    def create_workspace(self):

        self.workspace = ctk.CTkScrollableFrame(
            self.main_frame,
            fg_color="#f5f7fb"
        )

        self.workspace.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=20,
            pady=20
        )


        # -------------------------------------------------
        # SELECT IMAGES
        # -------------------------------------------------

        top_card = ctk.CTkFrame(
            self.workspace,
            fg_color="#ffffff",
            corner_radius=18
        )

        top_card.pack(
            fill="x",
            pady=(0, 15)
        )

        ctk.CTkLabel(
            top_card,
            text="📤 Upload Images",
            font=ctk.CTkFont(
                size=24,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=25,
            pady=(20, 5)
        )

        ctk.CTkLabel(
            top_card,
            text=(
                "Select one or multiple "
                "PNG, JPG or JPEG images."
            ),
            text_color="#6b7280"
        ).pack(
            anchor="w",
            padx=25
        )

        ctk.CTkButton(
            top_card,
            text="Select Images",
            height=45,
            command=self.select_images
        ).pack(
            fill="x",
            padx=25,
            pady=18
        )

        self.selected_label = ctk.CTkLabel(
            top_card,
            text="No images selected"
        )

        self.selected_label.pack(
            pady=(0, 18)
        )


        # -------------------------------------------------
        # FILE LIST
        # -------------------------------------------------

        self.files_box = ctk.CTkTextbox(
            self.workspace,
            height=100
        )

        self.files_box.pack(
            fill="x",
            pady=(0, 15)
        )

        self.files_box.configure(
            state="disabled"
        )


        # -------------------------------------------------
        # PREVIEW CARD
        # -------------------------------------------------

        preview_card = ctk.CTkFrame(
            self.workspace,
            fg_color="#ffffff",
            corner_radius=18
        )

        preview_card.pack(
            fill="x",
            pady=(0, 15)
        )

        ctk.CTkLabel(
            preview_card,
            text="🖼 Image Preview",
            font=ctk.CTkFont(
                size=22,
                weight="bold"
            )
        ).pack(
            pady=(18, 10)
        )

        self.preview_label = ctk.CTkLabel(
            preview_card,
            text="Select an image to preview",
            width=600,
            height=330,
            fg_color="#f8fafc",
            corner_radius=12
        )

        self.preview_label.pack(
            padx=25,
            pady=(0, 15)
        )

        self.image_info = ctk.CTkLabel(
            preview_card,
            text="Image information will appear here.",
            text_color="#52647a"
        )

        self.image_info.pack(
            pady=(0, 18)
        )


        # -------------------------------------------------
        # QUALITY CARD
        # -------------------------------------------------

        self.quality_status = ctk.CTkLabel(
            self.workspace,
            text="Quality Check: Waiting for image",
            font=ctk.CTkFont(
                size=15,
                weight="bold"
            ),
            fg_color="#ffffff",
            corner_radius=12,
            height=55
        )

        self.quality_status.pack(
            fill="x",
            pady=(0, 15)
        )


        # -------------------------------------------------
        # OUTPUT FOLDER
        # -------------------------------------------------

        folder_card = ctk.CTkFrame(
            self.workspace,
            fg_color="#ffffff",
            corner_radius=18
        )

        folder_card.pack(
            fill="x",
            pady=(0, 15)
        )

        ctk.CTkLabel(
            folder_card,
            text="📁 Output Folder",
            font=ctk.CTkFont(
                size=20,
                weight="bold"
            )
        ).pack(
            pady=(18, 8)
        )

        self.folder_label = ctk.CTkLabel(
            folder_card,
            text="",
            wraplength=750
        )

        self.folder_label.pack(
            padx=20,
            pady=5
        )

        ctk.CTkButton(
            folder_card,
            text="Choose Output Folder",
            command=self.choose_output_folder
        ).pack(
            pady=(5, 18)
        )


        # -------------------------------------------------
        # ACTIONS
        # -------------------------------------------------

        action_frame = ctk.CTkFrame(
            self.workspace,
            fg_color="transparent"
        )

        action_frame.pack(
            fill="x",
            pady=10
        )

        action_frame.grid_columnconfigure(
            0,
            weight=2
        )

        action_frame.grid_columnconfigure(
            1,
            weight=1
        )

        action_frame.grid_columnconfigure(
            2,
            weight=1
        )

        self.convert_button = ctk.CTkButton(
            action_frame,
            text="🚀 Convert Images",
            height=52,
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            ),
            command=self.convert_images
        )

        self.convert_button.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 6)
        )

        ctk.CTkButton(
            action_frame,
            text="Reset",
            height=52,
            command=self.reset_app
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=6
        )

        ctk.CTkButton(
            action_frame,
            text="Open Output",
            height=52,
            command=self.open_output_folder
        ).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(6, 0)
        )

        self.status_label = ctk.CTkLabel(
            self.workspace,
            text="Ready",
            font=ctk.CTkFont(
                size=15,
                weight="bold"
            )
        )

        self.status_label.pack(
            pady=15
        )


    # =====================================================
    # SECTION LABEL
    # =====================================================

    def section_label(
        self,
        text,
        parent=None
    ):

        if parent is None:
            parent = self.settings

        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(
                size=17,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=20,
            pady=(15, 3)
        )


    # =====================================================
    # REFRESH CONTROLS
    # =====================================================

    def refresh_controls(self):

        output_format = (
            self.output_format.get()
        )

        is_image_export = (
            output_format
            in ("TIFF", "BMP")
        )

        frames = [
            self.size_frame,
            self.resize_frame,
            self.dpi_frame,
            self.color_frame,
            self.quality_frame
        ]

        if is_image_export:

            for frame in frames:
                frame.pack(
                    fill="x"
                )

        else:

            for frame in frames:
                frame.pack_forget()

        if output_format == "TIFF":

            self.compression_frame.pack(
                fill="x"
            )

        else:

            self.compression_frame.pack_forget()

        self.screen_frame.pack_forget()
        self.print_frame.pack_forget()
        self.custom_frame.pack_forget()

        if not is_image_export:
            return

        mode = self.size_mode.get()

        if mode == "Screen Resolution":

            self.screen_frame.pack(
                fill="x"
            )

        elif mode == "Print Preset":

            self.print_frame.pack(
                fill="x"
            )

        elif mode == "Custom Size":

            self.custom_frame.pack(
                fill="x"
            )


    # =====================================================
    # DPI
    # =====================================================

    def update_dpi(
        self,
        value
    ):

        value = int(
            round(value)
        )

        self.dpi_label.configure(
            text=f"{value} DPI"
        )

        self.dpi_entry.delete(
            0,
            "end"
        )

        self.dpi_entry.insert(
            0,
            str(value)
        )


    def sync_dpi_entry(
        self,
        event=None
    ):

        try:

            value = int(
                self.dpi_entry.get()
            )

        except ValueError:

            value = 300

        value = max(
            72,
            min(
                600,
                value
            )
        )

        self.dpi_value.set(
            value
        )

        self.dpi_label.configure(
            text=f"{value} DPI"
        )

        self.dpi_entry.delete(
            0,
            "end"
        )

        self.dpi_entry.insert(
            0,
            str(value)
        )


    # =====================================================
    # SELECT IMAGES
    # =====================================================

    def select_images(self):

        files = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[
                (
                    "Image Files",
                    "*.png *.jpg *.jpeg"
                )
            ]
        )

        if not files:
            return

        self.selected_files = list(
            files
        )

        self.selected_label.configure(
            text=(
                f"{len(self.selected_files)} "
                "image(s) selected"
            )
        )

        self.files_box.configure(
            state="normal"
        )

        self.files_box.delete(
            "1.0",
            "end"
        )

        for file_path in self.selected_files:

            self.files_box.insert(
                "end",
                os.path.basename(
                    file_path
                ) + "\n"
            )

        self.files_box.configure(
            state="disabled"
        )

        self.show_preview(
            self.selected_files[0]
        )


    # =====================================================
    # PREVIEW
    # =====================================================

    def show_preview(
        self,
        image_path
    ):

        try:

            with Image.open(
                image_path
            ) as opened:

                image = opened.copy()

                width, height = (
                    opened.size
                )

                image_format = (
                    opened.format
                )

                mode = opened.mode

                original_dpi = (
                    opened.info.get(
                        "dpi",
                        "Not available"
                    )
                )

            preview = ImageOps.contain(
                image,
                (650, 320),
                Image.Resampling.LANCZOS
            )

            if preview.mode not in (
                "RGB",
                "RGBA"
            ):

                preview = preview.convert(
                    "RGB"
                )

            self.preview_ctk_image = (
                ctk.CTkImage(
                    light_image=preview,
                    dark_image=preview,
                    size=preview.size
                )
            )

            self.preview_label.configure(
                image=self.preview_ctk_image,
                text=""
            )

            self.image_info.configure(
                text=(
                    f"{os.path.basename(image_path)}   |   "
                    f"{width} × {height} px   |   "
                    f"{image_format}   |   "
                    f"{mode}   |   "
                    f"DPI: {original_dpi}"
                )
            )

            self.update_quality_preview(
                image.size
            )

        except Exception as error:

            messagebox.showerror(
                "Preview Error",
                str(error)
            )


    # =====================================================
    # TARGET DIMENSIONS
    # =====================================================

    def get_target_dimensions(
        self,
        original_size
    ):

        if self.output_format.get() not in (
            "TIFF",
            "BMP"
        ):

            return original_size

        dpi = int(
            self.dpi_value.get()
        )

        width_text = (
            self.custom_width.get()
            or "1920"
        )

        height_text = (
            self.custom_height.get()
            or "1080"
        )

        return calculate_target_size(
            original_size,
            self.size_mode.get(),
            self.screen_preset.get(),
            self.paper_size.get(),
            self.orientation.get(),
            float(width_text),
            float(height_text),
            self.custom_unit.get(),
            dpi
        )


    # =====================================================
    # QUALITY PREVIEW
    # =====================================================

    def update_quality_preview(
        self,
        original_size
    ):

        try:

            target = (
                self.get_target_dimensions(
                    original_size
                )
            )

            if self.resize_behavior.get() == "Fit":

                ow, oh = original_size
                tw, th = target

                scale = min(
                    tw / ow,
                    th / oh
                )

                output_width = round(
                    ow * scale
                )

                output_height = round(
                    oh * scale
                )

            else:

                output_width, output_height = (
                    target
                )

            title, message = (
                get_quality_message(
                    original_size[0],
                    original_size[1],
                    output_width,
                    output_height
                )
            )

            self.quality_status.configure(
                text=(
                    f"{title}\n{message}"
                )
            )

        except Exception:

            pass


    # =====================================================
    # OUTPUT FOLDER
    # =====================================================

    def choose_output_folder(self):

        folder = (
            filedialog.askdirectory(
                title="Choose Output Folder"
            )
        )

        if folder:

            self.output_folder = folder

            self.update_output_folder_label()


    def update_output_folder_label(self):

        self.folder_label.configure(
            text=self.output_folder
        )


    def open_output_folder(self):

        os.makedirs(
            self.output_folder,
            exist_ok=True
        )

        try:

            os.startfile(
                self.output_folder
            )

        except Exception as error:

            messagebox.showerror(
                "Error",
                str(error)
            )


    # =====================================================
    # CONVERT IMAGES
    # =====================================================

    def convert_images(self):

        if not self.selected_files:

            messagebox.showwarning(
                "No Images",
                "Please select at least one image."
            )

            return

        os.makedirs(
            self.output_folder,
            exist_ok=True
        )

        output_format = (
            self.output_format.get()
        )

        dpi = int(
            self.dpi_value.get()
        )

        successful = 0

        failed = []


        for index, file_path in enumerate(
            self.selected_files,
            start=1
        ):

            try:

                self.status_label.configure(
                    text=(
                        f"Converting {index}/"
                        f"{len(self.selected_files)}..."
                    )
                )

                self.update_idletasks()


                with Image.open(
                    file_path
                ) as opened:

                    image = opened.copy()


                if output_format in (
                    "TIFF",
                    "BMP"
                ):

                    target_width, target_height = (
                        self.get_target_dimensions(
                            image.size
                        )
                    )

                    image = resize_with_behavior(
                        image,
                        target_width,
                        target_height,
                        self.resize_behavior.get(),
                        self.resize_quality.get()
                    )

                    image = apply_color_mode(
                        image,
                        self.color_mode.get()
                    )


                base_name = os.path.splitext(
                    os.path.basename(
                        file_path
                    )
                )[0]


                # =========================================
                # TIFF
                # =========================================

                if output_format == "TIFF":

                    output_path = (
                        unique_output_path(
                            self.output_folder,
                            base_name,
                            ".tiff"
                        )
                    )

                    image.save(
                        output_path,
                        format="TIFF",
                        dpi=(dpi, dpi),
                        compression=(
                            get_tiff_compression(
                                self.tiff_compression.get()
                            )
                        )
                    )


                # =========================================
                # BMP
                # =========================================

                elif output_format == "BMP":

                    output_path = (
                        unique_output_path(
                            self.output_folder,
                            base_name,
                            ".bmp"
                        )
                    )

                    image.save(
                        output_path,
                        format="BMP",
                        dpi=(dpi, dpi)
                    )


                # =========================================
                # PDF
                # =========================================

                elif output_format == "PDF":

                    output_path = (
                        unique_output_path(
                            self.output_folder,
                            base_name,
                            ".pdf"
                        )
                    )

                    image = convert_to_rgb(
                        image
                    )

                    image.save(
                        output_path,
                        format="PDF",
                        resolution=100.0
                    )


                # =========================================
                # PSD
                # =========================================

                elif output_format == "PSD":

                    output_path = (
                        unique_output_path(
                            self.output_folder,
                            base_name,
                            ".psd"
                        )
                    )

                    image = convert_to_rgb(
                        image
                    )

                    psd = PSDImage.frompil(
                        image
                    )

                    psd.save(
                        output_path
                    )


                successful += 1


            except Exception as error:

                failed.append(
                    f"{os.path.basename(file_path)}: "
                    f"{error}"
                )


        self.status_label.configure(
            text="Conversion Complete"
        )


        if successful:

            message = (
                f"{successful} image(s) "
                "converted successfully.\n\n"
                f"Saved to:\n"
                f"{self.output_folder}"
            )

            if failed:

                message += (
                    f"\n\nFailed: "
                    f"{len(failed)}"
                )

            messagebox.showinfo(
                "Conversion Complete",
                message
            )

        else:

            messagebox.showerror(
                "Conversion Failed",
                "\n".join(failed)
            )


    # =====================================================
    # RESET
    # =====================================================

    def reset_app(self):

        self.selected_files = []

        self.selected_label.configure(
            text="No images selected"
        )

        self.files_box.configure(
            state="normal"
        )

        self.files_box.delete(
            "1.0",
            "end"
        )

        self.files_box.configure(
            state="disabled"
        )

        self.preview_label.configure(
            image=None,
            text="Select an image to preview"
        )

        self.preview_ctk_image = None

        self.image_info.configure(
            text="Image information will appear here."
        )

        self.quality_status.configure(
            text="Quality Check: Waiting for image"
        )

        self.status_label.configure(
            text="Ready"
        )


# =========================================================
# START APP
# =========================================================

if __name__ == "__main__":

    app = ImageCraftDesktop()

    app.mainloop()