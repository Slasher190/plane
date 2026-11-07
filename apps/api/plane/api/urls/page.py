# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.api.views.page import (
    WorkspacePageListCreateAPIEndpoint,
    WorkspacePageDetailAPIEndpoint,
    WorkspacePageArchiveAPIEndpoint,
    ProjectPageListCreateAPIEndpoint,
    ProjectPageDetailAPIEndpoint,
    ProjectPageArchiveAPIEndpoint,
)

urlpatterns = [
    # Workspace (wiki) pages — plane-sdk / MCP omit project_id
    path(
        "workspaces/<str:slug>/pages/",
        WorkspacePageListCreateAPIEndpoint.as_view(),
        name="workspace-pages",
    ),
    path(
        "workspaces/<str:slug>/pages/<uuid:page_id>/",
        WorkspacePageDetailAPIEndpoint.as_view(),
        name="workspace-page-detail",
    ),
    path(
        "workspaces/<str:slug>/pages/<uuid:page_id>/archive/",
        WorkspacePageArchiveAPIEndpoint.as_view(),
        name="workspace-page-archive",
    ),
    # Project pages
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/",
        ProjectPageListCreateAPIEndpoint.as_view(),
        name="project-pages",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/",
        ProjectPageDetailAPIEndpoint.as_view(),
        name="project-page-detail",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/archive/",
        ProjectPageArchiveAPIEndpoint.as_view(),
        name="project-page-archive",
    ),
]
