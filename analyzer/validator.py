"""Backend input validation and request error handling (Issue #60).

Provides request validation, safe error formatting, and error handlers to ensure:
- Required request fields and files are safely validated.
- Malformed inputs or missing form data are caught with meaningful messages.
- Appropriate HTTP status codes are attached.
- Consistent JSON error responses are returned for API clients.
- Internal server details and stack traces are never exposed to clients.
"""

import json
import logging
import os
from typing import Any, Dict, Optional, Tuple
from flask import Request, jsonify
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_JOB_DESCRIPTION_LENGTH = 20000


def wants_json_response(request: Request) -> bool:
    """Determine whether the client prefers a JSON response.

    Returns True if:
    - Path starts with /api/
    - Request Content-Type is application/json
    - Request Accept header explicitly requests application/json
    - Request has X-Requested-With: XMLHttpRequest
    """
    if request.path.startswith("/api/"):
        return True
    if request.is_json:
        return True
    accept = request.headers.get("Accept", "").lower()
    if "application/json" in accept and "text/html" not in accept:
        return True
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    return False


def format_error_response(
    message: str,
    status_code: int = 400,
    error_code: str = "BAD_REQUEST",
    request: Optional[Request] = None,
    legacy_200_for_html: bool = False,
) -> Tuple[Any, int]:
    """Format an error response appropriately for API clients vs browser forms.

    Args:
        message: Human-readable error message.
        status_code: HTTP status code to return.
        error_code: Machine-readable error code.
        request: The active Flask request.
        legacy_200_for_html: If True and client is not requesting JSON, return 200
                             to preserve existing browser/test contract.

    Returns:
        Tuple of (response_body, http_status_code).
    """
    is_api = request is not None and wants_json_response(request)

    if is_api:
        return (
            jsonify({
                "status": "error",
                "error": message,
                "code": error_code,
                "status_code": status_code,
            }),
            status_code,
        )

    # For traditional browser form submissions
    http_status = 200 if legacy_200_for_html else status_code
    return message, http_status


def validate_resume_upload(
    request: Request,
) -> Tuple[bool, Optional[FileStorage], Optional[str], Optional[Tuple[Any, int]]]:
    """Validate incoming resume upload request.

    Returns:
        (is_valid, file_storage, extension, error_response)
        If valid: (True, file_storage, extension, None)
        If invalid: (False, None, None, (response, status_code))
    """
    if "resume" not in request.files:
        error_resp = format_error_response(
            message="Please upload a resume.",
            status_code=400,
            error_code="MISSING_FILE",
            request=request,
            legacy_200_for_html=True,
        )
        return False, None, None, error_resp

    file = request.files["resume"]

    if not file.filename or not file.filename.strip():
        error_resp = format_error_response(
            message="No file selected.",
            status_code=400,
            error_code="EMPTY_FILENAME",
            request=request,
            legacy_200_for_html=True,
        )
        return False, None, None, error_resp

    original_filename = file.filename
    extension = os.path.splitext(original_filename)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        error_resp = format_error_response(
            message="Only PDF and DOCX files are allowed.",
            status_code=415 if wants_json_response(request) else 400,
            error_code="UNSUPPORTED_MEDIA_TYPE",
            request=request,
            legacy_200_for_html=True,
        )
        return False, None, None, error_resp

    sanitized = secure_filename(original_filename)
    if not sanitized:
        error_resp = format_error_response(
            message="Invalid filename.",
            status_code=400,
            error_code="INVALID_FILENAME",
            request=request,
            legacy_200_for_html=True,
        )
        return False, None, None, error_resp

    return True, file, extension, None


def validate_report_download(
    request: Request,
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Tuple[Any, int]]]:
    """Validate incoming report download request.

    Returns:
        (is_valid, report_data_dict, error_response)
    """
    raw_report = None

    if request.is_json and request.json:
        raw_report = request.json.get("report") or request.json
    elif "report" in request.form:
        raw_report = request.form["report"]

    if not raw_report:
        error_resp = format_error_response(
            message="Unable to create the report. Please analyze your resume again.",
            status_code=400,
            error_code="MISSING_REPORT_DATA",
            request=request,
            legacy_200_for_html=False,
        )
        return False, None, error_resp

    # Parse JSON if passed as string
    if isinstance(raw_report, str):
        try:
            report_dict = json.loads(raw_report)
        except (ValueError, json.JSONDecodeError):
            error_resp = format_error_response(
                message="Unable to create the report. Please analyze your resume again.",
                status_code=400,
                error_code="MALFORMED_JSON",
                request=request,
                legacy_200_for_html=False,
            )
            return False, None, error_resp
    elif isinstance(raw_report, dict):
        report_dict = raw_report
    else:
        error_resp = format_error_response(
            message="Unable to create the report. Please analyze your resume again.",
            status_code=400,
            error_code="INVALID_DATA_FORMAT",
            request=request,
            legacy_200_for_html=False,
        )
        return False, None, error_resp

    if not isinstance(report_dict, dict):
        error_resp = format_error_response(
            message="Unable to create the report. Please analyze your resume again.",
            status_code=400,
            error_code="INVALID_REPORT_STRUCTURE",
            request=request,
            legacy_200_for_html=False,
        )
        return False, None, error_resp

    return True, report_dict, None
