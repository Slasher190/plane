# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path
from oauth2_provider import views as oauth2_views

from .views import OidcLoginView, OidcResumeView, OneplaceAuthorizationView

app_name = "oauth2_provider"

# Mounted at /auth/oidc/ — issuer: ${OIDC_ISSUER}
urlpatterns = [
    path("authorize/", OneplaceAuthorizationView.as_view(), name="authorize"),
    path("token/", oauth2_views.TokenView.as_view(), name="token"),
    path("revoke_token/", oauth2_views.RevokeTokenView.as_view(), name="revoke-token"),
    path("userinfo/", oauth2_views.UserInfoView.as_view(), name="user-info"),
    path(".well-known/openid-configuration", oauth2_views.ConnectDiscoveryInfoView.as_view(), name="oidc-connect-discovery-info"),
    path(".well-known/jwks.json", oauth2_views.JwksInfoView.as_view(), name="jwks-info"),
    path("logout/", oauth2_views.RPInitiatedLogoutView.as_view(), name="rp-initiated-logout"),
    path("login/", OidcLoginView.as_view(), name="oneplace-oidc-login"),
    path("resume/<str:key>/", OidcResumeView.as_view(), name="oneplace-oidc-resume"),
]
