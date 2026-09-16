import copy

from PIL import Image


# =========================================================
# VALIDATE IMAGE
# =========================================================

def validate_image(image):

    if not isinstance(
        image,
        Image.Image,
    ):
        raise ValueError(
            "Layer image must be a PIL Image."
        )

    return image


# =========================================================
# DUPLICATE LAYER
# =========================================================

def duplicate_layer(layer):

    if not isinstance(
        layer,
        dict,
    ):
        raise ValueError(
            "Layer must be a dictionary."
        )

    duplicated = copy.deepcopy(
        layer
    )

    if isinstance(
        layer.get("image"),
        Image.Image,
    ):

        duplicated["image"] = (
            layer["image"].copy()
        )

    duplicated.pop(
        "_uid",
        None,
    )

    old_name = (
        layer.get(
            "_saved_name"
        )
        or
        layer.get(
            "name"
        )
        or
        "Layer"
    )

    duplicated[
        "name"
    ] = (
        f"{old_name} Copy"
    )

    duplicated[
        "_saved_name"
    ] = (
        f"{old_name} Copy"
    )

    return duplicated


# =========================================================
# ROTATE
# =========================================================

def rotate_layer_image(
    image,
    angle,
):

    image = validate_image(
        image
    ).convert(
        "RGBA"
    )

    return image.rotate(
        angle,
        resample=Image.Resampling.BICUBIC,
        expand=False,
        fillcolor=(
            0,
            0,
            0,
            0,
        ),
    )


# =========================================================
# ROTATE LEFT
# =========================================================

def rotate_left(
    image,
):

    return rotate_layer_image(
        image,
        90,
    )


# =========================================================
# ROTATE RIGHT
# =========================================================

def rotate_right(
    image,
):

    return rotate_layer_image(
        image,
        -90,
    )


# =========================================================
# FLIP HORIZONTAL
# =========================================================

def flip_horizontal(
    image,
):

    image = validate_image(
        image
    ).convert(
        "RGBA"
    )

    return image.transpose(
        Image.Transpose.FLIP_LEFT_RIGHT
    )


# =========================================================
# FLIP VERTICAL
# =========================================================

def flip_vertical(
    image,
):

    image = validate_image(
        image
    ).convert(
        "RGBA"
    )

    return image.transpose(
        Image.Transpose.FLIP_TOP_BOTTOM
    )


# =========================================================
# MOVE / TRANSLATE
# =========================================================

def move_layer_image(
    image,
    offset_x=0,
    offset_y=0,
):

    image = validate_image(
        image
    ).convert(
        "RGBA"
    )

    width, height = (
        image.size
    )

    canvas = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        (
            0,
            0,
            0,
            0,
        ),
    )

    canvas.alpha_composite(
        image,
        (
            int(
                offset_x
            ),
            int(
                offset_y
            ),
        ),
    )

    return canvas


# =========================================================
# SCALE LAYER AROUND CENTER
# =========================================================

def scale_layer_image(
    image,
    scale_percent=100,
):

    image = validate_image(
        image
    ).convert(
        "RGBA"
    )

    scale_percent = max(
        1,
        min(
            int(
                scale_percent
            ),
            500,
        ),
    )

    original_width, original_height = (
        image.size
    )

    scale = (
        scale_percent
        /
        100.0
    )

    new_width = max(
        1,
        int(
            original_width
            *
            scale
        ),
    )

    new_height = max(
        1,
        int(
            original_height
            *
            scale
        ),
    )

    resized = image.resize(
        (
            new_width,
            new_height,
        ),
        Image.Resampling.LANCZOS,
    )

    canvas = Image.new(
        "RGBA",
        (
            original_width,
            original_height,
        ),
        (
            0,
            0,
            0,
            0,
        ),
    )

    x = (
        original_width
        -
        new_width
    ) // 2

    y = (
        original_height
        -
        new_height
    ) // 2

    canvas.alpha_composite(
        resized,
        (
            x,
            y,
        ),
    )

    return canvas


# =========================================================
# APPLY TRANSFORM TO LAYER DICTIONARY
# =========================================================

def transform_layer(
    layer,
    operation,
    **kwargs,
):

    if not isinstance(
        layer,
        dict,
    ):
        raise ValueError(
            "Layer must be a dictionary."
        )

    image = (
        layer.get(
            "image"
        )
    )

    validate_image(
        image
    )

    transformed = (
        layer.copy()
    )

    operation = str(
        operation
    ).lower().strip()


    if operation == "rotate_left":

        transformed[
            "image"
        ] = rotate_left(
            image
        )


    elif operation == "rotate_right":

        transformed[
            "image"
        ] = rotate_right(
            image
        )


    elif operation == "flip_horizontal":

        transformed[
            "image"
        ] = flip_horizontal(
            image
        )


    elif operation == "flip_vertical":

        transformed[
            "image"
        ] = flip_vertical(
            image
        )


    elif operation == "move":

        transformed[
            "image"
        ] = move_layer_image(
            image,

            offset_x=kwargs.get(
                "offset_x",
                0,
            ),

            offset_y=kwargs.get(
                "offset_y",
                0,
            ),
        )


    elif operation == "scale":

        transformed[
            "image"
        ] = scale_layer_image(
            image,

            scale_percent=kwargs.get(
                "scale_percent",
                100,
            ),
        )


    else:

        raise ValueError(
            f"Unknown layer operation: "
            f"{operation}"
        )

    return transformed