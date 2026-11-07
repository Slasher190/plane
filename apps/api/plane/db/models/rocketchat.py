# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.conf import settings
from django.db import models

from .base import BaseModel


class RocketChatWorkspaceLink(BaseModel):
    """Maps a Oneplace workspace to a Rocket.Chat team."""

    workspace = models.OneToOneField(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="rocketchat_link",
    )
    rc_team_id = models.CharField(max_length=64)
    rc_team_name = models.CharField(max_length=255)
    rc_room_id = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        db_table = "rocketchat_workspace_links"
        verbose_name = "Rocket.Chat Workspace Link"
        verbose_name_plural = "Rocket.Chat Workspace Links"

    def __str__(self):
        return f"{self.workspace_id} → {self.rc_team_id}"


class RocketChatUserLink(BaseModel):
    """Maps a Oneplace user to a Rocket.Chat user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rocketchat_link",
    )
    rc_user_id = models.CharField(max_length=64)
    rc_username = models.CharField(max_length=255)

    class Meta:
        db_table = "rocketchat_user_links"
        verbose_name = "Rocket.Chat User Link"
        verbose_name_plural = "Rocket.Chat User Links"

    def __str__(self):
        return f"{self.user_id} → {self.rc_user_id}"
