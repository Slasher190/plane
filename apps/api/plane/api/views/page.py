# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""API-key page endpoints used by plane-sdk / MCP (workspace + project scope)."""

from __future__ import annotations

from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db.models import Q, UUIDField, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.api.serializers.page import (
    PageAPISerializer,
    PageCreateAPISerializer,
    PageUpdateAPISerializer,
)
from plane.api.views.base import BaseAPIView
from plane.app.permissions import ProjectEntityPermission, WorkspaceMemberPermission
from plane.bgtasks.page_transaction_task import page_transaction
from plane.db.models import Page, Project, ProjectPage, Workspace
from plane.utils.page_document import apply_description_html


def _annotate_project_ids(qs):
    return qs.annotate(
        annotated_project_ids=Coalesce(
            ArrayAgg(
                "projects__id",
                distinct=True,
                filter=~Q(projects__id=None),
            ),
            Value([], output_field=ArrayField(UUIDField())),
        )
    )


def _page_response(page: Page) -> dict:
    page = _annotate_project_ids(Page.objects.filter(pk=page.pk)).get()
    return PageAPISerializer(page).data


class WorkspacePageListCreateAPIEndpoint(BaseAPIView):
    """GET/POST /api/v1/workspaces/{slug}/pages/"""

    permission_classes = [WorkspaceMemberPermission]
    use_read_replica = True

    def get_queryset(self):
        return (
            _annotate_project_ids(
                Page.objects.filter(
                    workspace__slug=self.kwargs.get("slug"),
                    is_global=True,
                ).filter(Q(owned_by=self.request.user) | Q(access=0))
            )
            .select_related("owned_by", "workspace", "parent")
            .order_by("-created_at")
            .distinct()
        )

    def get(self, request, slug):
        return self.paginate(
            request=request,
            queryset=self.get_queryset(),
            on_results=lambda pages: PageAPISerializer(pages, many=True).data,
            default_per_page=20,
        )

    def post(self, request, slug):
        serializer = PageCreateAPISerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        workspace = Workspace.objects.get(slug=slug)

        parent = None
        parent_id = data.get("parent_id")
        if parent_id:
            parent = Page.objects.filter(
                pk=parent_id, workspace_id=workspace.id, is_global=True
            ).first()
            if not parent:
                return Response({"error": "Parent page not found"}, status=status.HTTP_400_BAD_REQUEST)

        page = Page(
            workspace_id=workspace.id,
            name=data["name"],
            owned_by_id=request.user.id,
            access=data.get("access") if data.get("access") is not None else Page.PUBLIC_ACCESS,
            color=data.get("color") or "",
            is_locked=bool(data.get("is_locked") or False),
            external_id=data.get("external_id"),
            external_source=data.get("external_source"),
            parent=parent,
            is_global=True,
            view_props=data.get("view_props") or {"full_width": False},
            logo_props=data.get("logo_props") or {},
            created_by_id=request.user.id,
            updated_by_id=request.user.id,
        )

        # Best-effort live conversion; on failure binary is cleared so the
        # editor rebuilds from HTML (CE does not hard-fail creates on 502).
        apply_description_html(page, data["description_html"], require_live=False)

        page.save()
        page_transaction.delay(
            new_description_html=page.description_html,
            old_description_html=None,
            page_id=str(page.id),
        )
        return Response(_page_response(page), status=status.HTTP_201_CREATED)


