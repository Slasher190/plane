/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ClientLoaderFunctionArgs } from "react-router";
import { API_BASE_URL } from "@plane/constants";

// Oneplace: Pages moved to Oneplace Docs (AFFiNE). A project's Pages opens its
// "Pages" index doc there; an old page link opens the migrated doc. The API
// endpoint signs the user in to Docs on the way.
export const clientLoader = ({ params }: ClientLoaderFunctionArgs) => {
  const query = new URLSearchParams();
  if (params.projectId) query.set("project", params.projectId);
  if (params.pageId) query.set("page", params.pageId);
  const slug = encodeURIComponent(params.workspaceSlug ?? "");
  window.location.replace(`${API_BASE_URL}/api/workspaces/${slug}/docs/sso/?${query.toString()}`);
  return null;
};

export default function PagesToDocs() {
  return null;
}
