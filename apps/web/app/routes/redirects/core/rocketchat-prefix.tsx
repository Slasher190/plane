/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { redirect } from "react-router";

/**
 * Rocket.Chat is mounted at /chat, but its client often navigates to absolute
 * paths like /group/... or /direct/... (dropping the prefix). Bounce those
 * into /chat so host nginx serves Rocket.Chat instead of Plane's 404.
 */
function toChatPath(request: Request): string {
  const url = new URL(request.url);
  return `/chat${url.pathname}${url.search}`;
}

export const loader = ({ request }: { request: Request }) => {
  throw redirect(toChatPath(request));
};

export const clientLoader = ({ request }: { request: Request }) => {
  throw redirect(toChatPath(request));
};

export default function RocketChatPrefixRedirect() {
  return null;
}
