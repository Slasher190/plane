# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.core.management.base import BaseCommand

from plane.app.services.affine import docs_ai_settings, sync_docs_ai


class Command(BaseCommand):
    help = "Push god-mode → AI settings (Ollama endpoint, key, main + fallback models) to Oneplace Docs."

    def handle(self, *args, **options):
        provider, base_url, api_key, models = docs_ai_settings()
        self.stdout.write(
            f"provider={provider} base_url={base_url} key={'set' if api_key else 'MISSING'} models={models}"
        )
        for workspace_id, result in sync_docs_ai():
            self.stdout.write(f"{workspace_id}: {result}")
