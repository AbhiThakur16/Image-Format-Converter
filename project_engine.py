import io
import json
import re
import zipfile

import numpy as np
from PIL import Image


# =========================================================
# SAFE FILE NAME
# =========================================================

def safe_name(name):

    name = str(name).strip()

    name = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        name
    )

    if not name:
        name = "item"

    return name


# =========================================================
# JSON SAFE VALUE
# =========================================================

def make_json_safe(value):

    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool
        )
    ):
        return value

    if isinstance(
        value,
        np.integer
    ):
        return int(value)

    if isinstance(
        value,
        np.floating
    ):
        return float(value)

    if isinstance(
        value,
        tuple
    ):
        return [
            make_json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        list
    ):
        return [
            make_json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        dict
    ):
        return {
            str(key):
                make_json_safe(item)
            for key, item
            in value.items()
            if key not in (
                "image",
                "mask"
            )
        }

    return str(value)


# =========================================================
# IMAGE → PNG BYTES
# =========================================================

def image_to_png_bytes(image):

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG"
    )

    buffer.seek(0)

    return buffer.getvalue()


# =========================================================
# MASK → PNG BYTES
# =========================================================

def mask_to_png_bytes(mask):

    mask_array = np.asarray(
        mask,
        dtype=np.uint8
    )

    mask_image = Image.fromarray(
        mask_array,
        mode="L"
    )

    return image_to_png_bytes(
        mask_image
    )


# =========================================================
# SAVE PROJECT
# =========================================================

def save_project(
    original_image,
    original_filename,
    layer_groups=None,
    settings=None,
    edited_image=None
):

    if layer_groups is None:
        layer_groups = {}

    if settings is None:
        settings = {}

    project_buffer = io.BytesIO()

    manifest = {
        "project_format":
            "AI Image Studio Project",

        "version":
            1,

        "original_filename":
            original_filename,

        "original_size":
            [
                original_image.width,
                original_image.height
            ],

        "original_mode":
            original_image.mode,

        "settings":
            make_json_safe(
                settings
            ),

        "layer_groups":
            {}
    }


    with zipfile.ZipFile(
        project_buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED
    ) as archive:

        # =================================================
        # ORIGINAL IMAGE
        # =================================================

        archive.writestr(
            "original/original.png",
            image_to_png_bytes(
                original_image.convert(
                    "RGBA"
                )
            )
        )


        # =================================================
        # EDITED IMAGE
        # =================================================

        if edited_image is not None:

            archive.writestr(
                "edited/edited.png",
                image_to_png_bytes(
                    edited_image.convert(
                        "RGBA"
                    )
                )
            )

            manifest[
                "edited_image"
            ] = (
                "edited/edited.png"
            )


        # =================================================
        # LAYER GROUPS
        # =================================================

        for group_name, layers in (
            layer_groups.items()
        ):

            clean_group = (
                safe_name(
                    group_name
                )
            )

            group_manifest = []


            for index, layer in enumerate(
                layers
            ):

                layer_manifest = {}

                # -----------------------------------------
                # SAVE METADATA
                # -----------------------------------------

                for key, value in (
                    layer.items()
                ):

                    if key in (
                        "image",
                        "mask",
                        "_uid"
                    ):
                        continue

                    layer_manifest[
                        key
                    ] = (
                        make_json_safe(
                            value
                        )
                    )


                # -----------------------------------------
                # SAVE LAYER IMAGE
                # -----------------------------------------

                if (
                    "image"
                    in layer
                    and isinstance(
                        layer["image"],
                        Image.Image
                    )
                ):

                    image_path = (
                        f"layers/"
                        f"{clean_group}/"
                        f"layer_{index + 1}.png"
                    )

                    archive.writestr(
                        image_path,
                        image_to_png_bytes(
                            layer[
                                "image"
                            ].convert(
                                "RGBA"
                            )
                        )
                    )

                    layer_manifest[
                        "image_path"
                    ] = image_path


                # -----------------------------------------
                # SAVE MASK
                # -----------------------------------------

                if (
                    "mask"
                    in layer
                    and layer[
                        "mask"
                    ] is not None
                ):

                    try:

                        mask_path = (
                            f"masks/"
                            f"{clean_group}/"
                            f"mask_{index + 1}.png"
                        )

                        archive.writestr(
                            mask_path,
                            mask_to_png_bytes(
                                layer[
                                    "mask"
                                ]
                            )
                        )

                        layer_manifest[
                            "mask_path"
                        ] = mask_path

                    except Exception:

                        pass


                group_manifest.append(
                    layer_manifest
                )


            manifest[
                "layer_groups"
            ][
                group_name
            ] = group_manifest


        # =================================================
        # MANIFEST
        # =================================================

        archive.writestr(
            "manifest.json",
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False
            )
        )


    project_buffer.seek(0)

    return project_buffer.getvalue()