class WorkspacePageDetailAPIEndpoint(BaseAPIView):
    """GET/PUT/DELETE /api/v1/workspaces/{slug}/pages/{page_id}/"""

    permission_classes = [WorkspaceMemberPermission]
    use_read_replica = True

    def _get_page(self, slug, page_id, user):
        return (
            _annotate_project_ids(
                Page.objects.filter(
                    pk=page_id,
                    workspace__slug=slug,
                    is_global=True,
                ).filter(Q(owned_by=user) | Q(access=0))
            )
            .select_related("owned_by", "workspace", "parent")
            .first()
        )

    def get(self, request, slug, page_id):
        page = self._get_page(slug, page_id, request.user)
        if not page:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(PageAPISerializer(page).data)

    def put(self, request, slug, page_id):
        page = self._get_page(slug, page_id, request.user)
        if not page:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)
        if page.is_locked:
            return Response({"error": "Page is locked"}, status=status.HTTP_400_BAD_REQUEST)
        if page.archived_at:
            return Response({"error": "Page is archived"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PageUpdateAPISerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        old_html = page.description_html

        for field in ("name", "access", "color", "is_locked", "external_id", "external_source", "view_props", "logo_props"):
            if field in data and data[field] is not None:
                setattr(page, field, data[field])

        if "description_html" in data:
            # Clear stale Yjs binary when live conversion fails so the editor
            # reloads from the new HTML instead of showing the old document.
            apply_description_html(page, data["description_html"], require_live=False)

        page.updated_by_id = request.user.id
        page.save()

        if "description_html" in data:
            page_transaction.delay(
                new_description_html=page.description_html,
                old_description_html=old_html,
                page_id=str(page.id),
            )

        return Response(_page_response(page))

    def delete(self, request, slug, page_id):
        page = self._get_page(slug, page_id, request.user)
        if not page:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)
        if not page.archived_at:
            return Response(
                {"error": "The page should be archived before deleting"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        page.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspacePageArchiveAPIEndpoint(BaseAPIView):
    """POST archive / DELETE unarchive workspace page."""

    permission_classes = [WorkspaceMemberPermission]

    def _get_page(self, slug, page_id, user):
        return Page.objects.filter(
            pk=page_id,
            workspace__slug=slug,
            is_global=True,
        ).filter(Q(owned_by=user) | Q(access=0)).first()

    def post(self, request, slug, page_id):
        page = self._get_page(slug, page_id, request.user)
        if not page:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)
        page.archived_at = timezone.now().date()
        page.save(update_fields=["archived_at", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, slug, page_id):
        page = self._get_page(slug, page_id, request.user)
        if not page:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)
        page.archived_at = None
        page.save(update_fields=["archived_at", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectPageListCreateAPIEndpoint(BaseAPIView):
    """GET/POST /api/v1/workspaces/{slug}/projects/{project_id}/pages/"""

    permission_classes = [ProjectEntityPermission]
    use_read_replica = True

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        project_id = self.kwargs.get("project_id")
        return (
            _annotate_project_ids(
                Page.objects.filter(
                    workspace__slug=slug,
                    project_pages__project_id=project_id,
                    project_pages__deleted_at__isnull=True,
                ).filter(Q(owned_by=self.request.user) | Q(access=0))
            )
            .select_related("owned_by", "workspace", "parent")
            .order_by("-created_at")
            .distinct()
        )

    def get(self, request, slug, project_id):
        return self.paginate(
            request=request,
            queryset=self.get_queryset(),
            on_results=lambda pages: PageAPISerializer(pages, many=True).data,
            default_per_page=20,
        )

    def post(self, request, slug, project_id):
        serializer = PageCreateAPISerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            project = Project.objects.get(pk=project_id, workspace__slug=slug)
        except Project.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        parent = None
        parent_id = data.get("parent_id")
        if parent_id:
            parent = Page.objects.filter(
                pk=parent_id,
                workspace_id=project.workspace_id,
                project_pages__project_id=project_id,
                project_pages__deleted_at__isnull=True,
            ).first()
            if not parent:
                return Response({"error": "Parent page not found"}, status=status.HTTP_400_BAD_REQUEST)

        page = Page(
            workspace_id=project.workspace_id,
            name=data["name"],
            owned_by_id=request.user.id,
            access=data.get("access") if data.get("access") is not None else Page.PUBLIC_ACCESS,
            color=data.get("color") or "",
            is_locked=bool(data.get("is_locked") or False),
            external_id=data.get("external_id"),
            external_source=data.get("external_source"),
            parent=parent,
            is_global=False,
            view_props=data.get("view_props") or {"full_width": False},
            logo_props=data.get("logo_props") or {},
            created_by_id=request.user.id,
            updated_by_id=request.user.id,
        )

        # Project pages still benefit from live conversion, but do not hard-fail
        # create if live is briefly unavailable — clear binary instead.
        apply_description_html(page, data["description_html"], require_live=False)
        page.save()

        ProjectPage.objects.create(
            workspace_id=page.workspace_id,
            project_id=project_id,
            page_id=page.id,
            created_by_id=page.created_by_id,
            updated_by_id=page.updated_by_id,
        )

        page_transaction.delay(
            new_description_html=page.description_html,
            old_description_html=None,
            page_id=str(page.id),
        )
        return Response(_page_response(page), status=status.HTTP_201_CREATED)


class ProjectPageDetailAPIEndpoint(BaseAPIView):
    """GET/PUT/DELETE /api/v1/workspaces/{slug}/projects/{project_id}/pages/{page_id}/"""

    permission_classes = [ProjectEntityPermission]
    use_read_replica = True

    def _get_page(self, slug, project_id, page_id, user):
        return (
            _annotate_project_ids(
                Page.objects.filter(
                    pk=page_id,
                    workspace__slug=slug,
                    project_pages__project_id=project_id,
                    project_pages__deleted_at__isnull=True,
                ).filter(Q(owned_by=user) | Q(access=0))
            )
            .select_related("owned_by", "workspace", "parent")
            .first()
        )

    def get(self, request, slug, project_id, page_id):
        page = self._get_page(slug, project_id, page_id, request.user)
        if not page:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(PageAPISerializer(page).data)

    def put(self, request, slug, project_id, page_id):
        page = self._get_page(slug, project_id, page_id, request.user)
        if not page:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)
        if page.is_locked:
            return Response({"error": "Page is locked"}, status=status.HTTP_400_BAD_REQUEST)
        if page.archived_at:
            return Response({"error": "Page is archived"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PageUpdateAPISerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        old_html = page.description_html

        for field in ("name", "access", "color", "is_locked", "external_id", "external_source", "view_props", "logo_props"):
            if field in data and data[field] is not None:
                setattr(page, field, data[field])

        if "description_html" in data:
            # Prefer live conversion so open editors see the new body; fall back
            # to clearing binary when live is down so HTML wins on next open.
            apply_description_html(page, data["description_html"], require_live=False)

        page.updated_by_id = request.user.id
        page.save()

        if "description_html" in data:
            page_transaction.delay(
                new_description_html=page.description_html,
                old_description_html=old_html,
                page_id=str(page.id),
            )

        return Response(_page_response(page))

    def delete(self, request, slug, project_id, page_id):
        page = self._get_page(slug, project_id, page_id, request.user)
        if not page:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)
        if not page.archived_at:
            return Response(
                {"error": "The page should be archived before deleting"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        page.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectPageArchiveAPIEndpoint(BaseAPIView):
    """POST archive / DELETE unarchive project page."""

    permission_classes = [ProjectEntityPermission]

    def _get_page(self, slug, project_id, page_id, user):
        return Page.objects.filter(
            pk=page_id,
            workspace__slug=slug,
            project_pages__project_id=project_id,
            project_pages__deleted_at__isnull=True,
        ).filter(Q(owned_by=user) | Q(access=0)).first()

    def post(self, request, slug, project_id, page_id):
        page = self._get_page(slug, project_id, page_id, request.user)
        if not page:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)
        page.archived_at = timezone.now().date()
        page.save(update_fields=["archived_at", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, slug, project_id, page_id):
        page = self._get_page(slug, project_id, page_id, request.user)
        if not page:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)
        page.archived_at = None
        page.save(update_fields=["archived_at", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)
