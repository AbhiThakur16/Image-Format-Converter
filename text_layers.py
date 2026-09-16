import cv2
import numpy as np
from PIL import Image, ImageDraw


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
# MASK → TRANSPARENT RGBA LAYER
# =========================================================

def create_rgba_layer(
    image: Image.Image,
    mask: np.ndarray
):

    rgb_array = np.array(
        image.convert("RGB")
    )

    height, width = (
        rgb_array.shape[:2]
    )

    rgba = np.zeros(
        (
            height,
            width,
            4
        ),
        dtype=np.uint8
    )

    rgba[:, :, :3] = (
        rgb_array
    )

    rgba[:, :, 3] = (
        mask.astype(
            np.uint8
        )
    )

    return Image.fromarray(
        rgba,
        mode="RGBA"
    )


# =========================================================
# IOU
# =========================================================

def box_iou(
    box1,
    box2
):

    x1, y1, w1, h1 = (
        box1
    )

    x2, y2, w2, h2 = (
        box2
    )

    left = max(
        x1,
        x2
    )

    top = max(
        y1,
        y2
    )

    right = min(
        x1 + w1,
        x2 + w2
    )

    bottom = min(
        y1 + h1,
        y2 + h2
    )

    intersection_width = max(
        0,
        right - left
    )

    intersection_height = max(
        0,
        bottom - top
    )

    intersection = (
        intersection_width
        * intersection_height
    )

    area1 = (
        w1 * h1
    )

    area2 = (
        w2 * h2
    )

    union = (
        area1
        + area2
        - intersection
    )

    if union <= 0:

        return 0.0

    return (
        intersection
        / union
    )


# =========================================================
# REMOVE DUPLICATE BOXES
# =========================================================

def remove_duplicate_boxes(
    boxes,
    threshold=0.5
):

    if not boxes:

        return []

    boxes = sorted(
        boxes,
        key=lambda item:
        item[2] * item[3],
        reverse=True
    )

    final_boxes = []

    for box in boxes:

        duplicate = False

        for existing in (
            final_boxes
        ):

            if (
                box_iou(
                    box,
                    existing
                )
                >= threshold
            ):

                duplicate = True

                break

        if not duplicate:

            final_boxes.append(
                box
            )

    return final_boxes


# =========================================================
# TEXT REGION DETECTION
# =========================================================

