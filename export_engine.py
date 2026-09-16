import io
from PIL import Image, ImageOps


# =========================================================
# SUPPORTED FORMATS
# =========================================================

SUPPORTED_FORMATS = [
    "PNG",
    "JPEG",
    "WEBP",
    "TIFF",
    "BMP",
    "PDF"
]


# =========================================================
# RGB CONVERSION
# =========================================================

def flatten_transparency(
    image: Image.Image,
    background_color=(255, 255, 255)
):

    if image.mode not in (
        "RGBA",
        "LA"
    ):

        return image.convert("RGB")

    rgba = image.convert("RGBA")

    background = Image.new(
        "RGBA",
        rgba.size,
        background_color + (255,)
    )

    background.alpha_composite(
        rgba
    )

    return background.convert(
        "RGB"
    )


# =========================================================
# COLOR MODE
# =========================================================

def convert_color_mode(
    image: Image.Image,
    color_mode,
    output_format
):

    warnings = []

    output_format = (
        output_format.upper()
    )


    # -----------------------------------------------------
    # GRAYSCALE
    # -----------------------------------------------------

    if color_mode == "Grayscale":

        return (
            image.convert("L"),
            warnings
        )


    # -----------------------------------------------------
    # CMYK
    # -----------------------------------------------------

    if color_mode == "CMYK":

        if output_format in (
            "JPEG",
            "TIFF",
            "PDF"
        ):

            if image.mode in (
                "RGBA",
                "LA"
            ):

                image = flatten_transparency(
                    image
                )

                warnings.append(
                    "Transparency was flattened because "
                    "CMYK does not preserve alpha transparency."
                )

            return (
                image.convert("CMYK"),
                warnings
            )

        warnings.append(
            f"{output_format} export does not use CMYK "
            f"in this workflow. Image was exported as RGB."
        )

        if image.mode in (
            "RGBA",
            "LA"
        ) and output_format == "PNG":

            return (
                image.convert("RGBA"),
                warnings
            )

        return (
            flatten_transparency(
                image
            ),
            warnings
        )


    # -----------------------------------------------------
    # RGB
    # -----------------------------------------------------

    if output_format in (
        "JPEG",
        "BMP",
        "PDF"
    ):

        if image.mode in (
            "RGBA",
            "LA"
        ):

            warnings.append(
                "Transparency was flattened for "
                f"{output_format} export."
            )

            return (
                flatten_transparency(
                    image
                ),
                warnings
            )

        return (
            image.convert("RGB"),
            warnings
        )


    if image.mode in (
        "RGBA",
        "LA"
    ):

        return (
            image.convert("RGBA"),
            warnings
        )


    return (
        image.convert("RGB"),
        warnings
    )


# =========================================================
# RESIZE
# =========================================================

def resize_for_export(
    image,
    width,
    height,
    resize_mode="Fit",
    resample=Image.Resampling.LANCZOS
):

    width = max(
        1,
        int(width)
    )

    height = max(
        1,
        int(height)
    )


    if image.size == (
        width,
        height
    ):

        return image


    # -----------------------------------------------------
    # FIT
    # -----------------------------------------------------

    if resize_mode == "Fit":

        result = image.copy()

        result.thumbnail(
            (
                width,
                height
            ),
            resample
        )

        return result


    # -----------------------------------------------------
    # FILL + CROP
    # -----------------------------------------------------

    if resize_mode == "Fill & Crop":

        return ImageOps.fit(
            image,
            (
                width,
                height
            ),
            method=resample,
            centering=(
                0.5,
                0.5
            )
        )


    # -----------------------------------------------------
    # STRETCH
    # -----------------------------------------------------

    return image.resize(
        (
            width,
            height
        ),
        resample
    )


# =========================================================
# MIME TYPE
# =========================================================

def get_mime_type(
    output_format
):

    mapping = {

        "PNG":
            "image/png",

        "JPEG":
            "image/jpeg",

        "WEBP":
            "image/webp",

        "TIFF":
            "image/tiff",

        "BMP":
            "image/bmp",

        "PDF":
            "application/pdf"
    }

    return mapping.get(
        output_format.upper(),
        "application/octet-stream"
    )


# =========================================================
# EXTENSION
# =========================================================

def get_extension(
    output_format
):

    mapping = {

        "PNG":
            ".png",

        "JPEG":
            ".jpg",

        "WEBP":
            ".webp",

        "TIFF":
            ".tiff",

        "BMP":
            ".bmp",

        "PDF":
            ".pdf"
    }

    return mapping[
        output_format.upper()
    ]


# =========================================================
# PROFESSIONAL EXPORT
# =========================================================

