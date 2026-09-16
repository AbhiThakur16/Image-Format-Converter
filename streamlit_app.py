import io
import math
import os
import re
import hashlib

import streamlit as st
from PIL import Image

from ai_analysis import analyze_image
from layer_engine import extract_color_layers, rebuild_image
from semantic_layers import create_semantic_layers
from object_detection import create_object_layers

from segmentation_engine import (
    create_segmented_object_layers,
    remove_background,
)

from color_editor import (
    hex_to_rgb,
    create_mask_preview,
    color_selection_info,
    replace_color,
    remove_color,
    extract_color_layer,
    merge_colors,
)

from text_layers import create_text_layers
from ocr_engine import create_ocr_layers

from quality_check import run_quality_check
from export_engine import export_image

from project_engine import (
    save_project,
    load_project,
    get_project_info,
)

from smart_export import (
    EXPORT_PURPOSES,
    recommend_export_settings,
)

from psd_export import export_flattened_psd

from input_engine import (
    load_input_file,
    get_input_info,
    input_result_to_png_bytes,
)

from pdf_batch_engine import (
    render_all_pdf_pages_as_png,
)


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Image Studio",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
<style>

:root {
    color-scheme: light;
}

.stApp {
    background-color: #f6f8fc !important;
    color: #172033 !important;
}

.block-container {
    max-width: 1400px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}

h1, h2, h3, h4, h5, h6 {
    color: #172033 !important;
}

.stApp p,
.stApp label,
.stApp li,
.stApp span {
    color: #334155;
}

[data-testid="stMarkdownContainer"] {
    color: #334155 !important;
}

[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    color: #172033 !important;
}

[data-baseweb="select"] span {
    color: #172033 !important;
}

[role="option"] {
    background-color: #ffffff !important;
    color: #172033 !important;
}

[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input,
textarea {
    background-color: #ffffff !important;
    color: #172033 !important;
}

[data-testid="stMetric"] {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 12px;
}

[data-testid="stMetricLabel"],
[data-testid="stMetricValue"] {
    color: #172033 !important;
}

[data-testid="stFileUploader"] {
    background-color: #ffffff !important;
    border: 2px dashed #94a3b8;
    border-radius: 16px;
    padding: 10px;
}

div.stButton > button,
div.stDownloadButton > button {
    width: 100%;
    min-height: 46px;
    border-radius: 10px;
    font-weight: 700;
}

@media (max-width: 768px) {

    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1rem !important;
    }

    h1 {
        font-size: 2rem !important;
    }

    h2 {
        font-size: 1.5rem !important;
    }
}

</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# CONSTANTS
# =========================================================

MAX_DIMENSION = 150000
MAX_TOTAL_EXPORT_PIXELS = 150_000_000


VALID_EXPORT_FORMATS = [
    "PNG",
    "JPEG",
    "WEBP",
    "TIFF",
    "BMP",
    "PDF",
    "PSD (Flattened)",
]


DPI_PRESETS = [
    72,
    96,
    150,
    300,
    600,
    1200,
]


INPUT_RENDER_DPI_PRESETS = [
    72,
    96,
    150,
    300,
    600,
]


SMART_EXPORT_PRIORITIES = [
    "Balanced",
    "Smallest File",
    "Maximum Quality",
]


# =========================================================
# CACHE
# =========================================================

@st.cache_data(show_spinner=False)
def cached_ai_analysis(image_bytes):

    with Image.open(
        io.BytesIO(image_bytes)
    ) as opened:

        image = opened.copy()

    return analyze_image(image)


@st.cache_data(show_spinner=False)
def cached_get_input_info(
    file_bytes,
    filename,
):

    return get_input_info(
        file_bytes,
        filename,
    )


@st.cache_data(show_spinner=False)
def cached_prepare_input(
    file_bytes,
    filename,
    page_number=1,
    render_dpi=150,
):

    result = load_input_file(
        file_bytes,
        filename,
        page_number=page_number,
        render_dpi=render_dpi,
    )

    png_bytes = input_result_to_png_bytes(
        result
    )

    image = result["image"]

    return {
        "png_bytes": png_bytes,
        "format": result.get(
            "format",
            "Unknown",
        ),
        "mode": image.mode,
        "width": image.width,
        "height": image.height,
        "dpi": result.get("dpi"),
        "type": result.get(
            "type",
            "image",
        ),
        "page_count": result.get(
            "page_count",
            1,
        ),
        "selected_page": result.get(
            "selected_page",
            1,
        ),
        "warnings": result.get(
            "warnings",
            [],
        ),
    }


@st.cache_data(show_spinner=False)
def cached_prepare_all_pdf_pages(
    file_bytes,
    render_dpi=150,
):

    pages = render_all_pdf_pages_as_png(
        file_bytes,
        dpi=render_dpi,
    )

    prepared = []

    for page in pages:

        prepared.append(
            {
                "page_number":
                    page["page_number"],

                "page_count":
                    page["page_count"],

                "png_bytes":
                    page["data"],

                "width":
                    page["width"],

                "height":
                    page["height"],

                "mode":
                    page["mode"],

                "dpi":
                    page["dpi"],
            }
        )

    return prepared


# =========================================================
# PIXEL HELPERS
# =========================================================

def target_pixels_to_dimensions(
    original_size,
    total_pixels,
):

    original_width, original_height = (
        original_size
    )

    total_pixels = max(
        1,
        min(
            int(total_pixels),
            150000,
        ),
    )

    if total_pixels == 1:
        return 1, 1

    aspect_ratio = (
        original_width
        / original_height
    )

    width = max(
        1,
        int(
            math.sqrt(
                total_pixels
                * aspect_ratio
            )
        ),
    )

    height = max(
        1,
        total_pixels // width,
    )

    while (
        width * height
        > total_pixels
    ):

        if height > 1:
            height -= 1

        elif width > 1:
            width -= 1

        else:
            break

    return (
        int(width),
        int(height),
    )


def dimensions_from_width(
    original_size,
    new_width,
):

    original_width, original_height = (
        original_size
    )

    ratio = (
        original_height
        / original_width
    )

    new_height = round(
        new_width
        * ratio
    )

    new_height = max(
        1,
        min(
            int(new_height),
            MAX_DIMENSION,
        ),
    )

    return (
        int(new_width),
        int(new_height),
    )


# =========================================================
# IMAGE HELPERS
# =========================================================

def image_to_bytes(image):

    buffer = io.BytesIO()

    image.convert(
        "RGBA"
    ).save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)

    return buffer.getvalue()


def safe_filename_part(text):

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "_",
        text,
    )

    return text.strip("_")


# =========================================================
# MEMORY FILE
# =========================================================

class MemoryUploadedFile:

    def __init__(
        self,
        name,
        data,
    ):

        self.name = name
        self._data = data

    def getvalue(self):

        return self._data


# =========================================================
# LAYER STATE
# =========================================================

def initialize_layer_state(
    prefix,
    layers,
):

    revision_key = (
        f"{prefix}_revision"
    )

    st.session_state[
        revision_key
    ] = (
        st.session_state.get(
            revision_key,
            0,
        )
        + 1
    )

    revision = (
        st.session_state[
            revision_key
        ]
    )

    prepared_layers = []

    for index, layer in enumerate(
        layers
    ):

        layer_copy = layer.copy()

        layer_copy["_uid"] = (
            f"{prefix}_"
            f"{revision}_"
            f"{index}_"
            f"{layer.get('type', 'layer')}"
        )

        prepared_layers.append(
            layer_copy
        )

    st.session_state[
        f"{prefix}_layers"
    ] = prepared_layers

    st.session_state[
        f"{prefix}_visibility"
    ] = [
        True
        for _ in prepared_layers
    ]

    st.session_state[
        f"{prefix}_opacity"
    ] = [
        100
        for _ in prepared_layers
    ]

    st.session_state[
        f"{prefix}_names"
    ] = [
        layer.get(
            "name",
            f"Layer {index + 1}",
        )
        for index, layer
        in enumerate(
            prepared_layers
        )
    ]


def collect_project_layers(prefix):

    layers_key = (
        f"{prefix}_layers"
    )

    if (
        layers_key
        not in st.session_state
    ):
        return []

    layers = (
        st.session_state[
            layers_key
        ]
    )

    visibility = (
        st.session_state.get(
            f"{prefix}_visibility",
            [
                True
                for _ in layers
            ],
        )
    )

    opacity = (
        st.session_state.get(
            f"{prefix}_opacity",
            [
                100
                for _ in layers
            ],
        )
    )

    names = (
        st.session_state.get(
            f"{prefix}_names",
            [
                layer.get(
                    "name",
                    f"Layer {index + 1}",
                )
                for index, layer
                in enumerate(layers)
            ],
        )
    )

    project_layers = []

    for index, layer in enumerate(
        layers
    ):

        layer_copy = layer.copy()

        layer_copy[
            "_saved_visible"
        ] = bool(
            visibility[index]
        )

        layer_copy[
            "_saved_opacity"
        ] = int(
            opacity[index]
        )

        layer_copy[
            "_saved_name"
        ] = names[index]

        project_layers.append(
            layer_copy
        )

    return project_layers


def restore_project_layers(
    prefix,
    layers,
):

    if not layers:
        return

    initialize_layer_state(
        prefix,
        layers,
    )

    for index, layer in enumerate(
        layers
    ):

        if index >= len(
            st.session_state[
                f"{prefix}_layers"
            ]
        ):
            break

        st.session_state[
            f"{prefix}_visibility"
        ][index] = bool(
            layer.get(
                "_saved_visible",
                True,
            )
        )

        st.session_state[
            f"{prefix}_opacity"
        ][index] = int(
            layer.get(
                "_saved_opacity",
                100,
            )
        )

        st.session_state[
            f"{prefix}_names"
        ][index] = layer.get(
            "_saved_name",
            layer.get(
                "name",
                f"Layer {index + 1}",
            ),
        )


