# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from oauth2_provider.oauth2_validators import OAuth2Validator


class OneplaceOIDCValidator(OAuth2Validator):
    """Adds the identity claims relying parties (AFFiNE) need.

    `sub` is the Oneplace user id. Oneplace is the trusted identity source for
    its own apps, so the email is reported as verified.
    """

    oidc_claim_scope = {
        **OAuth2Validator.oidc_claim_scope,
        "email": "email",
        "email_verified": "email",
        "name": "profile",
        "preferred_username": "profile",
        "given_name": "profile",
        "family_name": "profile",
    }

    def get_additional_claims(self, request):
        user = request.user
        first, last = (user.first_name or "").strip(), (user.last_name or "").strip()
        # Some accounts already hold the full name in first_name ("Sudhi Ranjan Gupta" + "Gupta").
        full_name = first if last and first.endswith(last) else " ".join(p for p in (first, last) if p)
        return {
            "email": user.email,
            "email_verified": True,
            "name": full_name or user.display_name or user.email,
            "preferred_username": user.display_name or user.email,
            "given_name": user.first_name or "",
            "family_name": user.last_name or "",
        }
