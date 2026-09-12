import io
import os

import streamlit as st
from PIL import Image, ImageOps
from psd_tools import PSDImage

from converter import (
    physical_size_to_pixels,
    print_preset_to_pixels,
    pixels_to_physical_size
)


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="ImageCraft Pro",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# LIGHT PROFESSIONAL UI
# =========================================================

st.markdown(
    """
<style>

.stApp {
    background-color: #eef4ff;
}

.block-container {
    max-width: 1450px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    background-color: #e8f1ff;
    border-right: 1px solid #bfd3f2;
}

h1, h2, h3, h4 {
    color: #172033 !important;
}

.stApp p,
.stApp label {
    color: #334155;
}

[data-testid="stMetric"] {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 15px;
    padding: 15px;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
}

[data-testid="stFileUploader"] {
    background-color: #ffffff;
    border: 2px dashed #b8c8df;
    border-radius: 16px;
    padding: 10px;
}

[data-baseweb="select"] > div {
    background-color: #ffffff !important;
}

[data-testid="stNumberInput"] input {
    background-color: #ffffff !important;
    color: #172033 !important;
}

div.stButton > button {
    width: 100%;
    min-height: 48px;
    border-radius: 12px;
    font-weight: 700;
}

div.stDownloadButton > button {
    width: 100%;
    min-height: 46px;
    border-radius: 12px;
    font-weight: 700;
}

[data-testid="stAlert"] {
    border-radius: 14px;
}

button[data-baseweb="tab"] {
    font-weight: 650;
}

hr {
    border-color: #e2e8f0;
}


/* =========================================================
   MOBILE / TABLET OPTIMIZATION
   Existing desktop design and sidebar are unchanged.
   ========================================================= */

@media (max-width: 900px) {

    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1rem !important;
    }

    h1 {
        font-size: 2rem !important;
        line-height: 1.15 !important;
    }

    h2 {
        font-size: 1.35rem !important;
    }

    h3 {
        font-size: 1.1rem !important;
    }

    div.stButton > button,
    div.stDownloadButton > button {
        min-height: 48px !important;
    }
}


@media (max-width: 640px) {

    .block-container {
        padding-left: 0.65rem !important;
        padding-right: 0.65rem !important;
        padding-top: 0.7rem !important;
        padding-bottom: 2rem !important;
    }

    h1 {
        font-size: 1.65rem !important;
        line-height: 1.12 !important;
    }

    h2 {
        font-size: 1.22rem !important;
        line-height: 1.2 !important;
    }

    h3 {
        font-size: 1.05rem !important;
    }

    p,
    label {
        font-size: 0.92rem !important;
    }

    /* Stack normal page columns vertically on mobile */
    section.main [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 0.55rem !important;
    }

    section.main [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 100% !important;
    }

    [data-testid="stMetric"] {
        padding: 10px !important;
        border-radius: 12px !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.05rem !important;
    }

    [data-testid="stFileUploader"] {
        padding: 5px !important;
        border-radius: 12px !important;
    }

    [data-testid="stFileUploaderDropzone"] {
        padding: 0.75rem !important;
        min-height: 82px !important;
    }

    div.stButton > button,
    div.stDownloadButton > button {
        width: 100% !important;
        min-height: 48px !important;
        font-size: 0.98rem !important;
        border-radius: 11px !important;
    }

    [data-baseweb="select"] > div,
    [data-testid="stNumberInput"] input {
        min-height: 46px !important;
        font-size: 16px !important;
    }

    .stMarkdown,
    .stCaption,
    code,
    pre {
        overflow-wrap: anywhere !important;
        word-break: break-word !important;
    }

    hr {
        margin-top: 0.8rem !important;
        margin-bottom: 0.8rem !important;
    }

    [data-testid="stVerticalBlock"] {
        gap: 0.55rem !important;
    }
}

</style>
""",
    unsafe_allow_html=True
)


# =========================================================
# CONSTANTS
# =========================================================

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


def apply_color_mode(
    image,
    color_mode
):

    if color_mode == "Grayscale":
        return image.convert("L")

    return convert_to_rgb(image)


# =========================================================
# RESAMPLING
# =========================================================

def get_resampling_filter(
    resize_quality
):

    if resize_quality == "Fast - Bilinear":
        return Image.Resampling.BILINEAR

    if resize_quality == "Balanced - Bicubic":
        return Image.Resampling.BICUBIC

    return Image.Resampling.LANCZOS