def rebuild_layer_group(prefix):

    layers_key = (
        f"{prefix}_layers"
    )

    if (
        layers_key
        not in st.session_state
    ):
        return None

    layers = (
        st.session_state[
            layers_key
        ]
    )

    if not layers:
        return None

    visibility = (
        st.session_state.get(
            f"{prefix}_visibility",
            [
                True
                for _ in layers
            ],
        )
    )

    opacity = (
        st.session_state.get(
            f"{prefix}_opacity",
            [
                100
                for _ in layers
            ],
        )
    )

    try:

        return rebuild_image(
            layers,
            visibility=visibility,
            opacities=opacity,
        )

    except Exception:

        return None


# =========================================================
# EXPORT SOURCES
# =========================================================

def build_export_sources(
    original_image,
):

    sources = {
        "Original Image":
            original_image
    }

    smart_color = (
        st.session_state.get(
            "smart_color_result"
        )
    )

    if isinstance(
        smart_color,
        Image.Image,
    ):

        sources[
            "Smart Color Edited Image"
        ] = smart_color

    background_result = (
        st.session_state.get(
            "background_remove_result"
        )
    )

    if isinstance(
        background_result,
        dict,
    ):

        background_image = (
            background_result.get(
                "image"
            )
        )

        if isinstance(
            background_image,
            Image.Image,
        ):

            sources[
                "Background Removed Image"
            ] = background_image

    group_map = {
        "Color Layer Reconstruction":
            "color",

        "Semantic Reconstruction":
            "semantic",

        "Object Layer Reconstruction":
            "object",

        "Segmented Objects":
            "segment",

        "Extracted Color Layer":
            "smartcolor",

        "Text Layer Reconstruction":
            "text",

        "OCR Layer Reconstruction":
            "ocr",
    }

    for source_name, prefix in (
        group_map.items()
    ):

        rebuilt = (
            rebuild_layer_group(
                prefix
            )
        )

        if isinstance(
            rebuilt,
            Image.Image,
        ):

            sources[
                source_name
            ] = rebuilt

    return sources


# =========================================================
# OUTPUT KEYS
# =========================================================

OUTPUT_SETTING_KEYS = [
    "output_export_source",
    "output_export_mode",
    "output_single_format",
    "output_multiple_formats",
    "output_pixel_mode",
    "output_target_pixels",
    "output_maintain_ratio",
    "output_custom_width",
    "output_custom_height",
    "output_dpi_mode",
    "output_dpi_preset",
    "output_custom_dpi",
    "output_color_mode",
    "output_resize_mode",
    "output_quality",
    "output_webp_lossless",
    "output_png_compression",
    "output_tiff_compression",
    "smart_export_purpose",
    "smart_export_priority",
]


def clear_workspace_state():

    prefixes = [
        "color",
        "semantic",
        "object",
        "segment",
        "smartcolor",
        "text",
        "ocr",
    ]

    for prefix in prefixes:

        for suffix in [
            "layers",
            "visibility",
            "opacity",
            "names",
        ]:

            key = (
                f"{prefix}_{suffix}"
            )

            if key in st.session_state:

                del st.session_state[
                    key
                ]

    result_keys = [
        "object_result",
        "segmentation_result",
        "background_remove_result",
        "smart_color_result",
        "smart_color_operation",
        "text_detection_result",
        "ocr_result",
        "ocr_text_output",
        "quality_result",
        "quality_signature",
        "professional_export_results",
        "loaded_project_settings",
        "project_settings_applied",
    ]

    for key in result_keys:

        if key in st.session_state:

            del st.session_state[
                key
            ]

    for key in OUTPUT_SETTING_KEYS:

        if key in st.session_state:

            del st.session_state[
                key
            ]


# =========================================================
# OUTPUT DEFAULTS
# =========================================================

def ensure_output_defaults(
    original_width,
    original_height,
):

    original_total = (
        original_width
        * original_height
    )

    defaults = {
        "output_export_source":
            "Original Image",

        "output_export_mode":
            "Single Format",

        "output_single_format":
            "PNG",

        "output_multiple_formats":
            [
                "PNG",
                "TIFF",
            ],

        "output_pixel_mode":
            "Original Size",

        "output_target_pixels":
            max(
                1,
                min(
                    original_total,
                    150000,
                ),
            ),

        "output_maintain_ratio":
            True,

        "output_custom_width":
            max(
                1,
                min(
                    int(original_width),
                    150000,
                ),
            ),

        "output_custom_height":
            max(
                1,
                min(
                    int(original_height),
                    150000,
                ),
            ),

        "output_dpi_mode":
            "Preset",

        "output_dpi_preset":
            300,

        "output_custom_dpi":
            300,

        "output_color_mode":
            "RGB",

        "output_resize_mode":
            "Fit",

        "output_quality":
            95,

        "output_webp_lossless":
            False,

        "output_png_compression":
            6,

        "output_tiff_compression":
            "LZW - Lossless",

        "smart_export_purpose":
            "General Purpose",

        "smart_export_priority":
            "Balanced",
    }

    for key, value in (
        defaults.items()
    ):

        st.session_state.setdefault(
            key,
            value,
        )


# =========================================================
# PROJECT SETTINGS RESTORE
# =========================================================

def apply_loaded_project_settings():

    if not st.session_state.get(
        "project_is_open",
        False,
    ):
        return

    if st.session_state.get(
        "project_settings_applied",
        False,
    ):
        return

    settings = (
        st.session_state.get(
            "loaded_project_settings",
            {},
        )
    )

    if not settings:
        return

    st.session_state[
        "output_export_source"
    ] = settings.get(
        "export_source",
        "Original Image",
    )

    export_mode = settings.get(
        "export_mode",
        "Single Format",
    )

    if export_mode not in (
        "Single Format",
        "Multiple Formats",
    ):
        export_mode = (
            "Single Format"
        )

    st.session_state[
        "output_export_mode"
    ] = export_mode

    saved_formats = settings.get(
        "selected_formats",
        ["PNG"],
    )

    if not isinstance(
        saved_formats,
        list,
    ):
        saved_formats = [
            "PNG"
        ]

    saved_formats = [
        item
        for item in saved_formats
        if item
        in VALID_EXPORT_FORMATS
    ]

    if not saved_formats:
        saved_formats = [
            "PNG"
        ]

    st.session_state[
        "output_single_format"
    ] = saved_formats[0]

    st.session_state[
        "output_multiple_formats"
    ] = saved_formats

    pixel_mode = settings.get(
        "pixel_mode",
        "Original Size",
    )

    if pixel_mode not in (
        "Original Size",
        "Target Total Pixels",
        "Custom Dimensions",
    ):
        pixel_mode = (
            "Original Size"
        )

    st.session_state[
        "output_pixel_mode"
    ] = pixel_mode

    saved_width = max(
        1,
        min(
            int(
                settings.get(
                    "target_width",
                    1,
                )
            ),
            150000,
        ),
    )

    saved_height = max(
        1,
        min(
            int(
                settings.get(
                    "target_height",
                    1,
                )
            ),
            150000,
        ),
    )

    st.session_state[
        "output_custom_width"
    ] = saved_width

    st.session_state[
        "output_custom_height"
    ] = saved_height

    st.session_state[
        "output_target_pixels"
    ] = max(
        1,
        min(
            int(
                settings.get(
                    "target_total_pixels",
                    saved_width
                    * saved_height,
                )
            ),
            150000,
        ),
    )

    st.session_state[
        "output_maintain_ratio"
    ] = bool(
        settings.get(
            "maintain_ratio",
            True,
        )
    )

    saved_dpi = max(
        72,
        min(
            int(
                settings.get(
                    "dpi",
                    300,
                )
            ),
            1200,
        ),
    )

    if saved_dpi in DPI_PRESETS:

        st.session_state[
            "output_dpi_mode"
        ] = "Preset"

        st.session_state[
            "output_dpi_preset"
        ] = saved_dpi

    else:

        st.session_state[
            "output_dpi_mode"
        ] = "Custom"

        st.session_state[
            "output_custom_dpi"
        ] = saved_dpi

    color_mode = settings.get(
        "color_mode",
        "RGB",
    )

    if color_mode not in (
        "RGB",
        "CMYK",
        "Grayscale",
    ):
        color_mode = "RGB"

    st.session_state[
        "output_color_mode"
    ] = color_mode

    resize_mode = settings.get(
        "resize_mode",
        "Fit",
    )

    if resize_mode not in (
        "Fit",
        "Fill & Crop",
        "Stretch",
    ):
        resize_mode = "Fit"

    st.session_state[
        "output_resize_mode"
    ] = resize_mode

    st.session_state[
        "output_quality"
    ] = max(
        1,
        min(
            int(
                settings.get(
                    "quality",
                    95,
                )
            ),
            100,
        ),
    )

    st.session_state[
        "output_png_compression"
    ] = max(
        0,
        min(
            int(
                settings.get(
                    "png_compress_level",
                    6,
                )
            ),
            9,
        ),
    )

    st.session_state[
        "output_webp_lossless"
    ] = bool(
        settings.get(
            "webp_lossless",
            False,
        )
    )

    tiff_value = settings.get(
        "tiff_compression",
        "tiff_lzw",
    )

    tiff_reverse = {
        "tiff_lzw":
            "LZW - Lossless",

        "tiff_adobe_deflate":
            "Deflate - Lossless",

        "raw":
            "Uncompressed",

        "LZW - Lossless":
            "LZW - Lossless",

        "Deflate - Lossless":
            "Deflate - Lossless",

        "Uncompressed":
            "Uncompressed",
    }

    st.session_state[
        "output_tiff_compression"
    ] = tiff_reverse.get(
        tiff_value,
        "LZW - Lossless",
    )

    purpose = settings.get(
        "smart_export_purpose",
        "General Purpose",
    )

    if purpose not in EXPORT_PURPOSES:
        purpose = "General Purpose"

    st.session_state[
        "smart_export_purpose"
    ] = purpose

    priority = settings.get(
        "smart_export_priority",
        "Balanced",
    )

    if (
        priority
        not in SMART_EXPORT_PRIORITIES
    ):
        priority = "Balanced"

    st.session_state[
        "smart_export_priority"
    ] = priority

    st.session_state[
        "project_settings_applied"
    ] = True


