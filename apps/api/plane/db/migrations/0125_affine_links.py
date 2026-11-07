# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0124_rocketchat_links"),
    ]

    operations = [
        migrations.CreateModel(
            name="AffineWorkspaceLink",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("affine_workspace_id", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "workspace",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="affine_link", to="db.workspace"
                    ),
                ),
            ],
            options={"db_table": "affine_workspace_links"},
        ),
        migrations.CreateModel(
            name="AffineProjectLink",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("affine_workspace_id", models.CharField(max_length=64)),
                ("folder_id", models.CharField(max_length=64)),
                ("index_doc_id", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "project",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="affine_link", to="db.project"
                    ),
                ),
            ],
            options={"db_table": "affine_project_links"},
        ),
        migrations.CreateModel(
            name="AffinePageLink",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("affine_workspace_id", models.CharField(max_length=64)),
                ("affine_doc_id", models.CharField(max_length=64)),
                ("source_hash", models.CharField(blank=True, default="", max_length=64)),
                ("warnings", models.TextField(blank=True, default="")),
                ("migrated_at", models.DateTimeField(auto_now_add=True)),
                (
                    "page",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="affine_link", to="db.page"
                    ),
                ),
            ],
            options={"db_table": "affine_page_links"},
        ),
    ]
