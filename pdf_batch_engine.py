import io

import pymupdf
from PIL import Image


# =========================================================
# PIXMAP → PIL IMAGE
# =========================================================

def pixmap_to_pil(pixmap):

    if pixmap.alpha:
        mode = "RGBA"

    elif pixmap.n >= 3:
        mode = "RGB"

    else:
        mode = "L"

    return Image.frombytes(
        mode,
        (
            pixmap.width,
            pixmap.height,
        ),
        pixmap.samples,
    )


# =========================================================
# GET PDF PAGE COUNT
# =========================================================

def get_pdf_page_count(file_bytes):

    document = pymupdf.open(
        stream=file_bytes,
        filetype="pdf",
    )

    try:

        return int(
            document.page_count
        )

    finally:

        document.close()


# =========================================================
# RENDER ONE PDF PAGE
# =========================================================

def render_pdf_page(
    file_bytes,
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

    document = pymupdf.open(
        stream=file_bytes,
        filetype="pdf",
    )

    try:

        page_count = int(
            document.page_count
        )

        if page_count < 1:

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

        return {
            "page_number":
                page_number,

            "page_count":
                page_count,

            "image":
                image,

            "width":
                image.width,

            "height":
                image.height,

            "mode":
                image.mode,

            "dpi":
                dpi,
        }

    finally:

        document.close()


# =========================================================
# RENDER ALL PDF PAGES
# =========================================================

def render_all_pdf_pages(
    file_bytes,
    dpi=150,
):

    dpi = max(
        72,
        min(
            int(dpi),
            600,
        ),
    )

    document = pymupdf.open(
        stream=file_bytes,
        filetype="pdf",
    )

    results = []

    try:

        page_count = int(
            document.page_count
        )

        if page_count < 1:

            raise ValueError(
                "PDF does not contain any pages."
            )

        for page_index in range(
            page_count
        ):

            page = document.load_page(
                page_index
            )

            pixmap = page.get_pixmap(
                dpi=dpi,
                alpha=True,
            )

            image = pixmap_to_pil(
                pixmap
            )

            results.append(
                {
                    "page_number":
                        page_index + 1,

                    "page_count":
                        page_count,

                    "image":
                        image,

                    "width":
                        image.width,

                    "height":
                        image.height,

                    "mode":
                        image.mode,

                    "dpi":
                        dpi,
                }
            )

    finally:

        document.close()

    return results


# =========================================================
# PIL IMAGE → PNG BYTES
# =========================================================

def image_to_png_bytes(image):

    buffer = io.BytesIO()

    image.convert(
        "RGBA"
    ).save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)

    return buffer.getvalue()


# =========================================================
# RENDER ONE PAGE AS PNG
# =========================================================

def render_pdf_page_as_png(
    file_bytes,
    page_number=1,
    dpi=150,
):

    page = render_pdf_page(
        file_bytes,
        page_number=page_number,
        dpi=dpi,
    )

    return {
        "page_number":
            page[
                "page_number"
            ],

        "page_count":
            page[
                "page_count"
            ],

        "data":
            image_to_png_bytes(
                page[
                    "image"
                ]
            ),

        "width":
            page[
                "width"
            ],

        "height":
            page[
                "height"
            ],

        "mode":
            page[
                "mode"
            ],

        "dpi":
            page[
                "dpi"
            ],
    }


# =========================================================
# RENDER ALL PAGES AS PNG
# =========================================================

def render_all_pdf_pages_as_png(
    file_bytes,
    dpi=150,
):

    pages = render_all_pdf_pages(
        file_bytes,
        dpi=dpi,
    )

    results = []

    for page in pages:

        results.append(
            {
                "page_number":
                    page[
                        "page_number"
                    ],

                "page_count":
                    page[
                        "page_count"
                    ],

                "data":
                    image_to_png_bytes(
                        page[
                            "image"
                        ]
                    ),

                "width":
                    page[
                        "width"
                    ],

                "height":
                    page[
                        "height"
                    ],

                "mode":
                    page[
                        "mode"
                    ],

                "dpi":
                    page[
                        "dpi"
                    ],
            }
        )

    return results