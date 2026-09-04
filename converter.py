import os
from PIL import Image
from psd_tools import PSDImage


SUPPORTED_INPUT_FORMATS = [".png", ".jpg", ".jpeg"]
SUPPORTED_OUTPUT_FORMATS = ["TIFF", "BMP", "PDF", "PSD"]


def validate_input_file(input_path):
    if not os.path.isfile(input_path):
        raise FileNotFoundError("Input image does not exist.")

    extension = os.path.splitext(input_path)[1].lower()

    if extension not in SUPPORTED_INPUT_FORMATS:
        raise ValueError(
            "Unsupported input format. Only PNG, JPG and JPEG are supported."
        )


def convert_to_rgb(image):
    # Handle images with transparency
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


def generate_unique_output_path(
    output_directory,
    file_name,
    extension
):
    """
    Prevent overwriting existing files.

    Example:
    photo.pdf
    photo_1.pdf
    photo_2.pdf
    """

    output_path = os.path.join(
        output_directory,
        file_name + extension
    )

    if not os.path.exists(output_path):
        return output_path

    counter = 1

    while True:
        output_path = os.path.join(
            output_directory,
            f"{file_name}_{counter}{extension}"
        )

        if not os.path.exists(output_path):
            return output_path

        counter += 1


def convert_image(
    input_path,
    output_directory,
    output_format
):
    validate_input_file(input_path)

    output_format = output_format.upper()

    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(
            f"Unsupported output format: {output_format}"
        )

    os.makedirs(
        output_directory,
        exist_ok=True
    )

    file_name = os.path.basename(input_path)

    file_name_without_extension = os.path.splitext(
        file_name
    )[0]

    extension_mapping = {
        "TIFF": ".tiff",
        "BMP": ".bmp",
        "PDF": ".pdf",
        "PSD": ".psd"
    }

    output_path = generate_unique_output_path(
        output_directory,
        file_name_without_extension,
        extension_mapping[output_format]
    )

    try:
        with Image.open(input_path) as image:

            if output_format == "TIFF":
                image.save(
                    output_path,
                    format="TIFF"
                )

            elif output_format == "BMP":
                converted_image = convert_to_rgb(image)

                converted_image.save(
                    output_path,
                    format="BMP"
                )

            elif output_format == "PDF":
                converted_image = convert_to_rgb(image)

                converted_image.save(
                    output_path,
                    format="PDF",
                    resolution=100.0
                )

            elif output_format == "PSD":
                converted_image = convert_to_rgb(image)

                psd_image = PSDImage.frompil(
                    converted_image
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
    output_format
):
    successful_files = []
    failed_files = []

    for input_file in input_files:
        try:
            output_path = convert_image(
                input_file,
                output_directory,
                output_format
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