import cv2
import numpy as np
from PIL import Image


# =========================================================
# RGB → HEX
# =========================================================

def rgb_to_hex(rgb):
    r, g, b = rgb

    return (
        f"#{int(r):02X}"
        f"{int(g):02X}"
        f"{int(b):02X}"
    )


# =========================================================
# EXTRACT SMART COLOR LAYERS
# =========================================================

def extract_color_layers(
    image: Image.Image,
    layer_count=6
):
    """
    Separate an image into editable color-based layers.

    Returns a list containing:
    - layer name
    - dominant color
    - percentage
    - transparent RGBA layer image
    """

    image = image.convert("RGB")

    image_array = np.array(image)

    height, width, _ = (
        image_array.shape
    )

    pixels = image_array.reshape(
        (-1, 3)
    )

    total_pixels = len(
        pixels
    )

    # -----------------------------------------------------
    # Protect performance on large images
    # -----------------------------------------------------

    max_sample_pixels = 50000

    if total_pixels > max_sample_pixels:

        random_indices = np.random.choice(
            total_pixels,
            max_sample_pixels,
            replace=False
        )

        sample_pixels = pixels[
            random_indices
        ]

    else:

        sample_pixels = pixels


    sample_pixels = np.float32(
        sample_pixels
    )


    # -----------------------------------------------------
    # K-MEANS COLOR CLUSTERING
    # -----------------------------------------------------

    criteria = (
        cv2.TERM_CRITERIA_EPS
        + cv2.TERM_CRITERIA_MAX_ITER,
        30,
        0.2
    )


    _, _, centers = cv2.kmeans(
        sample_pixels,
        layer_count,
        None,
        criteria,
        10,
        cv2.KMEANS_PP_CENTERS
    )


    centers = np.uint8(
        centers
    )


    # -----------------------------------------------------
    # FIND CLOSEST COLOR CENTER FOR EVERY PIXEL
    # -----------------------------------------------------

    pixels_float = pixels.astype(
        np.float32
    )

    centers_float = centers.astype(
        np.float32
    )


    labels = np.empty(
        total_pixels,
        dtype=np.int32
    )


    # Process in chunks to reduce RAM use
    chunk_size = 100000

    for start in range(
        0,
        total_pixels,
        chunk_size
    ):

        end = min(
            start + chunk_size,
            total_pixels
        )

        chunk = pixels_float[
            start:end
        ]

        distances = np.sum(
            (
                chunk[:, None, :]
                - centers_float[None, :, :]
            ) ** 2,
            axis=2
        )

        labels[
            start:end
        ] = np.argmin(
            distances,
            axis=1
        )


    labels = labels.reshape(
        (
            height,
            width
        )
    )


    # -----------------------------------------------------
    # COUNT CLUSTER PIXELS
    # -----------------------------------------------------

    cluster_counts = []

    for cluster_index in range(
        layer_count
    ):

        count = int(
            np.count_nonzero(
                labels
                == cluster_index
            )
        )

        cluster_counts.append(
            (
                cluster_index,
                count
            )
        )


    # Largest layer first
    cluster_counts.sort(
        key=lambda item: item[1],
        reverse=True
    )


    layers = []


    # -----------------------------------------------------
    # CREATE RGBA LAYERS
    # -----------------------------------------------------

    for position, (
        cluster_index,
        count
    ) in enumerate(
        cluster_counts,
        start=1
    ):

        mask = (
            labels
            == cluster_index
        )


        rgba = np.zeros(
            (
                height,
                width,
                4
            ),
            dtype=np.uint8
        )


        # Keep original image RGB
        rgba[
            :, :, :3
        ] = image_array


        # Only this cluster remains visible
        rgba[
            :, :, 3
        ] = np.where(
            mask,
            255,
            0
        ).astype(
            np.uint8
        )


        layer_image = (
            Image.fromarray(
                rgba,
                mode="RGBA"
            )
        )


        center_color = tuple(
            int(value)
            for value
            in centers[
                cluster_index
            ]
        )


        percentage = (
            count
            / total_pixels
        ) * 100


        # Largest region = likely background
        if position == 1:

            layer_name = (
                "Background / Main Color"
            )

        else:

            layer_name = (
                f"Color Layer {position - 1}"
            )


        layers.append(
            {
                "id":
                    position,

                "name":
                    layer_name,

                "color":
                    center_color,

                "hex":
                    rgb_to_hex(
                        center_color
                    ),

                "percentage":
                    round(
                        float(
                            percentage
                        ),
                        2
                    ),

                "pixel_count":
                    count,

                "image":
                    layer_image
            }
        )


    return layers


# =========================================================
# APPLY OPACITY
# =========================================================

def apply_layer_opacity(
    layer_image: Image.Image,
    opacity
):
    """
    opacity:
    0 → invisible
    100 → fully visible
    """

    opacity = max(
        0,
        min(
            int(opacity),
            100
        )
    )


    image = layer_image.convert(
        "RGBA"
    )


    alpha = np.array(
        image.getchannel(
            "A"
        ),
        dtype=np.float32
    )


    alpha *= (
        opacity
        / 100.0
    )


    alpha = np.clip(
        alpha,
        0,
        255
    ).astype(
        np.uint8
    )


    image.putalpha(
        Image.fromarray(
            alpha
        )
    )


    return image


# =========================================================
# REBUILD IMAGE FROM LAYERS
# =========================================================

def rebuild_image(
    layers,
    visibility=None,
    opacities=None
):
    """
    Reconstruct an image from extracted layers.
    """

    if not layers:
        raise ValueError(
            "No layers available."
        )


    canvas_size = (
        layers[0][
            "image"
        ].size
    )


    reconstructed = (
        Image.new(
            "RGBA",
            canvas_size,
            (
                0,
                0,
                0,
                0
            )
        )
    )


    for index, layer in enumerate(
        layers
    ):

        # ---------------------------------------------
        # VISIBILITY
        # ---------------------------------------------

        if visibility is not None:

            if not visibility[
                index
            ]:

                continue


        # ---------------------------------------------
        # OPACITY
        # ---------------------------------------------

        opacity = 100

        if opacities is not None:

            opacity = (
                opacities[
                    index
                ]
            )


        layer_image = (
            apply_layer_opacity(
                layer[
                    "image"
                ],
                opacity
            )
        )


        reconstructed = (
            Image.alpha_composite(
                reconstructed,
                layer_image
            )
        )


    return reconstructed