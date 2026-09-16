import numpy as np
import torch

from PIL import Image, ImageDraw
from torchvision.transforms.functional import to_tensor
from torchvision.models.detection import (
    SSDLite320_MobileNet_V3_Large_Weights,
    ssdlite320_mobilenet_v3_large
)


# =========================================================
# GLOBAL MODEL
# =========================================================

_model = None
_weights = None
_categories = None


# =========================================================
# LOAD MODEL
# =========================================================

def get_object_model():

    global _model
    global _weights
    global _categories

    if _model is None:

        _weights = (
            SSDLite320_MobileNet_V3_Large_Weights.DEFAULT
        )

        _model = (
            ssdlite320_mobilenet_v3_large(
                weights=_weights
            )
        )

        _model.eval()

        _categories = (
            _weights.meta[
                "categories"
            ]
        )

    return (
        _model,
        _categories
    )


# =========================================================
# DETECT OBJECTS
# =========================================================

def detect_objects(
    image: Image.Image,
    confidence_threshold=0.50,
    max_objects=20
):

    model, categories = (
        get_object_model()
    )

    rgb_image = (
        image.convert(
            "RGB"
        )
    )

    tensor = (
        to_tensor(
            rgb_image
        )
    )

    with torch.no_grad():

        prediction = (
            model(
                [
                    tensor
                ]
            )[0]
        )


    boxes = (
        prediction[
            "boxes"
        ].cpu().numpy()
    )

    labels = (
        prediction[
            "labels"
        ].cpu().numpy()
    )

    scores = (
        prediction[
            "scores"
        ].cpu().numpy()
    )


    detections = []


    for box, label, score in zip(
        boxes,
        labels,
        scores
    ):

        confidence = float(
            score
        )

        if (
            confidence
            < confidence_threshold
        ):

            continue


        x1, y1, x2, y2 = (
            box
        )


        x1 = max(
            0,
            int(
                round(
                    x1
                )
            )
        )

        y1 = max(
            0,
            int(
                round(
                    y1
                )
            )
        )

        x2 = min(
            rgb_image.width,
            int(
                round(
                    x2
                )
            )
        )

        y2 = min(
            rgb_image.height,
            int(
                round(
                    y2
                )
            )
        )


        width = max(
            1,
            x2 - x1
        )

        height = max(
            1,
            y2 - y1
        )


        label_index = int(
            label
        )


        if (
            0
            <= label_index
            < len(
                categories
            )
        ):

            object_name = (
                categories[
                    label_index
                ]
            )

        else:

            object_name = (
                f"Object {label_index}"
            )


        detections.append(
            {
                "name":
                    object_name,

                "confidence":
                    round(
                        confidence
                        * 100,
                        2
                    ),

                "x":
                    x1,

                "y":
                    y1,

                "width":
                    width,

                "height":
                    height
            }
        )


        if (
            len(
                detections
            )
            >= max_objects
        ):

            break


    return detections


# =========================================================
# CREATE OBJECT PREVIEW
# =========================================================

def create_object_preview(
    image: Image.Image,
    detections
):

    preview = (
        image.convert(
            "RGB"
        ).copy()
    )

    draw = (
        ImageDraw.Draw(
            preview
        )
    )


    for index, detection in enumerate(
        detections,
        start=1
    ):

        x = detection[
            "x"
        ]

        y = detection[
            "y"
        ]

        width = detection[
            "width"
        ]

        height = detection[
            "height"
        ]


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
            width=3
        )


        label = (
            f"{index}. "
            f"{detection['name']} "
            f"{detection['confidence']}%"
        )


        draw.text(
            (
                x,
                max(
                    0,
                    y - 16
                )
            ),
            label,
            fill=(
                255,
                0,
                0
            )
        )


    return preview


# =========================================================
# CREATE EDITABLE OBJECT LAYERS
# =========================================================

def create_object_layers(
    image: Image.Image,
    confidence_threshold=0.50,
    max_objects=20
):

    image = (
        image.convert(
            "RGB"
        )
    )

    detections = (
        detect_objects(
            image,
            confidence_threshold,
            max_objects
        )
    )


    image_array = (
        np.array(
            image
        )
    )


    height, width = (
        image_array.shape[:2]
    )


    layers = []


    for index, detection in enumerate(
        detections,
        start=1
    ):

        x = detection[
            "x"
        ]

        y = detection[
            "y"
        ]

        object_width = detection[
            "width"
        ]

        object_height = detection[
            "height"
        ]


        x2 = min(
            width,
            x + object_width
        )

        y2 = min(
            height,
            y + object_height
        )


        rgba = (
            np.zeros(
                (
                    height,
                    width,
                    4
                ),
                dtype=np.uint8
            )
        )


        rgba[
            y:y2,
            x:x2,
            :3
        ] = (
            image_array[
                y:y2,
                x:x2
            ]
        )


        rgba[
            y:y2,
            x:x2,
            3
        ] = 255


        layer_image = (
            Image.fromarray(
                rgba,
                mode="RGBA"
            )
        )


        layers.append(
            {
                "type":
                    "detected_object",

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
                    x,

                "y":
                    y,

                "width":
                    object_width,

                "height":
                    object_height,

                "image":
                    layer_image
            }
        )


    preview = (
        create_object_preview(
            image,
            detections
        )
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
                detections
            )
    }