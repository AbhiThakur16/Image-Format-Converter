from PIL import Image


# =========================================================
# LOCK STATE
# =========================================================

def is_layer_locked(
    lock_states,
    uid,
):

    return bool(
        lock_states.get(
            uid,
            False,
        )
    )


def set_layer_locked(
    lock_states,
    uid,
    locked,
):

    lock_states[
        uid
    ] = bool(
        locked
    )

    return lock_states


def toggle_layer_lock(
    lock_states,
    uid,
):

    current = bool(
        lock_states.get(
            uid,
            False,
        )
    )

    lock_states[
        uid
    ] = not current

    return lock_states


# =========================================================
# ORIGINAL LAYER IMAGE
# =========================================================

def remember_original_layer(
    original_images,
    uid,
    image,
):

    if not isinstance(
        image,
        Image.Image,
    ):

        return original_images

    if uid not in original_images:

        original_images[
            uid
        ] = image.copy()

    return original_images


def get_original_layer(
    original_images,
    uid,
):

    image = (
        original_images.get(
            uid
        )
    )

    if isinstance(
        image,
        Image.Image,
    ):

        return image.copy()

    return None


# =========================================================
# RESET TRANSFORM
# =========================================================

def reset_layer_transform(
    layer,
    original_images,
    uid,
):

    if not isinstance(
        layer,
        dict,
    ):

        raise ValueError(
            "Layer must be a dictionary."
        )

    original = (
        get_original_layer(
            original_images,
            uid,
        )
    )

    if original is None:

        raise ValueError(
            "Original layer state is not available."
        )

    restored = (
        layer.copy()
    )

    restored[
        "image"
    ] = original

    return restored


# =========================================================
# CLEAN REMOVED LAYER STATE
# =========================================================

def remove_layer_state(
    lock_states,
    original_images,
    uid,
):

    lock_states.pop(
        uid,
        None,
    )

    original_images.pop(
        uid,
        None,
    )

    return (
        lock_states,
        original_images,
    )


# =========================================================
# DUPLICATE STATE
# =========================================================

def duplicate_layer_state(
    lock_states,
    original_images,
    source_uid,
    new_uid,
    new_image,
):

    # Duplicate starts unlocked
    lock_states[
        new_uid
    ] = False

    if isinstance(
        new_image,
        Image.Image,
    ):

        original_images[
            new_uid
        ] = (
            new_image.copy()
        )

    elif (
        source_uid
        in original_images
    ):

        original_images[
            new_uid
        ] = (
            original_images[
                source_uid
            ].copy()
        )

    return (
        lock_states,
        original_images,
    )