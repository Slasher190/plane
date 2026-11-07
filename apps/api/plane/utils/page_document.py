# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Keep page editor documents (HTML + Yjs binary) in sync for API/MCP writes."""

from __future__ import annotations

import base64
import logging

import requests
from django.conf import settings

from plane.utils.url import normalize_url_path

logger = logging.getLogger("plane.api")


def sync_page_description_formats(description_html: str) -> dict:
    """
    Ask the live collaborative service to convert HTML into editor JSON/binary.

    Returns a dict that may include description_json and description_binary
    (raw bytes). Empty dict when live is unavailable or conversion fails.
    """
    live_url = getattr(settings, "LIVE_URL", None)
    if not live_url or not description_html:
        return {}

    url = normalize_url_path(f"{live_url}/convert-document/")
    try:
        response = requests.post(
            url,
            json={"description_html": description_html, "variant": "rich"},
            timeout=30,
        )
        if response.status_code != 200:
            logger.warning(
                "live convert-document failed status=%s body=%s",
                response.status_code,
                response.text[:300],
            )
            return {}
        payload = response.json()
        binary_b64 = payload.get("description_binary")
        result: dict = {}
        if payload.get("description_json") is not None:
            result["description_json"] = payload["description_json"]
        if binary_b64:
            result["description_binary"] = base64.b64decode(binary_b64)
        return result
    except requests.RequestException as exc:
        logger.warning("live convert-document request error: %s", exc)
        return {}


def apply_description_html(page, description_html: str, *, require_live: bool = False) -> tuple[bool, str | None]:
    """
    Write description_html onto a Page and refresh editor binary/json.

    When live conversion succeeds, binary is updated so open editor sessions
    stay consistent. When conversion fails, binary is cleared so the next
    editor open regenerates from HTML (see live Database extension).

    If require_live is True and conversion fails, returns (False, error) without
    mutating the page — matching Plane Cloud's 502 behaviour for wiki updates.
    """
    formats = sync_page_description_formats(description_html)
    if require_live and not formats:
        return False, "Collaborative document service could not convert the page content."

    page.description_html = description_html or "<p></p>"
    if formats.get("description_json") is not None:
        page.description_json = formats["description_json"]
    if formats.get("description_binary") is not None:
        page.description_binary = formats["description_binary"]
    else:
        # Force the editor to rebuild from HTML on next open.
        page.description_binary = None
    return True, None
