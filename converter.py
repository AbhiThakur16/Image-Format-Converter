import os

from PIL import Image
from psd_tools import PSDImage


# =========================================================
# SUPPORTED FORMATS
# =========================================================

SUPPORTED_INPUT_FORMATS = [
    ".png",
    ".jpg",
    ".jpeg"
]

SUPPORTED_OUTPUT_FORMATS = [
    "TIFF",
    "BMP",
    "PDF",
    "PSD"
]


# =========================================================
# SCREEN RESOLUTION PRESETS
# =========================================================

RESOLUTION_PRESETS = {
    "Original": None,
    "HD": (1280, 720),
    "Full HD": (1920, 1080),
    "2K": (2560, 1440),
    "4K": (3840, 2160),
    "Custom": None
}


# =========================================================
# PRINT SIZE PRESETS
# Dimensions are in millimetres
# =========================================================

PRINT_PRESETS_MM = {
    "A5": (148, 210),
    "A4": (210, 297),
    "A3": (297, 420),
    "A2": (420, 594)
}


# =========================================================
# FILE VALIDATION
# =========================================================

def validate_input_file(input_path):

    if not os.path.isfile(input_path):

        raise FileNotFoundError(
            "Input image does not exist."
        )

    extension = os.path.splitext(
        input_path
    )[1].lower()

    if extension not in SUPPORTED_INPUT_FORMATS:

        raise ValueError(
            "Unsupported input format. "
            "Only PNG, JPG and JPEG are supported."
        )


# =========================================================
# DPI VALIDATION
# =========================================================

def validate_dpi(dpi):

    if dpi is None:
        return None

    dpi = int(dpi)

    if dpi < 72 or dpi > 600:

        raise ValueError(
            "DPI must be between 72 and 600."
        )

    return dpi


# =========================================================
# COLOR CONVERSION
# =========================================================

def convert_to_rgb(image):
    """
    Converts images safely to RGB.

    Transparent pixels are placed on a
    white background.
    """

    if image.mode in (
        "RGBA",
        "LA"
    ):

        rgba_image = image.convert(
            "RGBA"
        )

        background = Image.new(
            "RGB",
            rgba_image.size,
            "white"
        )

        background.paste(
            rgba_image,
            mask=rgba_image.getchannel("A")
        )

        return background

    if image.mode == "P":

        return image.convert(
            "RGB"
        )

    if image.mode != "RGB":

        return image.convert(
            "RGB"
        )

    return image


# =========================================================
# ASPECT RATIO CALCULATION
# =========================================================

def calculate_aspect_ratio_size(
    original_width,
    original_height,
    target_width,
    target_height
):
    """
    Fits the image inside the target dimensions
    without stretching it.
    """

    width_ratio = (
        target_width / original_width
    )

    height_ratio = (
        target_height / original_height
    )

    scale = min(
        width_ratio,
        height_ratio
    )

    new_width = max(
        1,
        round(
            original_width * scale
        )
    )

    new_height = max(
        1,
        round(
            original_height * scale
        )
    )

    return (
        new_width,
        new_height
    )


# =========================================================
# SCREEN OUTPUT DIMENSIONS
# =========================================================

def get_output_dimensions(
    original_size,
    resolution_preset="Original",
    custom_width=None,
    custom_height=None,
    maintain_aspect_ratio=True
):
    """
    Calculates output dimensions for:

    Original
    HD
    Full HD
    2K
    4K
    Custom
    """

    (
        original_width,
        original_height
    ) = original_size


    # -----------------------------------------------------
    # ORIGINAL
    # -----------------------------------------------------

    if resolution_preset == "Original":

        return (
            original_width,
            original_height
        )


    # -----------------------------------------------------
    # CUSTOM
    # -----------------------------------------------------

    if resolution_preset == "Custom":

        if (
            custom_width is None
            or custom_height is None
        ):

            raise ValueError(
                "Custom Width and Height are required."
            )

        target_width = int(
            custom_width
        )

        target_height = int(
            custom_height
        )


    # -----------------------------------------------------
    # PREDEFINED RESOLUTION
    # -----------------------------------------------------

    else:

        if (
            resolution_preset
            not in RESOLUTION_PRESETS
        ):

            raise ValueError(
                "Invalid resolution preset."
            )

        preset_size = (
            RESOLUTION_PRESETS[
                resolution_preset
            ]
        )

        if preset_size is None:

            return (
                original_width,
                original_height
            )

        (
            target_width,
            target_height
        ) = preset_size


    # -----------------------------------------------------
    # VALIDATE SIZE
    # -----------------------------------------------------

    if (
        target_width <= 0
        or target_height <= 0
    ):

        raise ValueError(
            "Width and Height must be greater than 0."
        )


    # -----------------------------------------------------
    # MAINTAIN ASPECT RATIO
    # -----------------------------------------------------

    if maintain_aspect_ratio:

        return calculate_aspect_ratio_size(
            original_width,
            original_height,
            target_width,
            target_height
        )


    # Exact dimensions
    return (
        target_width,
        target_height
    )


