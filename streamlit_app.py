import io
import os

import streamlit as st
from PIL import Image
from psd_tools import PSDImage


# =====================================================
# PAGE SETTINGS
# =====================================================

st.set_page_config(
    page_title="Image Format Converter",
    page_icon="🖼️",
    layout="wide"
)


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def convert_to_rgb(image):
    """
    Safely convert an image to RGB.
    Transparent areas are placed on white background.
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
    """

    if width is None and height is None:
        return image

    if width is None or height is None:
        raise ValueError(
            "Both Width and Height are required."
        )

    width = int(width)
    height = int(height)

    if width <= 0 or height <= 0:
        raise ValueError(
            "Width and Height must be greater than 0."
        )

    return image.resize(
        (width, height),
        Image.Resampling.LANCZOS
    )


def validate_dpi(dpi):

    dpi = int(dpi)

    if dpi <= 0:
        raise ValueError(
            "DPI must be greater than 0."
        )

    if dpi > 2400:
        raise ValueError(
            "Please use a DPI value of 2400 or less."
        )

    return dpi


def convert_image(
    uploaded_file,
    output_format,
    width=None,
    height=None,
    dpi=None
):
    """
    Convert uploaded image.

    TIFF/BMP:
        Pixel size + DPI supported.

    PDF/PSD:
        Original pixel dimensions used.
    """

    uploaded_file.seek(0)

    with Image.open(uploaded_file) as opened_image:
        image = opened_image.copy()

    original_name = os.path.splitext(
        uploaded_file.name
    )[0]

    output_format = output_format.upper()

    # -------------------------------------------------
    # TIFF
    # -------------------------------------------------

    if output_format == "TIFF":

        image = resize_image(
            image,
            width,
            height
        )

        dpi = validate_dpi(
            dpi
        )

        output_buffer = io.BytesIO()

        image.save(
            output_buffer,
            format="TIFF",
            dpi=(dpi, dpi)
        )

        output_buffer.seek(0)

        return (
            output_buffer.getvalue(),
            f"{original_name}.tiff",
            "image/tiff"
        )

    # -------------------------------------------------
    # BMP
    # -------------------------------------------------

    elif output_format == "BMP":

        image = resize_image(
            image,
            width,
            height
        )

        image = convert_to_rgb(
            image
        )

        dpi = validate_dpi(
            dpi
        )

        output_buffer = io.BytesIO()

        image.save(
            output_buffer,
            format="BMP",
            dpi=(dpi, dpi)
        )

        output_buffer.seek(0)

        return (
            output_buffer.getvalue(),
            f"{original_name}.bmp",
            "image/bmp"
        )

    # -------------------------------------------------
    # PDF
    # -------------------------------------------------

    elif output_format == "PDF":

        image = convert_to_rgb(
            image
        )

        output_buffer = io.BytesIO()

        image.save(
            output_buffer,
            format="PDF",
            resolution=100.0
        )

        output_buffer.seek(0)

        return (
            output_buffer.getvalue(),
            f"{original_name}.pdf",
            "application/pdf"
        )

    # -------------------------------------------------
    # PSD
    # -------------------------------------------------

    elif output_format == "PSD":

        image = convert_to_rgb(
            image
        )

        psd_image = PSDImage.frompil(
            image
        )

        output_buffer = io.BytesIO()

        psd_image.save(
            output_buffer
        )

        output_buffer.seek(0)

        return (
            output_buffer.getvalue(),
            f"{original_name}.psd",
            "application/octet-stream"
        )

    else:

        raise ValueError(
            "Unsupported output format."
        )


# =====================================================
# HEADER
# =====================================================

st.title(
    "🖼️ Image Format Converter"
)

st.write(
    "Convert PNG, JPG and JPEG images into "
    "TIFF, BMP, PDF and PSD formats."
)

st.caption(
    "TIFF and BMP also support custom Pixel Size and DPI."
)

st.divider()


# =====================================================
# UPLOAD
# =====================================================

uploaded_files = st.file_uploader(
    "Upload Images",
    type=[
        "png",
        "jpg",
        "jpeg"
    ],
    accept_multiple_files=True
)


# =====================================================
# OUTPUT FORMAT
# =====================================================

output_format = st.selectbox(
    "Choose Output Format",
    [
        "TIFF",
        "BMP",
        "PDF",
        "PSD"
    ]
)


# =====================================================
# TIFF / BMP ADVANCED SETTINGS
# =====================================================

width = None
height = None
dpi = None


