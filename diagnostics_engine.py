import os
import json
import time
import traceback
from datetime import datetime


LOG_FOLDER = "logs"
ERROR_LOG_FILE = "ai_image_studio_errors.jsonl"


def ensure_log_folder(base_directory="."):
    path = os.path.join(
        base_directory,
        LOG_FOLDER,
    )

    os.makedirs(
        path,
        exist_ok=True,
    )

    return path


def get_error_log_path(base_directory="."):
    folder = ensure_log_folder(
        base_directory
    )

    return os.path.join(
        folder,
        ERROR_LOG_FILE,
    )


def format_timestamp(timestamp=None):
    if timestamp is None:
        timestamp = time.time()

    return datetime.fromtimestamp(
        timestamp
    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def create_error_record(
    error,
    operation="Unknown Operation",
    context=None,
):
    return {
        "timestamp": time.time(),
        "datetime": format_timestamp(),
        "operation": str(operation),
        "error_type": type(error).__name__,
        "message": str(error),
        "context": (
            context
            if isinstance(context, dict)
            else {}
        ),
        "traceback": traceback.format_exc(),
    }


def log_error(
    error,
    operation="Unknown Operation",
    context=None,
    base_directory=".",
):
    record = create_error_record(
        error=error,
        operation=operation,
        context=context,
    )

    log_path = get_error_log_path(
        base_directory
    )

    with open(
        log_path,
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(
                record,
                ensure_ascii=False,
            )
            + "\n"
        )

    return record


def safe_error_message(
    error,
    operation="operation",
):
    error_type = type(error).__name__

    friendly_messages = {
        "MemoryError":
            "The image is too large for the available memory.",

        "FileNotFoundError":
            "A required file could not be found.",

        "PermissionError":
            "Windows blocked access to a required file or folder.",

        "ValueError":
            "The selected settings or input are not valid.",

        "ImportError":
            "A required Python package could not be loaded.",

        "ModuleNotFoundError":
            "A required Python package is missing.",
    }

    message = friendly_messages.get(
        error_type
    )

    if message is None:
        message = (
            f"The {operation} could not be completed."
        )

    return message


def handle_error(
    error,
    operation="operation",
    context=None,
    base_directory=".",
):
    try:
        record = log_error(
            error=error,
            operation=operation,
            context=context,
            base_directory=base_directory,
        )

    except Exception:
        record = {
            "error_type":
                type(error).__name__,

            "message":
                str(error),
        }

    return {
        "success": False,
        "title": f"{operation} failed",
        "user_message": safe_error_message(
            error,
            operation,
        ),
        "technical_message": str(error),
        "error_type": type(error).__name__,
        "record": record,
    }


def read_recent_errors(
    limit=20,
    base_directory=".",
):
    log_path = get_error_log_path(
        base_directory
    )

    if not os.path.exists(
        log_path
    ):
        return []

    records = []

    with open(
        log_path,
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                records.append(
                    json.loads(line)
                )
            except Exception:
                continue

    return records[
        -int(limit):
    ][::-1]


def clear_error_log(
    base_directory=".",
):
    log_path = get_error_log_path(
        base_directory
    )

    if os.path.exists(
        log_path
    ):
        os.remove(
            log_path
        )

        return True

    return False


def get_diagnostics_summary(
    base_directory=".",
):
    records = read_recent_errors(
        limit=1000,
        base_directory=base_directory,
    )

    error_types = {}

    for record in records:
        error_type = record.get(
            "error_type",
            "Unknown",
        )

        error_types[
            error_type
        ] = (
            error_types.get(
                error_type,
                0,
            )
            + 1
        )

    return {
        "total_errors": len(records),
        "error_types": error_types,
        "log_path": get_error_log_path(
            base_directory
        ),
    }