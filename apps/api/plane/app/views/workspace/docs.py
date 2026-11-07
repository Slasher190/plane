# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os
from urllib.parse import urlencode

from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.base import BaseAPIView


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
        return HttpResponseRedirect(f"{base}/oauth/login?" + urlencode({"provider": "OIDC", "redirect_uri": "/"}))
