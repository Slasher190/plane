# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Links between Oneplace objects and Oneplace Docs (AFFiNE)."""

import uuid

from django.db import models


class AffineWorkspaceLink(models.Model):
    """Oneplace workspace → AFFiNE workspace that holds its docs."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.OneToOneField("db.Workspace", on_delete=models.CASCADE, related_name="affine_link")
    affine_workspace_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "affine_workspace_links"


class AffineProjectLink(models.Model):
    """Project → its folder and "Pages" index doc in AFFiNE."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField("db.Project", on_delete=models.CASCADE, related_name="affine_link")
    affine_workspace_id = models.CharField(max_length=64)
    folder_id = models.CharField(max_length=64)
    index_doc_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "affine_project_links"


class AffinePageLink(models.Model):
    """Migrated Oneplace page → AFFiNE doc (the old page row is kept as a backup)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.OneToOneField("db.Page", on_delete=models.CASCADE, related_name="affine_link")
    affine_workspace_id = models.CharField(max_length=64)
    affine_doc_id = models.CharField(max_length=64)
    source_hash = models.CharField(max_length=64, blank=True, default="")
    warnings = models.TextField(blank=True, default="")
    migrated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "affine_page_links"