# =========================================================
# TIFF COMPRESSION
# =========================================================

def get_tiff_compression(
    compression_name
):

    compression_map = {
        "LZW - Lossless": "tiff_lzw",
        "Deflate - Lossless": "tiff_adobe_deflate",
        "None - Uncompressed": "raw"
    }

    return compression_map.get(
        compression_name,
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

    original_width, original_height = (
        original_size
    )

    # ORIGINAL
    if size_mode == "Original Size":

        return (
            original_width,
            original_height
        )

    # SCREEN
    if size_mode == "Screen Resolution":

        return SCREEN_PRESETS[
            screen_preset
        ]

    # PRINT
    if size_mode == "Print Preset":

        return print_preset_to_pixels(
            paper_size,
            orientation,
            dpi
        )

    # CUSTOM
    if size_mode == "Custom Size":

        return physical_size_to_pixels(
            custom_width,
            custom_height,
            custom_unit,
            dpi
        )

    return (
        original_width,
        original_height
    )


# =========================================================
# PREDICT OUTPUT SIZE
# =========================================================

def predict_output_size(
    original_size,
    target_size,
    resize_behavior
):

    original_width, original_height = (
        original_size
    )

    target_width, target_height = (
        target_size
    )

    # FIT
    if resize_behavior == "Fit":

        scale = min(
            target_width / original_width,
            target_height / original_height
        )

        new_width = max(
            1,
            round(
                original_width * scale
            )
        )

        new_height = max(
            1,
            round(
                original_height * scale
            )
        )

        return (
            new_width,
            new_height
        )

    # FILL AND CROP
    if resize_behavior == "Fill & Crop":

        return (
            target_width,
            target_height
        )

    # STRETCH
    if resize_behavior == "Stretch":

        return (
            target_width,
            target_height
        )

    return original_size


# =========================================================
# RESIZE BEHAVIOUR
# =========================================================

def resize_with_behavior(
    image,
    target_width,
    target_height,
    resize_behavior,
    resize_quality
):

    resampling_filter = (
        get_resampling_filter(
            resize_quality
        )
    )

    original_width, original_height = (
        image.size
    )

    # -----------------------------------------------------
    # FIT
    # -----------------------------------------------------

    if resize_behavior == "Fit":

        scale = min(
            target_width / original_width,
            target_height / original_height
        )

        new_width = max(
            1,
            round(
                original_width * scale
            )
        )

        new_height = max(
            1,
            round(
                original_height * scale
            )
        )

        return image.resize(
            (
                new_width,
                new_height
            ),
            resampling_filter
        )

    # -----------------------------------------------------
    # FILL & CROP
    # -----------------------------------------------------

    if resize_behavior == "Fill & Crop":

        return ImageOps.fit(
            image,
            (
                target_width,
                target_height
            ),
            method=resampling_filter,
            centering=(
                0.5,
                0.5
            )
        )

    # -----------------------------------------------------
    # STRETCH
    # -----------------------------------------------------

    if resize_behavior == "Stretch":

        return image.resize(
            (
                target_width,
                target_height
            ),
            resampling_filter
        )

    return image


# =========================================================
# QUALITY CHECK
# =========================================================

def get_quality_warning(
    original_width,
    original_height,
    output_width,
    output_height
):

    width_scale = (
        output_width / original_width
    )

    height_scale = (
        output_height / original_height
    )

    largest_scale = max(
        width_scale,
        height_scale
    )

    if largest_scale >= 3:

        return (
            "high",
            "High Upscaling",
            (
                "The image is being enlarged by about "
                f"{largest_scale:.1f}×. Increasing pixels "
                "does not create new source detail, so the "
                "result may look softer."
            )
        )

    if largest_scale >= 2:

        return (
            "medium",
            "Moderate Upscaling",
            (
                "The image is being enlarged significantly. "
                "High Quality - Lanczos is recommended."
            )
        )

    if largest_scale > 1:

        return (
            "light",
            "Light Upscaling",
            (
                "A small amount of enlargement will be applied."
            )
        )

    return (
        "good",
        "Good Quality",
        (
            "No major upscaling quality issue detected."
        )
    )


# =========================================================
# CONVERT IMAGE
# =========================================================

def convert_uploaded_image(
    uploaded_file,
    output_format,
    target_width,
    target_height,
    dpi,
    color_mode,
    resize_quality,
    tiff_compression,
    resize_behavior
):

    source_bytes = (
        uploaded_file.getvalue()
    )

    with Image.open(
        io.BytesIO(source_bytes)
    ) as opened_image:

        image = opened_image.copy()

    base_name = os.path.splitext(
        uploaded_file.name
    )[0]

    # -----------------------------------------------------
    # TIFF / BMP IMAGE PROCESSING
    # -----------------------------------------------------

    if output_format in (
        "TIFF",
        "BMP"
    ):

        image = resize_with_behavior(
            image,
            target_width,
            target_height,
            resize_behavior,
            resize_quality
        )

        image = apply_color_mode(
            image,
            color_mode
        )

    output_buffer = io.BytesIO()

    # -----------------------------------------------------
    # TIFF
    # -----------------------------------------------------

    if output_format == "TIFF":

        image.save(
            output_buffer,
            format="TIFF",
            dpi=(
                int(dpi),
                int(dpi)
            ),
            compression=get_tiff_compression(
                tiff_compression
            )
        )

        output_name = (
            f"{base_name}.tiff"
        )

        mime = "image/tiff"

    # -----------------------------------------------------
    # BMP
    # -----------------------------------------------------

    elif output_format == "BMP":

        image.save(
            output_buffer,
            format="BMP",
            dpi=(
                int(dpi),
                int(dpi)
            )
        )

        output_name = (
            f"{base_name}.bmp"
        )

        mime = "image/bmp"

    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    elif output_format == "PDF":

        image = convert_to_rgb(
            image
        )

        image.save(
            output_buffer,
            format="PDF",
            resolution=100.0
        )

        output_name = (
            f"{base_name}.pdf"
        )

        mime = "application/pdf"

    # -----------------------------------------------------
    # PSD
    # -----------------------------------------------------

    elif output_format == "PSD":

        image = convert_to_rgb(
            image
        )

        psd_image = PSDImage.frompil(
            image
        )

        psd_image.save(
            output_buffer
        )

        output_name = (
            f"{base_name}.psd"
        )

        mime = "application/octet-stream"

    else:

        raise ValueError(
            "Unsupported output format."
        )

    output_buffer.seek(0)

    return (
        output_buffer.getvalue(),
        output_name,
        mime,
        image
    )


# =========================================================
# PREVIEW BYTES
# =========================================================

def create_preview_bytes(
    image
):

    preview = image.copy()

    if preview.mode not in (
        "RGB",
        "RGBA"
    ):

        preview = preview.convert(
            "RGB"
        )

    buffer = io.BytesIO()

    preview.save(
        buffer,
        format="PNG"
    )

    buffer.seek(0)

    return buffer.getvalue()


# =========================================================
# DEFAULTS
# =========================================================

size_mode = "Original Size"

screen_preset = (
    "Full HD - 1920 × 1080"
)

paper_size = "A4"

orientation = "Portrait"

custom_width = 1920.0
custom_height = 1080.0

custom_unit = "Pixels"

custom_pixels_enabled = False
custom_pixel_width = 1920
custom_pixel_height = 1080

dpi = 300

color_mode = "RGB Color"

resize_quality = (
    "High Quality - Lanczos"
)

resize_behavior = "Fit"

tiff_compression = (
    "LZW - Lossless"
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title(
        "🎛️ Export Studio"
    )

    st.caption(
        "Configure professional export settings."
    )

    st.divider()

    # -----------------------------------------------------
    # OUTPUT FORMAT
    # -----------------------------------------------------

    st.subheader(
        "File Format"
    )

    output_format = st.selectbox(
        "Output Format",
        [
            "TIFF",
            "BMP",
            "PDF",
            "PSD"
        ]
    )

    # =====================================================
    # TIFF / BMP OPTIONS
    # =====================================================

    if output_format in (
        "TIFF",
        "BMP"
    ):

        st.divider()

        # -------------------------------------------------
        # SIZE MODE
        # -------------------------------------------------

        st.subheader(
            "📐 Size & Resolution"
        )

        size_mode = st.selectbox(
            "Size Mode",
            [
                "Original Size",
                "Screen Resolution",
                "Print Preset",
                "Custom Size"
            ]
        )

        # -------------------------------------------------
        # SCREEN SIZE
        # -------------------------------------------------

        if size_mode == (
            "Screen Resolution"
        ):

            screen_preset = st.selectbox(
                "Screen Quality",
                list(
                    SCREEN_PRESETS.keys()
                )
            )

        # -------------------------------------------------
        # PRINT SIZE
        # -------------------------------------------------

        elif size_mode == (
            "Print Preset"
        ):

            paper_size = st.selectbox(
                "Paper Size",
                [
                    "A5",
                    "A4",
                    "A3",
                    "A2"
                ]
            )

            orientation = st.selectbox(
                "Orientation",
                [
                    "Portrait",
                    "Landscape"
                ]
            )

        # -------------------------------------------------
        # CUSTOM SIZE
        # -------------------------------------------------

        elif size_mode == (
            "Custom Size"
        ):

            custom_unit = st.selectbox(
                "Measurement Unit",
                [
                    "Pixels",
                    "Inches",
                    "CM",
                    "MM"
                ]
            )

            custom_col1, custom_col2 = (
                st.columns(2)
            )

            if custom_unit == "Pixels":

                default_width = 1920.0
                default_height = 1080.0
                step_size = 1.0

            else:

                default_width = 10.0
                default_height = 8.0
                step_size = 0.1

            with custom_col1:

                custom_width = (
                    st.number_input(
                        "Width",
                        min_value=0.1,
                        max_value=20000.0,
                        value=default_width,
                        step=step_size
                    )
                )

            with custom_col2:

                custom_height = (
                    st.number_input(
                        "Height",
                        min_value=0.1,
                        max_value=20000.0,
                        value=default_height,
                        step=step_size
                    )
                )

        # -------------------------------------------------
        # SEPARATE CUSTOM PIXELS CHANGER
        # -------------------------------------------------

        st.divider()

        st.subheader(
            "🔢 Custom Pixels Changer"
        )

        custom_pixels_enabled = st.checkbox(
            "Use Custom Pixels",
            value=False,
            help=(
                "Enable this to override the selected "
                "size preset with any pixel width and height."
            )
        )

        pixel_col1, pixel_col2 = (
            st.columns(2)
        )

        with pixel_col1:
            custom_pixel_width = (
                st.number_input(
                    "Width (px)",
                    min_value=1,
                    max_value=150000,
                    value=1920,
                    step=1,
                    disabled=not custom_pixels_enabled
                )
            )

        with pixel_col2:
            custom_pixel_height = (
                st.number_input(
                    "Height (px)",
                    min_value=1,
                    max_value=150000,
                    value=1080,
                    step=1,
                    disabled=not custom_pixels_enabled
                )
            )

        st.caption(
            "Enter any Width and Height. "
            "When enabled, these pixels override "
            "the selected size setting."
        )

        # -------------------------------------------------
        # RESIZE BEHAVIOUR
        # -------------------------------------------------

        st.divider()

        st.subheader(
            "↔️ Resize Behaviour"
        )

        resize_behavior = st.selectbox(
            "Image Fitting",
            [
                "Fit",
                "Fill & Crop",
                "Stretch"
            ]
        )

        if resize_behavior == "Fit":

            st.caption(
                "Preserves image proportions and "
                "fits the complete image inside the target size."
            )

        elif resize_behavior == "Fill & Crop":

            st.caption(
                "Fills the exact target dimensions while "
                "preserving proportions. Some edges may be cropped."
            )

        else:

            st.warning(
                "Stretch uses the exact width and height "
                "and may distort the image."
            )

        # -------------------------------------------------
        # DPI
        # -------------------------------------------------

        st.divider()

        st.subheader(
            "🖨️ DPI Control"
        )

        dpi = st.slider(
            "DPI",
            min_value=72,
            max_value=600,
            value=300,
            step=1
        )

        st.caption(
            f"Selected DPI: {dpi}"
        )

        # -------------------------------------------------
        # COLOR MODE
        # -------------------------------------------------

        st.divider()

        st.subheader(
            "🎨 Color Mode"
        )

        color_mode = st.selectbox(
            "Output Color",
            [
                "RGB Color",
                "Grayscale"
            ]
        )

        # -------------------------------------------------
        # QUALITY
        # -------------------------------------------------

        st.divider()

        st.subheader(
            "✨ Resize Quality"
        )

        resize_quality = st.selectbox(
            "Resampling Method",
            [
                "High Quality - Lanczos",
                "Balanced - Bicubic",
                "Fast - Bilinear"
            ]
        )

        if resize_quality == (
            "High Quality - Lanczos"
        ):

            st.caption(
                "Recommended for best quality."
            )

        elif resize_quality == (
            "Balanced - Bicubic"
        ):

            st.caption(
                "Good balance of speed and quality."
            )

        else:

            st.caption(
                "Faster processing with lower resize quality."
            )

        # -------------------------------------------------
        # TIFF COMPRESSION
        # -------------------------------------------------

        if output_format == "TIFF":

            st.divider()

            st.subheader(
                "📦 TIFF Compression"
            )

            tiff_compression = st.selectbox(
                "Compression",
                [
                    "LZW - Lossless",
                    "Deflate - Lossless",
                    "None - Uncompressed"
                ]
            )

            st.caption(
                "LZW is recommended for most TIFF exports."
            )

    st.divider()

    st.caption(
        "Input: PNG • JPG • JPEG"
    )

    st.caption(
        "Output: TIFF • BMP • PDF • PSD"
    )


# =========================================================
# HEADER
# =========================================================

with st.container(
    border=True
):

    st.title(
        "🖼️ ImageCraft Pro"
    )

    st.subheader(
        "Professional Image Conversion & Export Studio"
    )

    st.write(
        "Prepare images for screen, print and "
        "professional TIFF/BMP workflows."
    )


# =========================================================
# FEATURE CARDS
# =========================================================

feature1, feature2, feature3, feature4 = (
    st.columns(4)
)

feature1.metric(
    "Formats",
    "4"
)

feature2.metric(
    "Screen Quality",
    "Up to 4K"
)

feature3.metric(
    "DPI Range",
    "72–600"
)

feature4.metric(
    "Print Presets",
    "A5–A2"
)


# =========================================================
# UPLOAD
# =========================================================

st.header(
    "📤 Upload Images"
)

uploaded_files = st.file_uploader(
    "Upload PNG/JPG/JPEG",
    type=[
        "png",
        "jpg",
        "jpeg"
    ],
    accept_multiple_files=True,
    label_visibility="collapsed"
)


# =========================================================
# EMPTY STATE
# =========================================================

if not uploaded_files:

    with st.container(
        border=True
    ):

        st.subheader(
            "🚀 Ready to Convert"
        )

        st.write(
            "Upload one or more PNG/JPG/JPEG images above."
        )

        left, right = st.columns(2)

        with left:

            st.markdown(
                """
**Digital Export**

- Original Size
- HD
- Full HD
- 2K
- 4K
- Custom Pixels
"""
            )

        with right:

            st.markdown(
                """
**Print Export**

- A5 / A4 / A3 / A2
- Portrait / Landscape
- Inches / CM / MM
- 72–600 DPI
- RGB / Grayscale
"""
            )

        st.info(
            "Converted files are downloaded directly "
            "in the selected format. No ZIP is required."
        )

    st.stop()


# =========================================================
# SELECTED FILES
# =========================================================

st.success(
    f"✅ {len(uploaded_files)} image(s) selected."
)


# =========================================================
# FIRST IMAGE OUTPUT SPECIFICATION
# =========================================================

if output_format in (
    "TIFF",
    "BMP"
):

    try:

        first_bytes = (
            uploaded_files[0].getvalue()
        )

        with Image.open(
            io.BytesIO(first_bytes)
        ) as first_image:

            first_original_size = (
                first_image.size
            )

        target_width, target_height = (
            calculate_target_size(
                first_original_size,
                size_mode,
                screen_preset,
                paper_size,
                orientation,
                custom_width,
                custom_height,
                custom_unit,
                dpi
            )
        )
        # CUSTOM PIXELS OVERRIDE - OUTPUT SPEC
        if custom_pixels_enabled:
            target_width = int(
                custom_pixel_width
            )
            target_height = int(
                custom_pixel_height
            )


        (
            expected_width,
            expected_height
        ) = predict_output_size(
            first_original_size,
            (
                target_width,
                target_height
            ),
            resize_behavior
        )

        physical = (
            pixels_to_physical_size(
                expected_width,
                expected_height,
                dpi
            )
        )

        width_in, height_in = (
            physical["inches"]
        )

        width_cm, height_cm = (
            physical["cm"]
        )

        st.subheader(
            "📊 Output Specification"
        )

        spec1, spec2, spec3, spec4 = (
            st.columns(4)
        )

        spec1.metric(
            "Pixel Size",
            (
                f"{expected_width} × "
                f"{expected_height}"
            )
        )

        spec2.metric(
            "DPI",
            dpi
        )

        spec3.metric(
            "Print Size",
            (
                f"{width_in:.2f} × "
                f"{height_in:.2f} in"
            )
        )

        spec4.metric(
            "Print Size",
            (
                f"{width_cm:.1f} × "
                f"{height_cm:.1f} cm"
            )
        )

        # -------------------------------------------------
        # QUALITY CHECK BEFORE CONVERSION
        # -------------------------------------------------

        (
            quality_level,
            quality_title,
            quality_message
        ) = get_quality_warning(
            first_original_size[0],
            first_original_size[1],
            expected_width,
            expected_height
        )

        if quality_level == "high":

            st.warning(
                f"⚠️ {quality_title}: "
                f"{quality_message}"
            )

        elif quality_level == "medium":

            st.info(
                f"ℹ️ {quality_title}: "
                f"{quality_message}"
            )

        elif quality_level == "light":

            st.info(
                f"ℹ️ {quality_title}: "
                f"{quality_message}"
            )

        else:

            st.success(
                f"✅ {quality_title}: "
                f"{quality_message}"
            )

        # -------------------------------------------------
        # CURRENT SETTINGS
        # -------------------------------------------------

        with st.expander(
            "⚙️ Current Export Settings",
            expanded=False
        ):

            setting1, setting2, setting3 = (
                st.columns(3)
            )

            with setting1:

                st.write(
                    f"**Size Mode:** "
                    f"{size_mode}"
                )

                st.write(
                    f"**DPI:** {dpi}"
                )

            with setting2:

                st.write(
                    f"**Resize Behaviour:** "
                    f"{resize_behavior}"
                )

                st.write(
                    f"**Color:** "
                    f"{color_mode}"
                )

            with setting3:

                st.write(
                    f"**Quality:** "
                    f"{resize_quality}"
                )

                if output_format == "TIFF":

                    st.write(
                        f"**Compression:** "
                        f"{tiff_compression}"
                    )

    except Exception as error:

        st.error(
            f"Output settings error: {error}"
        )


# =========================================================
# CONVERT BUTTON
# =========================================================

st.write("")

convert_clicked = st.button(
    "🚀 Convert Images",
    type="primary",
    use_container_width=True
)


# =========================================================
# SESSION STATE
# =========================================================

if "conversion_results" not in (
    st.session_state
):

    st.session_state[
        "conversion_results"
    ] = []


if "conversion_signature" not in (
    st.session_state
):

    st.session_state[
        "conversion_signature"
    ] = None


file_signature = tuple(
    (
        uploaded_file.name,
        uploaded_file.size
    )
    for uploaded_file
    in uploaded_files
)


current_signature = (
    file_signature,
    output_format,
    size_mode,
    screen_preset,
    paper_size,
    orientation,
    custom_width,
    custom_height,
    custom_unit,
    custom_pixels_enabled,
    custom_pixel_width,
    custom_pixel_height,
    dpi,
    color_mode,
    resize_quality,
    resize_behavior,
    tiff_compression
)


# =========================================================
# RUN CONVERSION
# =========================================================

if convert_clicked:

    conversion_results = []

    progress_bar = st.progress(
        0,
        text="Preparing conversion..."
    )

    total_files = len(
        uploaded_files
    )

    for index, uploaded_file in enumerate(
        uploaded_files,
        start=1
    ):

        try:

            progress_bar.progress(
                (index - 1) / total_files,
                text=(
                    f"Converting "
                    f"{uploaded_file.name}..."
                )
            )

            original_bytes = (
                uploaded_file.getvalue()
            )

            with Image.open(
                io.BytesIO(original_bytes)
            ) as opened_image:

                original_image = (
                    opened_image.copy()
                )

                original_width, original_height = (
                    opened_image.size
                )

                original_format = (
                    opened_image.format
                )

                original_mode = (
                    opened_image.mode
                )

                original_dpi = (
                    opened_image.info.get(
                        "dpi",
                        "Not available"
                    )
                )

            # ---------------------------------------------
            # TARGET SIZE
            # ---------------------------------------------

            if output_format in (
                "TIFF",
                "BMP"
            ):

                target_width, target_height = (
                    calculate_target_size(
                        original_image.size,
                        size_mode,
                        screen_preset,
                        paper_size,
                        orientation,
                        custom_width,
                        custom_height,
                        custom_unit,
                        dpi
                    )
                )
                # CUSTOM PIXELS OVERRIDE - CONVERSION
                if custom_pixels_enabled:
                    target_width = int(
                        custom_pixel_width
                    )
                    target_height = int(
                        custom_pixel_height
                    )

            else:

                target_width, target_height = (
                    original_image.size
                )

            # ---------------------------------------------
            # CONVERSION
            # ---------------------------------------------

            (
                converted_data,
                output_name,
                mime,
                output_image
            ) = convert_uploaded_image(
                uploaded_file,
                output_format,
                target_width,
                target_height,
                int(dpi),
                color_mode,
                resize_quality,
                tiff_compression,
                resize_behavior
            )

            output_width, output_height = (
                output_image.size
            )

            # ---------------------------------------------
            # QUALITY CHECK
            # ---------------------------------------------

            (
                quality_level,
                quality_title,
                quality_message
            ) = get_quality_warning(
                original_width,
                original_height,
                output_width,
                output_height
            )

            conversion_results.append(
                {
                    "original_name":
                        uploaded_file.name,

                    "original_preview":
                        create_preview_bytes(
                            original_image
                        ),

                    "original_width":
                        original_width,

                    "original_height":
                        original_height,

                    "original_format":
                        original_format,

                    "original_mode":
                        original_mode,

                    "original_dpi":
                        original_dpi,

                    "original_size_kb":
                        len(original_bytes) / 1024,

                    "output_preview":
                        create_preview_bytes(
                            output_image
                        ),

                    "output_width":
                        output_width,

                    "output_height":
                        output_height,

                    "output_size_kb":
                        len(converted_data) / 1024,

                    "output_name":
                        output_name,

                    "output_data":
                        converted_data,

                    "mime":
                        mime,

                    "quality_level":
                        quality_level,

                    "quality_title":
                        quality_title,

                    "quality_message":
                        quality_message
                }
            )

        except Exception as error:

            st.error(
                f"{uploaded_file.name}: "
                f"{error}"
            )

    progress_bar.progress(
        1.0,
        text="Conversion complete."
    )

    st.session_state[
        "conversion_results"
    ] = conversion_results

    st.session_state[
        "conversion_signature"
    ] = current_signature


# =========================================================
# RESULTS
# =========================================================

results = st.session_state[
    "conversion_results"
]


if results:

    if (
        st.session_state[
            "conversion_signature"
        ]
        != current_signature
    ):

        st.warning(
            "⚠️ Export settings or selected files have changed. "
            "Click Convert Images again to update the results."
        )

    else:

        st.success(
            f"✅ {len(results)} image(s) "
            "converted successfully."
        )

        st.header(
            "✅ Conversion Results"
        )

        for index, result in enumerate(
            results,
            start=1
        ):

            with st.container(
                border=True
            ):

                st.subheader(
                    f"{index}. "
                    f"{result['original_name']}"
                )

                # -----------------------------------------
                # METRICS
                # -----------------------------------------

                metric1, metric2, metric3, metric4 = (
                    st.columns(4)
                )

                metric1.metric(
                    "Original Pixels",
                    (
                        f"{result['original_width']} × "
                        f"{result['original_height']}"
                    )
                )

                metric2.metric(
                    "Output Pixels",
                    (
                        f"{result['output_width']} × "
                        f"{result['output_height']}"
                    )
                )

                metric3.metric(
                    "Original Size",
                    (
                        f"{result['original_size_kb']:.1f} KB"
                    )
                )

                metric4.metric(
                    "Output Size",
                    (
                        f"{result['output_size_kb']:.1f} KB"
                    )
                )

                # -----------------------------------------
                # QUALITY RESULT
                # -----------------------------------------

                if result[
                    "quality_level"
                ] == "high":

                    st.warning(
                        f"⚠️ {result['quality_title']}: "
                        f"{result['quality_message']}"
                    )

                elif result[
                    "quality_level"
                ] in (
                    "medium",
                    "light"
                ):

                    st.info(
                        f"ℹ️ {result['quality_title']}: "
                        f"{result['quality_message']}"
                    )

                else:

                    st.success(
                        f"✅ {result['quality_title']}: "
                        f"{result['quality_message']}"
                    )

                # -----------------------------------------
                # TABS
                # -----------------------------------------

                preview_tab, info_tab = (
                    st.tabs(
                        [
                            "🖼️ Before / After",
                            "📊 Export Information"
                        ]
                    )
                )

                # =========================================
                # PREVIEW
                # =========================================

                with preview_tab:

                    before, after = (
                        st.columns(2)
                    )

                    with before:

                        st.subheader(
                            "Original"
                        )

                        st.image(
                            result[
                                "original_preview"
                            ],
                            caption=(
                                f"{result['original_width']} × "
                                f"{result['original_height']} px"
                            ),
                            use_container_width=True
                        )

                    with after:

                        st.subheader(
                            "Converted"
                        )

                        st.image(
                            result[
                                "output_preview"
                            ],
                            caption=(
                                f"{result['output_width']} × "
                                f"{result['output_height']} px"
                            ),
                            use_container_width=True
                        )

                # =========================================
                # INFORMATION
                # =========================================

                with info_tab:

                    original_col, output_col = (
                        st.columns(2)
                    )

                    with original_col:

                        st.subheader(
                            "Original Image"
                        )

                        st.write(
                            f"**Format:** "
                            f"{result['original_format']}"
                        )

                        st.write(
                            f"**Pixels:** "
                            f"{result['original_width']} × "
                            f"{result['original_height']}"
                        )

                        st.write(
                            f"**Color Mode:** "
                            f"{result['original_mode']}"
                        )

                        st.write(
                            f"**DPI:** "
                            f"{result['original_dpi']}"
                        )

                        st.write(
                            f"**File Size:** "
                            f"{result['original_size_kb']:.2f} KB"
                        )

                    with output_col:

                        st.subheader(
                            "Exported Image"
                        )

                        st.write(
                            f"**Format:** "
                            f"{output_format}"
                        )

                        st.write(
                            f"**Pixels:** "
                            f"{result['output_width']} × "
                            f"{result['output_height']}"
                        )

                        if output_format in (
                            "TIFF",
                            "BMP"
                        ):

                            st.write(
                                f"**DPI:** "
                                f"{dpi}"
                            )

                            st.write(
                                f"**Color:** "
                                f"{color_mode}"
                            )

                            st.write(
                                f"**Resize Behaviour:** "
                                f"{resize_behavior}"
                            )

                            st.write(
                                f"**Resize Quality:** "
                                f"{resize_quality}"
                            )

                            if output_format == "TIFF":

                                st.write(
                                    f"**Compression:** "
                                    f"{tiff_compression}"
                                )

                            physical = (
                                pixels_to_physical_size(
                                    result[
                                        "output_width"
                                    ],
                                    result[
                                        "output_height"
                                    ],
                                    dpi
                                )
                            )

                            print_inches = (
                                physical["inches"]
                            )

                            print_cm = (
                                physical["cm"]
                            )

                            st.write(
                                "**Print Size:** "
                                f"{print_inches[0]:.2f} × "
                                f"{print_inches[1]:.2f} inches"
                            )

                            st.write(
                                "**Print Size:** "
                                f"{print_cm[0]:.1f} × "
                                f"{print_cm[1]:.1f} cm"
                            )

                # -----------------------------------------
                # NORMAL DIRECT DOWNLOAD
                # -----------------------------------------

                st.download_button(
                    label=(
                        f"⬇️ Download "
                        f"{result['output_name']}"
                    ),
                    data=result[
                        "output_data"
                    ],
                    file_name=result[
                        "output_name"
                    ],
                    mime=result[
                        "mime"
                    ],
                    key=(
                        f"download_"
                        f"{index}_"
                        f"{output_format}"
                    ),
                    use_container_width=True
                )

                st.caption(
                    f"Direct download: "
                    f"{result['output_name']}"
                )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "ImageCraft Pro • Professional Image Conversion & Export Studio"
)