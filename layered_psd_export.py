import io
from PIL import Image
from psd_tools import PSDImage


# =========================================================
# SAFE LAYER NAME
# =========================================================

def safe_layer_name(
    name,
    fallback="Layer",
):

    name = str(
        name or fallback
    ).strip()

    if not name:
        name = fallback

    return name[:255]


# =========================================================
# PREPARE IMAGE FOR PSD
# =========================================================

def prepare_layer_image(
    image,
    canvas_size,
):

    if not isinstance(
        image,
        Image.Image,
    ):

        raise ValueError(
            "Layer does not contain a valid PIL image."
        )

    canvas_width, canvas_height = (
        canvas_size
    )

    image = image.convert(
        "RGBA"
    )

    # Already correct canvas size
    if image.size == canvas_size:

        return image

    # Create transparent PSD-size canvas
    canvas = Image.new(
        "RGBA",
        canvas_size,
        (
            0,
            0,
            0,
            0,
        ),
    )

    paste_width = min(
        image.width,
        canvas_width,
    )

    paste_height = min(
        image.height,
        canvas_height,
    )

    if (
        paste_width != image.width
        or
        paste_height != image.height
    ):

        image = image.crop(
            (
                0,
                0,
                paste_width,
                paste_height,
            )
        )

    canvas.paste(
        image,
        (
            0,
            0,
        ),
        image,
    )

    return canvas


# =========================================================
# NORMALIZE OPACITY
# =========================================================

def normalize_opacity(
    opacity,
):

    try:

        opacity = float(
            opacity
        )

    except Exception:

        opacity = 100

    opacity = max(
        0,
        min(
            opacity,
            100,
        ),
    )

    # psd-tools uses 0 → 255
    return int(
        round(
            opacity
            * 255
            / 100
        )
    )


# =========================================================
# EXTRACT LAYER VALUES
# =========================================================

def get_layer_image(layer):

    if not isinstance(
        layer,
        dict,
    ):

        return None

    return layer.get(
        "image"
    )


def get_layer_name(
    layer,
    index,
):

    if not isinstance(
        layer,
        dict,
    ):

        return (
            f"Layer {index + 1}"
        )

    return safe_layer_name(
        layer.get(
            "_saved_name"
        )
        or
        layer.get(
            "name"
        )
        or
        layer.get(
            "object_name"
        )
        or
        layer.get(
            "text"
        )
        or
        f"Layer {index + 1}"
    )


def get_layer_opacity(layer):

    if not isinstance(
        layer,
        dict,
    ):

        return 255

    value = layer.get(
        "_saved_opacity",
        100,
    )

    return normalize_opacity(
        value
    )


def get_layer_visibility(layer):

    if not isinstance(
        layer,
        dict,
    ):

        return True

    return bool(
        layer.get(
            "_saved_visible",
            True,
        )
    )


# =========================================================
# ADD PIXEL LAYER
# =========================================================

def add_pixel_layer(
    psd,
    image,
    name,
    opacity=255,
    visible=True,
):

    prepared = (
        prepare_layer_image(
            image,
            psd.size,
        )
    )

    layer = (
        psd.create_pixel_layer(
            prepared,
            name=(
                safe_layer_name(
                    name
                )
            ),
            top=0,
            left=0,
            opacity=int(
                opacity
            ),
        )
    )

    try:

        layer.visible = bool(
            visible
        )

    except Exception:

        pass

    return layer


# =========================================================
# ADD GROUP
# =========================================================

def add_layer_group(
    psd,
    group_name,
    layers,
):

    if not layers:

        return None

    group = (
        psd.create_group(
            name=(
                safe_layer_name(
                    group_name
                )
            )
        )
    )

    added_count = 0

    for index, layer_data in enumerate(
        layers
    ):

        image = (
            get_layer_image(
                layer_data
            )
        )

        if not isinstance(
            image,
            Image.Image,
        ):

            continue

        name = (
            get_layer_name(
                layer_data,
                index,
            )
        )

        opacity = (
            get_layer_opacity(
                layer_data
            )
        )

        visible = (
            get_layer_visibility(
                layer_data
            )
        )

        # create_pixel_layer initially adds to PSD root.
        pixel_layer = (
            add_pixel_layer(
                psd,
                image,
                name=name,
                opacity=opacity,
                visible=visible,
            )
        )

        # Move layer into group.
        group.append(
            pixel_layer
        )

        added_count += 1

    if added_count == 0:

        try:
            psd.remove(
                group
            )
        except Exception:
            pass

        return None

    return group


# =========================================================
# EXPORT LAYERED PSD
# =========================================================

def export_layered_psd(
    base_image,
    layer_groups=None,
    document_name="AI Image Studio",
    include_original=True,
):

    if not isinstance(
        base_image,
        Image.Image,
    ):

        raise ValueError(
            "A valid base image is required."
        )

    layer_groups = (
        layer_groups
        or {}
    )

    canvas_size = (
        base_image.size
    )

    # RGB 8-bit PSD
    psd = PSDImage.new(
        mode="RGB",
        size=canvas_size,
        depth=8,
        color=(
            255,
            255,
            255,
        ),
    )

    # =====================================================
    # ORIGINAL IMAGE
    # =====================================================

    if include_original:

        add_pixel_layer(
            psd,
            base_image,
            name=(
                "Original Image"
            ),
            opacity=255,
            visible=True,
        )

    # =====================================================
    # LAYER GROUPS
    # =====================================================

    group_display_names = {
        "color":
            "Color Layers",

        "semantic":
            "Semantic Layers",

        "object":
            "Object Layers",

        "segment":
            "Segmentation Layers",

        "smartcolor":
            "Smart Color Layers",

        "text":
            "Text Detection Layers",

        "ocr":
            "OCR Layers",
    }

    group_count = 0

    layer_count = (
        1
        if include_original
        else 0
    )

    for (
        group_key,
        group_layers
    ) in (
        layer_groups.items()
    ):

        if not group_layers:

            continue

        display_name = (
            group_display_names.get(
                group_key,
                group_key.replace(
                    "_",
                    " ",
                ).title(),
            )
        )

        group = (
            add_layer_group(
                psd,
                display_name,
                group_layers,
            )
        )

        if group is not None:

            group_count += 1

            layer_count += len(
                [
                    layer
                    for layer
                    in group_layers
                    if isinstance(
                        get_layer_image(
                            layer
                        ),
                        Image.Image,
                    )
                ]
            )

    # =====================================================
    # SAVE PSD TO MEMORY
    # =====================================================

    buffer = (
        io.BytesIO()
    )

    psd.save(
        buffer
    )

    buffer.seek(0)

    psd_bytes = (
        buffer.getvalue()
    )

    return {
        "data":
            psd_bytes,

        "format":
            "PSD (Layered)",

        "extension":
            ".psd",

        "mime":
            "image/vnd.adobe.photoshop",

        "width":
            canvas_size[0],

        "height":
            canvas_size[1],

        "mode":
            "RGB",

        "depth":
            8,

        "dpi":
            None,

        "group_count":
            group_count,

        "layer_count":
            layer_count,

        "document_name":
            document_name,

        "warnings":
            [
                (
                    "Layers are exported as editable raster "
                    "pixel layers."
                ),
                (
                    "Detected text is not exported as native "
                    "Photoshop editable text."
                ),
                (
                    "Detected shapes are not exported as native "
                    "Photoshop vector shape layers."
                ),
            ],
    }