def detect_text_regions(
    image: Image.Image,
    max_regions=30
):
    """
    Detect possible text areas.

    This does NOT read the text.
    It only detects text-like regions.
    """

    cv_image = pil_to_cv(
        image
    )

    height, width = (
        cv_image.shape[:2]
    )

    gray = cv2.cvtColor(
        cv_image,
        cv2.COLOR_BGR2GRAY
    )

    # -----------------------------------------------------
    # Improve local contrast
    # -----------------------------------------------------

    gray = cv2.equalizeHist(
        gray
    )

    # -----------------------------------------------------
    # Adaptive threshold
    # -----------------------------------------------------

    threshold = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        12
    )

    # -----------------------------------------------------
    # Connect letters into words / lines
    # -----------------------------------------------------

    horizontal_kernel = (
        cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (
                9,
                3
            )
        )
    )

    connected = cv2.morphologyEx(
        threshold,
        cv2.MORPH_CLOSE,
        horizontal_kernel,
        iterations=1
    )

    # -----------------------------------------------------
    # Find regions
    # -----------------------------------------------------

    contours, _ = cv2.findContours(
        connected,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    image_area = (
        width * height
    )

    boxes = []

    for contour in contours:

        x, y, box_width, box_height = (
            cv2.boundingRect(
                contour
            )
        )

        area = (
            box_width
            * box_height
        )

        # ---------------------------------------------
        # Ignore tiny regions
        # ---------------------------------------------

        if area < 40:

            continue

        # ---------------------------------------------
        # Ignore nearly whole image
        # ---------------------------------------------

        if (
            area
            > image_area * 0.80
        ):

            continue

        # ---------------------------------------------
        # Ignore extremely small height
        # ---------------------------------------------

        if box_height < 4:

            continue

        # ---------------------------------------------
        # Ignore impossible text proportions
        # ---------------------------------------------

        aspect_ratio = (
            box_width
            / max(
                box_height,
                1
            )
        )

        if aspect_ratio < 0.15:

            continue

        # ---------------------------------------------
        # Ignore giant block
        # ---------------------------------------------

        if (
            box_height
            > height * 0.50
        ):

            continue

        boxes.append(
            (
                int(x),
                int(y),
                int(box_width),
                int(box_height)
            )
        )

    boxes = (
        remove_duplicate_boxes(
            boxes
        )
    )

    boxes = sorted(
        boxes,
        key=lambda item:
        (
            item[1],
            item[0]
        )
    )

    return boxes[
        :max_regions
    ]


# =========================================================
# CREATE COMBINED TEXT LAYER
# =========================================================

def create_text_layer(
    image: Image.Image,
    padding=3
):

    image = image.convert(
        "RGB"
    )

    boxes = detect_text_regions(
        image
    )

    mask = np.zeros(
        (
            image.height,
            image.width
        ),
        dtype=np.uint8
    )

    for (
        x,
        y,
        width,
        height
    ) in boxes:

        x1 = max(
            0,
            x - padding
        )

        y1 = max(
            0,
            y - padding
        )

        x2 = min(
            image.width,
            x + width + padding
        )

        y2 = min(
            image.height,
            y + height + padding
        )

        mask[
            y1:y2,
            x1:x2
        ] = 255

    text_layer = (
        create_rgba_layer(
            image,
            mask
        )
    )

    return {
        "type":
            "text",

        "name":
            "Detected Text Layer",

        "image":
            text_layer,

        "regions":
            boxes,

        "region_count":
            len(
                boxes
            )
    }


# =========================================================
# CREATE INDIVIDUAL TEXT REGION LAYERS
# =========================================================

def create_individual_text_layers(
    image: Image.Image,
    max_layers=15,
    padding=3
):

    image = image.convert(
        "RGB"
    )

    boxes = detect_text_regions(
        image,
        max_regions=max_layers
    )

    layers = []

    for index, (
        x,
        y,
        width,
        height
    ) in enumerate(
        boxes,
        start=1
    ):

        mask = np.zeros(
            (
                image.height,
                image.width
            ),
            dtype=np.uint8
        )

        x1 = max(
            0,
            x - padding
        )

        y1 = max(
            0,
            y - padding
        )

        x2 = min(
            image.width,
            x + width + padding
        )

        y2 = min(
            image.height,
            y + height + padding
        )

        mask[
            y1:y2,
            x1:x2
        ] = 255

        layer_image = (
            create_rgba_layer(
                image,
                mask
            )
        )

        layers.append(
            {
                "type":
                    "text",

                "name":
                    f"Text Region {index}",

                "image":
                    layer_image,

                "x":
                    x,

                "y":
                    y,

                "width":
                    width,

                "height":
                    height
            }
        )

    return layers


# =========================================================
# PREVIEW DETECTED TEXT BOXES
# =========================================================

def create_text_detection_preview(
    image: Image.Image
):

    preview = (
        image.convert(
            "RGB"
        ).copy()
    )

    boxes = detect_text_regions(
        image
    )

    draw = ImageDraw.Draw(
        preview
    )

    for index, (
        x,
        y,
        width,
        height
    ) in enumerate(
        boxes,
        start=1
    ):

        draw.rectangle(
            [
                (
                    x,
                    y
                ),
                (
                    x + width,
                    y + height
                )
            ],
            outline=(
                255,
                0,
                0
            ),
            width=2
        )

        draw.text(
            (
                x,
                max(
                    0,
                    y - 12
                )
            ),
            str(index),
            fill=(
                255,
                0,
                0
            )
        )

    return preview


# =========================================================
# MAIN TEXT EXTRACTION PIPELINE
# =========================================================

def create_text_layers(
    image: Image.Image,
    individual=True
):

    combined = (
        create_text_layer(
            image
        )
    )

    preview = (
        create_text_detection_preview(
            image
        )
    )

    individual_layers = []

    if individual:

        individual_layers = (
            create_individual_text_layers(
                image
            )
        )

    return {
        "combined_layer":
            combined,

        "individual_layers":
            individual_layers,

        "preview":
            preview,

        "region_count":
            combined[
                "region_count"
            ]
    }