# =========================================================
# LAYER PANEL
# =========================================================

def render_layer_panel(
    prefix,
    info_type="basic",
):

    layers_key = (
        f"{prefix}_layers"
    )

    visibility_key = (
        f"{prefix}_visibility"
    )

    opacity_key = (
        f"{prefix}_opacity"
    )

    names_key = (
        f"{prefix}_names"
    )

    if (
        layers_key
        not in st.session_state
    ):
        return None

    layers = (
        st.session_state[
            layers_key
        ]
    )

    if not layers:

        st.warning(
            "All layers have been deleted."
        )

        return None

    st.write(
        f"Total Layers: "
        f"**{len(layers)}**"
    )

    for index, layer in enumerate(
        layers
    ):

        uid = layer["_uid"]

        with st.container(
            border=True
        ):

            title_col, delete_col = (
                st.columns(
                    [5, 1]
                )
            )

            with title_col:

                st.markdown(
                    f"### 🧩 Layer "
                    f"{index + 1}"
                )

            with delete_col:

                if st.button(
                    "🗑️ Delete",
                    key=(
                        f"delete_{uid}"
                    ),
                ):

                    st.session_state[
                        layers_key
                    ].pop(index)

                    st.session_state[
                        visibility_key
                    ].pop(index)

                    st.session_state[
                        opacity_key
                    ].pop(index)

                    st.session_state[
                        names_key
                    ].pop(index)

                    st.rerun()

            preview_col, control_col = (
                st.columns(
                    [1, 2]
                )
            )

            with preview_col:

                if "image" in layer:

                    st.image(
                        layer["image"],
                        use_container_width=True,
                    )

                if info_type in (
                    "color",
                    "smartcolor",
                ):

                    if "hex" in layer:

                        st.color_picker(
                            "Detected Color",
                            value=(
                                layer["hex"]
                            ),
                            disabled=True,
                            key=(
                                f"color_{uid}"
                            ),
                        )

                    if "percentage" in layer:

                        st.caption(
                            f"Area: "
                            f"{layer['percentage']}%"
                        )

                elif info_type == "semantic":

                    st.caption(
                        f"Type: "
                        f"{layer.get('type', 'region')}"
                    )

                elif info_type in (
                    "object",
                    "segmentation",
                ):

                    st.write(
                        f"**Object:** "
                        f"{layer.get('object_name', 'Object')}"
                    )

                    st.caption(
                        f"Confidence: "
                        f"{layer.get('confidence', 0)}%"
                    )

                elif info_type == "text":

                    st.caption(
                        "Type: Text Region"
                    )

                elif info_type == "ocr":

                    st.write(
                        f"**Text:** "
                        f"{layer.get('text', '')}"
                    )

                    st.caption(
                        f"Confidence: "
                        f"{layer.get('confidence', 0)}%"
                    )

            with control_col:

                layer_name = (
                    st.text_input(
                        "Layer Name",
                        value=(
                            st.session_state[
                                names_key
                            ][index]
                        ),
                        key=(
                            f"name_{uid}"
                        ),
                    )
                )

                st.session_state[
                    names_key
                ][index] = layer_name

                visible = (
                    st.checkbox(
                        "👁 Show Layer",
                        value=(
                            st.session_state[
                                visibility_key
                            ][index]
                        ),
                        key=(
                            f"visible_{uid}"
                        ),
                    )
                )

                st.session_state[
                    visibility_key
                ][index] = visible

                opacity = (
                    st.slider(
                        "Opacity",
                        min_value=0,
                        max_value=100,
                        value=(
                            st.session_state[
                                opacity_key
                            ][index]
                        ),
                        key=(
                            f"opacity_{uid}"
                        ),
                    )
                )

                st.session_state[
                    opacity_key
                ][index] = opacity

    return rebuild_image(
        st.session_state[
            layers_key
        ],
        visibility=(
            st.session_state[
                visibility_key
            ]
        ),
        opacities=(
            st.session_state[
                opacity_key
            ]
        ),
    )


# =========================================================
# HEADER
# =========================================================

st.title(
    "🖼️ AI Image Studio"
)

st.subheader(
    "Multi-Format Input • PDF All Pages • "
    "Analysis • Editable Layers • OCR • "
    "Professional Export"
)

st.caption(
    "JPG • PNG • WEBP • TIFF • BMP • "
    "PDF • SVG • HEIC • HEIF"
)

st.divider()


# =========================================================
# 01 — OPEN FILE
# =========================================================

st.header(
    "01 — 📂 Open Image or Project"
)


image_tab, project_tab = (
    st.tabs(
        [
            "🖼️ Open Image / PDF / SVG / HEIC",
            "📁 Open .aistudio Project",
        ]
    )
)


prepared_normal_uploaded_files = []
normal_input_metadata = None


# =========================================================
# IMAGE INPUT
# =========================================================