def export_image(
    image: Image.Image,
    output_format,
    width,
    height,
    dpi=300,
    color_mode="RGB",
    resize_mode="Fit",
    quality=95,
    tiff_compression="tiff_lzw",
    png_compress_level=6,
    webp_lossless=False
):

    output_format = (
        output_format.upper()
    )


    if output_format not in (
        SUPPORTED_FORMATS
    ):

        raise ValueError(
            f"Unsupported export format: "
            f"{output_format}"
        )


    width = int(
        width
    )

    height = int(
        height
    )

    dpi = int(
        dpi
    )


    # -----------------------------------------------------
    # SAFETY
    # -----------------------------------------------------

    if width < 1 or height < 1:

        raise ValueError(
            "Width and height must be at least 1 pixel."
        )


    if dpi < 72 or dpi > 1200:

        raise ValueError(
            "DPI must be between 72 and 1200."
        )


    # -----------------------------------------------------
    # RESIZE
    # -----------------------------------------------------

    working_image = (
        resize_for_export(
            image,
            width,
            height,
            resize_mode
        )
    )


    # -----------------------------------------------------
    # COLOR MODE
    # -----------------------------------------------------

    working_image, warnings = (
        convert_color_mode(
            working_image,
            color_mode,
            output_format
        )
    )


    buffer = (
        io.BytesIO()
    )


    # =====================================================
    # PNG
    # =====================================================

    if output_format == "PNG":

        working_image.save(
            buffer,
            format="PNG",
            dpi=(
                dpi,
                dpi
            ),
            compress_level=max(
                0,
                min(
                    int(
                        png_compress_level
                    ),
                    9
                )
            )
        )


    # =====================================================
    # JPEG
    # =====================================================

    elif output_format == "JPEG":

        if working_image.mode not in (
            "RGB",
            "L",
            "CMYK"
        ):

            working_image = (
                flatten_transparency(
                    working_image
                )
            )

        working_image.save(
            buffer,
            format="JPEG",
            quality=max(
                1,
                min(
                    int(
                        quality
                    ),
                    100
                )
            ),
            dpi=(
                dpi,
                dpi
            ),
            optimize=True
        )


    # =====================================================
    # WEBP
    # =====================================================

    elif output_format == "WEBP":

        working_image.save(
            buffer,
            format="WEBP",
            quality=max(
                1,
                min(
                    int(
                        quality
                    ),
                    100
                )
            ),
            lossless=bool(
                webp_lossless
            ),
            method=6
        )


    # =====================================================
    # TIFF
    # =====================================================

    elif output_format == "TIFF":

        working_image.save(
            buffer,
            format="TIFF",
            dpi=(
                dpi,
                dpi
            ),
            compression=(
                tiff_compression
            )
        )


    # =====================================================
    # BMP
    # =====================================================

    elif output_format == "BMP":

        if working_image.mode not in (
            "RGB",
            "L"
        ):

            working_image = (
                flatten_transparency(
                    working_image
                )
            )

        working_image.save(
            buffer,
            format="BMP",
            dpi=(
                dpi,
                dpi
            )
        )


    # =====================================================
    # PDF
    # =====================================================

    elif output_format == "PDF":

        if working_image.mode not in (
            "RGB",
            "L",
            "CMYK"
        ):

            working_image = (
                flatten_transparency(
                    working_image
                )
            )

        working_image.save(
            buffer,
            format="PDF",
            resolution=float(
                dpi
            )
        )


    buffer.seek(
        0
    )


    return {

        "data":
            buffer.getvalue(),

        "format":
            output_format,

        "extension":
            get_extension(
                output_format
            ),

        "mime":
            get_mime_type(
                output_format
            ),

        "width":
            working_image.width,

        "height":
            working_image.height,

        "dpi":
            dpi,

        "mode":
            working_image.mode,

        "warnings":
            warnings
    }


# =========================================================
# MULTIPLE EXPORT
# =========================================================

def export_multiple_formats(
    image,
    formats,
    width,
    height,
    dpi=300,
    color_mode="RGB",
    resize_mode="Fit",
    quality=95
):

    results = []


    for output_format in formats:

        try:

            result = (
                export_image(
                    image=image,
                    output_format=(
                        output_format
                    ),
                    width=width,
                    height=height,
                    dpi=dpi,
                    color_mode=(
                        color_mode
                    ),
                    resize_mode=(
                        resize_mode
                    ),
                    quality=(
                        quality
                    )
                )
            )

            result[
                "success"
            ] = True

            results.append(
                result
            )


        except Exception as error:

            results.append(
                {
                    "format":
                        output_format,

                    "success":
                        False,

                    "error":
                        str(
                            error
                        )
                }
            )


    return results