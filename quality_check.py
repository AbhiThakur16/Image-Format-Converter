from PIL import Image


# =========================================================
# HELPER
# =========================================================

def add_check(
    checks,
    title,
    status,
    message
):
    checks.append(
        {
            "title": title,
            "status": status,
            "message": message
        }
    )


# =========================================================
# TRANSPARENCY
# =========================================================

def has_transparency(
    image: Image.Image
):

    if image.mode in (
        "RGBA",
        "LA"
    ):

        alpha = image.getchannel(
            "A"
        )

        minimum, maximum = (
            alpha.getextrema()
        )

        return minimum < 255

    if image.mode == "P":

        return (
            "transparency"
            in image.info
        )

    return False


# =========================================================
# IMAGE BIT DEPTH
# =========================================================

def estimate_bit_depth(
    image: Image.Image
):

    mode = image.mode

    if mode == "1":
        return 1

    if mode in (
        "L",
        "P",
        "RGB",
        "RGBA",
        "CMYK"
    ):
        return 8

    if mode in (
        "I;16",
        "I;16L",
        "I;16B"
    ):
        return 16

    if mode == "F":
        return 32

    return None


# =========================================================
# DPI QUALITY LABEL
# =========================================================

def dpi_quality(
    dpi
):

    dpi = float(
        dpi
    )

    if dpi >= 300:

        return (
            "PASS",
            "Suitable for high-quality print."
        )

    if dpi >= 150:

        return (
            "WARN",
            "Usable for standard print, but below professional 300 DPI."
        )

    if dpi >= 96:

        return (
            "WARN",
            "Better suited to screens than high-quality printing."
        )

    return (
        "WARN",
        "Low DPI for print."
    )


# =========================================================
# PIXEL DIMENSION CHECK
# =========================================================

def check_pixel_dimensions(
    width,
    height
):

    smallest_side = min(
        width,
        height
    )

    if smallest_side >= 2000:

        return (
            "PASS",
            "High pixel dimensions."
        )

    if smallest_side >= 1000:

        return (
            "PASS",
            "Good general-purpose pixel dimensions."
        )

    if smallest_side >= 500:

        return (
            "WARN",
            "Moderate resolution. Large prints may appear soft."
        )

    return (
        "WARN",
        "Low pixel dimensions. Enlarging may cause visible pixelation."
    )


# =========================================================
# UPSCALE CHECK
# =========================================================

def check_resize_quality(
    original_size,
    target_size
):

    original_width, original_height = (
        original_size
    )

    target_width, target_height = (
        target_size
    )

    width_scale = (
        target_width
        / max(
            original_width,
            1
        )
    )

    height_scale = (
        target_height
        / max(
            original_height,
            1
        )
    )

    scale = max(
        width_scale,
        height_scale
    )

    if scale <= 1.0:

        return (
            "PASS",
            scale,
            "Image is not being enlarged."
        )

    if scale <= 1.5:

        return (
            "PASS",
            scale,
            "Small enlargement. Quality loss should be limited."
        )

    if scale <= 2.0:

        return (
            "WARN",
            scale,
            "Moderate enlargement may reduce sharpness."
        )

    return (
        "WARN",
        scale,
        "Large enlargement detected. Pixelation or blur may become visible."
    )


# =========================================================
# FORMAT COMPATIBILITY
# =========================================================

def check_format(
    image,
    output_format
):

    transparency = has_transparency(
        image
    )

    output_format = (
        output_format.upper()
    )

    if transparency:

        if output_format in (
            "BMP",
            "JPEG",
            "JPG"
        ):

            return (
                "WARN",
                (
                    f"{output_format} may not preserve "
                    f"the current transparency."
                )
            )

        return (
            "PASS",
            "Selected format can be used with the current image workflow."
        )

    return (
        "PASS",
        "No transparency compatibility issue detected."
    )


# =========================================================
# PRINT DIMENSIONS
# =========================================================

def calculate_print_size(
    width,
    height,
    dpi
):

    dpi = max(
        float(dpi),
        1
    )

    width_inches = (
        width
        / dpi
    )

    height_inches = (
        height
        / dpi
    )

    width_cm = (
        width_inches
        * 2.54
    )

    height_cm = (
        height_inches
        * 2.54
    )

    return {
        "width_inches":
            width_inches,

        "height_inches":
            height_inches,

        "width_cm":
            width_cm,

        "height_cm":
            height_cm
    }


# =========================================================
# MAIN QUALITY CHECK
# =========================================================