# =========================================================
# LOAD IMAGE FROM ZIP
# =========================================================

def load_zip_image(
    archive,
    path
):

    image_bytes = (
        archive.read(
            path
        )
    )

    with Image.open(
        io.BytesIO(
            image_bytes
        )
    ) as image:

        return image.copy()


# =========================================================
# LOAD MASK FROM ZIP
# =========================================================

def load_zip_mask(
    archive,
    path
):

    mask_image = load_zip_image(
        archive,
        path
    ).convert(
        "L"
    )

    return np.array(
        mask_image,
        dtype=np.uint8
    )


# =========================================================
# LOAD PROJECT
# =========================================================

def load_project(
    project_bytes
):

    project_buffer = io.BytesIO(
        project_bytes
    )


    with zipfile.ZipFile(
        project_buffer,
        mode="r"
    ) as archive:

        # =================================================
        # MANIFEST
        # =================================================

        if (
            "manifest.json"
            not in archive.namelist()
        ):

            raise ValueError(
                "Invalid AI Image Studio project."
            )


        manifest = json.loads(
            archive.read(
                "manifest.json"
            ).decode(
                "utf-8"
            )
        )


        # =================================================
        # ORIGINAL
        # =================================================

        original_image = (
            load_zip_image(
                archive,
                "original/original.png"
            )
        )


        # =================================================
        # EDITED
        # =================================================

        edited_image = None


        edited_path = (
            manifest.get(
                "edited_image"
            )
        )


        if (
            edited_path
            and edited_path
            in archive.namelist()
        ):

            edited_image = (
                load_zip_image(
                    archive,
                    edited_path
                )
            )


        # =================================================
        # LAYERS
        # =================================================

        loaded_groups = {}


        for group_name, layer_data in (
            manifest.get(
                "layer_groups",
                {}
            ).items()
        ):

            loaded_layers = []


            for item in layer_data:

                layer = {}


                for key, value in (
                    item.items()
                ):

                    if key in (
                        "image_path",
                        "mask_path"
                    ):
                        continue

                    layer[
                        key
                    ] = value


                # -----------------------------------------
                # LOAD IMAGE
                # -----------------------------------------

                image_path = (
                    item.get(
                        "image_path"
                    )
                )


                if (
                    image_path
                    and image_path
                    in archive.namelist()
                ):

                    layer[
                        "image"
                    ] = (
                        load_zip_image(
                            archive,
                            image_path
                        ).convert(
                            "RGBA"
                        )
                    )


                # -----------------------------------------
                # LOAD MASK
                # -----------------------------------------

                mask_path = (
                    item.get(
                        "mask_path"
                    )
                )


                if (
                    mask_path
                    and mask_path
                    in archive.namelist()
                ):

                    layer[
                        "mask"
                    ] = (
                        load_zip_mask(
                            archive,
                            mask_path
                        )
                    )


                loaded_layers.append(
                    layer
                )


            loaded_groups[
                group_name
            ] = loaded_layers


    return {
        "manifest":
            manifest,

        "original_image":
            original_image,

        "edited_image":
            edited_image,

        "layer_groups":
            loaded_groups,

        "settings":
            manifest.get(
                "settings",
                {}
            ),

        "original_filename":
            manifest.get(
                "original_filename",
                "image"
            )
    }


# =========================================================
# PROJECT INFORMATION
# =========================================================

def get_project_info(
    project_bytes
):

    project_buffer = io.BytesIO(
        project_bytes
    )


    with zipfile.ZipFile(
        project_buffer,
        mode="r"
    ) as archive:

        if (
            "manifest.json"
            not in archive.namelist()
        ):

            raise ValueError(
                "Invalid AI Image Studio project."
            )


        manifest = json.loads(
            archive.read(
                "manifest.json"
            ).decode(
                "utf-8"
            )
        )


    layer_groups = (
        manifest.get(
            "layer_groups",
            {}
        )
    )


    total_layers = sum(
        len(layers)
        for layers
        in layer_groups.values()
    )


    return {
        "version":
            manifest.get(
                "version"
            ),

        "original_filename":
            manifest.get(
                "original_filename"
            ),

        "original_size":
            manifest.get(
                "original_size"
            ),

        "group_count":
            len(
                layer_groups
            ),

        "total_layers":
            total_layers
    }