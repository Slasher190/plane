# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.base import BaseAPIView
from plane.app.services.rocketchat import rocketchat_enabled, sso_redirect_url, sync_workspace
from plane.db.models import Workspace
from plane.db.models.rocketchat import RocketChatWorkspaceLink
from plane.utils.exception_logger import log_exception


class WorkspaceChatSSOEndpoint(BaseAPIView):
    """Redirect an authenticated Oneplace user into Rocket.Chat under /chat."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def get(self, request, slug):
        if not rocketchat_enabled():
            return Response(
                {"error": "Oneplace Chat is not enabled"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            workspace = Workspace.objects.get(slug=slug)
            url = sso_redirect_url(request.user, workspace)
            return HttpResponseRedirect(url)
        except Exception as exc:
            log_exception(exc)
            return Response(
                {"error": "Unable to open Oneplace Chat. Check Rocket.Chat admin credentials."},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class WorkspaceChatStatusEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        link = RocketChatWorkspaceLink.objects.filter(workspace=workspace).first()
        return Response(
            {
                "enabled": rocketchat_enabled(),
                "synced": bool(link),
                "rc_team_id": link.rc_team_id if link else None,
                "rc_team_name": link.rc_team_name if link else None,
            },
            status=status.HTTP_200_OK,
        )

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        """Force re-sync workspace members into Rocket.Chat."""
        if not rocketchat_enabled():
            return Response({"error": "Oneplace Chat is not enabled"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        workspace = Workspace.objects.get(slug=slug)
        try:
            sync_workspace(workspace, owner=request.user)
            link = RocketChatWorkspaceLink.objects.filter(workspace=workspace).first()
            return Response(
                {
                    "synced": bool(link),
                    "rc_team_id": link.rc_team_id if link else None,
                    "rc_team_name": link.rc_team_name if link else None,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            log_exception(exc)
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
