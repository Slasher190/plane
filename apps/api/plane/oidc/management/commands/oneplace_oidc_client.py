# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os

from django.core.management.base import BaseCommand, CommandError
from oauth2_provider.models import get_application_model


class Command(BaseCommand):
    help = "Create or update the OIDC client for Oneplace Docs (AFFiNE) from environment variables."

    def handle(self, *args, **options):
        client_id = os.environ.get("AFFINE_OIDC_CLIENT_ID", "")
        client_secret = os.environ.get("AFFINE_OIDC_CLIENT_SECRET", "")
        redirect_uri = os.environ.get("AFFINE_OIDC_REDIRECT_URI", "https://docs.roinetinsurance.in/oauth/callback")
        if not client_id or not client_secret:
            raise CommandError("AFFINE_OIDC_CLIENT_ID and AFFINE_OIDC_CLIENT_SECRET must be set")

        Application = get_application_model()
        app, created = Application.objects.get_or_create(client_id=client_id, defaults={"name": "Oneplace Docs"})
        app.name = "Oneplace Docs"
        app.client_type = Application.CLIENT_CONFIDENTIAL
        app.authorization_grant_type = Application.GRANT_AUTHORIZATION_CODE
        app.redirect_uris = redirect_uri
        app.algorithm = Application.RS256_ALGORITHM
        app.skip_authorization = True
        app.client_secret = client_secret  # hashed on save
        app.save()
        self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} OIDC client {client_id} → {redirect_uri}"))