with image_tab:

    normal_uploaded_files = (
        st.file_uploader(
            "Drag & Drop Image or Document Here",
            type=[
                "jpg",
                "jpeg",
                "png",
                "webp",
                "tiff",
                "tif",
                "bmp",
                "pdf",
                "svg",
                "heic",
                "heif",
            ],
            accept_multiple_files=True,
            key="normal_image_uploader",
        )
    )

    st.caption(
        "Supported: JPG, JPEG, PNG, WEBP, TIFF, BMP, "
        "PDF, SVG, HEIC and HEIF"
    )

    if normal_uploaded_files:

        first_normal_file = (
            normal_uploaded_files[0]
        )

        first_normal_bytes = (
            first_normal_file.getvalue()
        )

        try:

            first_input_info = (
                cached_get_input_info(
                    first_normal_bytes,
                    first_normal_file.name,
                )
            )

            input_type = (
                first_input_info.get(
                    "type",
                    "image",
                )
            )

            extension = (
                first_input_info.get(
                    "extension",
                    "",
                )
            )

            input_render_dpi = 150
            selected_pdf_page = 1
            pdf_page_mode = "Single Page"


            # =============================================
            # PDF
            # =============================================

            if input_type == "pdf":

                page_count = int(
                    first_input_info.get(
                        "page_count",
                        1,
                    )
                )

                st.success(
                    f"📄 PDF detected — "
                    f"{page_count} page(s)"
                )

                pdf_page_mode = (
                    st.radio(
                        "PDF Page Mode",
                        [
                            "Single Page",
                            "All Pages",
                        ],
                        horizontal=True,
                        key="input_pdf_page_mode",
                    )
                )

                pdf_col1, pdf_col2 = (
                    st.columns(2)
                )

                with pdf_col2:

                    input_render_dpi = (
                        st.select_slider(
                            "PDF Render DPI",
                            options=(
                                INPUT_RENDER_DPI_PRESETS
                            ),
                            value=150,
                            key="input_pdf_render_dpi",
                        )
                    )

                if (
                    pdf_page_mode
                    == "Single Page"
                ):

                    with pdf_col1:

                        selected_pdf_page = (
                            st.number_input(
                                "PDF Page",
                                min_value=1,
                                max_value=page_count,
                                value=1,
                                step=1,
                                key="input_pdf_page",
                            )
                        )

                    with st.spinner(
                        "Preparing selected PDF page..."
                    ):

                        prepared_first = (
                            cached_prepare_input(
                                first_normal_bytes,
                                first_normal_file.name,
                                page_number=int(
                                    selected_pdf_page
                                ),
                                render_dpi=int(
                                    input_render_dpi
                                ),
                            )
                        )

                    first_stem = (
                        os.path.splitext(
                            first_normal_file.name
                        )[0]
                    )

                    prepared_name = (
                        f"{first_stem}"
                        f"_page_"
                        f"{int(selected_pdf_page)}"
                        f".png"
                    )

                    prepared_normal_uploaded_files.append(
                        MemoryUploadedFile(
                            prepared_name,
                            prepared_first[
                                "png_bytes"
                            ],
                        )
                    )

                    normal_input_metadata = {
                        "source_filename":
                            first_normal_file.name,

                        "source_format":
                            "PDF",

                        "source_mode":
                            prepared_first[
                                "mode"
                            ],

                        "source_width":
                            prepared_first[
                                "width"
                            ],

                        "source_height":
                            prepared_first[
                                "height"
                            ],

                        "source_dpi":
                            prepared_first[
                                "dpi"
                            ],

                        "input_type":
                            "pdf",

                        "pdf_page_mode":
                            "Single Page",

                        "selected_page":
                            int(
                                selected_pdf_page
                            ),

                        "page_count":
                            page_count,

                        "render_dpi":
                            int(
                                input_render_dpi
                            ),
                    }

                    st.info(
                        f"Editing PDF Page "
                        f"{int(selected_pdf_page)} "
                        f"of {page_count}"
                    )


                # =========================================
                # ALL PDF PAGES
                # =========================================

                else:

                    with pdf_col1:

                        st.metric(
                            "Pages to Process",
                            page_count,
                        )

                    if (
                        page_count >= 10
                        and
                        input_render_dpi >= 300
                    ):

                        st.warning(
                            "Large PDF + high render DPI can use "
                            "a lot of RAM. 150 DPI is recommended "
                            "for normal editing."
                        )

                    with st.spinner(
                        f"Preparing all {page_count} PDF pages..."
                    ):

                        all_pages = (
                            cached_prepare_all_pdf_pages(
                                first_normal_bytes,
                                render_dpi=int(
                                    input_render_dpi
                                ),
                            )
                        )

                    first_stem = (
                        os.path.splitext(
                            first_normal_file.name
                        )[0]
                    )

                    for page in all_pages:

                        page_number = (
                            page[
                                "page_number"
                            ]
                        )

                        page_name = (
                            f"{first_stem}"
                            f"_page_"
                            f"{page_number}"
                            f".png"
                        )

                        prepared_normal_uploaded_files.append(
                            MemoryUploadedFile(
                                page_name,
                                page[
                                    "png_bytes"
                                ],
                            )
                        )

                    if all_pages:

                        first_page = (
                            all_pages[0]
                        )

                        normal_input_metadata = {
                            "source_filename":
                                first_normal_file.name,

                            "source_format":
                                "PDF",

                            "source_mode":
                                first_page[
                                    "mode"
                                ],

                            "source_width":
                                first_page[
                                    "width"
                                ],

                            "source_height":
                                first_page[
                                    "height"
                                ],

                            "source_dpi":
                                first_page[
                                    "dpi"
                                ],

                            "input_type":
                                "pdf",

                            "pdf_page_mode":
                                "All Pages",

                            "selected_page":
                                1,

                            "page_count":
                                len(
                                    all_pages
                                ),

                            "render_dpi":
                                int(
                                    input_render_dpi
                                ),
                        }

                    st.success(
                        f"✅ {len(all_pages)} PDF page(s) "
                        f"prepared for batch export."
                    )

                    st.info(
                        "Page 1 is used in the editor preview. "
                        "During Original Image export, every PDF "
                        "page will be exported separately."
                    )

                    preview_count = min(
                        len(all_pages),
                        6,
                    )

                    if preview_count > 0:

                        st.subheader(
                            "📄 PDF Page Preview"
                        )

                        preview_columns = (
                            st.columns(
                                min(
                                    3,
                                    preview_count,
                                )
                            )
                        )

                        for index in range(
                            preview_count
                        ):

                            page = (
                                all_pages[
                                    index
                                ]
                            )

                            with Image.open(
                                io.BytesIO(
                                    page[
                                        "png_bytes"
                                    ]
                                )
                            ) as page_image:

                                preview_image = (
                                    page_image.copy()
                                )

                            with preview_columns[
                                index
                                % len(
                                    preview_columns
                                )
                            ]:

                                st.image(
                                    preview_image,
                                    caption=(
                                        f"Page "
                                        f"{page['page_number']}"
                                    ),
                                    use_container_width=True,
                                )

                    if (
                        len(all_pages)
                        > preview_count
                    ):

                        st.caption(
                            f"+ "
                            f"{len(all_pages) - preview_count} "
                            f"more page(s) prepared."
                        )


            # =============================================
            # SVG
            # =============================================

            elif input_type == "svg":

                st.info(
                    "🔷 SVG detected. "
                    "It will be rasterized for editing."
                )

                input_render_dpi = (
                    st.select_slider(
                        "SVG Render DPI",
                        options=(
                            INPUT_RENDER_DPI_PRESETS
                        ),
                        value=150,
                        key="input_svg_render_dpi",
                    )
                )

                with st.spinner(
                    "Preparing SVG..."
                ):

                    prepared_first = (
                        cached_prepare_input(
                            first_normal_bytes,
                            first_normal_file.name,
                            page_number=1,
                            render_dpi=int(
                                input_render_dpi
                            ),
                        )
                    )

                first_stem = (
                    os.path.splitext(
                        first_normal_file.name
                    )[0]
                )

                prepared_name = (
                    f"{first_stem}.png"
                )

                prepared_normal_uploaded_files.append(
                    MemoryUploadedFile(
                        prepared_name,
                        prepared_first[
                            "png_bytes"
                        ],
                    )
                )

                normal_input_metadata = {
                    "source_filename":
                        first_normal_file.name,

                    "source_format":
                        "SVG",

                    "source_mode":
                        prepared_first[
                            "mode"
                        ],

                    "source_width":
                        prepared_first[
                            "width"
                        ],

                    "source_height":
                        prepared_first[
                            "height"
                        ],

                    "source_dpi":
                        prepared_first[
                            "dpi"
                        ],

                    "input_type":
                        "svg",

                    "page_count":
                        1,

                    "render_dpi":
                        int(
                            input_render_dpi
                        ),
                }

                for warning in (
                    prepared_first.get(
                        "warnings",
                        [],
                    )
                ):
                    st.warning(warning)


            # =============================================
            # NORMAL / HEIC / HEIF
            # =============================================

            else:

                if extension in (
                    ".heic",
                    ".heif",
                ):

                    st.info(
                        "📱 HEIC / HEIF image detected."
                    )

                with st.spinner(
                    "Preparing image..."
                ):

                    prepared_first = (
                        cached_prepare_input(
                            first_normal_bytes,
                            first_normal_file.name,
                            page_number=1,
                            render_dpi=150,
                        )
                    )

                first_stem = (
                    os.path.splitext(
                        first_normal_file.name
                    )[0]
                )

                prepared_name = (
                    f"{first_stem}.png"
                )

                prepared_normal_uploaded_files.append(
                    MemoryUploadedFile(
                        prepared_name,
                        prepared_first[
                            "png_bytes"
                        ],
                    )
                )

                normal_input_metadata = {
                    "source_filename":
                        first_normal_file.name,

                    "source_format":
                        prepared_first[
                            "format"
                        ],

                    "source_mode":
                        prepared_first[
                            "mode"
                        ],

                    "source_width":
                        prepared_first[
                            "width"
                        ],

                    "source_height":
                        prepared_first[
                            "height"
                        ],

                    "source_dpi":
                        prepared_first[
                            "dpi"
                        ],

                    "input_type":
                        prepared_first[
                            "type"
                        ],

                    "page_count":
                        1,
                }


            # =============================================
            # EXTRA UPLOADED FILES
            # =============================================

            if (
                len(
                    normal_uploaded_files
                )
                > 1
            ):

                st.caption(
                    "Additional uploaded files are also "
                    "prepared for batch export."
                )

                for extra_file in (
                    normal_uploaded_files[
                        1:
                    ]
                ):

                    try:

                        extra_bytes = (
                            extra_file.getvalue()
                        )

                        extra_info = (
                            cached_get_input_info(
                                extra_bytes,
                                extra_file.name,
                            )
                        )

                        extra_type = (
                            extra_info.get(
                                "type",
                                "image",
                            )
                        )

                        extra_stem = (
                            os.path.splitext(
                                extra_file.name
                            )[0]
                        )

                        if extra_type == "pdf":

                            extra_result = (
                                cached_prepare_input(
                                    extra_bytes,
                                    extra_file.name,
                                    page_number=1,
                                    render_dpi=150,
                                )
                            )

                            extra_name = (
                                f"{extra_stem}"
                                f"_page_1.png"
                            )

                        else:

                            extra_result = (
                                cached_prepare_input(
                                    extra_bytes,
                                    extra_file.name,
                                    page_number=1,
                                    render_dpi=150,
                                )
                            )

                            extra_name = (
                                f"{extra_stem}.png"
                            )

                        prepared_normal_uploaded_files.append(
                            MemoryUploadedFile(
                                extra_name,
                                extra_result[
                                    "png_bytes"
                                ],
                            )
                        )

                    except Exception as extra_error:

                        st.warning(
                            f"Could not prepare "
                            f"{extra_file.name}: "
                            f"{extra_error}"
                        )


            if normal_input_metadata:

                st.session_state[
                    "normal_input_metadata"
                ] = normal_input_metadata


        except Exception as error:

            st.error(
                "Could not process uploaded file."
            )

            st.exception(
                error
            )


# =========================================================
# INPUT CHANGE
# =========================================================

if prepared_normal_uploaded_files:

    input_names = tuple(
        file.name
        for file in (
            prepared_normal_uploaded_files
        )
    )

    normal_signature = (
        input_names,
        hashlib.sha1(
            prepared_normal_uploaded_files[
                0
            ].getvalue()
        ).hexdigest(),
    )

    if (
        st.session_state.get(
            "last_normal_upload_signature"
        )
        != normal_signature
    ):

        st.session_state[
            "last_normal_upload_signature"
        ] = normal_signature

        st.session_state[
            "active_input_mode"
        ] = "image"

        st.session_state[
            "project_is_open"
        ] = False


# =========================================================
# PROJECT TAB
# =========================================================

