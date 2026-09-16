import cv2
import numpy as np
from PIL import Image


# =========================================================
# PIL → OPENCV
# =========================================================

def pil_to_cv(image):
    image = image.convert("RGB")

    array = np.array(image)

    return cv2.cvtColor(
        array,
        cv2.COLOR_RGB2BGR
    )


# =========================================================
# CREATE RGBA IMAGE FROM MASK
# =========================================================

def create_rgba_layer(
    rgb_image,
    mask
):
    rgb_array = np.array(
        rgb_image.convert("RGB")
    )

    rgba = np.zeros(
        (
            rgb_array.shape[0],
            rgb_array.shape[1],
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
# FOREGROUND / BACKGROUND SEGMENTATION
# =========================================================

def separate_foreground_background(
    image
):
    """
    Smart foreground/background separation
    using OpenCV GrabCut.
    """

    rgb_image = image.convert(
        "RGB"
    )

    cv_image = pil_to_cv(
        rgb_image
    )

    height, width = (
        cv_image.shape[:2]
    )

    # Very small images
    if width < 10 or height < 10:

        full_mask = np.full(
            (
                height,
                width
            ),
            255,
            dtype=np.uint8
        )

        empty_mask = np.zeros(
            (
                height,
                width
            ),
            dtype=np.uint8
        )

        return {
            "foreground":
                create_rgba_layer(
                    rgb_image,
                    full_mask
                ),

            "background":
                create_rgba_layer(
                    rgb_image,
                    empty_mask
                ),

            "foreground_mask":
                full_mask,

            "background_mask":
                empty_mask
        }


    # Margin around image
    margin_x = max(
        1,
        int(
            width * 0.03
        )
    )

    margin_y = max(
        1,
        int(
            height * 0.03
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
        np.uint8
    )


    background_model = (
        np.zeros(
            (
                1,
                65
            ),
            np.float64
        )
    )

    foreground_model = (
        np.zeros(
            (
                1,
                65
            ),
            np.float64
        )
    )


    try:

        cv2.grabCut(
            cv_image,
            mask,
            rectangle,
            background_model,
            foreground_model,
            5,
            cv2.GC_INIT_WITH_RECT
        )


        foreground_mask = np.where(
            (
                mask == cv2.GC_FGD
            )
            |
            (
                mask
                == cv2.GC_PR_FGD
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


    background_mask = (
        255
        - foreground_mask
    )


    foreground_layer = (
        create_rgba_layer(
            rgb_image,
            foreground_mask
        )
    )


    background_layer = (
        create_rgba_layer(
            rgb_image,
            background_mask
        )
    )


    return {
        "foreground":
            foreground_layer,

        "background":
            background_layer,

        "foreground_mask":
            foreground_mask,

        "background_mask":
            background_mask
    }


# =========================================================
# OBJECT REGION DETECTION
# =========================================================

def detect_object_regions(
    image,
    minimum_area=500
):
    """
    Detect visually distinct object-like regions.

    This is a foundation for later AI object detection.
    """

    cv_image = pil_to_cv(
        image
    )


    gray = cv2.cvtColor(
        cv_image,
        cv2.COLOR_BGR2GRAY
    )


    blurred = cv2.GaussianBlur(
        gray,
        (
            5,
            5
        ),
        0
    )


    edges = cv2.Canny(
        blurred,
        60,
        150
    )


    kernel = np.ones(
        (
            5,
            5
        ),
        np.uint8
    )


    closed = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=2
    )


    contours, _ = cv2.findContours(
        closed,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )


    image_area = (
        image.width
        * image.height
    )


    regions = []


    for contour in contours:

        area = cv2.contourArea(
            contour
        )


        if area < minimum_area:
            continue


        # Ignore nearly whole-image contour
        if area > (
            image_area
            * 0.95
        ):
            continue


        x, y, width, height = (
            cv2.boundingRect(
                contour
            )
        )


        regions.append(
            {
                "x":
                    int(x),

                "y":
                    int(y),

                "width":
                    int(width),

                "height":
                    int(height),

                "area":
                    int(area)
            }
        )


    regions.sort(
        key=lambda item:
        item["area"],
        reverse=True
    )


    return regions


# =========================================================
# EXTRACT OBJECT LAYERS
# =========================================================

def extract_object_layers(
    image,
    max_objects=8
):
    """
    Convert detected regions into transparent
    editable object layers.
    """

    image = image.convert(
        "RGB"
    )


    regions = (
        detect_object_regions(
            image
        )
    )


    layers = []


    for index, region in enumerate(
        regions[
            :max_objects
        ],
        start=1
    ):

        x = region[
            "x"
        ]

        y = region[
            "y"
        ]

        width = region[
            "width"
        ]

        height = region[
            "height"
        ]


        mask = np.zeros(
            (
                image.height,
                image.width
            ),
            dtype=np.uint8
        )


        mask[
            y:
            y + height,

            x:
            x + width
        ] = 255


        layer_image = (
            create_rgba_layer(
                image,
                mask
            )
        )


        layers.append(
            {
                "id":
                    index,

                "name":
                    f"Object Layer {index}",

                "image":
                    layer_image,

                "x":
                    x,

                "y":
                    y,

                "width":
                    width,

                "height":
                    height,

                "area":
                    region[
                        "area"
                    ]
            }
        )


    return layers


# =========================================================
# CREATE SEMANTIC LAYER SET
# =========================================================

def create_semantic_layers(
    image
):
    """
    Main semantic layer pipeline.
    """

    separation = (
        separate_foreground_background(
            image
        )
    )


    object_layers = (
        extract_object_layers(
            image
        )
    )


    layers = [
        {
            "type":
                "background",

            "name":
                "Background Layer",

            "image":
                separation[
                    "background"
                ]
        },

        {
            "type":
                "foreground",

            "name":
                "Foreground Layer",

            "image":
                separation[
                    "foreground"
                ]
        }
    ]


    for object_layer in (
        object_layers
    ):

        layers.append(
            {
                "type":
                    "object",

                "name":
                    object_layer[
                        "name"
                    ],

                "image":
                    object_layer[
                        "image"
                    ],

                "x":
                    object_layer[
                        "x"
                    ],

                "y":
                    object_layer[
                        "y"
                    ],

                "width":
                    object_layer[
                        "width"
                    ],

                "height":
                    object_layer[
                        "height"
                    ]
            }
        )


    return layers