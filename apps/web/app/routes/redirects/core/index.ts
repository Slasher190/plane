/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { route } from "@react-router/dev/routes";
import type { RouteConfigEntry } from "@react-router/dev/routes";

export const coreRedirectRoutes: RouteConfigEntry[] = [
  // ========================================================================
  // WORKSPACE & PROJECT REDIRECTS
  // ========================================================================

  // Project settings redirect: /:workspaceSlug/projects/:projectId/settings/:path*
  // → /:workspaceSlug/settings/projects/:projectId/:path*
  route(":workspaceSlug/projects/:projectId/settings/*", "routes/redirects/core/project-settings.tsx"),

  // Analytics redirect: /:workspaceSlug/analytics → /:workspaceSlug/analytics/overview
  route(":workspaceSlug/analytics", "routes/redirects/core/analytics.tsx"),

  // API tokens redirect: /:workspaceSlug/settings/api-tokens
  // → /settings/profile/api-tokens
  route(":workspaceSlug/settings/api-tokens", "routes/redirects/core/api-tokens.tsx"),

  // Oneplace Docs sign-in: hand /auth/oidc/resume/:key back to the API (full page load)
  route("auth/oidc/resume/:key", "routes/redirects/core/oidc-resume.tsx"),

  // Oneplace: removed upsell pages (paid active cycles, billing & plans) → workspace home
  route(":workspaceSlug/active-cycles", "routes/redirects/core/removed-upsell.tsx", { id: "removed-active-cycles" }),
  route(":workspaceSlug/settings/billing", "routes/redirects/core/removed-upsell.tsx", { id: "removed-billing" }),

  // Inbox redirect: /:workspaceSlug/projects/:projectId/inbox
  // → /:workspaceSlug/projects/:projectId/intake
  route(":workspaceSlug/projects/:projectId/inbox", "routes/redirects/core/inbox.tsx"),

  // ========================================================================
  // AUTHENTICATION REDIRECTS
  // ========================================================================

  // Sign-up redirects
  route("accounts/sign-up", "routes/redirects/core/accounts-signup.tsx"),

  // Sign-in redirects (all redirect to home page)
  route("sign-in", "routes/redirects/core/sign-in.tsx"),
  route("signin", "routes/redirects/core/signin.tsx"),
  route("login", "routes/redirects/core/login.tsx"),

  // Register redirect
  route("register", "routes/redirects/core/register.tsx"),

  // ========================================================================
  // ROCKET.CHAT PREFIX RECOVERY (subpath /chat)
  // ========================================================================
  // RC client sometimes drops /chat and hits Plane at /group, /direct, etc.
  route("home", "routes/redirects/core/rocketchat-prefix.tsx"),
  route("group/*", "routes/redirects/core/rocketchat-prefix.tsx"),
  route("channel/*", "routes/redirects/core/rocketchat-prefix.tsx"),
  route("direct/*", "routes/redirects/core/rocketchat-prefix.tsx"),
  route("admin/*", "routes/redirects/core/rocketchat-prefix.tsx"),
  route("account/*", "routes/redirects/core/rocketchat-prefix.tsx"),
  route("directory", "routes/redirects/core/rocketchat-prefix.tsx"),
  route("directory/*", "routes/redirects/core/rocketchat-prefix.tsx"),
  route("composer/*", "routes/redirects/core/rocketchat-prefix.tsx"),
  route("lists/*", "routes/redirects/core/rocketchat-prefix.tsx"),
  route("omnichannel/*", "routes/redirects/core/rocketchat-prefix.tsx"),
];
