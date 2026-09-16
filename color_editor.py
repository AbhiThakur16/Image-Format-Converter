import cv2
import numpy as np
from PIL import Image


# =========================================================
# HEX / RGB HELPERS
# =========================================================

def hex_to_rgb(hex_color):

    hex_color = hex_color.strip().lstrip("#")

    if len(hex_color) != 6:
        raise ValueError(
            "HEX color must be in format #RRGGBB"
        )

    return tuple(
        int(
            hex_color[i:i + 2],
            16
        )
        for i in (
            0,
            2,
            4
        )
    )


def rgb_to_hex(rgb):

    r, g, b = rgb

    return (
        f"#{int(r):02X}"
        f"{int(g):02X}"
        f"{int(b):02X}"
    )


# =========================================================
# COLOR MASK
# =========================================================

def create_color_mask(
    image: Image.Image,
    target_color,
    tolerance=30
):
    """
    Select pixels similar to target_color.

    tolerance:
    0   = almost exact color
    255 = very broad selection
    """

    image = image.convert("RGB")

    image_array = np.array(
        image,
        dtype=np.int16
    )

    target = np.array(
        target_color,
        dtype=np.int16
    )

    difference = (
        image_array
        - target
    )

    distance = np.sqrt(
        np.sum(
            difference ** 2,
            axis=2
        )
    )

    max_distance = (
        np.sqrt(
            3 * (255 ** 2)
        )
    )

    threshold = (
        tolerance
        / 255.0
    ) * max_distance

    mask = np.where(
        distance <= threshold,
        255,
        0
    ).astype(
        np.uint8
    )

    return mask


# =========================================================
# CLEAN MASK
# =========================================================

def clean_color_mask(
    mask,
    kernel_size=3
):

    if kernel_size <= 1:
        return mask

    kernel = np.ones(
        (
            kernel_size,
            kernel_size
        ),
        dtype=np.uint8
    )

    cleaned = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel,
        iterations=1
    )

    cleaned = cv2.morphologyEx(
        cleaned,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=1
    )

    return cleaned


# =========================================================
# FEATHER MASK
# =========================================================

def feather_color_mask(
    mask,
    feather=0
):

    feather = int(
        feather
    )

    if feather <= 0:
        return mask

    if feather % 2 == 0:
        feather += 1

    return cv2.GaussianBlur(
        mask,
        (
            feather,
            feather
        ),
        0
    )


# =========================================================
# REPLACE COLOR
# =========================================================

def replace_color(
    image: Image.Image,
    source_color,
    replacement_color,
    tolerance=30,
    preserve_shading=True
):

    image = image.convert(
        "RGB"
    )

    array = np.array(
        image
    ).astype(
        np.float32
    )

    mask = create_color_mask(
        image,
        source_color,
        tolerance
    )

    selection = (
        mask.astype(
            np.float32
        )
        / 255.0
    )

    selection = selection[
        :,
        :,
        None
    ]

    replacement = np.array(
        replacement_color,
        dtype=np.float32
    )


    # -----------------------------------------------------
    # PRESERVE LIGHT / DARK DETAIL
    # -----------------------------------------------------

    if preserve_shading:

        source = np.array(
            source_color,
            dtype=np.float32
        )

        source_brightness = max(
            1.0,
            float(
                np.mean(
                    source
                )
            )
        )

        current_brightness = np.mean(
            array,
            axis=2,
            keepdims=True
        )

        brightness_ratio = (
            current_brightness
            / source_brightness
        )

        replacement_pixels = (
            replacement[
                None,
                None,
                :
            ]
            * brightness_ratio
        )

        replacement_pixels = np.clip(
            replacement_pixels,
            0,
            255
        )

    else:

        replacement_pixels = (
            np.zeros_like(
                array
            )
            + replacement
        )


    result = (
        array
        * (
            1.0
            - selection
        )
        +
        replacement_pixels
        * selection
    )


    result = np.clip(
        result,
        0,
        255
    ).astype(
        np.uint8
    )


    return Image.fromarray(
        result,
        mode="RGB"
    )


# =========================================================
# REMOVE COLOR → TRANSPARENT
# =========================================================

