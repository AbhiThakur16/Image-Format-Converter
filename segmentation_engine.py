import cv2
import numpy as np

from PIL import Image, ImageDraw

from object_detection import detect_objects


# =========================================================
# PIL → OPENCV
# =========================================================

def pil_to_cv(image: Image.Image):

    rgb = image.convert("RGB")

    array = np.array(rgb)

    return cv2.cvtColor(
        array,
        cv2.COLOR_RGB2BGR
    )


# =========================================================
# SAFE BOX
# =========================================================

def clamp_box(
    x,
    y,
    width,
    height,
    image_width,
    image_height
):

    x = max(
        0,
        int(x)
    )

    y = max(
        0,
        int(y)
    )

    width = max(
        1,
        int(width)
    )

    height = max(
        1,
        int(height)
    )

    x2 = min(
        image_width,
        x + width
    )

    y2 = min(
        image_height,
        y + height
    )

    width = max(
        1,
        x2 - x
    )

    height = max(
        1,
        y2 - y
    )

    return (
        x,
        y,
        width,
        height
    )


# =========================================================
# FALLBACK RECTANGULAR MASK
# =========================================================

def create_rectangle_mask(
    image_size,
    box
):

    image_width, image_height = (
        image_size
    )

    x, y, width, height = (
        box
    )

    mask = np.zeros(
        (
            image_height,
            image_width
        ),
        dtype=np.uint8
    )

    mask[
        y:
        y + height,

        x:
        x + width
    ] = 255

    return mask


# =========================================================
# SEGMENT SINGLE OBJECT USING GRABCUT
# =========================================================

def segment_object_from_box(
    image: Image.Image,
    detection,
    iterations=5
):

    rgb_image = image.convert(
        "RGB"
    )

    cv_image = pil_to_cv(
        rgb_image
    )

    image_height, image_width = (
        cv_image.shape[:2]
    )

    x, y, width, height = clamp_box(
        detection["x"],
        detection["y"],
        detection["width"],
        detection["height"],
        image_width,
        image_height
    )

    # -----------------------------------------------------
    # Very small objects → fallback box
    # -----------------------------------------------------

    if (
        width < 3
        or height < 3
    ):

        return create_rectangle_mask(
            rgb_image.size,
            (
                x,
                y,
                width,
                height
            )
        )

    # -----------------------------------------------------
    # GRABCUT MASK
    # -----------------------------------------------------

    mask = np.zeros(
        (
            image_height,
            image_width
        ),
        dtype=np.uint8
    )

    background_model = np.zeros(
        (
            1,
            65
        ),
        dtype=np.float64
    )

    foreground_model = np.zeros(
        (
            1,
            65
        ),
        dtype=np.float64
    )

    # Slightly shrink rectangle from image edges
    rect_x = max(
        0,
        x
    )

    rect_y = max(
        0,
        y
    )

    rect_width = min(
        width,
        image_width - rect_x
    )

    rect_height = min(
        height,
        image_height - rect_y
    )

    rectangle = (
        rect_x,
        rect_y,
        max(
            1,
            rect_width
        ),
        max(
            1,
            rect_height
        )
    )

    try:

        cv2.grabCut(
            cv_image,
            mask,
            rectangle,
            background_model,
            foreground_model,
            iterations,
            cv2.GC_INIT_WITH_RECT
        )

        binary_mask = np.where(
            (
                mask == cv2.GC_FGD
            )
            |
            (
                mask == cv2.GC_PR_FGD
            ),
            255,
            0
        ).astype(
            np.uint8
        )

        # -------------------------------------------------
        # If segmentation fails → fallback rectangle
        # -------------------------------------------------

        if (
            np.count_nonzero(
                binary_mask
            )
            < 5
        ):

            return create_rectangle_mask(
                rgb_image.size,
                (
                    x,
                    y,
                    width,
                    height
                )
            )

        return binary_mask

    except Exception:

        return create_rectangle_mask(
            rgb_image.size,
            (
                x,
                y,
                width,
                height
            )
        )


# =========================================================
# CLEAN MASK
# =========================================================