def run_quality_check(
    image: Image.Image,
    target_width,
    target_height,
    dpi,
    output_format,
    target_color_mode=None
):

    checks = []

    original_width, original_height = (
        image.size
    )

    target_width = int(
        target_width
    )

    target_height = int(
        target_height
    )

    dpi = float(
        dpi
    )

    total_pixels = (
        target_width
        * target_height
    )


    # =====================================================
    # ORIGINAL IMAGE
    # =====================================================

    add_check(
        checks,
        "Original Image",
        "INFO",
        (
            f"{original_width:,} × "
            f"{original_height:,} px"
        )
    )


    # =====================================================
    # OUTPUT DIMENSIONS
    # =====================================================

    pixel_status, pixel_message = (
        check_pixel_dimensions(
            target_width,
            target_height
        )
    )

    add_check(
        checks,
        "Pixel Dimensions",
        pixel_status,
        (
            f"{target_width:,} × "
            f"{target_height:,} px. "
            f"{pixel_message}"
        )
    )


    # =====================================================
    # TOTAL PIXELS
    # =====================================================

    add_check(
        checks,
        "Total Output Pixels",
        "INFO",
        f"{total_pixels:,} pixels"
    )


    # =====================================================
    # DPI
    # =====================================================

    dpi_status, dpi_message = (
        dpi_quality(
            dpi
        )
    )

    add_check(
        checks,
        "DPI",
        dpi_status,
        (
            f"{dpi:g} DPI. "
            f"{dpi_message}"
        )
    )


    # =====================================================
    # UPSCALING
    # =====================================================

    (
        upscale_status,
        scale,
        upscale_message
    ) = check_resize_quality(
        (
            original_width,
            original_height
        ),
        (
            target_width,
            target_height
        )
    )

    add_check(
        checks,
        "Resize Quality",
        upscale_status,
        (
            f"Maximum scale: "
            f"{scale:.2f}×. "
            f"{upscale_message}"
        )
    )


    # =====================================================
    # COLOR MODE
    # =====================================================

    if target_color_mode:

        add_check(
            checks,
            "Color Mode",
            "INFO",
            (
                f"Source: {image.mode}. "
                f"Target: {target_color_mode}."
            )
        )

    else:

        add_check(
            checks,
            "Color Mode",
            "INFO",
            (
                f"Current image mode: "
                f"{image.mode}."
            )
        )


    # =====================================================
    # BIT DEPTH
    # =====================================================

    bit_depth = (
        estimate_bit_depth(
            image
        )
    )

    if bit_depth is None:

        add_check(
            checks,
            "Bit Depth",
            "INFO",
            (
                f"Could not determine bit depth "
                f"for mode {image.mode}."
            )
        )

    else:

        add_check(
            checks,
            "Bit Depth",
            "INFO",
            (
                f"Estimated source bit depth: "
                f"{bit_depth}-bit per channel/mode basis."
            )
        )


    # =====================================================
    # TRANSPARENCY
    # =====================================================

    transparency = (
        has_transparency(
            image
        )
    )

    if transparency:

        add_check(
            checks,
            "Transparency",
            "PASS",
            "Transparent pixels detected."
        )

    else:

        add_check(
            checks,
            "Transparency",
            "INFO",
            "No transparent pixels detected."
        )


    # =====================================================
    # OUTPUT FORMAT
    # =====================================================

    format_status, format_message = (
        check_format(
            image,
            output_format
        )
    )

    add_check(
        checks,
        "Format Compatibility",
        format_status,
        format_message
    )


    # =====================================================
    # PRINT SIZE
    # =====================================================

    print_size = (
        calculate_print_size(
            target_width,
            target_height,
            dpi
        )
    )

    add_check(
        checks,
        "Print Size",
        "INFO",
        (
            f"{print_size['width_inches']:.2f} × "
            f"{print_size['height_inches']:.2f} in "
            f"({print_size['width_cm']:.2f} × "
            f"{print_size['height_cm']:.2f} cm)"
        )
    )


    # =====================================================
    # SCORE SUMMARY
    # =====================================================

    warning_count = sum(
        1
        for check in checks
        if check["status"] == "WARN"
    )

    pass_count = sum(
        1
        for check in checks
        if check["status"] == "PASS"
    )

    if warning_count == 0:

        overall_status = (
            "READY"
        )

        overall_message = (
            "No major quality warnings detected."
        )

    elif warning_count <= 2:

        overall_status = (
            "CHECK"
        )

        overall_message = (
            "Export is possible, but review the warnings."
        )

    else:

        overall_status = (
            "REVIEW"
        )

        overall_message = (
            "Multiple quality warnings were detected."
        )


    return {
        "overall_status":
            overall_status,

        "overall_message":
            overall_message,

        "warning_count":
            warning_count,

        "pass_count":
            pass_count,

        "checks":
            checks,

        "print_size":
            print_size
    }