import os
import json
import time
import hashlib


# =========================================================
# CONFIG
# =========================================================

RECOVERY_FOLDER = ".recovery"


# =========================================================
# CREATE RECOVERY DIRECTORY
# =========================================================

def ensure_recovery_folder(
    base_directory=".",
):

    recovery_path = os.path.join(
        base_directory,
        RECOVERY_FOLDER,
    )

    os.makedirs(
        recovery_path,
        exist_ok=True,
    )

    return recovery_path


# =========================================================
# SAFE FILE NAME
# =========================================================

def safe_recovery_name(
    project_name,
):

    project_name = str(
        project_name
        or
        "AI_Image_Studio"
    )

    safe_name = ""

    for character in project_name:

        if (
            character.isalnum()
            or character in (
                "_",
                "-",
            )
        ):

            safe_name += character

        else:

            safe_name += "_"

    safe_name = (
        safe_name.strip("_")
    )

    if not safe_name:

        safe_name = (
            "AI_Image_Studio"
        )

    return safe_name


# =========================================================
# HASH BYTES
# =========================================================

def calculate_bytes_hash(
    data,
):

    if data is None:

        return None

    if not isinstance(
        data,
        bytes,
    ):

        raise ValueError(
            "Recovery data must be bytes."
        )

    return hashlib.sha256(
        data
    ).hexdigest()


# =========================================================
# RECOVERY PATHS
# =========================================================

def get_recovery_paths(
    project_name,
    base_directory=".",
):

    recovery_folder = (
        ensure_recovery_folder(
            base_directory
        )
    )

    safe_name = (
        safe_recovery_name(
            project_name
        )
    )

    recovery_file = os.path.join(
        recovery_folder,
        f"{safe_name}.aistudio.recovery",
    )

    metadata_file = os.path.join(
        recovery_folder,
        f"{safe_name}.json",
    )

    return (
        recovery_file,
        metadata_file,
    )


# =========================================================
# SAVE RECOVERY
# =========================================================

def save_recovery(
    project_name,
    project_bytes,
    base_directory=".",
    metadata=None,
):

    if not isinstance(
        project_bytes,
        bytes,
    ):

        raise ValueError(
            "project_bytes must be bytes."
        )

    (
        recovery_file,
        metadata_file,
    ) = get_recovery_paths(
        project_name,
        base_directory,
    )

    # Atomic-ish temporary write
    temporary_file = (
        recovery_file
        +
        ".tmp"
    )

    with open(
        temporary_file,
        "wb",
    ) as file:

        file.write(
            project_bytes
        )

    os.replace(
        temporary_file,
        recovery_file,
    )

    recovery_metadata = {
        "project_name":
            project_name,

        "saved_at":
            time.time(),

        "size_bytes":
            len(
                project_bytes
            ),

        "sha256":
            calculate_bytes_hash(
                project_bytes
            ),
    }

    if isinstance(
        metadata,
        dict,
    ):

        recovery_metadata.update(
            metadata
        )

    temporary_metadata = (
        metadata_file
        +
        ".tmp"
    )

    with open(
        temporary_metadata,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            recovery_metadata,
            file,
            indent=2,
        )

    os.replace(
        temporary_metadata,
        metadata_file,
    )

    return {
        "success":
            True,

        "recovery_file":
            recovery_file,

        "metadata_file":
            metadata_file,

        "metadata":
            recovery_metadata,
    }


# =========================================================
# LOAD RECOVERY
# =========================================================

def load_recovery(
    project_name,
    base_directory=".",
):

    (
        recovery_file,
        metadata_file,
    ) = get_recovery_paths(
        project_name,
        base_directory,
    )

    if not os.path.exists(
        recovery_file
    ):

        return None

    with open(
        recovery_file,
        "rb",
    ) as file:

        project_bytes = (
            file.read()
        )

    metadata = {}

    if os.path.exists(
        metadata_file
    ):

        try:

            with open(
                metadata_file,
                "r",
                encoding="utf-8",
            ) as file:

                metadata = (
                    json.load(
                        file
                    )
                )

        except Exception:

            metadata = {}

    return {
        "project_bytes":
            project_bytes,

        "metadata":
            metadata,

        "recovery_file":
            recovery_file,

        "metadata_file":
            metadata_file,
    }


# =========================================================
# CHECK RECOVERY
# =========================================================

def recovery_exists(
    project_name,
    base_directory=".",
):

    (
        recovery_file,
        _,
    ) = get_recovery_paths(
        project_name,
        base_directory,
    )

    return os.path.exists(
        recovery_file
    )


# =========================================================
# DELETE RECOVERY
# =========================================================

def delete_recovery(
    project_name,
    base_directory=".",
):

    (
        recovery_file,
        metadata_file,
    ) = get_recovery_paths(
        project_name,
        base_directory,
    )

    deleted = False

    for path in (
        recovery_file,
        metadata_file,
    ):

        if os.path.exists(
            path
        ):

            os.remove(
                path
            )

            deleted = True

    return deleted


# =========================================================
# RECOVERY INFO
# =========================================================

def get_recovery_info(
    project_name,
    base_directory=".",
):

    result = load_recovery(
        project_name,
        base_directory,
    )

    if result is None:

        return None

    metadata = (
        result.get(
            "metadata",
            {},
        )
    )

    return {
        "project_name":
            metadata.get(
                "project_name",
                project_name,
            ),

        "saved_at":
            metadata.get(
                "saved_at"
            ),

        "size_bytes":
            metadata.get(
                "size_bytes",
                len(
                    result[
                        "project_bytes"
                    ]
                ),
            ),

        "sha256":
            metadata.get(
                "sha256"
            ),

        "recovery_file":
            result[
                "recovery_file"
            ],
    }