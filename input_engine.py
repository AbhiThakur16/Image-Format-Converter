import io
import os

from PIL import Image
import pymupdf

from pillow_heif import register_heif_opener


# =========================================================
# REGISTER HEIC / HEIF SUPPORT
# =========================================================

register_heif_opener(
    thumbnails=False
)


# =========================================================
# SUPPORTED INPUT FORMATS
# =========================================================

SUPPORTED_INPUT_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
    ".bmp",
    ".pdf",
    ".svg",
    ".heic",
    ".heif",
]


RASTER_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
    ".bmp",
    ".heic",
    ".heif",
]


# =========================================================
# NORMALIZE EXTENSION
# =========================================================

def get_extension(filename):

    if not filename:
        return ""

    return os.path.splitext(
        filename
    )[1].lower()


# =========================================================
# CHECK FORMAT
# =========================================================

def is_supported_input(filename):

    extension = get_extension(
        filename
    )

    return (
        extension
        in SUPPORTED_INPUT_EXTENSIONS
    )


# =========================================================
# COPY PIL IMAGE SAFELY
# =========================================================

def copy_pil_image(image):

    copied = image.copy()

    copied.info = (
        image.info.copy()
        if hasattr(
            image,
            "info"
        )
        else {}
    )

    return copied


# =========================================================
# LOAD NORMAL RASTER IMAGE
# =========================================================

def load_raster_image(
    file_bytes,
    filename="image",
):

    try:

        with Image.open(
            io.BytesIO(
                file_bytes
            )
        ) as image:

            result = (
                copy_pil_image(
                    image
                )
            )

            source_format = (
                image.format
            )

            source_mode = (
                image.mode
            )

            source_dpi = (
                image.info.get(
                    "dpi"
                )
            )

            frame_count = int(
                getattr(
                    image,
                    "n_frames",
                    1,
                )
            )

        return {
            "success":
                True,

            "type":
                "image",

            "image":
                result,

            "filename":
                filename,

            "format":
                source_format,

            "mode":
                source_mode,

            "dpi":
                source_dpi,

            "page_count":
                1,

            "frame_count":
                frame_count,

            "selected_page":
                1,

            "warnings":
                [],
        }

    except Exception as error:

        raise ValueError(
            f"Could not open image "
            f"'{filename}': {error}"
        ) from error


# =========================================================
# PIXMAP → PIL
# =========================================================

def pixmap_to_pil(pixmap):

    if pixmap.alpha:

        mode = "RGBA"

    elif pixmap.n >= 3:

        mode = "RGB"

    else:

        mode = "L"

    image = Image.frombytes(
        mode,
        (
            pixmap.width,
            pixmap.height,
        ),
        pixmap.samples,
    )

    return image


# =========================================================
# PDF INFORMATION
# =========================================================

def get_pdf_info(file_bytes):

    try:

        document = pymupdf.open(
            stream=file_bytes,
            filetype="pdf",
        )

        page_count = (
            document.page_count
        )

        metadata = (
            document.metadata
            or {}
        )

        pages = []

        for index in range(
            page_count
        ):

            page = document.load_page(
                index
            )

            rect = page.rect

            pages.append(
                {
                    "page":
                        index + 1,

                    "width_points":
                        float(
                            rect.width
                        ),

                    "height_points":
                        float(
                            rect.height
                        ),
                }
            )

        document.close()

        return {
            "page_count":
                page_count,

            "metadata":
                metadata,

            "pages":
                pages,
        }

    except Exception as error:

        raise ValueError(
            f"Could not read PDF: "
            f"{error}"
        ) from error


# =========================================================
# LOAD PDF PAGE
# =========================================================

def load_pdf_page(
    file_bytes,
    filename="document.pdf",
    page_number=1,
    dpi=150,
):

    dpi = max(
        72,
        min(
            int(dpi),
            600,
        ),
    )

    try:

        document = pymupdf.open(
            stream=file_bytes,
            filetype="pdf",
        )

        page_count = (
            document.page_count
        )

        if page_count < 1:

            document.close()

            raise ValueError(
                "PDF does not contain any pages."
            )

        page_number = max(
            1,
            min(
                int(page_number),
                page_count,
            ),
        )

        page = document.load_page(
            page_number - 1
        )

        pixmap = page.get_pixmap(
            dpi=dpi,
            alpha=True,
        )

        image = pixmap_to_pil(
            pixmap
        )

        metadata = (
            document.metadata
            or {}
        )

        document.close()

        return {
            "success":
                True,

            "type":
                "pdf",

            "image":
                image,

            "filename":
                filename,

            "format":
                "PDF",

            "mode":
                image.mode,

            "dpi":
                (
                    dpi,
                    dpi,
                ),

            "page_count":
                page_count,

            "frame_count":
                1,

            "selected_page":
                page_number,

            "metadata":
                metadata,

            "warnings":
                [
                    (
                        "PDF pages are rasterized "
                        "before editing. Vector objects "
                        "and original PDF editability "
                        "are not preserved."
                    )
                ],
        }

    except Exception as error:

        raise ValueError(
            f"Could not render PDF "
            f"'{filename}': {error}"
        ) from error


