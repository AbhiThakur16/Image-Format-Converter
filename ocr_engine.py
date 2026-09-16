import numpy as np
import easyocr

from PIL import Image, ImageDraw


# =========================================================
# OCR READER
# =========================================================

_reader = None


def get_reader():

    global _reader

    if _reader is None:

        _reader = easyocr.Reader(
            ["en"],
            gpu=False
        )

    return _reader


# =========================================================
# PIL → NUMPY
# =========================================================

def pil_to_numpy(image: Image.Image):

    return np.array(
        image.convert("RGB")
    )


# =========================================================
# RECOGNIZE TEXT
# =========================================================

def recognize_text(
    image: Image.Image,
    confidence_threshold=0.30
):

    reader = get_reader()

    image_array = pil_to_numpy(
        image
    )

    results = reader.readtext(
        image_array,
        detail=1,
        paragraph=False
    )

    detected_text = []

    for result in results:

        box = result[0]

        text = result[1]

        confidence = float(
            result[2]
        )

        if confidence < confidence_threshold:

            continue

        x_values = [
            point[0]
            for point in box
        ]

        y_values = [
            point[1]
            for point in box
        ]

        x1 = int(
            min(x_values)
        )

        y1 = int(
            min(y_values)
        )

        x2 = int(
            max(x_values)
        )

        y2 = int(
            max(y_values)
        )

        detected_text.append(
            {
                "text":
                    text,

                "confidence":
                    round(
                        confidence * 100,
                        2
                    ),

                "x":
                    x1,

                "y":
                    y1,

                "width":
                    max(
                        1,
                        x2 - x1
                    ),

                "height":
                    max(
                        1,
                        y2 - y1
                    ),

                "box":
                    box
            }
        )

    return detected_text


# =========================================================
# OCR PREVIEW
# =========================================================

def create_ocr_preview(
    image: Image.Image,
    detections
):

    preview = (
        image
        .convert("RGB")
        .copy()
    )

    draw = ImageDraw.Draw(
        preview
    )

    for index, item in enumerate(
        detections,
        start=1
    ):

        x = item["x"]
        y = item["y"]

        width = item["width"]
        height = item["height"]

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

        label = (
            f"{index}: "
            f"{item['text']}"
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

    return preview


# =========================================================
# CREATE OCR EDITABLE LAYERS
# =========================================================

def create_ocr_layers(
    image: Image.Image,
    confidence_threshold=0.30
):

    image = image.convert(
        "RGB"
    )

    detections = recognize_text(
        image,
        confidence_threshold
    )

    image_array = np.array(
        image
    )

    height, width = (
        image_array.shape[:2]
    )

    layers = []

    for index, item in enumerate(
        detections,
        start=1
    ):

        x = item["x"]
        y = item["y"]

        box_width = item[
            "width"
        ]

        box_height = item[
            "height"
        ]

        rgba = np.zeros(
            (
                height,
                width,
                4
            ),
            dtype=np.uint8
        )

        x2 = min(
            width,
            x + box_width
        )

        y2 = min(
            height,
            y + box_height
        )

        rgba[
            y:y2,
            x:x2,
            :3
        ] = image_array[
            y:y2,
            x:x2
        ]

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
                    "ocr_text",

                "name":
                    f"Text: {item['text']}",

                "text":
                    item["text"],

                "confidence":
                    item["confidence"],

                "x":
                    x,

                "y":
                    y,

                "width":
                    box_width,

                "height":
                    box_height,

                "image":
                    layer_image
            }
        )

    preview = create_ocr_preview(
        image,
        detections
    )

    full_text = "\n".join(
        item["text"]
        for item in detections
    )

    return {
        "detections":
            detections,

        "layers":
            layers,

        "preview":
            preview,

        "text_count":
            len(
                detections
            ),

        "full_text":
            full_text
    }