with project_tab:

    project_file = (
        st.file_uploader(
            "Open AI Image Studio Project",
            type=[
                "aistudio",
            ],
            accept_multiple_files=False,
            key="project_uploader",
        )
    )

    if project_file is not None:

        try:

            project_information = (
                get_project_info(
                    project_file.getvalue()
                )
            )

            p1, p2 = (
                st.columns(2)
            )

            p1.write(
                "**Original File:** "
                f"{project_information.get('original_filename')}"
            )

            p1.write(
                "**Version:** "
                f"{project_information.get('version')}"
            )

            p2.write(
                "**Layer Groups:** "
                f"{project_information.get('group_count')}"
            )

            p2.write(
                "**Total Layers:** "
                f"{project_information.get('total_layers')}"
            )

            if st.button(
                "📂 Open Project",
                type="primary",
                use_container_width=True,
            ):

                loaded_project = (
                    load_project(
                        project_file.getvalue()
                    )
                )

                clear_workspace_state()

                project_original = (
                    loaded_project[
                        "original_image"
                    ]
                )

                project_image_bytes = (
                    image_to_bytes(
                        project_original
                    )
                )

                project_filename = (
                    loaded_project.get(
                        "original_filename",
                        "project_image.png",
                    )
                )

                loaded_settings = (
                    loaded_project.get(
                        "settings",
                        {},
                    )
                )

                st.session_state[
                    "opened_project_image_bytes"
                ] = project_image_bytes

                st.session_state[
                    "opened_project_filename"
                ] = project_filename

                group_prefixes = {
                    "color":
                        "color",

                    "semantic":
                        "semantic",

                    "object":
                        "object",

                    "segment":
                        "segment",

                    "smartcolor":
                        "smartcolor",

                    "text":
                        "text",

                    "ocr":
                        "ocr",
                }

                for (
                    group_name,
                    prefix
                ) in (
                    group_prefixes.items()
                ):

                    layers = (
                        loaded_project[
                            "layer_groups"
                        ].get(
                            group_name,
                            [],
                        )
                    )

                    if layers:

                        restore_project_layers(
                            prefix,
                            layers,
                        )

                edited_image = (
                    loaded_project.get(
                        "edited_image"
                    )
                )

                saved_export_source = (
                    loaded_settings.get(
                        "export_source",
                        "Original Image",
                    )
                )

                if isinstance(
                    edited_image,
                    Image.Image,
                ):

                    if (
                        saved_export_source
                        == "Background Removed Image"
                    ):

                        st.session_state[
                            "background_remove_result"
                        ] = {
                            "image":
                                edited_image,

                            "mask":
                                None,
                        }

                    else:

                        st.session_state[
                            "smart_color_result"
                        ] = edited_image

                st.session_state[
                    "loaded_project_settings"
                ] = loaded_settings

                st.session_state[
                    "project_settings_applied"
                ] = False

                st.session_state[
                    "project_is_open"
                ] = True

                st.session_state[
                    "active_input_mode"
                ] = "project"

                st.session_state[
                    "active_image_signature"
                ] = (
                    project_filename,

                    hashlib.sha1(
                        project_image_bytes
                    ).hexdigest(),
                )

                st.rerun()

        except Exception as error:

            st.error(
                "Could not read this "
                ".aistudio project."
            )

            st.exception(
                error
            )


# =========================================================
# ACTIVE INPUT
# =========================================================

if (
    st.session_state.get(
        "active_input_mode"
    )
    == "project"
    and
    st.session_state.get(
        "project_is_open",
        False,
    )
    and
    "opened_project_image_bytes"
    in st.session_state
):

    uploaded_files = [

        MemoryUploadedFile(
            st.session_state.get(
                "opened_project_filename",
                "project_image.png",
            ),

            st.session_state[
                "opened_project_image_bytes"
            ],
        )
    ]


elif prepared_normal_uploaded_files:

    uploaded_files = (
        prepared_normal_uploaded_files
    )

    st.session_state[
        "active_input_mode"
    ] = "image"


else:

    uploaded_files = []


if not uploaded_files:

    st.info(
        "Upload an image, PDF, SVG, HEIC/HEIF "
        "or open an .aistudio project."
    )

    st.stop()


st.success(
    f"{len(uploaded_files)} "
    f"prepared image/page(s) ready."
)


# =========================================================
# ACTIVE IMAGE
# =========================================================

first_bytes = (
    uploaded_files[
        0
    ].getvalue()
)


current_signature = (
    uploaded_files[
        0
    ].name,

    hashlib.sha1(
        first_bytes
    ).hexdigest(),
)


if (
    st.session_state.get(
        "active_image_signature"
    )
    != current_signature
):

    if not st.session_state.get(
        "project_is_open",
        False,
    ):

        clear_workspace_state()

    st.session_state[
        "active_image_signature"
    ] = current_signature


with Image.open(
    io.BytesIO(
        first_bytes
    )
) as opened:

    first_image = opened.copy()

    prepared_format = opened.format

    prepared_mode = opened.mode

    prepared_dpi = (
        opened.info.get(
            "dpi",
            "Not available",
        )
    )


original_width, original_height = (
    first_image.size
)


source_metadata = (
    st.session_state.get(
        "normal_input_metadata",
        {},
    )
    if (
        st.session_state.get(
            "active_input_mode"
        )
        == "image"
    )
    else {}
)


# =========================================================
# 02 — ORIGINAL IMAGE
# =========================================================

st.header(
    "02 — Original / Prepared Image"
)


preview_col, info_col = (
    st.columns(2)
)


with preview_col:

    st.image(
        first_image,
        caption=(
            uploaded_files[
                0
            ].name
        ),
        use_container_width=True,
    )


with info_col:

    st.metric(
        "Width",
        f"{original_width:,} px",
    )

    st.metric(
        "Height",
        f"{original_height:,} px",
    )

    st.metric(
        "Total Pixels",
        f"{original_width * original_height:,}",
    )

    st.write(
        f"**Source Format:** "
        f"{source_metadata.get('source_format', prepared_format)}"
    )

    st.write(
        f"**Editing Mode:** "
        f"{prepared_mode}"
    )

    st.write(
        f"**Source DPI:** "
        f"{source_metadata.get('source_dpi', prepared_dpi)}"
    )


if (
    source_metadata.get(
        "input_type"
    )
    == "pdf"
):

    pdf_mode = (
        source_metadata.get(
            "pdf_page_mode",
            "Single Page",
        )
    )

    if pdf_mode == "All Pages":

        st.success(
            f"📚 All Pages mode active — "
            f"{source_metadata.get('page_count', len(uploaded_files))} "
            f"PDF page(s) prepared."
        )

        st.caption(
            "Page 1 is displayed for editing. "
            "Choose Original Image during export to "
            "export every PDF page separately."
        )

    else:

        st.info(
            f"PDF Page "
            f"{source_metadata.get('selected_page', 1)} "
            f"of "
            f"{source_metadata.get('page_count', 1)}"
        )


st.divider()


# =========================================================
# 03 — IMAGE ANALYSIS
# =========================================================

st.header(
    "03 — 🤖 Image Analysis"
)


with st.spinner(
    "Analyzing image..."
):

    analysis = (
        cached_ai_analysis(
            first_bytes
        )
    )


stats = (
    analysis[
        "statistics"
    ]
)


a1, a2, a3, a4 = (
    st.columns(4)
)


a1.metric(
    "Width",
    f"{stats['width']} px",
)

a2.metric(
    "Height",
    f"{stats['height']} px",
)

a3.metric(
    "Total Pixels",
    f"{stats['total_pixels']:,}",
)

a4.metric(
    "Edge Features",
    f"{analysis['edge_pixels']:,}",
)


if stats["transparency"]:

    st.info(
        "Transparency detected: "
        f"{stats['transparent_percentage']}%"
    )


dominant_colors = (
    analysis[
        "dominant_colors"
    ]
)


st.subheader(
    "🎨 Dominant Colors"
)


if dominant_colors:

    columns = st.columns(
        len(
            dominant_colors
        )
    )

    for index, (
        column,
        color
    ) in enumerate(
        zip(
            columns,
            dominant_colors,
        )
    ):

        with column:

            st.color_picker(
                f"Color {index + 1}",
                value=color["hex"],
                disabled=True,
                key=(
                    f"analysis_color_{index}"
                ),
            )

            st.caption(
                color["hex"].upper()
            )

            st.caption(
                f"{color['percentage']}%"
            )


shapes = analysis["shapes"]


st.subheader(
    "🔷 Shape Analysis"
)


s1, s2, s3, s4 = (
    st.columns(4)
)


s1.metric(
    "Rectangles",
    shapes["rectangles"],
)

s2.metric(
    "Triangles",
    shapes["triangles"],
)

s3.metric(
    "Circles / Curves",
    shapes["circles_or_curves"],
)

s4.metric(
    "Other Shapes",
    shapes["other_shapes"],
)


st.divider()


# =========================================================
# 04 — COLOR LAYERS
# =========================================================

st.header(
    "04 — 🎨 Color Editable Layers"
)


color_layer_count = (
    st.slider(
        "Number of Color Layers",
        2,
        12,
        6,
    )
)


if st.button(
    "🎨 Extract Color Layers",
    use_container_width=True,
):

    with st.spinner(
        "Creating color layers..."
    ):

        color_layers = (
            extract_color_layers(
                first_image,
                layer_count=(
                    color_layer_count
                ),
            )
        )

    initialize_layer_state(
        "color",
        color_layers,
    )


if "color_layers" in st.session_state:

    color_rebuilt = (
        render_layer_panel(
            "color",
            "color",
        )
    )

    if isinstance(
        color_rebuilt,
        Image.Image,
    ):

        st.image(
            color_rebuilt,
            caption=(
                "Color Reconstruction"
            ),
            use_container_width=True,
        )


st.divider()