# =========================================================
# LOAD SVG
# =========================================================

def load_svg(
    file_bytes,
    filename="graphic.svg",
    dpi=150,
):

    dpi = max(
        72,
        min(
            int(dpi),
            600,
        ),
    )

    try:

        document = pymupdf.open(
            stream=file_bytes,
            filetype="svg",
        )

        if document.page_count < 1:

            document.close()

            raise ValueError(
                "SVG could not be rendered."
            )

        page = document.load_page(
            0
        )

        pixmap = page.get_pixmap(
            dpi=dpi,
            alpha=True,
        )

        image = pixmap_to_pil(
            pixmap
        )

        document.close()

        return {
            "success":
                True,

            "type":
                "svg",

            "image":
                image,

            "filename":
                filename,

            "format":
                "SVG",

            "mode":
                image.mode,

            "dpi":
                (
                    dpi,
                    dpi,
                ),

            "page_count":
                1,

            "frame_count":
                1,

            "selected_page":
                1,

            "warnings":
                [
                    (
                        "SVG is rasterized for editing. "
                        "Original vector paths are not "
                        "preserved in the editor."
                    )
                ],
        }

    except Exception as error:

        raise ValueError(
            f"Could not render SVG "
            f"'{filename}': {error}"
        ) from error


# =========================================================
# UNIVERSAL INPUT LOADER
# =========================================================

def load_input_file(
    file_bytes,
    filename,
    page_number=1,
    render_dpi=150,
):

    if not file_bytes:

        raise ValueError(
            "Input file is empty."
        )

    extension = get_extension(
        filename
    )

    if (
        extension
        not in SUPPORTED_INPUT_EXTENSIONS
    ):

        raise ValueError(
            f"Unsupported input format: "
            f"{extension or 'unknown'}"
        )

    # =====================================================
    # PDF
    # =====================================================

    if extension == ".pdf":

        return load_pdf_page(
            file_bytes,
            filename=filename,
            page_number=page_number,
            dpi=render_dpi,
        )

    # =====================================================
    # SVG
    # =====================================================

    if extension == ".svg":

        return load_svg(
            file_bytes,
            filename=filename,
            dpi=render_dpi,
        )

    # =====================================================
    # RASTER / HEIC / HEIF
    # =====================================================

    return load_raster_image(
        file_bytes,
        filename=filename,
    )


# =========================================================
# GET INPUT INFORMATION
# =========================================================

def get_input_info(
    file_bytes,
    filename,
):

    extension = get_extension(
        filename
    )

    if not is_supported_input(
        filename
    ):

        return {
            "supported":
                False,

            "filename":
                filename,

            "extension":
                extension,

            "type":
                "unsupported",
        }

    if extension == ".pdf":

        pdf_info = (
            get_pdf_info(
                file_bytes
            )
        )

        return {
            "supported":
                True,

            "filename":
                filename,

            "extension":
                extension,

            "type":
                "pdf",

            "page_count":
                pdf_info[
                    "page_count"
                ],

            "metadata":
                pdf_info[
                    "metadata"
                ],

            "pages":
                pdf_info[
                    "pages"
                ],
        }

    if extension == ".svg":

        return {
            "supported":
                True,

            "filename":
                filename,

            "extension":
                extension,

            "type":
                "svg",

            "page_count":
                1,
        }

    return {
        "supported":
            True,

        "filename":
            filename,

        "extension":
            extension,

        "type":
            "image",

        "page_count":
            1,
    }


# =========================================================
# CONVERT RESULT TO PNG BYTES
# =========================================================

def input_result_to_png_bytes(
    input_result,
):

    image = input_result.get(
        "image"
    )

    if not isinstance(
        image,
        Image.Image,
    ):

        raise ValueError(
            "Input result does not "
            "contain a valid image."
        )

    buffer = io.BytesIO()

    image.convert(
        "RGBA"
    ).save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)

    return buffer.getvalue()