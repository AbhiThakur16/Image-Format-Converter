import io
import math
import os
import re
import hashlib
import json
import time

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
from layered_psd_export import export_layered_psd

from layer_transform_engine import (
    duplicate_layer,
    transform_layer,
)

from history_engine import (
    create_layer_snapshot,
    push_history,
    undo_history,
    redo_history,
)

from layer_state_engine import (
    is_layer_locked,
    set_layer_locked,
    remember_original_layer,
    reset_layer_transform,
    duplicate_layer_state,
)

from recovery_engine import (
    save_recovery,
    load_recovery,
    recovery_exists,
    delete_recovery,
    get_recovery_info,
)

from diagnostics_engine import (
    handle_error,
    read_recent_errors,
    clear_error_log,
    get_diagnostics_summary,
)

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
# DIAGNOSTICS HELPERS
# =========================================================

def report_app_error(
    error,
    operation,
    context=None,
    show_technical=False,
):
    """Log an exception and show a safe, useful Streamlit message."""

    try:
        result = handle_error(
            error=error,
            operation=operation,
            context=(
                context
                if isinstance(context, dict)
                else {}
            ),
            base_directory=".",
        )

    except Exception:
        result = {
            "title": f"{operation} failed",
            "user_message": (
                f"The {operation} could not be completed."
            ),
            "technical_message": str(error),
            "error_type": type(error).__name__,
        }

    st.error(
        f"❌ {result.get('title', f'{operation} failed')}"
    )

    st.warning(
        result.get(
            "user_message",
            f"The {operation} could not be completed.",
        )
    )

    if show_technical:
        with st.expander(
            "Technical details",
            expanded=False,
        ):
            st.code(
                f"{result.get('error_type', type(error).__name__)}: "
                f"{result.get('technical_message', str(error))}"
            )

    return result


def log_background_error(
    error,
    operation,
    context=None,
):
    """Log an error without forcing a new error box into the UI."""

    try:
        return handle_error(
            error=error,
            operation=operation,
            context=(
                context
                if isinstance(context, dict)
                else {}
            ),
            base_directory=".",
        )
    except Exception:
        return {
            "technical_message": str(error),
            "error_type": type(error).__name__,
        }


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
    "PSD (Layered)",
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
# MEMORY UPLOADED FILE
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
# CACHE — IMAGE ANALYSIS
# =========================================================

@st.cache_data(show_spinner=False)
def cached_ai_analysis(image_bytes):

    with Image.open(
        io.BytesIO(image_bytes)
    ) as opened:

        image = opened.copy()

    return analyze_image(image)


# =========================================================
# CACHE — INPUT INFO
# =========================================================

@st.cache_data(show_spinner=False)
def cached_get_input_info(
    file_bytes,
    filename,
):

    return get_input_info(
        file_bytes,
        filename,
    )


# =========================================================
# CACHE — PREPARE INPUT
# =========================================================

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

    png_bytes = (
        input_result_to_png_bytes(
            result
        )
    )

    image = result["image"]

    return {
        "png_bytes":
            png_bytes,

        "format":
            result.get(
                "format",
                "Unknown",
            ),

        "mode":
            image.mode,

        "width":
            image.width,

        "height":
            image.height,

        "dpi":
            result.get(
                "dpi"
            ),

        "type":
            result.get(
                "type",
                "image",
            ),

        "page_count":
            result.get(
                "page_count",
                1,
            ),

        "selected_page":
            result.get(
                "selected_page",
                1,
            ),

        "warnings":
            result.get(
                "warnings",
                [],
            ),
    }


# =========================================================
# CACHE — ALL PDF PAGES
# =========================================================

@st.cache_data(show_spinner=False)
def cached_prepare_all_pdf_pages(
    file_bytes,
    render_dpi=150,
):

    return render_all_pdf_pages_as_png(
        file_bytes,
        dpi=render_dpi,
    )


# =========================================================
# TARGET TOTAL PIXELS
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


# =========================================================
# ASPECT RATIO
# =========================================================

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
# IMAGE → PNG
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


# =========================================================
# SAFE FILE NAME
# =========================================================

def safe_filename_part(text):

    text = str(
        text
    ).lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "_",
        text,
    )

    return text.strip(
        "_"
    )


# =========================================================
# INITIALIZE LAYER STATE
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

        layer_copy = (
            layer.copy()
        )

        layer_copy[
            "_uid"
        ] = (
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

    # Lock state and original image are kept by UID.
    lock_states = {}
    original_images = {}

    for layer in prepared_layers:

        uid = layer.get(
            "_uid"
        )

        if not uid:
            continue

        lock_states[uid] = bool(
            layer.get(
                "_saved_locked",
                False,
            )
        )

        image = layer.get(
            "image"
        )

        if isinstance(
            image,
            Image.Image,
        ):

            remember_original_layer(
                original_images,
                uid,
                image,
            )

    st.session_state[
        f"{prefix}_lock_states"
    ] = lock_states

    st.session_state[
        f"{prefix}_original_images"
    ] = original_images

    # A newly extracted/restored layer set starts a fresh history.
    st.session_state[
        f"{prefix}_undo_stack"
    ] = []

    st.session_state[
        f"{prefix}_redo_stack"
    ] = []


# =========================================================
# COLLECT PROJECT LAYERS
# =========================================================

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
                in enumerate(
                    layers
                )
            ],
        )
    )

    lock_states = (
        st.session_state.get(
            f"{prefix}_lock_states",
            {},
        )
    )

    project_layers = []

    for index, layer in enumerate(
        layers
    ):

        layer_copy = (
            layer.copy()
        )

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
        ] = (
            names[index]
        )

        uid = layer.get(
            "_uid"
        )

        layer_copy[
            "_saved_locked"
        ] = bool(
            lock_states.get(
                uid,
                False,
            )
        )

        project_layers.append(
            layer_copy
        )

    return project_layers


# =========================================================
# CURRENT EDITABLE LAYER GROUPS
# =========================================================

def get_current_layer_groups():

    groups = {}

    for group_name in [
        "color",
        "semantic",
        "object",
        "segment",
        "smartcolor",
        "text",
        "ocr",
    ]:

        layers = (
            collect_project_layers(
                group_name
            )
        )

        if layers:

            groups[
                group_name
            ] = layers

    return groups


# =========================================================
# RESTORE PROJECT LAYERS
# =========================================================

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


# =========================================================
# LAYER LOCK / RESET STATE HELPERS
# =========================================================

def ensure_layer_edit_state(prefix):

    layers = st.session_state.get(
        f"{prefix}_layers",
        [],
    )

    lock_key = f"{prefix}_lock_states"
    original_key = f"{prefix}_original_images"

    st.session_state.setdefault(
        lock_key,
        {},
    )

    st.session_state.setdefault(
        original_key,
        {},
    )

    lock_states = st.session_state[
        lock_key
    ]

    original_images = st.session_state[
        original_key
    ]

    for layer in layers:

        uid = layer.get(
            "_uid"
        )

        if not uid:
            continue

        lock_states.setdefault(
            uid,
            bool(
                layer.get(
                    "_saved_locked",
                    False,
                )
            ),
        )

        image = layer.get(
            "image"
        )

        if isinstance(
            image,
            Image.Image,
        ):

            remember_original_layer(
                original_images,
                uid,
                image,
            )


def get_layer_lock_state(prefix, uid):

    ensure_layer_edit_state(
        prefix
    )

    return is_layer_locked(
        st.session_state[
            f"{prefix}_lock_states"
        ],
        uid,
    )


def update_layer_lock_state(
    prefix,
    uid,
    locked,
):

    ensure_layer_edit_state(
        prefix
    )

    st.session_state[
        f"{prefix}_lock_states"
    ] = set_layer_locked(
        st.session_state[
            f"{prefix}_lock_states"
        ],
        uid,
        locked,
    )


# =========================================================
# LAYER HISTORY HELPERS
# =========================================================

def ensure_layer_history(prefix):

    st.session_state.setdefault(
        f"{prefix}_undo_stack",
        [],
    )

    st.session_state.setdefault(
        f"{prefix}_redo_stack",
        [],
    )


