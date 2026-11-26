"""Secure Temporary File Management for AI Resume Analyzer (Issue #36).

Provides:
- Dedicated temporary directory management with safe permissions.
- Unique, non-colliding filename generation without personal information.
- Safe removal with retry logic and garbage collection to release OS file locks (Windows).
- Automatic cleanup for both successful and failed analysis requests.
- Stale file cleanup to purge orphaned temporary documents.
"""

import gc
import os
import tempfile
import time
import uuid
from typing import Optional
from werkzeug.datastructures import FileStorage


DEFAULT_TEMP_DIR = os.path.join(tempfile.gettempdir(), "ai_resume_analyzer_uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def get_temp_upload_dir(base_dir: Optional[str] = None) -> str:
    """Return the dedicated secure temporary upload directory path, creating it if needed.

    Ensures the directory exists with restricted permissions (0o700).
    """
    directory = base_dir or os.environ.get("RESUME_UPLOAD_FOLDER") or DEFAULT_TEMP_DIR
    os.makedirs(directory, mode=0o700, exist_ok=True)
    return os.path.abspath(directory)


def generate_secure_filename(extension: str) -> str:
    """Generate a cryptographically secure, unguessable filename for uploads.

    Avoids leaking personal information (e.g. candidate names present in the
    original filename) by using a clean prefix and a UUID4 hex token.
    """
    ext = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension '{ext}'. Only PDF and DOCX are allowed.")

    unique_token = uuid.uuid4().hex
    return f"resume_{unique_token}{ext}"


def save_temp_upload(
    file_storage: FileStorage,
    directory: Optional[str] = None,
    extension: Optional[str] = None,
) -> str:
    """Save an incoming Flask FileStorage object into the dedicated temporary directory.

    Returns the absolute path to the saved temporary file.
    """
    target_dir = get_temp_upload_dir(directory)
    if extension is None:
        filename = file_storage.filename or ""
        extension = os.path.splitext(filename)[1].lower()

    secure_name = generate_secure_filename(extension)
    filepath = os.path.join(target_dir, secure_name)

    file_storage.save(filepath)
    return filepath


def remove_temp_file(
    filepath: Optional[str],
    max_retries: int = 3,
    retry_delay: float = 0.05,
) -> bool:
    """Safely remove a temporary file with retry logic for Windows file locks.

    Triggers garbage collection if needed to release lingering file handles
    (e.g., from pypdf or python-docx reader streams).

    Returns:
        True if the file was deleted or does not exist, False otherwise.
    """
    if not filepath or not os.path.exists(filepath):
        return True

    for attempt in range(max_retries):
        try:
            os.remove(filepath)
            return True
        except (PermissionError, OSError):
            # Run garbage collector to release unclosed handles on Windows
            gc.collect()
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

    # Final attempt after brief delay
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
    except OSError:
        return False
    return True


def cleanup_stale_temp_files(
    directory: Optional[str] = None,
    max_age_seconds: int = 3600,
) -> int:
    """Remove orphaned temporary files in the upload directory older than max_age_seconds.

    Returns the number of files cleaned up.
    """
    target_dir = directory or get_temp_upload_dir()
    if not os.path.exists(target_dir):
        return 0

    removed_count = 0
    now = time.time()

    try:
        entries = os.listdir(target_dir)
    except OSError:
        return 0

    for entry in entries:
        full_path = os.path.join(target_dir, entry)
        if not os.path.isfile(full_path):
            continue

        try:
            file_age = now - os.path.getmtime(full_path)
            if file_age >= max_age_seconds:
                if remove_temp_file(full_path):
                    removed_count += 1
        except OSError:
            continue

    return removed_count