# =========================================================
# 05 — SEMANTIC
# =========================================================

st.header(
    "05 — 🧠 Smart Semantic Layers"
)


st.info(
    "Semantic separation is approximate."
)


if st.button(
    "✨ Detect Smart Semantic Layers",
    use_container_width=True,
):

    with st.spinner(
        "Detecting regions..."
    ):

        semantic_layers = (
            create_semantic_layers(
                first_image
            )
        )

    initialize_layer_state(
        "semantic",
        semantic_layers,
    )


if "semantic_layers" in st.session_state:

    render_layer_panel(
        "semantic",
        "semantic",
    )


st.divider()


# =========================================================
# 06 — OBJECT DETECTION
# =========================================================

st.header(
    "06 — 🎯 AI Object Recognition"
)


object_confidence = (
    st.slider(
        "Object Detection Confidence",
        20,
        95,
        50,
        5,
    )
)


max_objects = (
    st.slider(
        "Maximum Objects",
        1,
        20,
        10,
    )
)


if st.button(
    "🎯 Detect & Recognize Objects",
    use_container_width=True,
):

    try:

        with st.spinner(
            "Recognizing objects..."
        ):

            result = (
                create_object_layers(
                    first_image,
                    confidence_threshold=(
                        object_confidence
                        / 100
                    ),
                    max_objects=(
                        max_objects
                    ),
                )
            )

        st.session_state[
            "object_result"
        ] = result

        if result["layers"]:

            initialize_layer_state(
                "object",
                result["layers"],
            )

    except Exception as error:

        st.exception(error)


if "object_result" in st.session_state:

    st.image(
        st.session_state[
            "object_result"
        ]["preview"],
        use_container_width=True,
    )


if "object_layers" in st.session_state:

    render_layer_panel(
        "object",
        "object",
    )


st.divider()


# =========================================================
# 07 — SEGMENTATION
# =========================================================

st.header(
    "07 — ✂️ Segmentation & Background Removal"
)


seg_tab, bg_tab = (
    st.tabs(
        [
            "🎯 Object Segmentation",
            "🪄 Background Removal",
        ]
    )
)


with seg_tab:

    seg_confidence = (
        st.slider(
            "Segmentation Confidence",
            20,
            95,
            50,
            5,
        )
    )

    seg_max_objects = (
        st.slider(
            "Maximum Segmented Objects",
            1,
            20,
            10,
        )
    )

    seg_iterations = (
        st.slider(
            "Segmentation Refinement",
            1,
            10,
            5,
        )
    )

    seg_feather = (
        st.slider(
            "Edge Feather",
            0,
            15,
            3,
        )
    )

    if st.button(
        "✂️ Segment Detected Objects",
        use_container_width=True,
    ):

        try:

            result = (
                create_segmented_object_layers(
                    first_image,
                    confidence_threshold=(
                        seg_confidence
                        / 100
                    ),
                    max_objects=(
                        seg_max_objects
                    ),
                    iterations=(
                        seg_iterations
                    ),
                    feather=(
                        seg_feather
                    ),
                )
            )

            st.session_state[
                "segmentation_result"
            ] = result

            if result["layers"]:

                initialize_layer_state(
                    "segment",
                    result["layers"],
                )

        except Exception as error:

            st.exception(error)

    if (
        "segmentation_result"
        in st.session_state
    ):

        st.image(
            st.session_state[
                "segmentation_result"
            ]["preview"],
            use_container_width=True,
        )

    if "segment_layers" in st.session_state:

        render_layer_panel(
            "segment",
            "segmentation",
        )


with bg_tab:

    bg_margin = (
        st.slider(
            "Background Detection Margin (%)",
            1,
            15,
            3,
        )
    )

    bg_iterations = (
        st.slider(
            "Background Refinement",
            1,
            10,
            5,
        )
    )

    bg_feather = (
        st.slider(
            "Background Edge Feather",
            0,
            15,
            3,
        )
    )

    if st.button(
        "🪄 Remove Background",
        use_container_width=True,
    ):

        try:

            result = (
                remove_background(
                    first_image,
                    margin_percent=(
                        bg_margin
                        / 100
                    ),
                    iterations=(
                        bg_iterations
                    ),
                    feather=(
                        bg_feather
                    ),
                )
            )

            st.session_state[
                "background_remove_result"
            ] = result

        except Exception as error:

            st.exception(error)

    if (
        "background_remove_result"
        in st.session_state
    ):

        st.image(
            st.session_state[
                "background_remove_result"
            ]["image"],
            use_container_width=True,
        )


st.divider()


# =========================================================
# 08 — COLOR EDITOR
# =========================================================

st.header(
    "08 — 🎨 Smart Color Editor"
)


default_source_color = (
    dominant_colors[0]["hex"]
    if dominant_colors
    else "#000000"
)


color_tabs = st.tabs(
    [
        "🎨 Replace",
        "🫥 Remove",
        "🧩 Extract",
        "🔀 Merge",
    ]
)


with color_tabs[0]:

    source_color = (
        st.color_picker(
            "Source Color",
            default_source_color,
        )
    )

    new_color = (
        st.color_picker(
            "New Color",
            "#FF0000",
        )
    )

    tolerance = (
        st.slider(
            "Tolerance",
            0,
            255,
            30,
        )
    )

    preserve = (
        st.checkbox(
            "Preserve Light / Shadow",
            True,
        )
    )

    source_rgb = (
        hex_to_rgb(
            source_color
        )
    )

    st.image(
        create_mask_preview(
            first_image,
            source_rgb,
            tolerance,
        ),
        use_container_width=True,
    )

    if st.button(
        "🎨 Apply Color Replacement",
        use_container_width=True,
    ):

        st.session_state[
            "smart_color_result"
        ] = replace_color(
            first_image,
            source_rgb,
            hex_to_rgb(
                new_color
            ),
            tolerance=tolerance,
            preserve_shading=preserve,
        )

        st.rerun()


with color_tabs[1]:

    remove_target = (
        st.color_picker(
            "Color to Remove",
            default_source_color,
            key="remove_target",
        )
    )

    remove_tolerance = (
        st.slider(
            "Remove Tolerance",
            0,
            255,
            30,
        )
    )

    remove_feather = (
        st.slider(
            "Remove Feather",
            0,
            15,
            3,
        )
    )

    if st.button(
        "🫥 Remove Selected Color",
        use_container_width=True,
    ):

        st.session_state[
            "smart_color_result"
        ] = remove_color(
            first_image,
            hex_to_rgb(
                remove_target
            ),
            tolerance=(
                remove_tolerance
            ),
            feather=(
                remove_feather
            ),
        )

        st.rerun()


with color_tabs[2]:

    extract_target = (
        st.color_picker(
            "Color to Extract",
            default_source_color,
            key="extract_target",
        )
    )

    extract_tolerance = (
        st.slider(
            "Extraction Tolerance",
            0,
            255,
            30,
        )
    )

    if st.button(
        "🧩 Extract Selected Color",
        use_container_width=True,
    ):

        layer = (
            extract_color_layer(
                first_image,
                hex_to_rgb(
                    extract_target
                ),
                tolerance=(
                    extract_tolerance
                ),
                feather=1,
            )
        )

        initialize_layer_state(
            "smartcolor",
            [layer],
        )

        st.rerun()

    if (
        "smartcolor_layers"
        in st.session_state
    ):

        render_layer_panel(
            "smartcolor",
            "smartcolor",
        )


with color_tabs[3]:

    merge_one = (
        st.color_picker(
            "Source Color 1",
            default_source_color,
            key="merge_one",
        )
    )

    merge_two = (
        st.color_picker(
            "Source Color 2",
            "#808080",
            key="merge_two",
        )
    )

    destination = (
        st.color_picker(
            "Destination",
            "#0000FF",
        )
    )

    merge_tolerance = (
        st.slider(
            "Merge Tolerance",
            0,
            255,
            30,
        )
    )

    if st.button(
        "🔀 Merge Colors",
        use_container_width=True,
    ):

        st.session_state[
            "smart_color_result"
        ] = merge_colors(
            first_image,
            [
                hex_to_rgb(
                    merge_one
                ),
                hex_to_rgb(
                    merge_two
                ),
            ],
            hex_to_rgb(
                destination
            ),
            tolerance=(
                merge_tolerance
            ),
            preserve_shading=True,
        )

        st.rerun()


if "smart_color_result" in st.session_state:

    st.image(
        st.session_state[
            "smart_color_result"
        ],
        caption="Edited Result",
        use_container_width=True,
    )


st.divider()


# =========================================================
# 09 — TEXT
# =========================================================

st.header(
    "09 — 🔤 Text Detection"
)


if st.button(
    "🔍 Detect Text Regions",
    use_container_width=True,
):

    result = (
        create_text_layers(
            first_image,
            individual=True,
        )
    )

    st.session_state[
        "text_detection_result"
    ] = result

    if result["individual_layers"]:

        initialize_layer_state(
            "text",
            result[
                "individual_layers"
            ],
        )

    st.rerun()


if (
    "text_detection_result"
    in st.session_state
):

    st.image(
        st.session_state[
            "text_detection_result"
        ]["preview"],
        use_container_width=True,
    )


if "text_layers" in st.session_state:

    render_layer_panel(
        "text",
        "text",
    )


st.divider()


# =========================================================
# 10 — OCR
# =========================================================

st.header(
    "10 — 🔎 OCR"
)


ocr_confidence = (
    st.slider(
        "OCR Minimum Confidence",
        10,
        95,
        30,
        5,
    )
)


