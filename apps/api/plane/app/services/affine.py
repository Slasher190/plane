# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Client for the Oneplace Docs (AFFiNE) internal import API.

The API lives in the Oneplace build of AFFiNE (core/oneplace-import), is reached
over the Docker network (AFFINE_INTERNAL_URL, e.g. http://affine:3010/docs) and
needs ONEPLACE_IMPORT_SECRET. It isn't reachable from outside.
"""

import os
import secrets
import string
from typing import List, Optional

import requests

ID_ALPHABET = string.ascii_letters + string.digits + "_-"
BASE62 = string.digits + string.ascii_uppercase + string.ascii_lowercase


def new_doc_id() -> str:
    """AFFiNE-style 21-char id (nanoid alphabet)."""
    return "".join(secrets.choice(ID_ALPHABET) for _ in range(21))


def order_key(i: int) -> str:
    """Fractional-index style sort keys: a0..az, then b00.. (base62)."""
    if i < 62:
        return "a" + BASE62[i]
    i -= 62
    return "b" + BASE62[(i // 62) % 62] + BASE62[i % 62]


def public_url() -> str:
    return os.environ.get("AFFINE_PUBLIC_URL", "").rstrip("/")


def doc_url(workspace_id: str, doc_id: str) -> str:
    return f"{public_url()}/workspace/{workspace_id}/{doc_id}"


class AffineImportClient:
    def __init__(self, base_url: Optional[str] = None, secret: Optional[str] = None, timeout: int = 60):
        self.base_url = (base_url or os.environ.get("AFFINE_INTERNAL_URL", "")).rstrip("/")
        self.secret = secret or os.environ.get("ONEPLACE_IMPORT_SECRET", "")
        self.timeout = timeout
        if not self.base_url or not self.secret:
            raise RuntimeError("AFFINE_INTERNAL_URL and ONEPLACE_IMPORT_SECRET must be set")

    def _req(self, method: str, path: str, **kwargs):
        resp = requests.request(
            method,
            f"{self.base_url}/api/oneplace/import{path}",
            headers={"x-oneplace-import-secret": self.secret},
            timeout=self.timeout,
            **kwargs,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"AFFiNE import API {method} {path} → {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def user_exists(self, email: str) -> bool:
        return bool(self._req("GET", "/users", params={"email": email}).get("exists"))

    def owned_workspaces(self, owner_email: str) -> List[dict]:
        return self._req("GET", "/workspaces", params={"ownerEmail": owner_email}).get("workspaces", [])

    def doc_exists(self, workspace_id: str, doc_id: str) -> bool:
        return bool(self._req("GET", f"/workspaces/{workspace_id}/docs/{doc_id}").get("exists"))

    def create_doc(self, workspace_id: str, doc_id: str, title: str, markdown: str,
                   editor_email: Optional[str] = None, create_date_ms: Optional[int] = None) -> dict:
        body = {"docId": doc_id, "title": title, "markdown": markdown}
        if editor_email:
            body["editorEmail"] = editor_email
        if create_date_ms:
            body["createDate"] = create_date_ms
        return self._req("POST", f"/workspaces/{workspace_id}/docs", json=body)

    def upsert_folders(self, workspace_id: str, nodes: List[dict]) -> dict:
        return self._req("POST", f"/workspaces/{workspace_id}/folders", json={"nodes": nodes})


# Providers whose API is OpenAI-compatible (AFFiNE BYOK "openai_compatible" endpoint).
OPENAI_COMPATIBLE_PROVIDERS = {"ollama", "openrouter", "litellm", "azure", "openai"}


def docs_ai_settings():
    """God-mode → AI settings as used by Oneplace Docs: (provider, base_url, api_key, [models])."""
    from plane.license.utils.instance_value import get_configuration_value

    provider, base_url, api_key, model, fallbacks = get_configuration_value(
        [
            {"key": "LLM_PROVIDER", "default": os.environ.get("LLM_PROVIDER", "")},
            {"key": "LLM_BASE_URL", "default": os.environ.get("LLM_BASE_URL", "")},
            {"key": "LLM_API_KEY", "default": os.environ.get("LLM_API_KEY", "")},
            {"key": "LLM_MODEL", "default": os.environ.get("LLM_MODEL", "")},
            {"key": "LLM_FALLBACK_MODELS", "default": os.environ.get("LLM_FALLBACK_MODELS", "")},
        ]
    )
    if (provider or "").lower() == "ollama" and not base_url:
        base_url = os.environ.get("OLLAMA_BASE_URL", "https://ollama.com/v1")
    models = [m.strip() for m in [model or ""] + (fallbacks or "").split(",") if m and m.strip()]
    return (provider or "").lower(), (base_url or "").strip(), api_key or "", list(dict.fromkeys(models))


def sync_docs_ai():
    """Push god-mode AI settings to every linked Oneplace Docs workspace.

    Returns a list of (affine_workspace_id, result-or-error) for reporting.
    """
    from plane.db.models import AffineWorkspaceLink

    provider, base_url, api_key, models = docs_ai_settings()
    if provider not in OPENAI_COMPATIBLE_PROVIDERS:
        return [("-", f"skipped: provider {provider or 'unset'} is not OpenAI-compatible")]
    if not base_url or not models:
        return [("-", "skipped: base URL or model missing in god-mode → AI")]
    client = AffineImportClient()
    results = []
    for link in AffineWorkspaceLink.objects.all():
        try:
            res = client._req(
                "POST",
                f"/workspaces/{link.affine_workspace_id}/ai",
                json={"baseUrl": base_url, "apiKey": api_key, "models": models},
            )
            results.append((link.affine_workspace_id, res))
        except Exception as exc:  # report, never raise into the god-mode save
            results.append((link.affine_workspace_id, f"error: {exc}"))
    return results
