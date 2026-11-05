/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { redirect } from "react-router";
import type { ClientLoaderFunctionArgs } from "react-router";

// Oneplace: upsell pages (paid active cycles, billing & plans) were removed.
// Old links land on the workspace home instead.
// Mounted on two paths, so typegen does not emit per-route types for it.
export const clientLoader = ({ params }: ClientLoaderFunctionArgs) => {
  const { workspaceSlug } = params;
  throw redirect(`/${workspaceSlug}/`);
};

export default function RemovedUpsell() {
  return null;
}
