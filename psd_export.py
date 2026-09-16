import io

from PIL import Image
from psd_tools import PSDImage


# =========================================================
# FLATTEN TRANSPARENCY
# =========================================================

def flatten_transparency(
    image,
    background=(255, 255, 255),
):

    if image.mode in (
        "RGBA",
        "LA",
    ):

        rgba = image.convert(
            "RGBA"
        )

        background_image = Image.new(
            "RGBA",
            rgba.size,
            (
                background[0],
                background[1],
                background[2],
                255,
            ),
        )

        background_image.alpha_composite(
            rgba
        )

        return background_image.convert(
            "RGB"
        )

    return image.convert(
        "RGB"
    )


# =========================================================
# RESIZE PSD IMAGE
# =========================================================

def resize_psd_image(
    image,
    width,
    height,
    resize_mode="Fit",
):

    width = int(
        width
    )

    height = int(
        height
    )

    if width < 1 or height < 1:

        raise ValueError(
            "PSD width and height must be at least 1 pixel."
        )


    source = image.copy()


    # =====================================================
    # STRETCH
    # =====================================================

    if resize_mode == "Stretch":

        return source.resize(
            (
                width,
                height,
            ),
            Image.Resampling.LANCZOS,
        )


    # =====================================================
    # FILL & CROP
    # =====================================================

    if resize_mode == "Fill & Crop":

        source_ratio = (
            source.width
            / source.height
        )

        target_ratio = (
            width
            / height
        )


        if (
            source_ratio
            > target_ratio
        ):

            new_height = (
                height
            )

            new_width = round(
                height
                * source_ratio
            )

        else:

            new_width = (
                width
            )

            new_height = round(
                width
                / source_ratio
            )


        resized = source.resize(
            (
                new_width,
                new_height,
            ),
            Image.Resampling.LANCZOS,
        )


        left = max(
            0,
            (
                new_width
                - width
            )
            // 2,
        )

        top = max(
            0,
            (
                new_height
                - height
            )
            // 2,
        )


        return resized.crop(
            (
                left,
                top,
                left + width,
                top + height,
            )
        )


    # =====================================================
    # FIT
    # =====================================================

    source.thumbnail(
        (
            width,
            height,
        ),
        Image.Resampling.LANCZOS,
    )

    return source


# =========================================================
# EXPORT FLATTENED PSD
# =========================================================

def export_flattened_psd(
    image,
    width,
    height,
    resize_mode="Fit",
):

    resized = resize_psd_image(
        image,
        width,
        height,
        resize_mode,
    )


    rgb_image = flatten_transparency(
        resized
    )


    try:

        psd = PSDImage.frompil(
            rgb_image
        )

    except Exception as error:

        raise RuntimeError(
            "Could not create PSD from image."
        ) from error


    buffer = io.BytesIO()


    try:

        psd.save(
            buffer
        )

    except Exception as error:

        raise RuntimeError(
            "Could not save PSD file."
        ) from error


    buffer.seek(
        0
    )


    return {
        "data":
            buffer.getvalue(),

        "format":
            "PSD (Flattened)",

        "extension":
            ".psd",

        "mime":
            "image/vnd.adobe.photoshop",

        "width":
            rgb_image.width,

        "height":
            rgb_image.height,

        "mode":
            rgb_image.mode,

        "dpi":
            None,

        "warnings":
            [
                (
                    "This PSD is flattened. "
                    "It does not contain the original "
                    "Photoshop/CorelDRAW editable layers."
                )
            ],
    }