if output_format in (
    "TIFF",
    "BMP"
):

    st.subheader(
        "Pixel Size & DPI Settings"
    )

    st.info(
        "You can change the image dimensions "
        "and DPI before conversion."
    )

    keep_original_size = st.checkbox(
        "Keep Original Pixel Size",
        value=True
    )

    # ---------------------------------------------
    # FIND DEFAULT DIMENSIONS
    # ---------------------------------------------

    default_width = 1920
    default_height = 1080

    if uploaded_files:

        try:

            uploaded_files[0].seek(0)

            with Image.open(
                uploaded_files[0]
            ) as temp_image:

                default_width, default_height = (
                    temp_image.size
                )

            uploaded_files[0].seek(0)

        except Exception:
            pass


    # ---------------------------------------------
    # PIXEL SIZE
    # ---------------------------------------------

    if not keep_original_size:

        column1, column2 = st.columns(2)

        with column1:

            width = st.number_input(
                "Width (px)",
                min_value=1,
                max_value=20000,
                value=int(default_width),
                step=1
            )

        with column2:

            height = st.number_input(
                "Height (px)",
                min_value=1,
                max_value=20000,
                value=int(default_height),
                step=1
            )

    else:

        width = None
        height = None

        if uploaded_files:

            st.write(
                f"Original Pixel Size: "
                f"**{default_width} × "
                f"{default_height} px**"
            )


    # ---------------------------------------------
    # DPI
    # ---------------------------------------------

    dpi_option = st.selectbox(
        "DPI",
        [
            "72",
            "96",
            "150",
            "300",
            "Custom"
        ],
        index=3
    )

    if dpi_option == "Custom":

        dpi = st.number_input(
            "Custom DPI",
            min_value=1,
            max_value=2400,
            value=300,
            step=1
        )

    else:

        dpi = int(
            dpi_option
        )


# =====================================================
# SHOW SELECTED FILES
# =====================================================

if uploaded_files:

    st.success(
        f"{len(uploaded_files)} image(s) selected."
    )

    for index, uploaded_file in enumerate(
        uploaded_files,
        start=1
    ):

        try:

            uploaded_file.seek(0)

            with Image.open(
                uploaded_file
            ) as opened_image:

                image = opened_image.copy()

                original_format = (
                    opened_image.format
                )

                original_width, original_height = (
                    opened_image.size
                )

                image_mode = (
                    opened_image.mode
                )

                original_dpi = (
                    opened_image.info.get(
                        "dpi",
                        "Not available"
                    )
                )

            file_size_kb = (
                uploaded_file.size / 1024
            )

            st.subheader(
                f"{index}. {uploaded_file.name}"
            )

            col1, col2 = st.columns(
                [1, 2]
            )

            # -----------------------------------------
            # IMAGE PREVIEW
            # -----------------------------------------

            with col1:

                st.image(
                    image,
                    caption=uploaded_file.name,
                    use_container_width=True
                )

            # -----------------------------------------
            # IMAGE INFORMATION
            # -----------------------------------------

            with col2:

                st.write(
                    f"**Original Format:** "
                    f"{original_format}"
                )

                st.write(
                    f"**Original Dimensions:** "
                    f"{original_width} × "
                    f"{original_height} pixels"
                )

                st.write(
                    f"**Color Mode:** "
                    f"{image_mode}"
                )

                st.write(
                    f"**Original DPI:** "
                    f"{original_dpi}"
                )

                st.write(
                    f"**File Size:** "
                    f"{file_size_kb:.2f} KB"
                )

                # -------------------------------------
                # OUTPUT INFORMATION
                # -------------------------------------

                if output_format in (
                    "TIFF",
                    "BMP"
                ):

                    st.markdown(
                        "### Output Settings"
                    )

                    if (
                        width is not None
                        and height is not None
                    ):

                        st.write(
                            f"**New Pixel Size:** "
                            f"{width} × {height}px"
                        )

                    else:

                        st.write(
                            "**Pixel Size:** "
                            "Original size"
                        )

                    st.write(
                        f"**DPI:** {dpi}"
                    )


            # -----------------------------------------
            # CONVERSION
            # -----------------------------------------

            uploaded_file.seek(0)

            converted_data, file_name, mime_type = (
                convert_image(
                    uploaded_file,
                    output_format,
                    width,
                    height,
                    dpi
                )
            )

            # -----------------------------------------
            # DOWNLOAD
            # -----------------------------------------

            st.download_button(
                label=(
                    f"Download {output_format} - "
                    f"{uploaded_file.name}"
                ),
                data=converted_data,
                file_name=file_name,
                mime=mime_type,
                key=f"download_{index}"
            )

            st.divider()

        except Exception as error:

            st.error(
                f"Failed to process "
                f"{uploaded_file.name}: "
                f"{error}"
            )

else:

    st.info(
        "Upload one or more PNG/JPG/JPEG "
        "images to start conversion."
    )


# =====================================================
# FOOTER
# =====================================================

st.caption(
    "Image Format Converter | "
    "Built with Python, Pillow, "
    "psd-tools and Streamlit"
)