def remove_color(
    image: Image.Image,
    target_color,
    tolerance=30,
    feather=3
):

    image = image.convert(
        "RGBA"
    )

    rgb_image = image.convert(
        "RGB"
    )

    mask = create_color_mask(
        rgb_image,
        target_color,
        tolerance
    )

    mask = clean_color_mask(
        mask
    )

    mask = feather_color_mask(
        mask,
        feather
    )

    array = np.array(
        image
    )

    alpha = array[
        :,
        :,
        3
    ].astype(
        np.float32
    )

    remove_strength = (
        mask.astype(
            np.float32
        )
        / 255.0
    )

    alpha = (
        alpha
        * (
            1.0
            - remove_strength
        )
    )

    array[
        :,
        :,
        3
    ] = np.clip(
        alpha,
        0,
        255
    ).astype(
        np.uint8
    )

    return Image.fromarray(
        array,
        mode="RGBA"
    )


# =========================================================
# EXTRACT SELECTED COLOR AS LAYER
# =========================================================

def extract_color_layer(
    image: Image.Image,
    target_color,
    tolerance=30,
    feather=1
):

    image = image.convert(
        "RGB"
    )

    mask = create_color_mask(
        image,
        target_color,
        tolerance
    )

    mask = clean_color_mask(
        mask
    )

    mask = feather_color_mask(
        mask,
        feather
    )

    rgb = np.array(
        image
    )

    rgba = np.zeros(
        (
            image.height,
            image.width,
            4
        ),
        dtype=np.uint8
    )

    rgba[
        :,
        :,
        :3
    ] = rgb

    rgba[
        :,
        :,
        3
    ] = mask

    pixel_count = int(
        np.count_nonzero(
            mask > 127
        )
    )

    percentage = (
        pixel_count
        / (
            image.width
            * image.height
        )
        * 100
    )

    return {
        "type":
            "custom_color",

        "name":
            (
                f"Color "
                f"{rgb_to_hex(target_color)}"
            ),

        "color":
            target_color,

        "hex":
            rgb_to_hex(
                target_color
            ),

        "pixel_count":
            pixel_count,

        "percentage":
            round(
                percentage,
                2
            ),

        "mask":
            mask,

        "image":
            Image.fromarray(
                rgba,
                mode="RGBA"
            )
    }


# =========================================================
# MERGE MULTIPLE COLORS
# =========================================================

def merge_colors(
    image: Image.Image,
    source_colors,
    destination_color,
    tolerance=30,
    preserve_shading=True
):

    result = image.convert(
        "RGB"
    )

    for source_color in source_colors:

        result = replace_color(
            result,
            source_color,
            destination_color,
            tolerance,
            preserve_shading
        )

    return result


# =========================================================
# MASK PREVIEW
# =========================================================

def create_mask_preview(
    image: Image.Image,
    target_color,
    tolerance=30
):

    image = image.convert(
        "RGB"
    )

    original = np.array(
        image
    )

    mask = create_color_mask(
        image,
        target_color,
        tolerance
    )

    preview = (
        original.copy()
    )

    selected = (
        mask > 0
    )

    # Highlight selected area
    overlay = np.zeros_like(
        preview
    )

    overlay[
        :,
        :,
        0
    ] = 255

    preview[
        selected
    ] = (
        (
            preview[
                selected
            ].astype(
                np.float32
            )
            * 0.45
        )
        +
        (
            overlay[
                selected
            ].astype(
                np.float32
            )
            * 0.55
        )
    ).astype(
        np.uint8
    )

    return Image.fromarray(
        preview,
        mode="RGB"
    )


# =========================================================
# COLOR SELECTION INFORMATION
# =========================================================

def color_selection_info(
    image: Image.Image,
    target_color,
    tolerance=30
):

    mask = create_color_mask(
        image,
        target_color,
        tolerance
    )

    selected_pixels = int(
        np.count_nonzero(
            mask
        )
    )

    total_pixels = (
        image.width
        * image.height
    )

    percentage = (
        selected_pixels
        / total_pixels
        * 100
    )

    return {
        "selected_pixels":
            selected_pixels,

        "total_pixels":
            total_pixels,

        "percentage":
            round(
                percentage,
                2
            ),

        "hex":
            rgb_to_hex(
                target_color
            )
    }