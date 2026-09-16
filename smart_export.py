# =========================================================
# AI IMAGE STUDIO
# SMART EXPORT RECOMMENDATION ENGINE
# =========================================================


EXPORT_PURPOSES = [
    "Web / Website",
    "Social Media",
    "Professional Print",
    "High Quality Archive",
    "Transparent Graphic",
    "Email / WhatsApp",
    "General Purpose",
]


# =========================================================
# IMAGE INFORMATION
# =========================================================

def get_image_info(image):

    width, height = image.size

    total_pixels = (
        width * height
    )

    megapixels = (
        total_pixels
        / 1_000_000
    )

    has_alpha = (
        image.mode in (
            "RGBA",
            "LA",
        )
    )

    return {
        "width":
            width,

        "height":
            height,

        "total_pixels":
            total_pixels,

        "megapixels":
            round(
                megapixels,
                2,
            ),

        "mode":
            image.mode,

        "has_transparency":
            has_alpha,
    }


# =========================================================
# WEB RECOMMENDATION
# =========================================================

def recommend_web(
    image_info,
):

    transparency = (
        image_info[
            "has_transparency"
        ]
    )

    if transparency:

        output_format = (
            "WEBP"
        )

        reason = (
            "WebP keeps transparency while "
            "usually producing smaller files."
        )

    else:

        output_format = (
            "WEBP"
        )

        reason = (
            "WebP provides good visual quality "
            "with efficient file size for websites."
        )

    return {
        "format":
            output_format,

        "dpi":
            96,

        "color_mode":
            "RGB",

        "quality":
            85,

        "resize_mode":
            "Fit",

        "webp_lossless":
            False,

        "png_compression":
            6,

        "tiff_compression":
            "tiff_lzw",

        "reason":
            reason,
    }


# =========================================================
# SOCIAL MEDIA
# =========================================================

def recommend_social_media(
    image_info,
):

    return {
        "format":
            "JPEG",

        "dpi":
            96,

        "color_mode":
            "RGB",

        "quality":
            90,

        "resize_mode":
            "Fit",

        "webp_lossless":
            False,

        "png_compression":
            6,

        "tiff_compression":
            "tiff_lzw",

        "reason":
            (
                "JPEG with high quality is broadly "
                "compatible and suitable for social media."
            ),
    }


# =========================================================
# PROFESSIONAL PRINT
# =========================================================

def recommend_print(
    image_info,
):

    return {
        "format":
            "TIFF",

        "dpi":
            300,

        "color_mode":
            "CMYK",

        "quality":
            100,

        "resize_mode":
            "Fit",

        "webp_lossless":
            False,

        "png_compression":
            6,

        "tiff_compression":
            "tiff_lzw",

        "reason":
            (
                "TIFF with 300 DPI is suitable for "
                "high-quality print workflows. "
                "CMYK can be used when required by the printer."
            ),
    }


# =========================================================
# ARCHIVE
# =========================================================

def recommend_archive(
    image_info,
):

    return {
        "format":
            "TIFF",

        "dpi":
            300,

        "color_mode":
            "RGB",

        "quality":
            100,

        "resize_mode":
            "Fit",

        "webp_lossless":
            False,

        "png_compression":
            6,

        "tiff_compression":
            "tiff_lzw",

        "reason":
            (
                "Lossless TIFF is suitable for maintaining "
                "a high-quality archival raster copy."
            ),
    }


# =========================================================
# TRANSPARENT GRAPHIC
# =========================================================

def recommend_transparent(
    image_info,
):

    return {
        "format":
            "PNG",

        "dpi":
            300,

        "color_mode":
            "RGB",

        "quality":
            100,

        "resize_mode":
            "Fit",

        "webp_lossless":
            True,

        "png_compression":
            6,

        "tiff_compression":
            "tiff_lzw",

        "reason":
            (
                "PNG preserves transparency and uses "
                "lossless compression."
            ),
    }


# =========================================================
# EMAIL / WHATSAPP
# =========================================================

def recommend_messaging(
    image_info,
):

    return {
        "format":
            "JPEG",

        "dpi":
            96,

        "color_mode":
            "RGB",

        "quality":
            80,

        "resize_mode":
            "Fit",

        "webp_lossless":
            False,

        "png_compression":
            6,

        "tiff_compression":
            "tiff_lzw",

        "reason":
            (
                "JPEG quality 80 provides a useful balance "
                "between image quality and smaller file size."
            ),
    }


# =========================================================
# GENERAL PURPOSE
# =========================================================

def recommend_general(
    image_info,
):

    if image_info[
        "has_transparency"
    ]:

        output_format = (
            "PNG"
        )

        reason = (
            "Transparency detected, so PNG is "
            "recommended to preserve it."
        )

    else:

        output_format = (
            "JPEG"
        )

        reason = (
            "JPEG is broadly compatible for "
            "general image sharing."
        )

    return {
        "format":
            output_format,

        "dpi":
            150,

        "color_mode":
            "RGB",

        "quality":
            92,

        "resize_mode":
            "Fit",

        "webp_lossless":
            False,

        "png_compression":
            6,

        "tiff_compression":
            "tiff_lzw",

        "reason":
            reason,
    }