def current_layer_snapshot(prefix):

    layers = st.session_state.get(
        f"{prefix}_layers",
        [],
    )

    visibility = st.session_state.get(
        f"{prefix}_visibility",
        [True for _ in layers],
    )

    opacity = st.session_state.get(
        f"{prefix}_opacity",
        [100 for _ in layers],
    )

    names = st.session_state.get(
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

    return create_layer_snapshot(
        layers,
        visibility,
        opacity,
        names,
    )


def record_layer_history(prefix):

    ensure_layer_history(prefix)

    undo_key = f"{prefix}_undo_stack"
    redo_key = f"{prefix}_redo_stack"

    snapshot = current_layer_snapshot(
        prefix
    )

    st.session_state[undo_key] = (
        push_history(
            st.session_state[undo_key],
            snapshot,
            max_history=30,
        )
    )

    # A new edit invalidates the redo branch.
    st.session_state[redo_key] = []


def clear_layer_basic_widget_state(prefix, extra_layers=None):

    layer_sets = [
        st.session_state.get(
            f"{prefix}_layers",
            [],
        )
    ]

    if extra_layers:
        layer_sets.append(
            extra_layers
        )

    seen_uids = set()

    for layers in layer_sets:
        for layer in layers:
            if not isinstance(
                layer,
                dict,
            ):
                continue

            uid = layer.get(
                "_uid"
            )

            if not uid or uid in seen_uids:
                continue

            seen_uids.add(
                uid
            )

            for key_prefix in (
                "name",
                "visible",
                "opacity",
            ):
                st.session_state.pop(
                    f"{key_prefix}_{uid}",
                    None,
                )


def commit_layer_name_change(
    prefix,
    index,
    widget_key,
):

    names_key = f"{prefix}_names"

    if names_key not in st.session_state:
        return

    if index >= len(
        st.session_state[names_key]
    ):
        return

    old_value = st.session_state[names_key][index]
    new_value = st.session_state.get(
        widget_key,
        old_value,
    )

    if new_value == old_value:
        return

    record_layer_history(prefix)
    st.session_state[names_key][index] = str(
        new_value
    )


def commit_layer_visibility_change(
    prefix,
    index,
    widget_key,
):

    visibility_key = f"{prefix}_visibility"

    if visibility_key not in st.session_state:
        return

    if index >= len(
        st.session_state[visibility_key]
    ):
        return

    old_value = bool(
        st.session_state[visibility_key][index]
    )
    new_value = bool(
        st.session_state.get(
            widget_key,
            old_value,
        )
    )

    if new_value == old_value:
        return

    record_layer_history(prefix)
    st.session_state[visibility_key][index] = new_value


def commit_layer_opacity_change(
    prefix,
    index,
    widget_key,
):

    opacity_key = f"{prefix}_opacity"

    if opacity_key not in st.session_state:
        return

    if index >= len(
        st.session_state[opacity_key]
    ):
        return

    old_value = int(
        st.session_state[opacity_key][index]
    )
    new_value = int(
        st.session_state.get(
            widget_key,
            old_value,
        )
    )

    if new_value == old_value:
        return

    record_layer_history(prefix)
    st.session_state[opacity_key][index] = max(
        0,
        min(
            new_value,
            100,
        ),
    )


def apply_layer_snapshot(prefix, snapshot):

    snapshot_layers = snapshot.get(
        "layers",
        [],
    )

    # Streamlit widgets keep their own values by key. Clear the
    # basic layer widget keys so Undo/Redo can visibly restore
    # renamed layers, visibility and opacity.
    clear_layer_basic_widget_state(
        prefix,
        extra_layers=snapshot_layers,
    )

    st.session_state[
        f"{prefix}_layers"
    ] = snapshot_layers

    st.session_state[
        f"{prefix}_visibility"
    ] = snapshot.get(
        "visibility",
        [],
    )

    st.session_state[
        f"{prefix}_opacity"
    ] = snapshot.get(
        "opacity",
        [],
    )

    st.session_state[
        f"{prefix}_names"
    ] = snapshot.get(
        "names",
        [],
    )


def perform_layer_undo(prefix):

    ensure_layer_history(prefix)

    undo_key = f"{prefix}_undo_stack"
    redo_key = f"{prefix}_redo_stack"

    result = undo_history(
        st.session_state[undo_key],
        st.session_state[redo_key],
        current_layer_snapshot(prefix),
    )

    st.session_state[undo_key] = (
        result["undo_stack"]
    )

    st.session_state[redo_key] = (
        result["redo_stack"]
    )

    if result["success"]:
        apply_layer_snapshot(
            prefix,
            result["snapshot"],
        )
        return True

    return False


def perform_layer_redo(prefix):

    ensure_layer_history(prefix)

    undo_key = f"{prefix}_undo_stack"
    redo_key = f"{prefix}_redo_stack"

    result = redo_history(
        st.session_state[undo_key],
        st.session_state[redo_key],
        current_layer_snapshot(prefix),
    )

    st.session_state[undo_key] = (
        result["undo_stack"]
    )

    st.session_state[redo_key] = (
        result["redo_stack"]
    )

    if result["success"]:
        apply_layer_snapshot(
            prefix,
            result["snapshot"],
        )
        return True

    return False


# =========================================================
# REBUILD LAYER GROUP
# =========================================================

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
# BUILD EXPORT SOURCES
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

    color_rebuilt = (
        rebuild_layer_group(
            "color"
        )
    )

    if isinstance(
        color_rebuilt,
        Image.Image,
    ):

        sources[
            "Color Layer Reconstruction"
        ] = color_rebuilt

    semantic_rebuilt = (
        rebuild_layer_group(
            "semantic"
        )
    )

    if isinstance(
        semantic_rebuilt,
        Image.Image,
    ):

        sources[
            "Semantic Reconstruction"
        ] = semantic_rebuilt

    object_rebuilt = (
        rebuild_layer_group(
            "object"
        )
    )

    if isinstance(
        object_rebuilt,
        Image.Image,
    ):

        sources[
            "Object Layer Reconstruction"
        ] = object_rebuilt

    segment_rebuilt = (
        rebuild_layer_group(
            "segment"
        )
    )

    if isinstance(
        segment_rebuilt,
        Image.Image,
    ):

        sources[
            "Segmented Objects"
        ] = segment_rebuilt

    smart_color_layer = (
        rebuild_layer_group(
            "smartcolor"
        )
    )

    if isinstance(
        smart_color_layer,
        Image.Image,
    ):

        sources[
            "Extracted Color Layer"
        ] = smart_color_layer

    text_rebuilt = (
        rebuild_layer_group(
            "text"
        )
    )

    if isinstance(
        text_rebuilt,
        Image.Image,
    ):

        sources[
            "Text Layer Reconstruction"
        ] = text_rebuilt

    ocr_rebuilt = (
        rebuild_layer_group(
            "ocr"
        )
    )

    if isinstance(
        ocr_rebuilt,
        Image.Image,
    ):

        sources[
            "OCR Layer Reconstruction"
        ] = ocr_rebuilt

    return sources


# =========================================================
# OUTPUT SETTINGS KEYS
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


# =========================================================
# PROJECT STATE / RECOVERY HELPERS
# =========================================================

def image_state_fingerprint(image):

    if not isinstance(
        image,
        Image.Image,
    ):
        return "none"

    cache = st.session_state.setdefault(
        "_image_fingerprint_cache",
        {},
    )

    cache_key = (
        id(image),
        image.size,
        image.mode,
    )

    if cache_key in cache:
        return cache[cache_key]

    converted = image.convert(
        "RGBA"
    )

    digest = hashlib.sha1(
        converted.tobytes()
    ).hexdigest()

    # Keep the cache bounded during long editing sessions.
    if len(cache) > 512:
        cache.clear()

    cache[cache_key] = digest

    return digest


def build_project_state_signature(
    project_name,
    original_source_hash,
    layer_groups,
    settings,
    edited_image=None,
):

    hasher = hashlib.sha256()

    hasher.update(
        str(
            project_name
            or "AI_Image_Project"
        ).encode(
            "utf-8"
        )
    )

    hasher.update(
        str(
            original_source_hash
        ).encode(
            "utf-8"
        )
    )

    settings_json = json.dumps(
        settings,
        sort_keys=True,
        default=str,
        separators=(
            ",",
            ":",
        ),
    )

    hasher.update(
        settings_json.encode(
            "utf-8"
        )
    )

    for group_name in sorted(
        layer_groups.keys()
    ):

        hasher.update(
            group_name.encode(
                "utf-8"
            )
        )

        for index, layer in enumerate(
            layer_groups[
                group_name
            ]
        ):

            hasher.update(
                str(index).encode(
                    "utf-8"
                )
            )

            if not isinstance(
                layer,
                dict,
            ):
                hasher.update(
                    repr(layer).encode(
                        "utf-8"
                    )
                )
                continue

            metadata = {
                "uid": layer.get(
                    "_uid"
                ),
                "name": (
                    layer.get(
                        "_saved_name"
                    )
                    or
                    layer.get(
                        "name"
                    )
                ),
                "visible": bool(
                    layer.get(
                        "_saved_visible",
                        True,
                    )
                ),
                "opacity": int(
                    layer.get(
                        "_saved_opacity",
                        100,
                    )
                ),
                "locked": bool(
                    layer.get(
                        "_saved_locked",
                        False,
                    )
                ),
                "type": layer.get(
                    "type"
                ),
                "object_name": layer.get(
                    "object_name"
                ),
                "text": layer.get(
                    "text"
                ),
            }

            hasher.update(
                json.dumps(
                    metadata,
                    sort_keys=True,
                    default=str,
                ).encode(
                    "utf-8"
                )
            )

            hasher.update(
                image_state_fingerprint(
                    layer.get(
                        "image"
                    )
                ).encode(
                    "utf-8"
                )
            )

    hasher.update(
        image_state_fingerprint(
            edited_image
        ).encode(
            "utf-8"
        )
    )

    return hasher.hexdigest()


def format_recovery_timestamp(
    timestamp,
):

    if not timestamp:
        return "Unknown time"

    try:
        return time.strftime(
            "%d %b %Y, %I:%M:%S %p",
            time.localtime(
                float(timestamp)
            ),
        )
    except Exception:
        return "Unknown time"


def mark_project_downloaded_as_saved(
    signature,
    project_name,
):

    st.session_state[
        "saved_project_signature"
    ] = signature

    st.session_state[
        "recovered_session_pending_save"
    ] = False

    st.session_state[
        "recovery_choice_resolved"
    ] = True

    st.session_state.pop(
        "last_recovery_signature",
        None,
    )

    try:
        delete_recovery(
            project_name,
            base_directory=".",
        )
    except Exception:
        pass


def activate_loaded_project_data(
    loaded_project,
    recovered=False,
):

    clear_workspace_state()

    project_original = loaded_project[
        "original_image"
    ]

    project_image_bytes = image_to_bytes(
        project_original
    )

    project_filename = loaded_project.get(
        "original_filename",
        "project_image.png",
    )

    loaded_settings = loaded_project.get(
        "settings",
        {},
    )

    st.session_state[
        "opened_project_image_bytes"
    ] = project_image_bytes

    st.session_state[
        "opened_project_filename"
    ] = project_filename

    for group_name in [
        "color",
        "semantic",
        "object",
        "segment",
        "smartcolor",
        "text",
        "ocr",
    ]:

        layers = loaded_project.get(
            "layer_groups",
            {},
        ).get(
            group_name,
            [],
        )

        if layers:
            restore_project_layers(
                group_name,
                layers,
            )

    edited_image = loaded_project.get(
        "edited_image"
    )

    saved_export_source = loaded_settings.get(
        "export_source",
        "Original Image",
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
                "image": edited_image,
                "mask": None,
            }
        else:
            st.session_state[
                "smart_color_result"
            ] = edited_image

            st.session_state[
                "smart_color_operation"
            ] = (
                "Recovered Project Edit"
                if recovered
                else "Restored Project Edit"
            )

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

    st.session_state[
        "recovered_session_pending_save"
    ] = bool(
        recovered
    )

    st.session_state[
        "recovery_choice_resolved"
    ] = True

# =========================================================
# CLEAR WORKSPACE
# =========================================================

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
            "undo_stack",
            "redo_stack",
            "lock_states",
            "original_images",
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
        "saved_project_signature",
        "last_recovery_signature",
        "recovery_choice_resolved",
        "recovered_session_pending_save",
        "recovery_last_message",
        "_image_fingerprint_cache",
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
# DEFAULT OUTPUT SETTINGS
# =========================================================

def ensure_output_defaults(
    original_width,
    original_height,
):

    original_total = (
        original_width
        * original_height
    )

    st.session_state.setdefault(
        "output_export_source",
        "Original Image",
    )

    st.session_state.setdefault(
        "output_export_mode",
        "Single Format",
    )

    st.session_state.setdefault(
        "output_single_format",
        "PNG",
    )

    st.session_state.setdefault(
        "output_multiple_formats",
        [
            "PNG",
            "TIFF",
        ],
    )

    st.session_state.setdefault(
        "output_pixel_mode",
        "Original Size",
    )

    st.session_state.setdefault(
        "output_target_pixels",
        max(
            1,
            min(
                original_total,
                150000,
            ),
        ),
    )

    st.session_state.setdefault(
        "output_maintain_ratio",
        True,
    )

    st.session_state.setdefault(
        "output_custom_width",
        max(
            1,
            min(
                int(original_width),
                150000,
            ),
        ),
    )

    st.session_state.setdefault(
        "output_custom_height",
        max(
            1,
            min(
                int(original_height),
                150000,
            ),
        ),
    )

    st.session_state.setdefault(
        "output_dpi_mode",
        "Preset",
    )

    st.session_state.setdefault(
        "output_dpi_preset",
        300,
    )

    st.session_state.setdefault(
        "output_custom_dpi",
        300,
    )

    st.session_state.setdefault(
        "output_color_mode",
        "RGB",
    )

    st.session_state.setdefault(
        "output_resize_mode",
        "Fit",
    )

    st.session_state.setdefault(
        "output_quality",
        95,
    )

    st.session_state.setdefault(
        "output_webp_lossless",
        False,
    )

    st.session_state.setdefault(
        "output_png_compression",
        6,
    )

    st.session_state.setdefault(
        "output_tiff_compression",
        "LZW - Lossless",
    )

    st.session_state.setdefault(
        "smart_export_purpose",
        "General Purpose",
    )

    st.session_state.setdefault(
        "smart_export_priority",
        "Balanced",
    )


# =========================================================
# APPLY PROJECT SETTINGS
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
        for item
        in saved_formats
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

    target_pixels = settings.get(
        "target_total_pixels",
        saved_width * saved_height,
    )

    st.session_state[
        "output_target_pixels"
    ] = max(
        1,
        min(
            int(target_pixels),
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

        st.session_state[
            "output_custom_dpi"
        ] = saved_dpi

    else:

        st.session_state[
            "output_dpi_mode"
        ] = "Custom"

        st.session_state[
            "output_custom_dpi"
        ] = saved_dpi

    saved_color_mode = settings.get(
        "color_mode",
        "RGB",
    )

    if saved_color_mode not in (
        "RGB",
        "CMYK",
        "Grayscale",
    ):

        saved_color_mode = (
            "RGB"
        )

    st.session_state[
        "output_color_mode"
    ] = saved_color_mode

    saved_resize_mode = settings.get(
        "resize_mode",
        "Fit",
    )

    if saved_resize_mode not in (
        "Fit",
        "Fill & Crop",
        "Stretch",
    ):

        saved_resize_mode = (
            "Fit"
        )

    st.session_state[
        "output_resize_mode"
    ] = saved_resize_mode

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

        purpose = (
            "General Purpose"
        )

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

        priority = (
            "Balanced"
        )

    st.session_state[
        "smart_export_priority"
    ] = priority

    st.session_state[
        "project_settings_applied"
    ] = True


# =========================================================
# EDITABLE LAYER PANEL
# =========================================================

def render_layer_panel(
    prefix,
    info_type="basic",
):

    layers_key = f"{prefix}_layers"
    visibility_key = f"{prefix}_visibility"
    opacity_key = f"{prefix}_opacity"
    names_key = f"{prefix}_names"
    lock_key = f"{prefix}_lock_states"
    original_key = f"{prefix}_original_images"

    if layers_key not in st.session_state:
        return None

    layers = st.session_state[layers_key]

    ensure_layer_history(prefix)
    ensure_layer_edit_state(prefix)

    undo_key = f"{prefix}_undo_stack"
    redo_key = f"{prefix}_redo_stack"

    history_col1, history_col2, history_col3 = (
        st.columns([1, 1, 2])
    )

    with history_col1:
        undo_clicked = st.button(
            "↶ Undo",
            key=f"undo_{prefix}",
            disabled=(
                len(st.session_state[undo_key]) == 0
            ),
            use_container_width=True,
        )

    with history_col2:
        redo_clicked = st.button(
            "↷ Redo",
            key=f"redo_{prefix}",
            disabled=(
                len(st.session_state[redo_key]) == 0
            ),
            use_container_width=True,
        )

    with history_col3:
        st.caption(
            f"History: "
            f"{len(st.session_state[undo_key])} undo • "
            f"{len(st.session_state[redo_key])} redo "
            f"(max 30 edits)"
        )

    if undo_clicked:
        if perform_layer_undo(prefix):
            st.rerun()

    if redo_clicked:
        if perform_layer_redo(prefix):
            st.rerun()

    if not layers:
        st.warning(
            "All layers have been deleted. "
            "Use Undo to restore the last layer."
        )
        return None

    # Keep all parallel state lists aligned with the layer list.
    if visibility_key not in st.session_state:
        st.session_state[visibility_key] = [
            True
            for _ in layers
        ]

    if opacity_key not in st.session_state:
        st.session_state[opacity_key] = [
            100
            for _ in layers
        ]

    if names_key not in st.session_state:
        st.session_state[names_key] = [
            layer.get(
                "name",
                f"Layer {index + 1}",
            )
            for index, layer
            in enumerate(layers)
        ]

    while len(st.session_state[visibility_key]) < len(layers):
        st.session_state[visibility_key].append(True)

    while len(st.session_state[opacity_key]) < len(layers):
        st.session_state[opacity_key].append(100)

    while len(st.session_state[names_key]) < len(layers):
        index = len(st.session_state[names_key])
        st.session_state[names_key].append(
            layers[index].get(
                "name",
                f"Layer {index + 1}",
            )
        )

    if len(st.session_state[visibility_key]) > len(layers):
        del st.session_state[visibility_key][len(layers):]

    if len(st.session_state[opacity_key]) > len(layers):
        del st.session_state[opacity_key][len(layers):]

    if len(st.session_state[names_key]) > len(layers):
        del st.session_state[names_key][len(layers):]

    ensure_layer_edit_state(prefix)

    st.write(
        f"Total Layers: "
        f"**{len(layers)}**"
    )

    st.caption(
        "🔒 Locked layers cannot be reordered, deleted or transformed. "
        "Rename, visibility and opacity remain available and are now "
        "included in Undo/Redo history."
    )

    for index, layer in enumerate(
        list(layers)
    ):

        uid = layer.get(
            "_uid",
            f"{prefix}_{index}",
        )

        # Repair missing UIDs from old project/session data.
        if "_uid" not in layer:
            revision_key = f"{prefix}_revision"
            st.session_state[revision_key] = (
                st.session_state.get(
                    revision_key,
                    0,
                )
                + 1
            )
            uid = (
                f"{prefix}_repair_"
                f"{st.session_state[revision_key]}_"
                f"{index}"
            )
            st.session_state[layers_key][index]["_uid"] = uid
            layer = st.session_state[layers_key][index]
            ensure_layer_edit_state(prefix)

        locked = get_layer_lock_state(
            prefix,
            uid,
        )

        with st.container(
            border=True
        ):

            title_col, lock_col = st.columns(
                [3, 1]
            )

            with title_col:
                st.markdown(
                    f"### 🧩 Layer {index + 1} "
                    f"{'🔒' if locked else '🔓'}"
                )

            with lock_col:
                new_locked = st.toggle(
                    "Lock Layer",
                    value=locked,
                    key=f"lock_{uid}",
                )

            if new_locked != locked:
                update_layer_lock_state(
                    prefix,
                    uid,
                    new_locked,
                )
                locked = new_locked

            # =================================================
            # ORDER / DUPLICATE / DELETE
            # =================================================

            (
                up_col,
                down_col,
                duplicate_col,
                delete_col,
            ) = st.columns(4)

            with up_col:
                move_up = st.button(
                    "⬆️ Up",
                    key=f"up_{uid}",
                    disabled=(
                        locked
                        or index == 0
                    ),
                    use_container_width=True,
                )

            if move_up:
                record_layer_history(prefix)
                previous_index = index - 1

                st.session_state[layers_key][previous_index], st.session_state[layers_key][index] = (
                    st.session_state[layers_key][index],
                    st.session_state[layers_key][previous_index],
                )

                st.session_state[visibility_key][previous_index], st.session_state[visibility_key][index] = (
                    st.session_state[visibility_key][index],
                    st.session_state[visibility_key][previous_index],
                )

                st.session_state[opacity_key][previous_index], st.session_state[opacity_key][index] = (
                    st.session_state[opacity_key][index],
                    st.session_state[opacity_key][previous_index],
                )

                st.session_state[names_key][previous_index], st.session_state[names_key][index] = (
                    st.session_state[names_key][index],
                    st.session_state[names_key][previous_index],
                )

                st.rerun()

            with down_col:
                move_down = st.button(
                    "⬇️ Down",
                    key=f"down_{uid}",
                    disabled=(
                        locked
                        or index == len(layers) - 1
                    ),
                    use_container_width=True,
                )

            if move_down:
                record_layer_history(prefix)
                next_index = index + 1

                st.session_state[layers_key][next_index], st.session_state[layers_key][index] = (
                    st.session_state[layers_key][index],
                    st.session_state[layers_key][next_index],
                )

                st.session_state[visibility_key][next_index], st.session_state[visibility_key][index] = (
                    st.session_state[visibility_key][index],
                    st.session_state[visibility_key][next_index],
                )

                st.session_state[opacity_key][next_index], st.session_state[opacity_key][index] = (
                    st.session_state[opacity_key][index],
                    st.session_state[opacity_key][next_index],
                )

                st.session_state[names_key][next_index], st.session_state[names_key][index] = (
                    st.session_state[names_key][index],
                    st.session_state[names_key][next_index],
                )

                st.rerun()

            with duplicate_col:
                duplicate_clicked = st.button(
                    "📄 Duplicate",
                    key=f"duplicate_{uid}",
                    use_container_width=True,
                )

            if duplicate_clicked:
                record_layer_history(prefix)
                duplicated = duplicate_layer(
                    layer
                )

                revision_key = f"{prefix}_revision"

                st.session_state[revision_key] = (
                    st.session_state.get(
                        revision_key,
                        0,
                    )
                    + 1
                )

                duplicated["_uid"] = (
                    f"{prefix}_duplicate_"
                    f"{st.session_state[revision_key]}_"
                    f"{index}"
                )

                new_uid = duplicated["_uid"]

                duplicated_name = (
                    duplicated.get("_saved_name")
                    or duplicated.get("name")
                    or "Layer Copy"
                )

                insert_position = index + 1

                st.session_state[layers_key].insert(
                    insert_position,
                    duplicated,
                )

                st.session_state[visibility_key].insert(
                    insert_position,
                    st.session_state[visibility_key][index],
                )

                st.session_state[opacity_key].insert(
                    insert_position,
                    st.session_state[opacity_key][index],
                )

                st.session_state[names_key].insert(
                    insert_position,
                    duplicated_name,
                )

                (
                    st.session_state[lock_key],
                    st.session_state[original_key],
                ) = duplicate_layer_state(
                    st.session_state[lock_key],
                    st.session_state[original_key],
                    uid,
                    new_uid,
                    duplicated.get("image"),
                )

                st.rerun()

            with delete_col:
                delete_clicked = st.button(
                    "🗑️ Delete",
                    key=f"delete_{uid}",
                    disabled=locked,
                    use_container_width=True,
                )

            if delete_clicked:
                record_layer_history(prefix)
                st.session_state[layers_key].pop(index)
                st.session_state[visibility_key].pop(index)
                st.session_state[opacity_key].pop(index)
                st.session_state[names_key].pop(index)

                # Keep UID lock/original state cached so Undo can restore
                # the layer with its reset baseline intact.
                st.rerun()

            # =================================================
            # PREVIEW + BASIC CONTROLS
            # =================================================

            preview_col, control_col = st.columns(
                [1, 2]
            )

            with preview_col:
                if isinstance(
                    layer.get("image"),
                    Image.Image,
                ):
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
                            value=layer["hex"],
                            disabled=True,
                            key=f"color_{uid}",
                        )

                    if "percentage" in layer:
                        st.caption(
                            f"Area: "
                            f"{layer['percentage']}%"
                        )

                    if "pixel_count" in layer:
                        st.caption(
                            f"Pixels: "
                            f"{layer['pixel_count']:,}"
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

                    st.caption(
                        f"Position: "
                        f"X {layer.get('x', 0)}, "
                        f"Y {layer.get('y', 0)}"
                    )

                    st.caption(
                        f"Size: "
                        f"{layer.get('width', 0)} × "
                        f"{layer.get('height', 0)}"
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
                name_widget_key = f"name_{uid}"
                visible_widget_key = f"visible_{uid}"
                opacity_widget_key = f"opacity_{uid}"

                layer_name = st.text_input(
                    "Layer Name",
                    value=st.session_state[names_key][index],
                    key=name_widget_key,
                    on_change=commit_layer_name_change,
                    args=(
                        prefix,
                        index,
                        name_widget_key,
                    ),
                )

                # The on_change callback updates the model state and
                # records the pre-edit snapshot. This assignment keeps
                # state aligned during ordinary reruns.
                st.session_state[names_key][index] = layer_name

                visible = st.checkbox(
                    "👁 Show Layer",
                    value=st.session_state[visibility_key][index],
                    key=visible_widget_key,
                    on_change=commit_layer_visibility_change,
                    args=(
                        prefix,
                        index,
                        visible_widget_key,
                    ),
                )

                st.session_state[visibility_key][index] = bool(
                    visible
                )

                opacity = st.slider(
                    "Opacity",
                    min_value=0,
                    max_value=100,
                    value=st.session_state[opacity_key][index],
                    step=1,
                    key=opacity_widget_key,
                    on_change=commit_layer_opacity_change,
                    args=(
                        prefix,
                        index,
                        opacity_widget_key,
                    ),
                )

                st.session_state[opacity_key][index] = int(
                    opacity
                )

                if locked:
                    st.info(
                        "🔒 Transform editing is locked for this layer."
                    )

            # =================================================
            # ADVANCED TRANSFORMS
            # =================================================

            if isinstance(
                layer.get("image"),
                Image.Image,
            ):
                with st.expander(
                    "🛠️ Transform Layer",
                    expanded=False,
                ):

                    st.caption(
                        "Transform buttons modify the current layer "
                        "cumulatively. Reset restores this layer to "
                        "its original editor state."
                    )

                    reset_col, status_col = st.columns(
                        [1, 2]
                    )

                    with reset_col:
                        reset_clicked = st.button(
                            "↺ Reset Transform",
                            key=f"reset_transform_{uid}",
                            disabled=locked,
                            use_container_width=True,
                        )

                    with status_col:
                        if locked:
                            st.caption(
                                "🔒 Unlock the layer to reset or transform it."
                            )
                        else:
                            st.caption(
                                "Reset is Undo-compatible."
                            )

                    if reset_clicked:
                        try:
                            record_layer_history(prefix)

                            st.session_state[layers_key][index] = (
                                reset_layer_transform(
                                    layer,
                                    st.session_state[original_key],
                                    uid,
                                )
                            )

                            # Reset control widgets for clearer UI.
                            for widget_key in [
                                f"move_x_{uid}",
                                f"move_y_{uid}",
                                f"scale_{uid}",
                            ]:
                                st.session_state.pop(
                                    widget_key,
                                    None,
                                )

                            st.rerun()

                        except Exception as error:
                            report_app_error(
                                error,
                                "Layer reset",
                                context={
                                    "layer_group": prefix,
                                    "layer_index": index,
                                },
                            )

                    st.divider()

                    (
                        rotate_left_col,
                        rotate_right_col,
                        flip_h_col,
                        flip_v_col,
                    ) = st.columns(4)

                    with rotate_left_col:
                        rotate_left_clicked = st.button(
                            "↶ Left",
                            key=f"rotate_left_{uid}",
                            disabled=locked,
                            use_container_width=True,
                        )

                    if rotate_left_clicked:
                        record_layer_history(prefix)
                        st.session_state[layers_key][index] = (
                            transform_layer(
                                layer,
                                "rotate_left",
                            )
                        )
                        st.rerun()

                    with rotate_right_col:
                        rotate_right_clicked = st.button(
                            "↷ Right",
                            key=f"rotate_right_{uid}",
                            disabled=locked,
                            use_container_width=True,
                        )

                    if rotate_right_clicked:
                        record_layer_history(prefix)
                        st.session_state[layers_key][index] = (
                            transform_layer(
                                layer,
                                "rotate_right",
                            )
                        )
                        st.rerun()

                    with flip_h_col:
                        flip_h_clicked = st.button(
                            "↔ Flip H",
                            key=f"flip_h_{uid}",
                            disabled=locked,
                            use_container_width=True,
                        )

                    if flip_h_clicked:
                        record_layer_history(prefix)
                        st.session_state[layers_key][index] = (
                            transform_layer(
                                layer,
                                "flip_horizontal",
                            )
                        )
                        st.rerun()

                    with flip_v_col:
                        flip_v_clicked = st.button(
                            "↕ Flip V",
                            key=f"flip_v_{uid}",
                            disabled=locked,
                            use_container_width=True,
                        )

                    if flip_v_clicked:
                        record_layer_history(prefix)
                        st.session_state[layers_key][index] = (
                            transform_layer(
                                layer,
                                "flip_vertical",
                            )
                        )
                        st.rerun()

                    st.divider()

                    move_x_col, move_y_col = st.columns(2)

                    with move_x_col:
                        offset_x = st.number_input(
                            "Move X (px)",
                            min_value=-5000,
                            max_value=5000,
                            value=0,
                            step=1,
                            key=f"move_x_{uid}",
                            disabled=locked,
                        )

                    with move_y_col:
                        offset_y = st.number_input(
                            "Move Y (px)",
                            min_value=-5000,
                            max_value=5000,
                            value=0,
                            step=1,
                            key=f"move_y_{uid}",
                            disabled=locked,
                        )

                    if st.button(
                        "📍 Apply Move",
                        key=f"apply_move_{uid}",
                        disabled=locked,
                        use_container_width=True,
                    ):
                        record_layer_history(prefix)
                        st.session_state[layers_key][index] = (
                            transform_layer(
                                layer,
                                "move",
                                offset_x=int(offset_x),
                                offset_y=int(offset_y),
                            )
                        )
                        st.rerun()

                    st.divider()

                    scale_percent = st.slider(
                        "Scale Layer (%)",
                        min_value=10,
                        max_value=300,
                        value=100,
                        step=5,
                        key=f"scale_{uid}",
                        disabled=locked,
                    )

                    if st.button(
                        "🔍 Apply Scale",
                        key=f"apply_scale_{uid}",
                        disabled=locked,
                        use_container_width=True,
                    ):
                        record_layer_history(prefix)
                        st.session_state[layers_key][index] = (
                            transform_layer(
                                layer,
                                "scale",
                                scale_percent=int(scale_percent),
                            )
                        )
                        st.rerun()

    try:
        return rebuild_image(
            st.session_state[layers_key],
            visibility=st.session_state[visibility_key],
            opacities=st.session_state[opacity_key],
        )

    except Exception as error:
        log_background_error(
            error,
            "Layer reconstruction",
            context={
                "layer_group": prefix,
            },
        )
        st.warning(
            "Layer reconstruction could not be completed. "
            "The error has been recorded in Diagnostics."
        )
        return None


# =========================================================
# HEADER
# =========================================================

st.title(
    "🖼️ AI Image Studio"
)

project_status_placeholder = st.empty()

st.subheader(
    "Multi-Format Input • Analysis • Editable Layers • "
    "Object Recognition • Segmentation • OCR • "
    "Smart Export • Layered PSD • Professional Output"
)

st.caption(
    "JPG • PNG • WEBP • TIFF • BMP • PDF • SVG • "
    "HEIC • HEIF → ANALYZE → EDIT → EXPORT"
)

st.divider()


# =========================================================
# 01 — OPEN IMAGE / PROJECT
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
# IMAGE / DOCUMENT INPUT
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
            key=(
                "normal_image_uploader"
            ),
        )
    )

    st.caption(
        "Supported Input: JPG, JPEG, PNG, WEBP, TIFF, BMP, "
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

            first_stem = (
                os.path.splitext(
                    first_normal_file.name
                )[0]
            )


            # =================================================
            # PDF INPUT
            # =================================================

            if input_type == "pdf":

                page_count = int(
                    first_input_info.get(
                        "page_count",
                        1,
                    )
                )

                st.info(
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
                        key=(
                            "input_pdf_page_mode"
                        ),
                    )
                )

                input_render_dpi = (
                    st.select_slider(
                        "PDF Render DPI",
                        options=(
                            INPUT_RENDER_DPI_PRESETS
                        ),
                        value=150,
                        key=(
                            "input_pdf_render_dpi"
                        ),
                    )
                )


                # =============================================
                # SINGLE PDF PAGE
                # =============================================

                if (
                    pdf_page_mode
                    == "Single Page"
                ):

                    selected_pdf_page = (
                        st.number_input(
                            "PDF Page",
                            min_value=1,
                            max_value=(
                                page_count
                            ),
                            value=1,
                            step=1,
                            key=(
                                "input_pdf_page"
                            ),
                        )
                    )

                    with st.spinner(
                        f"Preparing PDF Page "
                        f"{selected_pdf_page}..."
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

                    st.session_state[
                        "normal_input_metadata"
                    ] = (
                        normal_input_metadata
                    )

                    for warning in (
                        prepared_first.get(
                            "warnings",
                            [],
                        )
                    ):

                        st.warning(
                            warning
                        )

                    st.success(
                        f"PDF Page "
                        f"{selected_pdf_page} ready."
                    )


                # =============================================
                # ALL PDF PAGES
                # =============================================

                else:

                    st.info(
                        f"All {page_count} pages will be prepared "
                        f"for batch export. Page 1 is used as "
                        f"the editor preview."
                    )

                    if page_count > 50:

                        st.warning(
                            "Large PDF detected. "
                            "300 or 600 DPI may require "
                            "significant memory."
                        )

                    with st.spinner(
                        f"Rendering all "
                        f"{page_count} PDF pages..."
                    ):

                        all_pdf_pages = (
                            cached_prepare_all_pdf_pages(
                                first_normal_bytes,
                                render_dpi=int(
                                    input_render_dpi
                                ),
                            )
                        )

                    for page in (
                        all_pdf_pages
                    ):

                        page_number = int(
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
                                    "data"
                                ],
                            )
                        )

                    if all_pdf_pages:

                        first_page = (
                            all_pdf_pages[0]
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
                                (
                                    int(
                                        input_render_dpi
                                    ),
                                    int(
                                        input_render_dpi
                                    ),
                                ),

                            "input_type":
                                "pdf",

                            "pdf_page_mode":
                                "All Pages",

                            "selected_page":
                                1,

                            "page_count":
                                page_count,

                            "render_dpi":
                                int(
                                    input_render_dpi
                                ),
                        }

                        st.session_state[
                            "normal_input_metadata"
                        ] = (
                            normal_input_metadata
                        )

                    st.success(
                        f"✅ {len(all_pdf_pages)} "
                        f"PDF page(s) ready."
                    )


            # =================================================
            # NON-PDF INPUT
            # =================================================

            else:

                if (
                    input_type
                    == "svg"
                ):

                    st.info(
                        "🔷 SVG detected. "
                        "SVG will be rasterized for editing."
                    )

                    input_render_dpi = (
                        st.select_slider(
                            "SVG Render DPI",
                            options=(
                                INPUT_RENDER_DPI_PRESETS
                            ),
                            value=150,
                            key=(
                                "input_svg_render_dpi"
                            ),
                        )
                    )

                elif extension in (
                    ".heic",
                    ".heif",
                ):

                    st.info(
                        "📱 HEIC / HEIF detected. "
                        "Image will be converted internally "
                        "for editing."
                    )

                with st.spinner(
                    "Preparing input..."
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

                    "selected_page":
                        1,

                    "page_count":
                        1,

                    "render_dpi":
                        int(
                            input_render_dpi
                        ),
                }

                st.session_state[
                    "normal_input_metadata"
                ] = (
                    normal_input_metadata
                )

                for warning in (
                    prepared_first.get(
                        "warnings",
                        [],
                    )
                ):

                    st.warning(
                        warning
                    )


            # =================================================
            # INPUT INFO
            # =================================================

            if (
                prepared_normal_uploaded_files
            ):

                with Image.open(
                    io.BytesIO(
                        prepared_normal_uploaded_files[
                            0
                        ].getvalue()
                    )
                ) as preview_image:

                    p_width = (
                        preview_image.width
                    )

                    p_height = (
                        preview_image.height
                    )

                    p_mode = (
                        preview_image.mode
                    )

                info1, info2, info3 = (
                    st.columns(3)
                )

                info1.metric(
                    "Source Format",
                    (
                        normal_input_metadata.get(
                            "source_format",
                            "Unknown",
                        )
                        if normal_input_metadata
                        else "Unknown"
                    ),
                )

                info2.metric(
                    "Prepared Size",
                    (
                        f"{p_width} × "
                        f"{p_height}"
                    ),
                )

                info3.metric(
                    "Editing Mode",
                    p_mode,
                )


            # =================================================
            # EXTRA FILES
            # =================================================

            if (
                len(
                    normal_uploaded_files
                )
                > 1
            ):

                st.info(
                    "Additional files are prepared for batch export. "
                    "For additional PDFs, Page 1 is used."
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

                        extra_result = (
                            cached_prepare_input(
                                extra_bytes,
                                extra_file.name,
                                page_number=1,
                                render_dpi=150,
                            )
                        )

                        extra_stem = (
                            os.path.splitext(
                                extra_file.name
                            )[0]
                        )

                        if (
                            extra_type
                            == "pdf"
                        ):

                            extra_name = (
                                f"{extra_stem}"
                                f"_page_1.png"
                            )

                        else:

                            extra_name = (
                                f"{extra_stem}"
                                f".png"
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

                        logged_error = log_background_error(
                            extra_error,
                            "Additional input preparation",
                            context={
                                "filename": extra_file.name,
                            },
                        )

                        st.warning(
                            f"Could not load {extra_file.name}. "
                            f"{logged_error.get('technical_message', str(extra_error))}"
                        )


        except Exception as error:

            report_app_error(
                error,
                "Input preparation",
                context={
                    "filename": getattr(
                        first_normal_file,
                        "name",
                        "Unknown",
                    ),
                },
                show_technical=True,
            )


# =========================================================
# NORMAL INPUT CHANGE
# =========================================================

if (
    prepared_normal_uploaded_files
):

    normal_signature = (
        prepared_normal_uploaded_files[
            0
        ].name,

        hashlib.sha1(
            prepared_normal_uploaded_files[
                0
            ].getvalue()
        ).hexdigest(),

        len(
            prepared_normal_uploaded_files
        ),
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
# PROJECT INPUT
# =========================================================

with project_tab:

    project_file = (
        st.file_uploader(
            "Open AI Image Studio Project",
            type=[
                "aistudio",
            ],
            accept_multiple_files=False,
            key=(
                "project_uploader"
            ),
        )
    )

    if (
        project_file
        is not None
    ):

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

            project_size = (
                project_information.get(
                    "original_size"
                )
            )

            if project_size:

                st.caption(
                    f"Original Size: "
                    f"{project_size[0]} × "
                    f"{project_size[1]} px"
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
                ] = (
                    project_image_bytes
                )

                st.session_state[
                    "opened_project_filename"
                ] = (
                    project_filename
                )

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
                        ] = (
                            edited_image
                        )

                        st.session_state[
                            "smart_color_operation"
                        ] = (
                            "Restored Project Edit"
                        )

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

            report_app_error(
                error,
                "Project open",
                context={
                    "filename": getattr(
                        project_file,
                        "name",
                        "Unknown",
                    ),
                },
                show_technical=True,
            )


# =========================================================
# SWITCH BACK
# =========================================================

if (
    prepared_normal_uploaded_files
    and
    st.session_state.get(
        "active_input_mode"
    )
    == "project"
):

    if st.button(
        "🖼️ Switch to Uploaded Image / Document",
        use_container_width=True,
    ):

        clear_workspace_state()

        st.session_state[
            "project_is_open"
        ] = False

        st.session_state[
            "active_input_mode"
        ] = "image"

        st.rerun()


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


elif (
    prepared_normal_uploaded_files
):

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
        "or open an .aistudio project to start."
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

file_hash = (
    hashlib.sha1(
        first_bytes
    ).hexdigest()
)

current_signature = (
    uploaded_files[
        0
    ].name,

    file_hash,
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

    first_image = (
        opened.copy()
    )

    prepared_format = (
        opened.format
    )

    prepared_dpi = (
        opened.info.get(
            "dpi",
            "Not available",
        )
    )


original_width, original_height = (
    first_image.size
)


# =========================================================
# SOURCE METADATA
# =========================================================

if (
    st.session_state.get(
        "active_input_mode"
    )
    == "image"
):

    source_metadata = (
        st.session_state.get(
            "normal_input_metadata",
            {},
        )
    )

else:

    source_metadata = {}


display_source_name = (
    source_metadata.get(
        "source_filename",
        uploaded_files[
            0
        ].name,
    )
)


display_format = (
    source_metadata.get(
        "source_format",
        prepared_format,
    )
)


display_dpi = (
    source_metadata.get(
        "source_dpi",
        prepared_dpi,
    )
)


if st.session_state.get(
    "project_is_open",
    False,
):

    st.success(
        "📂 Editable .aistudio project is open."
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
            display_source_name
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
        (
            f"{original_width * original_height:,}"
        ),
    )

    st.write(
        f"**Source Format:** "
        f"{display_format}"
    )

    st.write(
        f"**Editing Mode:** "
        f"{first_image.mode}"
    )

    st.write(
        f"**Source DPI:** "
        f"{display_dpi}"
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

    if (
        pdf_mode
        == "All Pages"
    ):

        st.info(
            f"PDF All Pages Mode: "
            f"{source_metadata.get('page_count', 1)} pages loaded. "
            f"Page 1 is shown in the editor. "
            f"Render DPI: "
            f"{source_metadata.get('render_dpi', 150)}."
        )

    else:

        st.info(
            f"PDF Page "
            f"{source_metadata.get('selected_page', 1)} "
            f"of "
            f"{source_metadata.get('page_count', 1)} "
            f"was rasterized at "
            f"{source_metadata.get('render_dpi', 150)} DPI."
        )


elif (
    source_metadata.get(
        "input_type"
    )
    == "svg"
):

    st.info(
        "SVG has been rasterized for editing. "
        "Original vector paths are not preserved."
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


if (
    stats[
        "transparency"
    ]
):

    st.info(
        "Transparency detected: "
        f"{stats['transparent_percentage']}%"
    )

else:

    st.caption(
        "No transparent areas detected."
    )


# =========================================================
# DOMINANT COLORS
# =========================================================

st.subheader(
    "🎨 Dominant Colors"
)

dominant_colors = (
    analysis[
        "dominant_colors"
    ]
)

if dominant_colors:

    columns = (
        st.columns(
            len(
                dominant_colors
            )
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
                value=(
                    color[
                        "hex"
                    ]
                ),
                disabled=True,
                key=(
                    f"analysis_color_{index}"
                ),
            )

            st.caption(
                color[
                    "hex"
                ].upper()
            )

            st.caption(
                f"{color['percentage']}%"
            )


# =========================================================
# SHAPES
# =========================================================

st.subheader(
    "🔷 Shape Analysis"
)

shapes = (
    analysis[
        "shapes"
    ]
)

s1, s2, s3, s4 = (
    st.columns(4)
)

s1.metric(
    "Rectangles",
    shapes[
        "rectangles"
    ],
)

s2.metric(
    "Triangles",
    shapes[
        "triangles"
    ],
)

s3.metric(
    "Circles / Curves",
    shapes[
        "circles_or_curves"
    ],
)

s4.metric(
    "Other Shapes",
    shapes[
        "other_shapes"
    ],
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
        min_value=2,
        max_value=12,
        value=6,
        step=1,
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

    st.success(
        f"{len(color_layers)} "
        f"color layers created."
    )


if (
    "color_layers"
    in st.session_state
):

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

        left, right = (
            st.columns(2)
        )

        with left:

            st.image(
                first_image,
                caption="Original",
                use_container_width=True,
            )

        with right:

            st.image(
                color_rebuilt,
                caption=(
                    "Color Reconstruction"
                ),
                use_container_width=True,
            )


st.divider()


# =========================================================
# 05 — SEMANTIC LAYERS
# =========================================================

st.header(
    "05 — 🧠 Smart Semantic Layers"
)

st.info(
    "Semantic separation is approximate and does not "
    "restore original Photoshop/CorelDRAW layers."
)

if st.button(
    "✨ Detect Smart Semantic Layers",
    use_container_width=True,
):

    with st.spinner(
        "Detecting semantic regions..."
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

    st.success(
        f"{len(semantic_layers)} "
        f"semantic layers created."
    )


if (
    "semantic_layers"
    in st.session_state
):

    semantic_rebuilt = (
        render_layer_panel(
            "semantic",
            "semantic",
        )
    )

    if isinstance(
        semantic_rebuilt,
        Image.Image,
    ):

        st.image(
            semantic_rebuilt,
            caption=(
                "Semantic Reconstruction"
            ),
            use_container_width=True,
        )


st.divider()


# =========================================================
# 06 — OBJECT RECOGNITION
# =========================================================

st.header(
    "06 — 🎯 AI Object Recognition"
)

object_confidence = (
    st.slider(
        "Object Detection Confidence",
        min_value=20,
        max_value=95,
        value=50,
        step=5,
    )
)

max_objects = (
    st.slider(
        "Maximum Objects",
        min_value=1,
        max_value=20,
        value=10,
        step=1,
    )
)

if st.button(
    "🎯 Detect & Recognize Objects",
    type="primary",
    use_container_width=True,
):

    try:

        with st.spinner(
            "Recognizing objects..."
        ):

            object_result = (
                create_object_layers(
                    first_image,
                    confidence_threshold=(
                        object_confidence
                        / 100.0
                    ),
                    max_objects=(
                        max_objects
                    ),
                )
            )

        st.session_state[
            "object_result"
        ] = object_result

        if (
            object_result[
                "layers"
            ]
        ):

            initialize_layer_state(
                "object",
                object_result[
                    "layers"
                ],
            )

        st.success(
            f"{object_result['object_count']} "
            f"object(s) recognized."
        )

    except Exception as error:

        report_app_error(
            error,
            "Object recognition",
            context={
                "confidence": object_confidence,
                "max_objects": max_objects,
            },
            show_technical=True,
        )


if (
    "object_result"
    in st.session_state
):

    result = (
        st.session_state[
            "object_result"
        ]
    )

    st.image(
        result[
            "preview"
        ],
        caption=(
            "Detected Objects"
        ),
        use_container_width=True,
    )


if (
    "object_layers"
    in st.session_state
):

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

st.info(
    "Segmentation uses object detection + GrabCut. "
    "Masks are approximate."
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
            min_value=20,
            max_value=95,
            value=50,
            step=5,
        )
    )

    seg_max_objects = (
        st.slider(
            "Maximum Segmented Objects",
            min_value=1,
            max_value=20,
            value=10,
        )
    )

    seg_iterations = (
        st.slider(
            "Segmentation Refinement",
            min_value=1,
            max_value=10,
            value=5,
        )
    )

    seg_feather = (
        st.slider(
            "Edge Feather",
            min_value=0,
            max_value=15,
            value=3,
        )
    )

    if st.button(
        "✂️ Segment Detected Objects",
        type="primary",
        use_container_width=True,
    ):

        try:

            with st.spinner(
                "Segmenting objects..."
            ):

                result = (
                    create_segmented_object_layers(
                        first_image,
                        confidence_threshold=(
                            seg_confidence
                            / 100.0
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

            if (
                result[
                    "layers"
                ]
            ):

                initialize_layer_state(
                    "segment",
                    result[
                        "layers"
                    ],
                )

            st.success(
                f"{result['object_count']} "
                f"object(s) segmented."
            )

        except Exception as error:

            report_app_error(
                error,
                "Object segmentation",
                context={
                    "confidence": seg_confidence,
                    "max_objects": seg_max_objects,
                },
                show_technical=True,
            )

    if (
        "segmentation_result"
        in st.session_state
    ):

        st.image(
            st.session_state[
                "segmentation_result"
            ][
                "preview"
            ],
            caption=(
                "Segmentation Preview"
            ),
            use_container_width=True,
        )

    if (
        "segment_layers"
        in st.session_state
    ):

        render_layer_panel(
            "segment",
            "segmentation",
        )


with bg_tab:

    bg_margin = (
        st.slider(
            "Background Detection Margin (%)",
            min_value=1,
            max_value=15,
            value=3,
        )
    )

    bg_iterations = (
        st.slider(
            "Background Removal Refinement",
            min_value=1,
            max_value=10,
            value=5,
        )
    )

    bg_feather = (
        st.slider(
            "Background Edge Feather",
            min_value=0,
            max_value=15,
            value=3,
        )
    )

    if st.button(
        "🪄 Remove Background",
        type="primary",
        use_container_width=True,
    ):

        try:

            with st.spinner(
                "Removing background..."
            ):

                result = (
                    remove_background(
                        first_image,
                        margin_percent=(
                            bg_margin
                            / 100.0
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

            st.success(
                "Background removal complete."
            )

        except Exception as error:

            report_app_error(
                error,
                "Background removal",
                context={
                    "margin_percent": bg_margin,
                    "iterations": bg_iterations,
                    "feather": bg_feather,
                },
                show_technical=True,
            )

    if (
        "background_remove_result"
        in st.session_state
    ):

        st.image(
            st.session_state[
                "background_remove_result"
            ][
                "image"
            ],
            caption=(
                "Background Removed"
            ),
            use_container_width=True,
        )


st.divider()


# =========================================================
# 08 — SMART COLOR EDITOR
# =========================================================

st.header(
    "08 — 🎨 Smart Color Editor"
)

default_source_color = (
    dominant_colors[
        0
    ][
        "hex"
    ]
    if dominant_colors
    else "#000000"
)


color_tabs = (
    st.tabs(
        [
            "🎨 Replace",
            "🫥 Remove",
            "🧩 Extract Layer",
            "🔀 Merge",
        ]
    )
)


with color_tabs[0]:

    replace_source = (
        st.color_picker(
            "Source Color",
            value=(
                default_source_color
            ),
            key=(
                "replace_source_color"
            ),
        )
    )

    replacement_color = (
        st.color_picker(
            "New Color",
            value="#FF0000",
            key=(
                "replacement_color"
            ),
        )
    )

    replace_tolerance = (
        st.slider(
            "Tolerance",
            min_value=0,
            max_value=255,
            value=30,
            key=(
                "replace_tolerance"
            ),
        )
    )

    preserve_shading = (
        st.checkbox(
            "Preserve Light / Shadow Detail",
            value=True,
        )
    )

    source_rgb = (
        hex_to_rgb(
            replace_source
        )
    )

    preview = (
        create_mask_preview(
            first_image,
            source_rgb,
            replace_tolerance,
        )
    )

    selection_info = (
        color_selection_info(
            first_image,
            source_rgb,
            replace_tolerance,
        )
    )

    c1, c2 = (
        st.columns(2)
    )

    with c1:

        st.image(
            preview,
            use_container_width=True,
        )

    with c2:

        st.metric(
            "Selected Pixels",
            f"{selection_info['selected_pixels']:,}",
        )

        st.metric(
            "Selected Area",
            f"{selection_info['percentage']}%",
        )

    if st.button(
        "🎨 Apply Color Replacement",
        type="primary",
        use_container_width=True,
    ):

        edited = (
            replace_color(
                first_image,
                source_rgb,
                hex_to_rgb(
                    replacement_color
                ),
                tolerance=(
                    replace_tolerance
                ),
                preserve_shading=(
                    preserve_shading
                ),
            )
        )

        st.session_state[
            "smart_color_result"
        ] = edited

        st.session_state[
            "smart_color_operation"
        ] = (
            "Color Replacement"
        )

        st.rerun()


with color_tabs[1]:

    remove_target = (
        st.color_picker(
            "Color to Remove",
            value=(
                default_source_color
            ),
            key=(
                "remove_target_color"
            ),
        )
    )

    remove_tolerance = (
        st.slider(
            "Remove Tolerance",
            min_value=0,
            max_value=255,
            value=30,
        )
    )

    remove_feather = (
        st.slider(
            "Transparent Edge Feather",
            min_value=0,
            max_value=15,
            value=3,
        )
    )

    remove_rgb = (
        hex_to_rgb(
            remove_target
        )
    )

    st.image(
        create_mask_preview(
            first_image,
            remove_rgb,
            remove_tolerance,
        ),
        use_container_width=True,
    )

    if st.button(
        "🫥 Remove Selected Color",
        type="primary",
        use_container_width=True,
    ):

        edited = (
            remove_color(
                first_image,
                remove_rgb,
                tolerance=(
                    remove_tolerance
                ),
                feather=(
                    remove_feather
                ),
            )
        )

        st.session_state[
            "smart_color_result"
        ] = edited

        st.session_state[
            "smart_color_operation"
        ] = (
            "Transparent Color Removal"
        )

        st.rerun()


with color_tabs[2]:

    extract_target = (
        st.color_picker(
            "Color to Extract",
            value=(
                default_source_color
            ),
            key=(
                "extract_target_color"
            ),
        )
    )

    extract_tolerance = (
        st.slider(
            "Extraction Tolerance",
            min_value=0,
            max_value=255,
            value=30,
        )
    )

    extract_feather = (
        st.slider(
            "Layer Edge Feather",
            min_value=0,
            max_value=15,
            value=1,
        )
    )

    if st.button(
        "🧩 Extract Selected Color Layer",
        type="primary",
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
                feather=(
                    extract_feather
                ),
            )
        )

        initialize_layer_state(
            "smartcolor",
            [
                layer
            ],
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

    merge_count = (
        st.slider(
            "Number of Source Colors",
            min_value=2,
            max_value=4,
            value=2,
        )
    )

    merge_sources = []

    for index in range(
        merge_count
    ):

        default_color = (
            dominant_colors[
                index
            ][
                "hex"
            ]
            if (
                dominant_colors
                and
                index
                < len(
                    dominant_colors
                )
            )
            else "#808080"
        )

        value = (
            st.color_picker(
                f"Source Color {index + 1}",
                value=(
                    default_color
                ),
                key=(
                    f"merge_source_{index}"
                ),
            )
        )

        merge_sources.append(
            hex_to_rgb(
                value
            )
        )

    destination = (
        st.color_picker(
            "Destination Color",
            value="#0000FF",
            key=(
                "merge_destination"
            ),
        )
    )

    merge_tolerance = (
        st.slider(
            "Merge Tolerance",
            min_value=0,
            max_value=255,
            value=30,
        )
    )

    if st.button(
        "🔀 Merge Selected Colors",
        type="primary",
        use_container_width=True,
    ):

        merged = (
            merge_colors(
                first_image,
                merge_sources,
                hex_to_rgb(
                    destination
                ),
                tolerance=(
                    merge_tolerance
                ),
                preserve_shading=True,
            )
        )

        st.session_state[
            "smart_color_result"
        ] = merged

        st.session_state[
            "smart_color_operation"
        ] = (
            "Color Merge"
        )

        st.rerun()


if (
    "smart_color_result"
    in st.session_state
):

    st.subheader(
        "🖼️ Edited Result"
    )

    st.image(
        st.session_state[
            "smart_color_result"
        ],
        use_container_width=True,
    )


st.divider()


# =========================================================
# 09 — TEXT DETECTION
# =========================================================

st.header(
    "09 — 🔤 Text Detection & Layers"
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

    if (
        result[
            "individual_layers"
        ]
    ):

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
        ][
            "preview"
        ],
        use_container_width=True,
    )


if (
    "text_layers"
    in st.session_state
):

    render_layer_panel(
        "text",
        "text",
    )


st.divider()


# =========================================================
# 10 — OCR
# =========================================================

st.header(
    "10 — 🔎 OCR Text Recognition"
)

ocr_confidence = (
    st.slider(
        "OCR Minimum Confidence",
        min_value=10,
        max_value=95,
        value=30,
        step=5,
    )
)

if st.button(
    "🤖 Read Text with OCR",
    type="primary",
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
                        / 100.0
                    ),
                )
            )

        st.session_state[
            "ocr_result"
        ] = result

        if (
            result[
                "layers"
            ]
        ):

            initialize_layer_state(
                "ocr",
                result[
                    "layers"
                ],
            )

        st.rerun()

    except Exception as error:

        report_app_error(
            error,
            "OCR",
            context={
                "minimum_confidence": ocr_confidence,
            },
            show_technical=True,
        )


if (
    "ocr_result"
    in st.session_state
):

    result = (
        st.session_state[
            "ocr_result"
        ]
    )

    st.image(
        result[
            "preview"
        ],
        use_container_width=True,
    )

    if (
        result[
            "full_text"
        ].strip()
    ):

        st.text_area(
            "Extracted Text",
            value=(
                result[
                    "full_text"
                ]
            ),
            height=180,
        )


if (
    "ocr_layers"
    in st.session_state
):

    render_layer_panel(
        "ocr",
        "ocr",
    )


st.divider()


# =========================================================
# OUTPUT PREPARATION
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

available_source_names = (
    list(
        available_export_sources.keys()
    )
)

current_export_source = (
    st.session_state.get(
        "output_export_source",
        "Original Image",
    )
)

if (
    current_export_source
    not in available_source_names
):

    st.session_state[
        "output_export_source"
    ] = (
        "Original Image"
    )


selected_export_source = (
    st.selectbox(
        "Choose Final Export Source",
        available_source_names,
        key=(
            "output_export_source"
        ),
    )
)

export_source_image = (
    available_export_sources[
        selected_export_source
    ]
)

source_preview_col, source_info_col = (
    st.columns(
        [2, 1]
    )
)

with source_preview_col:

    st.image(
        export_source_image,
        caption=(
            selected_export_source
        ),
        use_container_width=True,
    )

with source_info_col:

    source_width, source_height = (
        export_source_image.size
    )

    st.metric(
        "Source Width",
        f"{source_width:,} px",
    )

    st.metric(
        "Source Height",
        f"{source_height:,} px",
    )

    st.metric(
        "Source Mode",
        export_source_image.mode,
    )


if (
    selected_export_source
    != "Original Image"
    and
    len(
        uploaded_files
    )
    > 1
):

    st.warning(
        "Edited export sources belong only to the active "
        "first image/page."
    )


# =========================================================
# SMART EXPORT
# =========================================================

st.subheader(
    "🧠 Smart Export Recommendation"
)

st.caption(
    "Rules-based recommendation using image properties "
    "and intended output purpose."
)

smart_col1, smart_col2 = (
    st.columns(2)
)

with smart_col1:

    smart_purpose = (
        st.selectbox(
            "Export Purpose",
            EXPORT_PURPOSES,
            key=(
                "smart_export_purpose"
            ),
        )
    )

with smart_col2:

    smart_priority = (
        st.selectbox(
            "File Size / Quality Priority",
            SMART_EXPORT_PRIORITIES,
            key=(
                "smart_export_priority"
            ),
        )
    )


try:

    recommendation = (
        recommend_export_settings(
            export_source_image,
            purpose=(
                smart_purpose
            ),
            file_size_priority=(
                smart_priority
            ),
        )
    )

    rec1, rec2, rec3, rec4 = (
        st.columns(4)
    )

    rec1.metric(
        "Format",
        recommendation[
            "format"
        ],
    )

    rec2.metric(
        "DPI",
        recommendation[
            "dpi"
        ],
    )

    rec3.metric(
        "Color Mode",
        recommendation[
            "color_mode"
        ],
    )

    rec4.metric(
        "Quality",
        recommendation[
            "quality"
        ],
    )

    st.info(
        recommendation[
            "reason"
        ]
    )

    resolution = (
        recommendation[
            "resolution_analysis"
        ]
    )

    st.write(
        "**Resolution Check:** "
        f"{resolution['level']} — "
        f"{resolution['message']}"
    )

    for warning in (
        recommendation[
            "warnings"
        ]
    ):

        st.warning(
            warning
        )

    if st.button(
        "✨ Apply Recommended Settings",
        type="primary",
        use_container_width=True,
    ):

        recommended_format = (
            recommendation[
                "format"
            ]
        )

        recommended_dpi = int(
            recommendation[
                "dpi"
            ]
        )

        st.session_state[
            "output_export_mode"
        ] = (
            "Single Format"
        )

        st.session_state[
            "output_single_format"
        ] = (
            recommended_format
        )

        st.session_state[
            "output_multiple_formats"
        ] = [
            recommended_format
        ]

        if (
            recommended_dpi
            in DPI_PRESETS
        ):

            st.session_state[
                "output_dpi_mode"
            ] = "Preset"

            st.session_state[
                "output_dpi_preset"
            ] = recommended_dpi

            st.session_state[
                "output_custom_dpi"
            ] = recommended_dpi

        else:

            st.session_state[
                "output_dpi_mode"
            ] = "Custom"

            st.session_state[
                "output_custom_dpi"
            ] = recommended_dpi

        st.session_state[
            "output_color_mode"
        ] = (
            recommendation[
                "color_mode"
            ]
        )

        st.session_state[
            "output_resize_mode"
        ] = (
            recommendation[
                "resize_mode"
            ]
        )

        st.session_state[
            "output_quality"
        ] = int(
            recommendation[
                "quality"
            ]
        )

        st.session_state[
            "output_webp_lossless"
        ] = bool(
            recommendation[
                "webp_lossless"
            ]
        )

        st.session_state[
            "output_png_compression"
        ] = int(
            recommendation[
                "png_compression"
            ]
        )

        tiff_reverse = {
            "tiff_lzw":
                "LZW - Lossless",

            "tiff_adobe_deflate":
                "Deflate - Lossless",

            "raw":
                "Uncompressed",
        }

        st.session_state[
            "output_tiff_compression"
        ] = (
            tiff_reverse.get(
                recommendation[
                    "tiff_compression"
                ],
                "LZW - Lossless",
            )
        )

        for key in [
            "quality_result",
            "quality_signature",
            "professional_export_results",
        ]:

            if key in st.session_state:

                del st.session_state[
                    key
                ]

        st.rerun()


except Exception as error:

    report_app_error(
        error,
        "Smart Export recommendation",
        context={
            "purpose": smart_purpose,
            "priority": smart_priority,
        },
        show_technical=True,
    )


st.divider()


# =========================================================
# 12 — PROFESSIONAL OUTPUT SETTINGS
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
        key=(
            "output_export_mode"
        ),
    )
)

if (
    export_mode
    == "Single Format"
):

    selected_formats = [
        st.selectbox(
            "Output Format",
            VALID_EXPORT_FORMATS,
            key=(
                "output_single_format"
            ),
        )
    ]

else:

    selected_formats = (
        st.multiselect(
            "Select Output Formats",
            VALID_EXPORT_FORMATS,
            key=(
                "output_multiple_formats"
            ),
        )
    )


# =========================================================
# PSD INFORMATION
# =========================================================

if (
    "PSD (Flattened)"
    in selected_formats
):

    st.info(
        "PSD (Flattened) contains one combined raster image."
    )


current_psd_groups = (
    get_current_layer_groups()
)

current_psd_layer_count = sum(
    len(layers)
    for layers
    in current_psd_groups.values()
)


if (
    "PSD (Layered)"
    in selected_formats
):

    if (
        current_psd_layer_count
        > 0
    ):

        st.success(
            f"PSD (Layered): "
            f"{len(current_psd_groups)} group(s) and "
            f"{current_psd_layer_count} extracted "
            f"layer(s) available."
        )

    else:

        st.warning(
            "PSD (Layered) selected, but no extracted "
            "layers are currently available. Extract Color, "
            "Semantic, Object, Segmentation, Text or OCR "
            "layers first."
        )

    st.caption(
        "PSD (Layered) uses editable raster pixel layers. "
        "Detected text is not native Photoshop text and "
        "detected shapes are not native Photoshop vectors."
    )


# =========================================================
# PIXEL SIZE
# =========================================================

pixel_mode = (
    st.selectbox(
        "Pixel Size Mode",
        [
            "Original Size",
            "Target Total Pixels",
            "Custom Dimensions",
        ],
        key=(
            "output_pixel_mode"
        ),
    )
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

source_width, source_height = (
    export_source_image.size
)


if (
    pixel_mode
    == "Original Size"
):

    target_width = (
        source_width
    )

    target_height = (
        source_height
    )

    st.info(
        f"Selected Source Size: "
        f"{target_width:,} × "
        f"{target_height:,} px"
    )


elif (
    pixel_mode
    == "Target Total Pixels"
):

    target_total_pixels = (
        st.slider(
            "Target Total Pixels",
            min_value=1,
            max_value=150000,
            step=1,
            key=(
                "output_target_pixels"
            ),
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

    st.success(
        f"Calculated Dimensions: "
        f"{target_width:,} × "
        f"{target_height:,} px"
    )

    st.caption(
        f"Actual Total Pixels: "
        f"{target_width * target_height:,}"
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

    d1, d2 = (
        st.columns(2)
    )

    with d1:

        custom_width = (
            st.number_input(
                "Width (px)",
                min_value=1,
                max_value=150000,
                step=1,
                key=(
                    "output_custom_width"
                ),
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
            int(
                custom_width
            ),
        )

        with d2:

            st.metric(
                "Height (px) 🔒",
                f"{target_height:,}",
            )

        st.info(
            f"🔒 Aspect Ratio Locked: "
            f"{target_width:,} × "
            f"{target_height:,} px"
        )

    else:

        with d2:

            custom_height = (
                st.number_input(
                    "Height (px)",
                    min_value=1,
                    max_value=150000,
                    step=1,
                    key=(
                        "output_custom_height"
                    ),
                )
            )

        target_width = int(
            custom_width
        )

        target_height = int(
            custom_height
        )

        st.success(
            f"🔓 Custom Dimensions: "
            f"{target_width:,} × "
            f"{target_height:,} px"
        )


# =========================================================
# DPI
# =========================================================

st.subheader(
    "🖨️ Resolution / DPI"
)

dpi_mode = (
    st.radio(
        "DPI Selection",
        [
            "Preset",
            "Custom",
        ],
        horizontal=True,
        key=(
            "output_dpi_mode"
        ),
    )
)

if (
    dpi_mode
    == "Preset"
):

    dpi = (
        st.select_slider(
            "DPI",
            options=(
                DPI_PRESETS
            ),
            key=(
                "output_dpi_preset"
            ),
        )
    )

else:

    dpi = (
        st.number_input(
            "Custom DPI",
            min_value=72,
            max_value=1200,
            step=1,
            key=(
                "output_custom_dpi"
            ),
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
        key=(
            "output_color_mode"
        ),
    )
)

if (
    color_mode
    == "CMYK"
):

    st.info(
        "Current CMYK conversion uses basic Pillow conversion. "
        "For professional printing, confirm the printer ICC profile."
    )


if (
    (
        "PSD (Flattened)"
        in selected_formats
        or
        "PSD (Layered)"
        in selected_formats
    )
    and
    color_mode != "RGB"
):

    st.warning(
        "Current PSD exporters create RGB PSD files. "
        "CMYK/Grayscale selection does not change PSD output."
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
        key=(
            "output_resize_mode"
        ),
    )
)


# =========================================================
# QUALITY
# =========================================================

quality = int(
    st.session_state.get(
        "output_quality",
        95,
    )
)

if (
    "JPEG"
    in selected_formats
    or
    "WEBP"
    in selected_formats
):

    quality = (
        st.slider(
            "JPEG / WebP Quality",
            min_value=1,
            max_value=100,
            key=(
                "output_quality"
            ),
        )
    )


# =========================================================
# WEBP
# =========================================================

webp_lossless = bool(
    st.session_state.get(
        "output_webp_lossless",
        False,
    )
)

if (
    "WEBP"
    in selected_formats
):

    webp_lossless = (
        st.checkbox(
            "WebP Lossless",
            key=(
                "output_webp_lossless"
            ),
        )
    )


# =========================================================
# PNG
# =========================================================

png_compress_level = int(
    st.session_state.get(
        "output_png_compression",
        6,
    )
)

if (
    "PNG"
    in selected_formats
):

    png_compress_level = (
        st.slider(
            "PNG Compression",
            min_value=0,
            max_value=9,
            key=(
                "output_png_compression"
            ),
        )
    )


# =========================================================
# TIFF
# =========================================================

tiff_compression_name = (
    st.session_state.get(
        "output_tiff_compression",
        "LZW - Lossless",
    )
)

if (
    "TIFF"
    in selected_formats
):

    tiff_compression_name = (
        st.selectbox(
            "TIFF Compression",
            [
                "LZW - Lossless",
                "Deflate - Lossless",
                "Uncompressed",
            ],
            key=(
                "output_tiff_compression"
            ),
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
    tiff_map.get(
        tiff_compression_name,
        "tiff_lzw",
    )
)


# =========================================================
# OUTPUT INFORMATION
# =========================================================

total_output_pixels = (
    int(
        target_width
    )
    *
    int(
        target_height
    )
)

o1, o2, o3, o4 = (
    st.columns(4)
)

o1.metric(
    "Width",
    f"{target_width:,} px",
)

o2.metric(
    "Height",
    f"{target_height:,} px",
)

o3.metric(
    "Total Pixels",
    f"{total_output_pixels:,}",
)

o4.metric(
    "DPI",
    dpi,
)


print_width = (
    target_width
    / dpi
)

print_height = (
    target_height
    / dpi
)

p1, p2 = (
    st.columns(2)
)

p1.metric(
    "Print Size (inch)",
    (
        f"{print_width:.2f} × "
        f"{print_height:.2f}"
    ),
)

p2.metric(
    "Print Size (cm)",
    (
        f"{print_width * 2.54:.2f} × "
        f"{print_height * 2.54:.2f}"
    ),
)


output_too_large = (
    total_output_pixels
    >
    MAX_TOTAL_EXPORT_PIXELS
)

if output_too_large:

    st.error(
        "Selected output is too large for safe processing."
    )

elif (
    total_output_pixels
    > 100_000_000
):

    st.warning(
        "Very large image selected. "
        "Export may require significant RAM."
    )


st.divider()


# =========================================================
# 13 — SAVE EDITABLE PROJECT + AUTO RECOVERY
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

safe_project_name = (
    project_name.strip()
    or
    "AI_Image_Project"
)

project_settings = {

    "export_source":
        selected_export_source,

    "target_width":
        int(
            target_width
        ),

    "target_height":
        int(
            target_height
        ),

    "target_total_pixels":
        int(
            target_total_pixels
        ),

    "maintain_ratio":
        bool(
            maintain_ratio
        ),

    "dpi":
        int(
            dpi
        ),

    "color_mode":
        color_mode,

    "resize_mode":
        resize_mode,

    "export_mode":
        export_mode,

    "selected_formats":
        selected_formats,

    "quality":
        int(
            quality
        ),

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

project_layer_groups = (
    get_current_layer_groups()
)

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

current_project_signature = (
    build_project_state_signature(
        safe_project_name,
        hashlib.sha1(
            first_bytes
        ).hexdigest(),
        project_layer_groups,
        project_settings,
        project_edited_image,
    )
)

saved_signature = (
    st.session_state.get(
        "saved_project_signature"
    )
)

if saved_signature is None:

    if st.session_state.get(
        "recovered_session_pending_save",
        False,
    ):
        project_has_unsaved_changes = True
    else:
        st.session_state[
            "saved_project_signature"
        ] = current_project_signature
        project_has_unsaved_changes = False

else:

    project_has_unsaved_changes = (
        current_project_signature
        != saved_signature
    )

if project_has_unsaved_changes:

    project_status_placeholder.warning(
        "🟠 Unsaved Changes • Auto-Recovery protects the current project state."
    )

else:

    project_status_placeholder.success(
        "🟢 Saved • No unsaved project changes."
    )

try:

    project_bytes = (
        save_project(
            original_image=(
                first_image
            ),
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

    # =====================================================
    # PRE-EXISTING RECOVERY OFFER
    # =====================================================

    existing_recovery = (
        recovery_exists(
            safe_project_name,
            base_directory=".",
        )
    )

    recovery_choice_resolved = (
        st.session_state.get(
            "recovery_choice_resolved",
            False,
        )
    )

    recovery_created_this_session = (
        st.session_state.get(
            "last_recovery_signature"
        )
        is not None
    )

    should_offer_recovery = (
        existing_recovery
        and
        not recovery_choice_resolved
        and
        not recovery_created_this_session
    )

    if should_offer_recovery:

        recovery_info = (
            get_recovery_info(
                safe_project_name,
                base_directory=".",
            )
        )

        saved_at_text = (
            format_recovery_timestamp(
                recovery_info.get(
                    "saved_at"
                )
                if recovery_info
                else None
            )
        )

        recovery_size = (
            recovery_info.get(
                "size_bytes",
                0,
            )
            if recovery_info
            else 0
        )

        st.warning(
            "🛟 Auto-Recovery found a previous unsaved session."
        )

        st.caption(
            f"Recovery saved: {saved_at_text} • "
            f"Size: {recovery_size / 1024:.1f} KB"
        )

        recover_col, discard_col = (
            st.columns(2)
        )

        with recover_col:

            recover_clicked = (
                st.button(
                    "🛟 Recover Last Session",
                    type="primary",
                    use_container_width=True,
                    key="recover_last_session",
                )
            )

        with discard_col:

            discard_clicked = (
                st.button(
                    "🗑️ Discard Recovery",
                    use_container_width=True,
                    key="discard_recovery",
                )
            )

        if recover_clicked:

            recovery_data = (
                load_recovery(
                    safe_project_name,
                    base_directory=".",
                )
            )

            if recovery_data is None:
                st.error(
                    "Recovery file is no longer available."
                )
            else:
                recovered_project = (
                    load_project(
                        recovery_data[
                            "project_bytes"
                        ]
                    )
                )

                activate_loaded_project_data(
                    recovered_project,
                    recovered=True,
                )

                st.session_state[
                    "last_recovery_signature"
                ] = (
                    recovery_data.get(
                        "metadata",
                        {},
                    ).get(
                        "state_signature",
                        "recovered",
                    )
                )

                st.rerun()

        if discard_clicked:

            delete_recovery(
                safe_project_name,
                base_directory=".",
            )

            st.session_state[
                "recovery_choice_resolved"
            ] = True

            st.session_state.pop(
                "last_recovery_signature",
                None,
            )

            st.rerun()

    # =====================================================
    # AUTO-RECOVERY SAVE
    # =====================================================

    elif project_has_unsaved_changes:

        last_recovery_signature = (
            st.session_state.get(
                "last_recovery_signature"
            )
        )

        if (
            current_project_signature
            != last_recovery_signature
        ):

            recovery_result = (
                save_recovery(
                    safe_project_name,
                    project_bytes,
                    base_directory=".",
                    metadata={
                        "state_signature":
                            current_project_signature,

                        "source_filename":
                            uploaded_files[
                                0
                            ].name,
                    },
                )
            )

            st.session_state[
                "last_recovery_signature"
            ] = current_project_signature

            st.session_state[
                "recovery_choice_resolved"
            ] = True

            st.session_state[
                "recovery_last_message"
            ] = (
                "Auto-Recovery updated"
            )

        st.caption(
            "🛟 Auto-Recovery: current unsaved project state is protected locally."
        )

    elif existing_recovery:

        st.caption(
            "🛟 A recovery file exists. Saving/downloading the project will clear it."
        )

    st.download_button(
        "💾 Save .aistudio Project",
        data=(
            project_bytes
        ),
        file_name=(
            f"{safe_project_name}"
            f".aistudio"
        ),
        mime=(
            "application/octet-stream"
        ),
        use_container_width=True,
        on_click=(
            mark_project_downloaded_as_saved
        ),
        args=(
            current_project_signature,
            safe_project_name,
        ),
    )

    st.caption(
        "Local Auto-Recovery uses the project .recovery folder. "
        "On Streamlit Cloud, server storage can be temporary, so keep downloaded .aistudio files as your permanent backup."
    )

except Exception as error:

    report_app_error(
        error,
        "Project save or recovery",
        context={
            "project_name": safe_project_name,
        },
        show_technical=True,
    )


st.divider()


# =========================================================
# 14 — QUALITY CHECK
# =========================================================

st.header(
    "14 — ✅ Professional Quality Check"
)

st.caption(
    "Rules-based preflight for the selected export source."
)

quality_format = (
    selected_formats[
        0
    ]
    if selected_formats
    else "PNG"
)


quality_check_internal_format = (
    "TIFF"
    if quality_format in (
        "PSD (Flattened)",
        "PSD (Layered)",
    )
    else quality_format
)


if quality_format in (
    "PSD (Flattened)",
    "PSD (Layered)",
):

    st.info(
        "PSD preflight uses TIFF-compatible raster checks."
    )


quality_signature = (
    selected_export_source,
    int(
        target_width
    ),
    int(
        target_height
    ),
    int(
        dpi
    ),
    tuple(
        selected_formats
    ),
    color_mode,
    resize_mode,
)


if st.button(
    "🔎 Run Professional Quality Check",
    type="primary",
    use_container_width=True,
):

    if not selected_formats:

        st.warning(
            "Select at least one output format."
        )

    elif output_too_large:

        st.error(
            "Output dimensions are too large."
        )

    else:

        try:

            with st.spinner(
                "Checking final export source..."
            ):

                result = (
                    run_quality_check(
                        export_source_image,
                        target_width=(
                            target_width
                        ),
                        target_height=(
                            target_height
                        ),
                        dpi=(
                            dpi
                        ),
                        output_format=(
                            quality_check_internal_format
                        ),
                        target_color_mode=(
                            color_mode
                        ),
                    )
                )

            st.session_state[
                "quality_result"
            ] = result

            st.session_state[
                "quality_signature"
            ] = (
                quality_signature
            )

        except Exception as error:

            report_app_error(
                error,
                "Professional quality check",
                context={
                    "format": quality_check_internal_format,
                    "dpi": dpi,
                    "color_mode": color_mode,
                },
                show_technical=True,
            )


if (
    "quality_result"
    in st.session_state
):

    result = (
        st.session_state[
            "quality_result"
        ]
    )

    if (
        st.session_state.get(
            "quality_signature"
        )
        != quality_signature
    ):

        st.warning(
            "Export source or settings changed. "
            "Run Quality Check again."
        )

    status = (
        result[
            "overall_status"
        ]
    )

    if (
        status
        == "READY"
    ):

        st.success(
            "✅ READY FOR EXPORT — "
            f"{result['overall_message']}"
        )

    elif (
        status
        == "CHECK"
    ):

        st.warning(
            "⚠️ CHECK BEFORE EXPORT — "
            f"{result['overall_message']}"
        )

    else:

        st.error(
            "🔴 REVIEW RECOMMENDED — "
            f"{result['overall_message']}"
        )

    q1, q2, q3 = (
        st.columns(3)
    )

    q1.metric(
        "Status",
        status,
    )

    q2.metric(
        "Passed",
        result[
            "pass_count"
        ],
    )

    q3.metric(
        "Warnings",
        result[
            "warning_count"
        ],
    )

    for check in (
        result[
            "checks"
        ]
    ):

        with st.container(
            border=True
        ):

            st.write(
                f"**{check['status']} — "
                f"{check['title']}**"
            )

            st.write(
                check[
                    "message"
                ]
            )


st.divider()


# =========================================================
# 15 — PROFESSIONAL EXPORT
# =========================================================

st.header(
    "15 — 🚀 Professional Export"
)

st.write(
    "**Final Export Source:** "
    f"{selected_export_source}"
)


# =========================================================
# BUILD EXPORT JOBS
# =========================================================

if (
    selected_export_source
    == "Original Image"
):

    export_jobs = []

    for uploaded_file in (
        uploaded_files
    ):

        try:

            with Image.open(
                io.BytesIO(
                    uploaded_file.getvalue()
                )
            ) as opened:

                image = (
                    opened.copy()
                )

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

            logged_error = log_background_error(
                error,
                "Export job preparation",
                context={
                    "filename": uploaded_file.name,
                },
            )

            st.warning(
                f"Could not prepare {uploaded_file.name}. "
                f"{logged_error.get('technical_message', str(error))}"
            )


else:

    original_base_name = (
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
            f"{original_base_name}_{suffix}",
            export_source_image,
        )
    ]


if (
    len(
        export_jobs
    )
    > 1
):

    st.info(
        f"Batch Export Ready: "
        f"{len(export_jobs)} images/pages."
    )


# =========================================================
# LAYERED PSD SAFETY
# =========================================================

layered_psd_selected = (
    "PSD (Layered)"
    in selected_formats
)


layered_psd_batch_conflict = (
    layered_psd_selected
    and
    len(
        export_jobs
    )
    > 1
)


layered_psd_missing_layers = (
    layered_psd_selected
    and
    current_psd_layer_count
    == 0
)


if layered_psd_batch_conflict:

    st.warning(
        "PSD (Layered) works with the active edited image/page only. "
        "For a multi-page PDF, choose Single Page mode before exporting "
        "PSD (Layered), or remove PSD (Layered) from the selected formats."
    )


if layered_psd_missing_layers:

    st.warning(
        "PSD (Layered) requires at least one extracted editable layer."
    )


export_disabled = (
    not selected_formats
    or
    output_too_large
    or
    len(
        export_jobs
    )
    == 0
    or
    layered_psd_batch_conflict
    or
    layered_psd_missing_layers
)


export_button = (
    st.button(
        "🚀 Export Final Image(s)",
        type="primary",
        use_container_width=True,
        disabled=(
            export_disabled
        ),
    )
)


if export_button:

    export_results = []

    total_jobs = (
        len(
            export_jobs
        )
        *
        len(
            selected_formats
        )
    )

    completed_jobs = 0

    progress = (
        st.progress(
            0,
            text=(
                "Preparing exports..."
            ),
        )
    )

    active_layer_groups = (
        get_current_layer_groups()
    )

    for (
        source_name,
        source_image
    ) in export_jobs:

        for export_format in (
            selected_formats
        ):

            completed_jobs += 1

            progress.progress(
                completed_jobs
                / total_jobs,
                text=(
                    f"Exporting "
                    f"{source_name} "
                    f"as {export_format}..."
                ),
            )

            try:

                # Original Size means each batch page/image keeps
                # its own dimensions instead of inheriting Page 1.
                if pixel_mode == "Original Size":
                    job_target_width, job_target_height = (
                        source_image.size
                    )
                else:
                    job_target_width = target_width
                    job_target_height = target_height

                # =========================================
                # PSD FLATTENED
                # =========================================

                if (
                    export_format
                    == "PSD (Flattened)"
                ):

                    export_result = (
                        export_flattened_psd(
                            image=(
                                source_image
                            ),
                            width=(
                                job_target_width
                            ),
                            height=(
                                job_target_height
                            ),
                            resize_mode=(
                                resize_mode
                            ),
                        )
                    )


                # =========================================
                # PSD LAYERED
                # =========================================

                elif (
                    export_format
                    == "PSD (Layered)"
                ):

                    if not active_layer_groups:

                        raise ValueError(
                            "No extracted editable layers are available."
                        )

                    export_result = (
                        export_layered_psd(
                            base_image=(
                                source_image
                            ),
                            layer_groups=(
                                active_layer_groups
                            ),
                            document_name=(
                                source_name
                            ),
                            include_original=True,
                        )
                    )


                # =========================================
                # NORMAL FORMATS
                # =========================================

                else:

                    export_result = (
                        export_image(
                            image=(
                                source_image
                            ),
                            output_format=(
                                export_format
                            ),
                            width=(
                                job_target_width
                            ),
                            height=(
                                job_target_height
                            ),
                            dpi=(
                                dpi
                            ),
                            color_mode=(
                                color_mode
                            ),
                            resize_mode=(
                                resize_mode
                            ),
                            quality=(
                                quality
                            ),
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

                logged_error = log_background_error(
                    error,
                    "Image export",
                    context={
                        "input": source_name,
                        "format": export_format,
                        "dpi": int(dpi),
                        "color_mode": color_mode,
                    },
                )

                export_results.append(
                    {
                        "success":
                            False,

                        "format":
                            export_format,

                        "input":
                            source_name,

                        "error":
                            logged_error.get(
                                "technical_message",
                                str(error),
                            ),
                    }
                )

    progress.empty()

    st.session_state[
        "professional_export_results"
    ] = (
        export_results
    )

    st.success(
        "Export processing complete."
    )


# =========================================================
# 16 — EXPORT RESULTS
# =========================================================

if (
    "professional_export_results"
    in st.session_state
):

    st.header(
        "16 — 📥 Export Results"
    )

    results = (
        st.session_state[
            "professional_export_results"
        ]
    )

    success_count = sum(
        1
        for result
        in results
        if result.get(
            "success"
        )
    )

    failure_count = (
        len(
            results
        )
        -
        success_count
    )

    r1, r2 = (
        st.columns(2)
    )

    r1.metric(
        "Successful Exports",
        success_count,
    )

    r2.metric(
        "Failed Exports",
        failure_count,
    )

    st.caption(
        "Each exported file has a separate download button."
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
                f"{result.get('format')}: "
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

            c1, c2, c3, c4 = (
                st.columns(4)
            )

            c1.metric(
                "Format",
                result[
                    "format"
                ],
            )

            c2.metric(
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

            c3.metric(
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

            c4.metric(
                "Color Mode",
                result[
                    "mode"
                ],
            )


            # =============================================
            # LAYERED PSD INFORMATION
            # =============================================

            if (
                result.get(
                    "format"
                )
                == "PSD (Layered)"
            ):

                p1, p2 = (
                    st.columns(2)
                )

                p1.metric(
                    "PSD Groups",
                    result.get(
                        "group_count",
                        0,
                    ),
                )

                p2.metric(
                    "PSD Layers",
                    result.get(
                        "layer_count",
                        0,
                    ),
                )


            for warning in (
                result.get(
                    "warnings",
                    [],
                )
            ):

                st.warning(
                    warning
                )


            st.download_button(
                (
                    "⬇️ Download "
                    f"{result['output_name']}"
                ),
                data=(
                    result[
                        "data"
                    ]
                ),
                file_name=(
                    result[
                        "output_name"
                    ]
                ),
                mime=(
                    result[
                        "mime"
                    ]
                ),
                key=(
                    f"download_"
                    f"{index}_"
                    f"{result['output_name']}"
                ),
                use_container_width=True,
            )


# =========================================================
# 17 — SYSTEM DIAGNOSTICS
# =========================================================

st.divider()

st.header(
    "17 — 🩺 System Diagnostics"
)

st.caption(
    "Runtime errors are recorded locally so failures can be reviewed "
    "without exposing full tracebacks in the main workflow."
)

try:
    diagnostics_summary = get_diagnostics_summary(
        base_directory=".",
    )

    recent_errors = read_recent_errors(
        limit=20,
        base_directory=".",
    )

    diagnostics_error_count = int(
        diagnostics_summary.get(
            "total_errors",
            0,
        )
    )

    diagnostics_status = (
        "Healthy"
        if diagnostics_error_count == 0
        else "Review Logs"
    )

    diagnostics_recovery_available = False

    try:
        diagnostics_recovery_available = recovery_exists(
            safe_project_name,
            base_directory=".",
        )
    except Exception:
        diagnostics_recovery_available = False

    d1, d2, d3, d4 = st.columns(4)

    d1.metric(
        "App Status",
        diagnostics_status,
    )

    d2.metric(
        "Recovery",
        (
            "Available"
            if diagnostics_recovery_available
            else "None"
        ),
    )

    d3.metric(
        "Recent Errors",
        diagnostics_error_count,
    )

    d4.metric(
        "Log",
        "Active",
    )

    st.caption(
        f"Error Log: {diagnostics_summary.get('log_path', 'logs/ai_image_studio_errors.jsonl')}"
    )

    if recent_errors:
        with st.expander(
            "🧾 View Recent Errors",
            expanded=False,
        ):

            for error_index, record in enumerate(
                recent_errors,
                start=1,
            ):
                st.markdown(
                    f"**{error_index}. "
                    f"{record.get('operation', 'Unknown Operation')}**"
                )

                st.caption(
                    f"{record.get('datetime', 'Unknown time')} • "
                    f"{record.get('error_type', 'UnknownError')}"
                )

                st.write(
                    record.get(
                        "message",
                        "No error message recorded.",
                    )
                )

                error_context = record.get(
                    "context",
                    {},
                )

                if isinstance(error_context, dict) and error_context:
                    st.json(
                        error_context
                    )

                st.divider()

        if st.button(
            "🧹 Clear Error Log",
            key="clear_diagnostics_error_log",
            use_container_width=True,
        ):
            clear_error_log(
                base_directory=".",
            )
            st.success(
                "Error log cleared."
            )
            st.rerun()

    else:
        st.success(
            "No recorded runtime errors. Diagnostics status is healthy."
        )

except Exception as diagnostics_error:
    st.warning(
        "Diagnostics panel could not be loaded, but the main editor can continue."
    )
    st.caption(
        str(diagnostics_error)
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "AI Image Studio • JPG • JPEG • PNG • WEBP • TIFF • BMP • "
    "PDF Single Page • PDF All Pages • SVG • HEIC • HEIF • "
    "Editable Color Layers • Semantic Layers • Object Layers • "
    "Segmentation • Background Removal • Color Editing • OCR • "
    "Smart Export • .aistudio Projects • "
    "PNG • JPEG • WEBP • TIFF • BMP • PDF • "
    "PSD (Flattened) • PSD (Layered) • Individual Downloads • "
    "Auto-Recovery • System Diagnostics"
)