import os
from PIL import Image
from psd_tools import PSDImage


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


def validate_input_file(input_path):
    if not os.path.isfile(input_path):
        raise FileNotFoundError(
            "Input image does not exist."
        )

    extension = os.path.splitext(input_path)[1].lower()

    if extension not in SUPPORTED_INPUT_FORMATS:
        raise ValueError(
            "Unsupported input format. "
            "Only PNG, JPG and JPEG are supported."
        )


def convert_to_rgb(image):
    """
    Convert image safely to RGB.
    Transparent areas are placed on a white background.
    """

    if image.mode in ("RGBA", "LA"):
        rgba_image = image.convert("RGBA")

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
        return image.convert("RGB")

    if image.mode != "RGB":
        return image.convert("RGB")

    return image


def resize_image(
    image,
    width=None,
    height=None
):
    """
    Resize image to exact pixel dimensions.

    Width and height must both be provided
    when resizing is requested.
    """

    if width is None and height is None:
        return image

    if width is None or height is None:
        raise ValueError(
            "Both width and height are required."
        )

    width = int(width)
    height = int(height)

    if width <= 0 or height <= 0:
        raise ValueError(
            "Width and height must be greater than 0."
        )

    return image.resize(
        (width, height),
        Image.Resampling.LANCZOS
    )


def validate_dpi(dpi):
    """
    Validate DPI value.
    """

    if dpi is None:
        return None

    dpi = int(dpi)

    if dpi <= 0:
        raise ValueError(
            "DPI must be greater than 0."
        )

    if dpi > 2400:
        raise ValueError(
            "DPI is too high. Please use 2400 DPI or less."
        )

    return dpi


def generate_unique_output_path(
    output_directory,
    file_name,
    extension
):
    """
    Avoid overwriting an existing file.

    Example:
    photo.tiff
    photo_1.tiff
    photo_2.tiff
    """

    output_path = os.path.join(
        output_directory,
        file_name + extension
    )

    if not os.path.exists(output_path):
        return output_path

    counter = 1

    while True:
        new_output_path = os.path.join(
            output_directory,
            f"{file_name}_{counter}{extension}"
        )

        if not os.path.exists(new_output_path):
            return new_output_path

        counter += 1


def convert_image(
    input_path,
    output_directory,
    output_format,
    width=None,
    height=None,
    dpi=None
):
    """
    Convert a single image.

    TIFF/BMP:
        Supports pixel size and DPI changes.

    PDF/PSD:
        Uses original pixel dimensions.
    """

    validate_input_file(
        input_path
    )

    output_format = output_format.upper()

    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(
            f"Unsupported output format: {output_format}"
        )

    os.makedirs(
        output_directory,
        exist_ok=True
    )

    original_file_name = os.path.basename(
        input_path
    )

    file_name = os.path.splitext(
        original_file_name
    )[0]

    extension_mapping = {
        "TIFF": ".tiff",
        "BMP": ".bmp",
        "PDF": ".pdf",
        "PSD": ".psd"
    }

    output_path = generate_unique_output_path(
        output_directory,
        file_name,
        extension_mapping[output_format]
    )

    try:
        with Image.open(input_path) as image:

            # --------------------------------
            # TIFF
            # --------------------------------

            if output_format == "TIFF":

                image = resize_image(
                    image,
                    width,
                    height
                )

                validated_dpi = validate_dpi(
                    dpi
                )

                save_options = {
                    "format": "TIFF"
                }

                if validated_dpi is not None:
                    save_options["dpi"] = (
                        validated_dpi,
                        validated_dpi
                    )

                image.save(
                    output_path,
                    **save_options
                )

            # --------------------------------
            # BMP
            # --------------------------------

            elif output_format == "BMP":

                image = resize_image(
                    image,
                    width,
                    height
                )

                image = convert_to_rgb(
                    image
                )

                validated_dpi = validate_dpi(
                    dpi
                )

                save_options = {
                    "format": "BMP"
                }

                if validated_dpi is not None:
                    save_options["dpi"] = (
                        validated_dpi,
                        validated_dpi
                    )

                image.save(
                    output_path,
                    **save_options
                )

            # --------------------------------
            # PDF
            # --------------------------------

            elif output_format == "PDF":

                image = convert_to_rgb(
                    image
                )

                image.save(
                    output_path,
                    format="PDF",
                    resolution=100.0
                )

            # --------------------------------
            # PSD
            # --------------------------------

            elif output_format == "PSD":

                image = convert_to_rgb(
                    image
                )

                psd_image = PSDImage.frompil(
                    image
                )

                psd_image.save(
                    output_path
                )

        return output_path

    except Exception as error:
        raise RuntimeError(
            f"Image conversion failed: {error}"
        )


def convert_multiple_images(
    input_files,
    output_directory,
    output_format,
    width=None,
    height=None,
    dpi=None
):
    """
    Convert multiple images.
    """

    successful_files = []
    failed_files = []

    for input_file in input_files:

        try:
            output_path = convert_image(
                input_file,
                output_directory,
                output_format,
                width,
                height,
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

    return successful_files, failed_files