# =========================================================
# RESOLUTION ANALYSIS
# =========================================================

def analyze_resolution(
    image_info,
):

    width = (
        image_info[
            "width"
        ]
    )

    height = (
        image_info[
            "height"
        ]
    )

    shortest_side = min(
        width,
        height,
    )

    if shortest_side < 500:

        return {
            "level":
                "LOW",

            "message":
                (
                    "The source image has low pixel dimensions. "
                    "Large printing or heavy enlargement may "
                    "produce visible softness or pixelation."
                ),
        }

    if shortest_side < 1000:

        return {
            "level":
                "MEDIUM",

            "message":
                (
                    "The image has moderate resolution. "
                    "It should work for many digital uses, "
                    "but large prints may need more pixels."
                ),
        }

    if shortest_side < 2000:

        return {
            "level":
                "GOOD",

            "message":
                (
                    "The image has good pixel dimensions "
                    "for general digital use and moderate printing."
                ),
        }

    return {
        "level":
            "HIGH",

        "message":
            (
                "The image has strong pixel dimensions "
                "for high-quality workflows."
            ),
    }


# =========================================================
# FILE SIZE PRIORITY ADJUSTMENT
# =========================================================

def apply_file_size_priority(
    recommendation,
    file_size_priority,
):

    result = (
        recommendation.copy()
    )

    if (
        file_size_priority
        == "Smallest File"
    ):

        if result[
            "format"
        ] == "PNG":

            result[
                "png_compression"
            ] = 9

        elif result[
            "format"
        ] == "WEBP":

            result[
                "quality"
            ] = min(
                result[
                    "quality"
                ],
                75,
            )

        elif result[
            "format"
        ] == "JPEG":

            result[
                "quality"
            ] = min(
                result[
                    "quality"
                ],
                75,
            )

    elif (
        file_size_priority
        == "Maximum Quality"
    ):

        if result[
            "format"
        ] in (
            "JPEG",
            "WEBP",
        ):

            result[
                "quality"
            ] = 100

        if result[
            "format"
        ] == "PNG":

            result[
                "png_compression"
            ] = 6

    return result


# =========================================================
# MAIN RECOMMENDATION ENGINE
# =========================================================

def recommend_export_settings(
    image,
    purpose="General Purpose",
    file_size_priority="Balanced",
):

    image_info = (
        get_image_info(
            image
        )
    )

    if (
        purpose
        == "Web / Website"
    ):

        recommendation = (
            recommend_web(
                image_info
            )
        )

    elif (
        purpose
        == "Social Media"
    ):

        recommendation = (
            recommend_social_media(
                image_info
            )
        )

    elif (
        purpose
        == "Professional Print"
    ):

        recommendation = (
            recommend_print(
                image_info
            )
        )

    elif (
        purpose
        == "High Quality Archive"
    ):

        recommendation = (
            recommend_archive(
                image_info
            )
        )

    elif (
        purpose
        == "Transparent Graphic"
    ):

        recommendation = (
            recommend_transparent(
                image_info
            )
        )

    elif (
        purpose
        == "Email / WhatsApp"
    ):

        recommendation = (
            recommend_messaging(
                image_info
            )
        )

    else:

        recommendation = (
            recommend_general(
                image_info
            )
        )


    recommendation = (
        apply_file_size_priority(
            recommendation,
            file_size_priority,
        )
    )


    resolution = (
        analyze_resolution(
            image_info
        )
    )


    recommendation[
        "purpose"
    ] = purpose

    recommendation[
        "file_size_priority"
    ] = file_size_priority

    recommendation[
        "image_info"
    ] = image_info

    recommendation[
        "resolution_analysis"
    ] = resolution


    # =====================================================
    # WARNINGS
    # =====================================================

    warnings = []


    if (
        purpose
        == "Professional Print"
        and
        resolution[
            "level"
        ]
        in (
            "LOW",
            "MEDIUM",
        )
    ):

        warnings.append(
            "Source resolution may be too low for "
            "large professional prints."
        )


    if (
        recommendation[
            "color_mode"
        ]
        == "CMYK"
    ):

        warnings.append(
            "Always confirm the required CMYK/ICC profile "
            "with the actual print provider."
        )


    if (
        image_info[
            "has_transparency"
        ]
        and
        recommendation[
            "format"
        ]
        == "JPEG"
    ):

        warnings.append(
            "JPEG cannot preserve transparency. "
            "Transparent pixels will need to be flattened."
        )


    recommendation[
        "warnings"
    ] = warnings


    return recommendation