# =========================================================
# PHYSICAL SIZE TO PIXELS
# =========================================================

def physical_size_to_pixels(
    width,
    height,
    unit,
    dpi
):
    """
    Converts physical dimensions into pixels.

    Supported units:

    Pixels
    Inches
    CM
    MM
    """

    width = float(
        width
    )

    height = float(
        height
    )

    dpi = validate_dpi(
        dpi
    )


    if (
        width <= 0
        or height <= 0
    ):

        raise ValueError(
            "Width and Height must be greater than 0."
        )


    # -----------------------------------------------------
    # PIXELS
    # -----------------------------------------------------

    if unit == "Pixels":

        return (
            max(
                1,
                int(round(width))
            ),
            max(
                1,
                int(round(height))
            )
        )


    # -----------------------------------------------------
    # INCHES
    # -----------------------------------------------------

    elif unit == "Inches":

        width_inches = width

        height_inches = height


    # -----------------------------------------------------
    # CENTIMETRES
    # -----------------------------------------------------

    elif unit == "CM":

        width_inches = (
            width / 2.54
        )

        height_inches = (
            height / 2.54
        )


    # -----------------------------------------------------
    # MILLIMETRES
    # -----------------------------------------------------

    elif unit == "MM":

        width_inches = (
            width / 25.4
        )

        height_inches = (
            height / 25.4
        )


    else:

        raise ValueError(
            "Unsupported measurement unit."
        )


    pixel_width = round(
        width_inches * dpi
    )

    pixel_height = round(
        height_inches * dpi
    )


    return (
        max(
            1,
            pixel_width
        ),
        max(
            1,
            pixel_height
        )
    )


# =========================================================
# PRINT PRESET TO PIXELS
# =========================================================

def print_preset_to_pixels(
    paper_size,
    orientation,
    dpi
):
    """
    Converts A5/A4/A3/A2 paper sizes into
    pixel dimensions based on DPI.
    """

    if paper_size not in PRINT_PRESETS_MM:

        raise ValueError(
            "Invalid print preset."
        )


    (
        width_mm,
        height_mm
    ) = PRINT_PRESETS_MM[
        paper_size
    ]


    # -----------------------------------------------------
    # ORIENTATION
    # -----------------------------------------------------

    if orientation == "Landscape":

        (
            width_mm,
            height_mm
        ) = (
            height_mm,
            width_mm
        )

    elif orientation != "Portrait":

        raise ValueError(
            "Orientation must be Portrait or Landscape."
        )


    return physical_size_to_pixels(
        width_mm,
        height_mm,
        "MM",
        dpi
    )


# =========================================================
# PIXELS TO PRINT SIZE
# =========================================================

def pixels_to_physical_size(
    width_pixels,
    height_pixels,
    dpi
):
    """
    Returns print size in inches, cm and mm.
    """

    dpi = validate_dpi(
        dpi
    )


    width_inches = (
        width_pixels / dpi
    )

    height_inches = (
        height_pixels / dpi
    )


    width_cm = (
        width_inches * 2.54
    )

    height_cm = (
        height_inches * 2.54
    )


    width_mm = (
        width_inches * 25.4
    )

    height_mm = (
        height_inches * 25.4
    )


    return {
        "inches": (
            width_inches,
            height_inches
        ),

        "cm": (
            width_cm,
            height_cm
        ),

        "mm": (
            width_mm,
            height_mm
        )
    }


# =========================================================
# RESIZE IMAGE
# =========================================================

def resize_image(
    image,
    resolution_preset="Original",
    custom_width=None,
    custom_height=None,
    maintain_aspect_ratio=True
):
    """
    High-quality image resizing using Lanczos.
    """

    (
        new_width,
        new_height
    ) = get_output_dimensions(
        image.size,
        resolution_preset,
        custom_width,
        custom_height,
        maintain_aspect_ratio
    )


    if image.size == (
        new_width,
        new_height
    ):

        return image


    return image.resize(
        (
            new_width,
            new_height
        ),
        Image.Resampling.LANCZOS
    )


