# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.apps import AppConfig


class OidcConfig(AppConfig):
    """Oneplace as an OpenID Connect provider (used by Oneplace Docs / AFFiNE)."""

    name = "plane.oidc"
    label = "oneplace_oidc"
