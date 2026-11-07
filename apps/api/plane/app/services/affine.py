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
