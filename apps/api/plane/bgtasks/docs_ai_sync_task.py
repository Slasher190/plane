# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from celery import shared_task

from plane.utils.exception_logger import log_exception


@shared_task
def sync_docs_ai_task():
    """Mirror god-mode → AI settings into Oneplace Docs (AFFiNE) workspaces."""
    try:
        from plane.app.services.affine import sync_docs_ai

        return [(ws, str(res)[:200]) for ws, res in sync_docs_ai()]
    except Exception as exc:
        log_exception(exc)
        return [("-", f"error: {exc}")]