def clean_mask(
    mask,
    kernel_size=3
):

    kernel = np.ones(
        (
            kernel_size,
            kernel_size
        ),
        np.uint8
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
# FEATHER MASK EDGES
# =========================================================

def feather_mask(
    mask,
    blur_amount=3
):

    if blur_amount <= 0:

        return mask

    if blur_amount % 2 == 0:

        blur_amount += 1

    blurred = cv2.GaussianBlur(
        mask,
        (
            blur_amount,
            blur_amount
        ),
        0
    )

    return blurred


# =========================================================
# CREATE RGBA OBJECT LAYER
# =========================================================

def mask_to_rgba_layer(
    image: Image.Image,
    mask
):

    rgb_array = np.array(
        image.convert("RGB")
    )

    rgba = np.zeros(
        (
            rgb_array.shape[0],
            rgb_array.shape[1],
            4
        ),
        dtype=np.uint8
    )

    rgba[
        :,
        :,
        :3
    ] = rgb_array

    rgba[
        :,
        :,
        3
    ] = mask.astype(
        np.uint8
    )

    return Image.fromarray(
        rgba,
        mode="RGBA"
    )


# =========================================================
# SEGMENT ALL DETECTED OBJECTS
# =========================================================

def create_segmented_object_layers(
    image: Image.Image,
    confidence_threshold=0.50,
    max_objects=10,
    iterations=5,
    feather=3
):

    image = image.convert(
        "RGB"
    )

    detections = detect_objects(
        image,
        confidence_threshold=confidence_threshold,
        max_objects=max_objects
    )

    layers = []

    for index, detection in enumerate(
        detections,
        start=1
    ):

        mask = segment_object_from_box(
            image,
            detection,
            iterations=iterations
        )

        mask = clean_mask(
            mask
        )

        mask = feather_mask(
            mask,
            feather
        )

        layer_image = mask_to_rgba_layer(
            image,
            mask
        )

        layers.append(
            {
                "type":
                    "segmented_object",

                "name":
                    (
                        f"{detection['name']} "
                        f"{index}"
                    ),

                "object_name":
                    detection[
                        "name"
                    ],

                "confidence":
                    detection[
                        "confidence"
                    ],

                "x":
                    detection[
                        "x"
                    ],

                "y":
                    detection[
                        "y"
                    ],

                "width":
                    detection[
                        "width"
                    ],

                "height":
                    detection[
                        "height"
                    ],

                "mask":
                    mask,

                "image":
                    layer_image
            }
        )

    preview = create_segmentation_preview(
        image,
        layers
    )

    return {
        "detections":
            detections,

        "layers":
            layers,

        "preview":
            preview,

        "object_count":
            len(
                layers
            )
    }


# =========================================================
# SEGMENTATION PREVIEW
# =========================================================

def create_segmentation_preview(
    image: Image.Image,
    layers
):

    preview = np.array(
        image.convert("RGB")
    )

    for layer in layers:

        mask = layer[
            "mask"
        ]

        # Find object boundary
        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        cv2.drawContours(
            preview,
            contours,
            -1,
            (
                255,
                0,
                0
            ),
            2
        )

    preview_image = Image.fromarray(
        preview
    )

    draw = ImageDraw.Draw(
        preview_image
    )

    for index, layer in enumerate(
        layers,
        start=1
    ):

        x = layer[
            "x"
        ]

        y = layer[
            "y"
        ]

        label = (
            f"{index}. "
            f"{layer['object_name']} "
            f"{layer['confidence']}%"
        )

        draw.text(
            (
                x,
                max(
                    0,
                    y - 15
                )
            ),
            label,
            fill=(
                255,
                0,
                0
            )
        )

    return preview_image


# =========================================================
# BACKGROUND REMOVAL
# =========================================================

def remove_background(
    image: Image.Image,
    margin_percent=0.03,
    iterations=5,
    feather=3
):

    image = image.convert(
        "RGB"
    )

    cv_image = pil_to_cv(
        image
    )

    height, width = (
        cv_image.shape[:2]
    )

    margin_x = max(
        1,
        int(
            width
            * margin_percent
        )
    )

    margin_y = max(
        1,
        int(
            height
            * margin_percent
        )
    )

    rectangle = (
        margin_x,
        margin_y,
        max(
            1,
            width
            - 2 * margin_x
        ),
        max(
            1,
            height
            - 2 * margin_y
        )
    )

    mask = np.zeros(
        (
            height,
            width
        ),
        dtype=np.uint8
    )

    background_model = np.zeros(
        (
            1,
            65
        ),
        dtype=np.float64
    )

    foreground_model = np.zeros(
        (
            1,
            65
        ),
        dtype=np.float64
    )

    try:

        cv2.grabCut(
            cv_image,
            mask,
            rectangle,
            background_model,
            foreground_model,
            iterations,
            cv2.GC_INIT_WITH_RECT
        )

        foreground_mask = np.where(
            (
                mask == cv2.GC_FGD
            )
            |
            (
                mask == cv2.GC_PR_FGD
            ),
            255,
            0
        ).astype(
            np.uint8
        )

    except Exception:

        foreground_mask = np.full(
            (
                height,
                width
            ),
            255,
            dtype=np.uint8
        )

    foreground_mask = clean_mask(
        foreground_mask
    )

    foreground_mask = feather_mask(
        foreground_mask,
        feather
    )

    transparent_image = mask_to_rgba_layer(
        image,
        foreground_mask
    )

    return {
        "image":
            transparent_image,

        "mask":
            foreground_mask
    }