# =========================================================
# UNIQUE OUTPUT FILE PATH
# =========================================================

def generate_unique_output_path(
    output_directory,
    file_name,
    extension
):
    """
    Prevents overwriting existing files.

    Example:

    photo.tiff
    photo_1.tiff
    photo_2.tiff
    """

    output_path = os.path.join(
        output_directory,
        file_name + extension
    )


    if not os.path.exists(
        output_path
    ):

        return output_path


    counter = 1


    while True:

        new_output_path = os.path.join(
            output_directory,
            f"{file_name}_{counter}{extension}"
        )


        if not os.path.exists(
            new_output_path
        ):

            return new_output_path


        counter += 1


# =========================================================
# SINGLE IMAGE CONVERSION
# =========================================================

def convert_image(
    input_path,
    output_directory,
    output_format,
    resolution_preset="Original",
    custom_width=None,
    custom_height=None,
    maintain_aspect_ratio=True,
    dpi=300
):
    """
    Converts one image.

    TIFF and BMP support:
    - Pixel resizing
    - Resolution presets
    - Aspect ratio
    - DPI

    PDF and PSD currently use original pixel size.
    """

    validate_input_file(
        input_path
    )


    output_format = (
        output_format.upper()
    )


    if (
        output_format
        not in SUPPORTED_OUTPUT_FORMATS
    ):

        raise ValueError(
            f"Unsupported output format: "
            f"{output_format}"
        )


    os.makedirs(
        output_directory,
        exist_ok=True
    )


    file_name = os.path.splitext(
        os.path.basename(
            input_path
        )
    )[0]


    extension_mapping = {

        "TIFF": ".tiff",

        "BMP": ".bmp",

        "PDF": ".pdf",

        "PSD": ".psd"
    }


    output_path = (
        generate_unique_output_path(
            output_directory,
            file_name,
            extension_mapping[
                output_format
            ]
        )
    )


    try:

        # -------------------------------------------------
        # OPEN IMAGE
        # -------------------------------------------------

        with Image.open(
            input_path
        ) as opened_image:

            image = (
                opened_image.copy()
            )


        # -------------------------------------------------
        # TIFF / BMP RESOLUTION
        # -------------------------------------------------

        if output_format in (
            "TIFF",
            "BMP"
        ):

            image = resize_image(
                image,
                resolution_preset,
                custom_width,
                custom_height,
                maintain_aspect_ratio
            )


            validated_dpi = (
                validate_dpi(
                    dpi
                )
            )


        # =================================================
        # TIFF
        # =================================================

        if output_format == "TIFF":

            image.save(
                output_path,
                format="TIFF",
                dpi=(
                    validated_dpi,
                    validated_dpi
                )
            )


        # =================================================
        # BMP
        # =================================================

        elif output_format == "BMP":

            image = convert_to_rgb(
                image
            )


            image.save(
                output_path,
                format="BMP",
                dpi=(
                    validated_dpi,
                    validated_dpi
                )
            )


        # =================================================
        # PDF
        # =================================================

        elif output_format == "PDF":

            image = convert_to_rgb(
                image
            )


            image.save(
                output_path,
                format="PDF",
                resolution=100.0
            )


        # =================================================
        # PSD
        # =================================================

        elif output_format == "PSD":

            image = convert_to_rgb(
                image
            )


            psd_image = (
                PSDImage.frompil(
                    image
                )
            )


            psd_image.save(
                output_path
            )


        return output_path


    except Exception as error:

        raise RuntimeError(
            f"Image conversion failed: "
            f"{error}"
        )


# =========================================================
# MULTIPLE IMAGE CONVERSION
# =========================================================

def convert_multiple_images(
    input_files,
    output_directory,
    output_format,
    resolution_preset="Original",
    custom_width=None,
    custom_height=None,
    maintain_aspect_ratio=True,
    dpi=300
):
    """
    Converts multiple images while allowing
    individual failures without stopping
    the whole batch.
    """

    successful_files = []

    failed_files = []


    for input_file in input_files:

        try:

            output_path = convert_image(
                input_file,
                output_directory,
                output_format,
                resolution_preset,
                custom_width,
                custom_height,
                maintain_aspect_ratio,
                dpi
            )


            successful_files.append(
                output_path
            )


        except Exception as error:

            failed_files.append(
                {
                    "file": input_file,
                    "error": str(error)
                }
            )


    return (
        successful_files,
        failed_files
    )