if st.button(
    "🤖 Read Text with OCR",
    use_container_width=True,
):

    try:

        with st.spinner(
            "Reading text..."
        ):

            result = (
                create_ocr_layers(
                    first_image,
                    confidence_threshold=(
                        ocr_confidence
                        / 100
                    ),
                )
            )

        st.session_state[
            "ocr_result"
        ] = result

        if result["layers"]:

            initialize_layer_state(
                "ocr",
                result["layers"],
            )

        st.rerun()

    except Exception as error:

        st.exception(error)


if "ocr_result" in st.session_state:

    result = (
        st.session_state[
            "ocr_result"
        ]
    )

    st.image(
        result["preview"],
        use_container_width=True,
    )

    if result["full_text"].strip():

        st.text_area(
            "Extracted Text",
            result["full_text"],
            height=180,
        )


if "ocr_layers" in st.session_state:

    render_layer_panel(
        "ocr",
        "ocr",
    )


st.divider()


# =========================================================
# OUTPUT DEFAULTS
# =========================================================

ensure_output_defaults(
    original_width,
    original_height,
)

apply_loaded_project_settings()


# =========================================================
# 11 — EXPORT SOURCE
# =========================================================

st.header(
    "11 — 🎯 Export Source & Smart Export"
)


available_export_sources = (
    build_export_sources(
        first_image
    )
)


source_names = list(
    available_export_sources.keys()
)


if (
    st.session_state.get(
        "output_export_source"
    )
    not in source_names
):

    st.session_state[
        "output_export_source"
    ] = "Original Image"


selected_export_source = (
    st.selectbox(
        "Choose Final Export Source",
        source_names,
        key="output_export_source",
    )
)


export_source_image = (
    available_export_sources[
        selected_export_source
    ]
)


st.image(
    export_source_image,
    caption=selected_export_source,
    use_container_width=True,
)


if (
    source_metadata.get(
        "pdf_page_mode"
    )
    == "All Pages"
    and
    selected_export_source
    != "Original Image"
):

    st.warning(
        "All PDF pages are batch exported only when "
        "'Original Image' is selected. Edited sources "
        "currently apply to Page 1 only."
    )


# =========================================================
# SMART EXPORT
# =========================================================

st.subheader(
    "🧠 Smart Export Recommendation"
)


smart1, smart2 = (
    st.columns(2)
)


with smart1:

    smart_purpose = (
        st.selectbox(
            "Export Purpose",
            EXPORT_PURPOSES,
            key="smart_export_purpose",
        )
    )


with smart2:

    smart_priority = (
        st.selectbox(
            "Priority",
            SMART_EXPORT_PRIORITIES,
            key="smart_export_priority",
        )
    )


try:

    recommendation = (
        recommend_export_settings(
            export_source_image,
            purpose=smart_purpose,
            file_size_priority=(
                smart_priority
            ),
        )
    )

    r1, r2, r3, r4 = (
        st.columns(4)
    )

    r1.metric(
        "Format",
        recommendation["format"],
    )

    r2.metric(
        "DPI",
        recommendation["dpi"],
    )

    r3.metric(
        "Color Mode",
        recommendation[
            "color_mode"
        ],
    )

    r4.metric(
        "Quality",
        recommendation["quality"],
    )

    st.info(
        recommendation["reason"]
    )

    for warning in (
        recommendation["warnings"]
    ):
        st.warning(warning)

except Exception as error:

    st.warning(
        f"Smart recommendation unavailable: "
        f"{error}"
    )


st.divider()


# =========================================================
# 12 — OUTPUT SETTINGS
# =========================================================

st.header(
    "12 — 🖨️ Professional Output Settings"
)


export_mode = (
    st.radio(
        "Export Mode",
        [
            "Single Format",
            "Multiple Formats",
        ],
        horizontal=True,
        key="output_export_mode",
    )
)


if export_mode == "Single Format":

    selected_formats = [
        st.selectbox(
            "Output Format",
            VALID_EXPORT_FORMATS,
            key="output_single_format",
        )
    ]

else:

    selected_formats = (
        st.multiselect(
            "Output Formats",
            VALID_EXPORT_FORMATS,
            key="output_multiple_formats",
        )
    )


if "PSD (Flattened)" in selected_formats:

    st.info(
        "PSD output is flattened. "
        "It does not contain original Photoshop layers."
    )


pixel_mode = (
    st.selectbox(
        "Pixel Size Mode",
        [
            "Original Size",
            "Target Total Pixels",
            "Custom Dimensions",
        ],
        key="output_pixel_mode",
    )
)


source_width, source_height = (
    export_source_image.size
)


target_total_pixels = (
    st.session_state.get(
        "output_target_pixels",
        100000,
    )
)


maintain_ratio = (
    st.session_state.get(
        "output_maintain_ratio",
        True,
    )
)


if pixel_mode == "Original Size":

    target_width = source_width
    target_height = source_height


elif (
    pixel_mode
    == "Target Total Pixels"
):

    target_total_pixels = (
        st.slider(
            "Target Total Pixels",
            1,
            150000,
            key="output_target_pixels",
        )
    )

    (
        target_width,
        target_height,
    ) = target_pixels_to_dimensions(
        (
            source_width,
            source_height,
        ),
        target_total_pixels,
    )


else:

    maintain_ratio = (
        st.checkbox(
            "Maintain Aspect Ratio",
            key=(
                "output_maintain_ratio"
            ),
        )
    )

    d1, d2 = st.columns(2)

    with d1:

        custom_width = (
            st.number_input(
                "Width (px)",
                min_value=1,
                max_value=150000,
                step=1,
                key="output_custom_width",
            )
        )

    if maintain_ratio:

        (
            target_width,
            target_height,
        ) = dimensions_from_width(
            (
                source_width,
                source_height,
            ),
            int(custom_width),
        )

        with d2:

            st.metric(
                "Height (px) 🔒",
                f"{target_height:,}",
            )

    else:

        with d2:

            custom_height = (
                st.number_input(
                    "Height (px)",
                    min_value=1,
                    max_value=150000,
                    step=1,
                    key="output_custom_height",
                )
            )

        target_width = int(
            custom_width
        )

        target_height = int(
            custom_height
        )


# =========================================================
# DPI
# =========================================================

dpi_mode = (
    st.radio(
        "DPI Selection",
        [
            "Preset",
            "Custom",
        ],
        horizontal=True,
        key="output_dpi_mode",
    )
)


if dpi_mode == "Preset":

    dpi = (
        st.select_slider(
            "DPI",
            options=DPI_PRESETS,
            key="output_dpi_preset",
        )
    )

else:

    dpi = (
        st.number_input(
            "Custom DPI",
            72,
            1200,
            key="output_custom_dpi",
        )
    )


# =========================================================
# COLOR MODE
# =========================================================

color_mode = (
    st.selectbox(
        "Color Mode",
        [
            "RGB",
            "CMYK",
            "Grayscale",
        ],
        key="output_color_mode",
    )
)


if color_mode == "CMYK":

    st.info(
        "CMYK currently uses basic Pillow conversion. "
        "Professional ICC-based color management is not "
        "implemented yet."
    )


# =========================================================
# RESIZE MODE
# =========================================================

resize_mode = (
    st.selectbox(
        "Resize Mode",
        [
            "Fit",
            "Fill & Crop",
            "Stretch",
        ],
        key="output_resize_mode",
    )
)


quality = (
    st.slider(
        "JPEG / WebP Quality",
        1,
        100,
        key="output_quality",
    )
)


webp_lossless = (
    st.checkbox(
        "WebP Lossless",
        key="output_webp_lossless",
    )
)


png_compress_level = (
    st.slider(
        "PNG Compression",
        0,
        9,
        key="output_png_compression",
    )
)


tiff_compression_name = (
    st.selectbox(
        "TIFF Compression",
        [
            "LZW - Lossless",
            "Deflate - Lossless",
            "Uncompressed",
        ],
        key="output_tiff_compression",
    )
)


tiff_map = {
    "LZW - Lossless":
        "tiff_lzw",

    "Deflate - Lossless":
        "tiff_adobe_deflate",

    "Uncompressed":
        "raw",
}


tiff_compression = (
    tiff_map[
        tiff_compression_name
    ]
)


total_output_pixels = (
    int(target_width)
    * int(target_height)
)


m1, m2, m3, m4 = (
    st.columns(4)
)


m1.metric(
    "Width",
    f"{target_width:,}",
)

m2.metric(
    "Height",
    f"{target_height:,}",
)

m3.metric(
    "Pixels",
    f"{total_output_pixels:,}",
)

m4.metric(
    "DPI",
    dpi,
)


output_too_large = (
    total_output_pixels
    >
    MAX_TOTAL_EXPORT_PIXELS
)


if output_too_large:

    st.error(
        "Selected dimensions are too large "
        "for safe processing."
    )


st.divider()


# =========================================================
# 13 — SAVE PROJECT
# =========================================================

st.header(
    "13 — 💾 Save Editable Project"
)


project_name = (
    st.text_input(
        "Project Name",
        value=(
            os.path.splitext(
                uploaded_files[
                    0
                ].name
            )[0]
        ),
    )
)


project_settings = {
    "export_source":
        selected_export_source,

    "target_width":
        int(target_width),

    "target_height":
        int(target_height),

    "target_total_pixels":
        int(
            target_total_pixels
        ),

    "maintain_ratio":
        bool(
            maintain_ratio
        ),

    "dpi":
        int(dpi),

    "color_mode":
        color_mode,

    "resize_mode":
        resize_mode,

    "export_mode":
        export_mode,

    "selected_formats":
        selected_formats,

    "quality":
        int(quality),

    "png_compress_level":
        int(
            png_compress_level
        ),

    "webp_lossless":
        bool(
            webp_lossless
        ),

    "tiff_compression":
        tiff_compression,

    "pixel_mode":
        pixel_mode,

    "smart_export_purpose":
        smart_purpose,

    "smart_export_priority":
        smart_priority,
}


