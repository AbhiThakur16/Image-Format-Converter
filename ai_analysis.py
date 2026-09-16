import cv2
import numpy as np
from PIL import Image


# =========================================================
# PIL IMAGE → OPENCV
# =========================================================

def pil_to_cv(image: Image.Image):

    image = image.convert("RGB")

    image_array = np.array(image)

    return cv2.cvtColor(
        image_array,
        cv2.COLOR_RGB2BGR
    )


# =========================================================
# DOMINANT COLORS
# =========================================================

def get_dominant_colors(
    image: Image.Image,
    color_count=6
):

    cv_image = pil_to_cv(image)

    pixels = cv_image.reshape(
        (-1, 3)
    )

    pixels = np.float32(
        pixels
    )

    criteria = (
        cv2.TERM_CRITERIA_EPS
        + cv2.TERM_CRITERIA_MAX_ITER,
        30,
        0.2
    )

    _, labels, centers = cv2.kmeans(
        pixels,
        color_count,
        None,
        criteria,
        10,
        cv2.KMEANS_PP_CENTERS
    )

    centers = np.uint8(
        centers
    )

    unique_labels, counts = np.unique(
        labels,
        return_counts=True
    )

    total_pixels = counts.sum()

    colors = []

    for label, count in zip(
        unique_labels,
        counts
    ):

        b, g, r = centers[label]

        percentage = (
            count / total_pixels
        ) * 100

        colors.append(
            {
                "rgb": (
                    int(r),
                    int(g),
                    int(b)
                ),

                "hex": (
                    f"#{int(r):02x}"
                    f"{int(g):02x}"
                    f"{int(b):02x}"
                ),

                "percentage": round(
                    float(percentage),
                    2
                )
            }
        )

    colors.sort(
        key=lambda item:
        item["percentage"],
        reverse=True
    )

    return colors


# =========================================================
# EDGE DETECTION
# =========================================================

def detect_edges(
    image: Image.Image
):

    cv_image = pil_to_cv(
        image
    )

    gray = cv2.cvtColor(
        cv_image,
        cv2.COLOR_BGR2GRAY
    )

    edges = cv2.Canny(
        gray,
        80,
        180
    )

    edge_pixels = int(
        np.count_nonzero(
            edges
        )
    )

    return (
        edges,
        edge_pixels
    )


# =========================================================
# SHAPE DETECTION
# =========================================================

def detect_shapes(
    image: Image.Image
):

    cv_image = pil_to_cv(
        image
    )

    gray = cv2.cvtColor(
        cv_image,
        cv2.COLOR_BGR2GRAY
    )

    blurred = cv2.GaussianBlur(
        gray,
        (5, 5),
        0
    )

    _, threshold_image = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY
        + cv2.THRESH_OTSU
    )

    contours, _ = cv2.findContours(
        threshold_image,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE
    )

    shapes = {
        "rectangles": 0,
        "triangles": 0,
        "circles_or_curves": 0,
        "other_shapes": 0
    }

    for contour in contours:

        area = cv2.contourArea(
            contour
        )

        # Ignore tiny noise
        if area < 150:
            continue

        perimeter = cv2.arcLength(
            contour,
            True
        )

        if perimeter == 0:
            continue

        approximation = cv2.approxPolyDP(
            contour,
            0.02 * perimeter,
            True
        )

        vertices = len(
            approximation
        )

        if vertices == 3:

            shapes[
                "triangles"
            ] += 1

        elif vertices == 4:

            shapes[
                "rectangles"
            ] += 1

        elif vertices >= 8:

            shapes[
                "circles_or_curves"
            ] += 1

        else:

            shapes[
                "other_shapes"
            ] += 1

    return shapes


# =========================================================
# TRANSPARENCY DETECTION
# =========================================================

def detect_transparency(
    image: Image.Image
):

    if image.mode not in (
        "RGBA",
        "LA"
    ):

        return (
            False,
            0.0
        )

    alpha_channel = (
        image.getchannel("A")
    )

    alpha_array = np.array(
        alpha_channel
    )

    transparent_pixels = int(
        np.sum(
            alpha_array < 255
        )
    )

    total_pixels = int(
        alpha_array.size
    )

    if total_pixels == 0:

        return (
            False,
            0.0
        )

    percentage = (
        transparent_pixels
        / total_pixels
    ) * 100

    return (
        transparent_pixels > 0,
        round(
            float(percentage),
            2
        )
    )


# =========================================================
# IMAGE STATISTICS
# =========================================================

def image_statistics(
    image: Image.Image
):

    width, height = (
        image.size
    )

    total_pixels = (
        width * height
    )

    (
        has_transparency,
        transparency_percentage
    ) = detect_transparency(
        image
    )

    return {
        "width":
            width,

        "height":
            height,

        "total_pixels":
            total_pixels,

        "mode":
            image.mode,

        "transparency":
            has_transparency,

        "transparent_percentage":
            transparency_percentage
    }


# =========================================================
# MAIN AI ANALYSIS FUNCTION
# =========================================================

def analyze_image(
    image: Image.Image
):
    """
    Main analysis pipeline used by streamlit_app.py
    """

    statistics = image_statistics(
        image
    )

    dominant_colors = get_dominant_colors(
        image,
        color_count=6
    )

    _, edge_count = detect_edges(
        image
    )

    shapes = detect_shapes(
        image
    )

    return {
        "statistics":
            statistics,

        "dominant_colors":
            dominant_colors,

        "edge_pixels":
            edge_count,

        "shapes":
            shapes
    }