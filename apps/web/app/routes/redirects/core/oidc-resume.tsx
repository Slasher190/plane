/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ClientLoaderFunctionArgs } from "react-router";

// Oneplace Docs sign-in: after logging in, the web app routes to next_path
// client-side. /auth/oidc/* is served by the API, so hand over with a full page load.
export const clientLoader = ({ params }: ClientLoaderFunctionArgs) => {
  const key = encodeURIComponent(params.key ?? "");
  window.location.replace(`/auth/oidc/resume/${key}/`);
  return null;
};

export default function OidcResume() {
  return null;
}
