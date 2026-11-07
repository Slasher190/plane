# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import serializers

from plane.db.models import Page
from plane.utils.content_validator import validate_html_content


class PageAPISerializer(serializers.ModelSerializer):
    """Public API page shape used by plane-sdk / MCP."""

    owned_by = serializers.UUIDField(source="owned_by_id", read_only=True)
    workspace = serializers.UUIDField(source="workspace_id", read_only=True)
    project_ids = serializers.SerializerMethodField()
    collection_id = serializers.SerializerMethodField()
    page_collection_id = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            "id",
            "name",
            "description_html",
            "description_stripped",
            "created_at",
            "updated_at",
            "owned_by",
            "workspace",
            "access",
            "color",
            "is_locked",
            "archived_at",
            "parent_id",
            "project_ids",
            "collection_id",
            "page_collection_id",
            "external_id",
            "external_source",
            "view_props",
            "logo_props",
            "is_global",
        ]
        read_only_fields = [
            "id",
            "description_stripped",
            "created_at",
            "updated_at",
            "owned_by",
            "workspace",
            "project_ids",
            "collection_id",
            "page_collection_id",
            "is_global",
        ]

    def get_project_ids(self, obj):
        # Prefer annotation when present; otherwise resolve through the M2M.
        project_ids = getattr(obj, "annotated_project_ids", None)
        if project_ids is not None:
            return [str(pid) for pid in project_ids if pid]
        return [str(pid) for pid in obj.projects.values_list("id", flat=True)]

    def get_collection_id(self, obj):
        # Collections are a commercial/wiki feature; CE has no collection table.
        return None

    def get_page_collection_id(self, obj):
        return None

    def validate_description_html(self, value):
        if value is None:
            return value
        is_valid, error_message, sanitized_html = validate_html_content(value)
        if not is_valid:
            raise serializers.ValidationError(error_message)
        return sanitized_html if sanitized_html is not None else value


class PageCreateAPISerializer(serializers.Serializer):
    name = serializers.CharField(required=True, allow_blank=False)
    description_html = serializers.CharField(required=True, allow_blank=True)
    access = serializers.IntegerField(required=False, allow_null=True)
    color = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_locked = serializers.BooleanField(required=False, allow_null=True)
    external_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    external_source = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    parent_id = serializers.UUIDField(required=False, allow_null=True)
    collection_id = serializers.UUIDField(required=False, allow_null=True)
    view_props = serializers.JSONField(required=False, allow_null=True)
    logo_props = serializers.JSONField(required=False, allow_null=True)

    def validate_description_html(self, value):
        is_valid, error_message, sanitized_html = validate_html_content(value or "<p></p>")
        if not is_valid:
            raise serializers.ValidationError(error_message)
        return sanitized_html if sanitized_html is not None else (value or "<p></p>")

    def validate_collection_id(self, value):
        if value:
            raise serializers.ValidationError(
                "Collections are not available on this Oneplace CE instance."
            )
        return value


class PageUpdateAPISerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=False)
    description_html = serializers.CharField(required=False, allow_blank=True)
    access = serializers.IntegerField(required=False, allow_null=True)
    color = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_locked = serializers.BooleanField(required=False, allow_null=True)
    external_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    external_source = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    view_props = serializers.JSONField(required=False, allow_null=True)
    logo_props = serializers.JSONField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one field is required.")
        return attrs

    def validate_description_html(self, value):
        is_valid, error_message, sanitized_html = validate_html_content(value or "<p></p>")
        if not is_valid:
            raise serializers.ValidationError(error_message)
        return sanitized_html if sanitized_html is not None else (value or "<p></p>")
