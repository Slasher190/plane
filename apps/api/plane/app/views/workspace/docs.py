# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os
import uuid
from urllib.parse import urlencode, urlparse

from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.base import BaseAPIView
from plane.db.models import AffinePageLink, AffineProjectLink, AffineWorkspaceLink


def docs_enabled() -> bool:
    return os.environ.get("AFFINE_ENABLED", "1") == "1" and bool(os.environ.get("AFFINE_PUBLIC_URL", ""))


class WorkspaceDocsSSOEndpoint(BaseAPIView):
    """Send an authenticated Oneplace user into Oneplace Docs (AFFiNE), signed in.

    AFFiNE starts its OIDC login against Oneplace (/auth/oidc/); the user already
    has a Oneplace session, so it completes without a prompt.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def get(self, request, slug):
        if not docs_enabled():
            return Response({"error": "Oneplace Docs is not enabled"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        base = os.environ["AFFINE_PUBLIC_URL"].rstrip("/")
        # Land on Docs home; with a sub-path deployment (/docs) that is "/docs/", not the site root.
        base_path = (urlparse(base).path or "").rstrip("/")
        target = base_path + "/"
        # ?page=<id> → the migrated doc; ?project=<id> → that project's "Pages" index doc.
        def as_uuid(value):
            try:
                return str(uuid.UUID(str(value))) if value else None
            except ValueError:
                return None

        page_id, project_id = as_uuid(request.GET.get("page")), as_uuid(request.GET.get("project"))
        page_link = AffinePageLink.objects.filter(page_id=page_id, page__workspace__slug=slug).first() if page_id else None
        project_link = (
            AffineProjectLink.objects.filter(project_id=project_id, project__workspace__slug=slug).first()
            if project_id
            else None
        )
        if page_link:
            target = f"{base_path}/workspace/{page_link.affine_workspace_id}/{page_link.affine_doc_id}"
        elif project_link:
            target = f"{base_path}/workspace/{project_link.affine_workspace_id}/{project_link.index_doc_id}"
        else:
            ws_link = AffineWorkspaceLink.objects.filter(workspace__slug=slug).first()
            if ws_link:
                target = f"{base_path}/workspace/{ws_link.affine_workspace_id}/all"
        return HttpResponseRedirect(f"{base}/oauth/login?" + urlencode({"provider": "OIDC", "redirect_uri": target}))
