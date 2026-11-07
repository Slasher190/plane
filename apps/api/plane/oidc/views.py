# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import secrets
from urllib.parse import urlencode

from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.views import View
from oauth2_provider.views import AuthorizationView

LOGIN_PATH = "/auth/oidc/login/"
AUTHORIZE_PREFIX = "/auth/oidc/authorize/"
PENDING_KEY = "oneplace-oidc-pending:{}"
PENDING_TTL_SECONDS = 600


class OneplaceAuthorizationView(AuthorizationView):
    """Authorize endpoint. Signed-in Oneplace users pass straight through
    (the AFFiNE client is registered with skip_authorization)."""

    login_url = LOGIN_PATH


class OidcLoginView(View):
    """Not signed in to Oneplace yet.

    Oneplace's sign-in page can only carry a simple `next_path`, so the full
    authorize URL is kept server-side for a few minutes and the user comes
    back through `/auth/oidc/resume/<key>/` after signing in.
    """

    def get(self, request):
        next_url = request.GET.get("next", "")
        if not next_url.startswith(AUTHORIZE_PREFIX):
            return HttpResponseRedirect("/")
        key = secrets.token_urlsafe(24)
        cache.set(PENDING_KEY.format(key), next_url, PENDING_TTL_SECONDS)
        return HttpResponseRedirect("/?" + urlencode({"next_path": f"/auth/oidc/resume/{key}/"}))


class OidcResumeView(View):
    def get(self, request, key):
        next_url = cache.get(PENDING_KEY.format(key))
        if not next_url or not next_url.startswith(AUTHORIZE_PREFIX):
            return HttpResponseRedirect("/")
        cache.delete(PENDING_KEY.format(key))
        return HttpResponseRedirect(next_url)
