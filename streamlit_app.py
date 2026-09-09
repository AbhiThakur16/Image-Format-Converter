import io
import os
import streamlit as st

from PIL import Image
from psd_tools import PSDImage


st.set_page_config(
    page_title="Image Format Converter",
    page_icon="🖼️",
    layout="wide"
)


def convert_to_rgb(image):
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


def convert_image(uploaded_file, output_format):
    image = Image.open(uploaded_file)

    original_name = os.path.splitext(
        uploaded_file.name
    )[0]

    output_format = output_format.upper()

    # TIFF
    if output_format == "TIFF":
        output_buffer = io.BytesIO()

        image.save(
            output_buffer,
            format="TIFF"
        )

        output_buffer.seek(0)

        return (
            output_buffer.getvalue(),
            f"{original_name}.tiff",
            "image/tiff"
        )

    # BMP
    elif output_format == "BMP":
        image = convert_to_rgb(image)

        output_buffer = io.BytesIO()

        image.save(
            output_buffer,
            format="BMP"
        )

        output_buffer.seek(0)

        return (
            output_buffer.getvalue(),
            f"{original_name}.bmp",
            "image/bmp"
        )

    # PDF
    elif output_format == "PDF":
        image = convert_to_rgb(image)

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

    # PSD
    elif output_format == "PSD":
        image = convert_to_rgb(image)

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


# -------------------------------------------------
# PAGE HEADER
# -------------------------------------------------

st.title("🖼️ Image Format Converter")

st.write(
    "Convert PNG, JPG and JPEG images "
    "into TIFF, BMP, PDF and PSD formats."
)

st.divider()


# -------------------------------------------------
# FILE UPLOAD
# -------------------------------------------------

uploaded_files = st.file_uploader(
    "Upload Images",
    type=[
        "png",
        "jpg",
        "jpeg"
    ],
    accept_multiple_files=True
)


# -------------------------------------------------
# OUTPUT FORMAT
# -------------------------------------------------

output_format = st.selectbox(
    "Choose Output Format",
    [
        "TIFF",
        "BMP",
        "PDF",
        "PSD"
    ]
)


# -------------------------------------------------
# PROCESS FILES
# -------------------------------------------------

if uploaded_files:

    st.success(
        f"{len(uploaded_files)} image(s) selected."
    )

    for index, uploaded_file in enumerate(
        uploaded_files,
        start=1
    ):

        try:
            image = Image.open(
                uploaded_file
            )

            width, height = image.size

            file_size_kb = (
                uploaded_file.size / 1024
            )

            st.subheader(
                f"{index}. {uploaded_file.name}"
            )

            col1, col2 = st.columns(
                [1, 2]
            )

            with col1:
                st.image(
                    image,
                    caption=uploaded_file.name,
                    use_container_width=True
                )

            with col2:
                st.write(
                    f"**Original Format:** "
                    f"{image.format}"
                )

                st.write(
                    f"**Dimensions:** "
                    f"{width} × {height} pixels"
                )

                st.write(
                    f"**Color Mode:** "
                    f"{image.mode}"
                )

                st.write(
                    f"**File Size:** "
                    f"{file_size_kb:.2f} KB"
                )

            # Reset uploaded file position
            uploaded_file.seek(0)

            converted_data, file_name, mime_type = (
                convert_image(
                    uploaded_file,
                    output_format
                )
            )

            st.download_button(
                label=(
                    f"Download "
                    f"{output_format} - "
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
                f"{uploaded_file.name}: {error}"
            )

else:
    st.info(
        "Upload one or more PNG/JPG/JPEG "
        "images to start conversion."
    )


# -------------------------------------------------
# FOOTER
# -------------------------------------------------

st.caption(
    "Image Format Converter | "
    "Built with Python, Pillow, "
    "psd-tools and Streamlit"
)