project_layer_groups = {
    name:
        collect_project_layers(
            name
        )

    for name in [
        "color",
        "semantic",
        "object",
        "segment",
        "smartcolor",
        "text",
        "ocr",
    ]
}


project_layer_groups = {
    name:
        layers

    for name, layers in (
        project_layer_groups.items()
    )

    if layers
}


project_edited_image = None


if (
    selected_export_source
    == "Smart Color Edited Image"
):

    project_edited_image = (
        st.session_state.get(
            "smart_color_result"
        )
    )


elif (
    selected_export_source
    == "Background Removed Image"
):

    result = (
        st.session_state.get(
            "background_remove_result"
        )
    )

    if isinstance(
        result,
        dict,
    ):

        project_edited_image = (
            result.get(
                "image"
            )
        )


try:

    project_bytes = (
        save_project(
            original_image=first_image,
            original_filename=(
                uploaded_files[
                    0
                ].name
            ),
            layer_groups=(
                project_layer_groups
            ),
            settings=(
                project_settings
            ),
            edited_image=(
                project_edited_image
            ),
        )
    )

    st.download_button(
        "💾 Save .aistudio Project",
        data=project_bytes,
        file_name=(
            f"{project_name.strip() or 'AI_Image_Project'}"
            f".aistudio"
        ),
        mime=(
            "application/octet-stream"
        ),
        use_container_width=True,
    )

except Exception as error:

    st.warning(
        f"Project could not be prepared: "
        f"{error}"
    )


st.divider()


# =========================================================
# 14 — QUALITY CHECK
# =========================================================

st.header(
    "14 — ✅ Professional Quality Check"
)


quality_format = (
    selected_formats[0]
    if selected_formats
    else "PNG"
)


internal_quality_format = (
    "TIFF"
    if (
        quality_format
        == "PSD (Flattened)"
    )
    else quality_format
)


if st.button(
    "🔎 Run Professional Quality Check",
    use_container_width=True,
):

    try:

        quality_result = (
            run_quality_check(
                export_source_image,
                target_width=(
                    target_width
                ),
                target_height=(
                    target_height
                ),
                dpi=dpi,
                output_format=(
                    internal_quality_format
                ),
                target_color_mode=(
                    color_mode
                ),
            )
        )

        st.session_state[
            "quality_result"
        ] = quality_result

    except Exception as error:

        st.exception(error)


if "quality_result" in st.session_state:

    result = (
        st.session_state[
            "quality_result"
        ]
    )

    status = (
        result[
            "overall_status"
        ]
    )

    if status == "READY":

        st.success(
            result[
                "overall_message"
            ]
        )

    elif status == "CHECK":

        st.warning(
            result[
                "overall_message"
            ]
        )

    else:

        st.error(
            result[
                "overall_message"
            ]
        )

    for check in result["checks"]:

        st.write(
            f"**{check['status']} — "
            f"{check['title']}**"
        )

        st.write(
            check["message"]
        )


st.divider()


# =========================================================
# 15 — EXPORT
# =========================================================

st.header(
    "15 — 🚀 Professional Export"
)


# =========================================================
# BUILD EXPORT JOBS
# =========================================================

if (
    selected_export_source
    == "Original Image"
):

    export_jobs = []

    for uploaded_file in uploaded_files:

        try:

            with Image.open(
                io.BytesIO(
                    uploaded_file.getvalue()
                )
            ) as opened:

                image = opened.copy()

            base_name = (
                os.path.splitext(
                    uploaded_file.name
                )[0]
            )

            export_jobs.append(
                (
                    base_name,
                    image,
                )
            )

        except Exception as error:

            st.warning(
                f"Could not prepare "
                f"{uploaded_file.name}: "
                f"{error}"
            )


else:

    original_base = (
        os.path.splitext(
            uploaded_files[
                0
            ].name
        )[0]
    )

    suffix = (
        safe_filename_part(
            selected_export_source
        )
    )

    export_jobs = [
        (
            f"{original_base}_{suffix}",
            export_source_image,
        )
    ]


if (
    source_metadata.get(
        "pdf_page_mode"
    )
    == "All Pages"
    and
    selected_export_source
    == "Original Image"
):

    st.success(
        f"📚 Batch PDF Export Ready: "
        f"{len(export_jobs)} page(s)"
    )


if selected_formats:

    st.write(
        f"**Jobs:** "
        f"{len(export_jobs)} image/page(s) × "
        f"{len(selected_formats)} format(s) = "
        f"{len(export_jobs) * len(selected_formats)} output file(s)"
    )


if st.button(
    "🚀 Export Final Image(s)",
    type="primary",
    use_container_width=True,
    disabled=(
        not selected_formats
        or
        output_too_large
        or
        len(export_jobs) == 0
    ),
):

    export_results = []

    total_jobs = (
        len(export_jobs)
        * len(selected_formats)
    )

    completed = 0

    progress = st.progress(
        0,
        text="Preparing exports...",
    )

    for (
        source_name,
        source_image
    ) in export_jobs:

        for export_format in (
            selected_formats
        ):

            completed += 1

            progress.progress(
                completed
                / total_jobs,
                text=(
                    f"Exporting "
                    f"{source_name} "
                    f"as {export_format}..."
                ),
            )

            try:

                if (
                    export_format
                    == "PSD (Flattened)"
                ):

                    export_result = (
                        export_flattened_psd(
                            image=source_image,
                            width=target_width,
                            height=target_height,
                            resize_mode=(
                                resize_mode
                            ),
                        )
                    )

                else:

                    export_result = (
                        export_image(
                            image=source_image,
                            output_format=(
                                export_format
                            ),
                            width=target_width,
                            height=target_height,
                            dpi=dpi,
                            color_mode=(
                                color_mode
                            ),
                            resize_mode=(
                                resize_mode
                            ),
                            quality=quality,
                            tiff_compression=(
                                tiff_compression
                            ),
                            png_compress_level=(
                                png_compress_level
                            ),
                            webp_lossless=(
                                webp_lossless
                            ),
                        )
                    )

                output_name = (
                    f"{source_name}"
                    f"{export_result['extension']}"
                )

                export_result[
                    "output_name"
                ] = output_name

                export_result[
                    "success"
                ] = True

                export_results.append(
                    export_result
                )

            except Exception as error:

                export_results.append(
                    {
                        "success":
                            False,

                        "input":
                            source_name,

                        "format":
                            export_format,

                        "error":
                            str(error),
                    }
                )

    progress.empty()

    st.session_state[
        "professional_export_results"
    ] = export_results

    st.success(
        "Export processing complete."
    )


# =========================================================
# 16 — INDIVIDUAL DOWNLOADS
# =========================================================

if (
    "professional_export_results"
    in st.session_state
):

    st.header(
        "16 — ⬇️ Export Results"
    )

    results = (
        st.session_state[
            "professional_export_results"
        ]
    )

    successful = [
        result
        for result in results
        if result.get(
            "success"
        )
    ]

    failed = [
        result
        for result in results
        if not result.get(
            "success"
        )
    ]

    e1, e2 = (
        st.columns(2)
    )

    e1.metric(
        "Successful Exports",
        len(successful),
    )

    e2.metric(
        "Failed Exports",
        len(failed),
    )


    # =====================================================
    # NO ZIP
    # =====================================================

    st.caption(
        "Each exported file can be downloaded separately."
    )


    for index, result in enumerate(
        results,
        start=1,
    ):

        if not result.get(
            "success"
        ):

            st.error(
                f"{result.get('input')} → "
                f"{result.get('format')} → "
                f"{result.get('error')}"
            )

            continue

        with st.container(
            border=True
        ):

            st.subheader(
                f"{index}. "
                f"{result['output_name']}"
            )

            d1, d2, d3, d4 = (
                st.columns(4)
            )

            d1.metric(
                "Format",
                result[
                    "format"
                ],
            )

            d2.metric(
                "Dimensions",
                (
                    f"{result['width']} × "
                    f"{result['height']}"
                ),
            )

            result_dpi = (
                result.get(
                    "dpi"
                )
            )

            d3.metric(
                "DPI",
                (
                    result_dpi
                    if (
                        result_dpi
                        is not None
                    )
                    else "N/A"
                ),
            )

            d4.metric(
                "Mode",
                result["mode"],
            )

            for warning in (
                result.get(
                    "warnings",
                    [],
                )
            ):

                st.warning(warning)

            st.download_button(
                (
                    "⬇️ Download "
                    f"{result['output_name']}"
                ),
                data=result["data"],
                file_name=(
                    result[
                        "output_name"
                    ]
                ),
                mime=result["mime"],
                key=(
                    f"individual_download_"
                    f"{index}_"
                    f"{result['output_name']}"
                ),
                use_container_width=True,
            )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "AI Image Studio • JPG • JPEG • PNG • WEBP • TIFF • BMP • "
    "PDF Single Page • PDF All Pages • SVG • HEIC • HEIF • "
    "Editable Layers • Object Recognition • Segmentation • "
    "Background Removal • Color Editing • OCR • "
    "Smart Export • .aistudio Projects • "
    "PNG • JPEG • WEBP • TIFF • BMP • PDF • PSD (Flattened) • "
    "Individual File Downloads"
)