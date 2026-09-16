import copy
from PIL import Image


# =========================================================
# SAFE COPY
# =========================================================

def safe_copy_value(value):

    if isinstance(value, Image.Image):
        return value.copy()

    try:
        return copy.deepcopy(value)

    except Exception:
        return value


# =========================================================
# COPY LAYER
# =========================================================

def copy_layer(layer):

    if not isinstance(layer, dict):
        return safe_copy_value(layer)

    copied = {}

    for key, value in layer.items():

        copied[key] = safe_copy_value(
            value
        )

    return copied


# =========================================================
# COPY LAYER LIST
# =========================================================

def copy_layers(layers):

    if not layers:
        return []

    return [
        copy_layer(layer)
        for layer in layers
    ]


# =========================================================
# CREATE SNAPSHOT
# =========================================================

def create_layer_snapshot(
    layers,
    visibility,
    opacity,
    names,
):

    return {
        "layers":
            copy_layers(
                layers
            ),

        "visibility":
            list(
                visibility
            ),

        "opacity":
            list(
                opacity
            ),

        "names":
            list(
                names
            ),
    }


# =========================================================
# RESTORE SNAPSHOT
# =========================================================

def restore_layer_snapshot(
    snapshot,
):

    if not isinstance(
        snapshot,
        dict,
    ):

        raise ValueError(
            "Invalid history snapshot."
        )

    return {
        "layers":
            copy_layers(
                snapshot.get(
                    "layers",
                    [],
                )
            ),

        "visibility":
            list(
                snapshot.get(
                    "visibility",
                    [],
                )
            ),

        "opacity":
            list(
                snapshot.get(
                    "opacity",
                    [],
                )
            ),

        "names":
            list(
                snapshot.get(
                    "names",
                    [],
                )
            ),
    }


# =========================================================
# PUSH HISTORY
# =========================================================

def push_history(
    undo_stack,
    snapshot,
    max_history=30,
):

    undo_stack.append(
        snapshot
    )

    if (
        len(
            undo_stack
        )
        >
        max_history
    ):

        del undo_stack[
            0
        ]

    return undo_stack


# =========================================================
# UNDO
# =========================================================

def undo_history(
    undo_stack,
    redo_stack,
    current_snapshot,
):

    if not undo_stack:

        return {
            "success": False,
            "snapshot": None,
            "undo_stack": undo_stack,
            "redo_stack": redo_stack,
        }

    previous_snapshot = (
        undo_stack.pop()
    )

    redo_stack.append(
        current_snapshot
    )

    return {
        "success": True,

        "snapshot":
            restore_layer_snapshot(
                previous_snapshot
            ),

        "undo_stack":
            undo_stack,

        "redo_stack":
            redo_stack,
    }


# =========================================================
# REDO
# =========================================================

def redo_history(
    undo_stack,
    redo_stack,
    current_snapshot,
):

    if not redo_stack:

        return {
            "success": False,
            "snapshot": None,
            "undo_stack": undo_stack,
            "redo_stack": redo_stack,
        }

    next_snapshot = (
        redo_stack.pop()
    )

    undo_stack.append(
        current_snapshot
    )

    return {
        "success": True,

        "snapshot":
            restore_layer_snapshot(
                next_snapshot
            ),

        "undo_stack":
            undo_stack,

        "redo_stack":
            redo_stack,
    }


# =========================================================
# CLEAR HISTORY
# =========================================================

def clear_history():

    return {
        "undo_stack": [],
        "redo_stack": [],
    }