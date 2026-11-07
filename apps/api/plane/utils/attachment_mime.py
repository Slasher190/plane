# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Resolve attachment MIME types when the client omits or misreports them."""

from __future__ import annotations

import os

from django.conf import settings

# Extension → MIME for types that browsers / magic-byte detectors often miss
# (e.g. text/html, text/csv) or report inconsistently.
EXTENSION_MIME_MAP: dict[str, str] = {
    ".pdf": "application/pdf",
    ".html": "text/html",
    ".htm": "text/html",
    ".xhtml": "application/xhtml+xml",
    ".zip": "application/zip",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".json": "application/json",
    ".xml": "application/xml",
    ".css": "text/css",
    ".js": "text/javascript",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".avif": "image/avif",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".ico": "image/x-icon",
    ".rar": "application/x-rar-compressed",
    ".7z": "application/x-7z-compressed",
    ".tar": "application/x-tar",
    ".gz": "application/gzip",
}


def resolve_attachment_mime_type(filename: str | None, mime_type: str | None) -> str | None:
    """
    Return an allowed attachment MIME type, or None if the file cannot be accepted.

    Prefer a client-provided type when it is already allowlisted. Otherwise infer
    from the filename extension (needed for text/html, text/csv, etc. when the
    browser or magic-byte detector leaves type empty).
    """
    allowed = settings.ATTACHMENT_MIME_TYPES

    if mime_type and mime_type in allowed:
        return mime_type

    if filename:
        _, ext = os.path.splitext(filename)
        inferred = EXTENSION_MIME_MAP.get(ext.lower())
        if inferred and inferred in allowed:
            return inferred

    return None
