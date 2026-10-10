/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export const API_BASE_URL = process.env.VITE_API_BASE_URL || "";
export const API_BASE_PATH = process.env.VITE_API_BASE_PATH || "";
export const API_URL = encodeURI(`${API_BASE_URL}${API_BASE_PATH}`);
// God Mode Admin App Base Url
export const ADMIN_BASE_URL = process.env.VITE_ADMIN_BASE_URL || "";
export const ADMIN_BASE_PATH = process.env.VITE_ADMIN_BASE_PATH || "";
export const GOD_MODE_URL = encodeURI(`${ADMIN_BASE_URL}${ADMIN_BASE_PATH}`);
// Publish App Base Url
export const SPACE_BASE_URL = process.env.VITE_SPACE_BASE_URL || "";
export const SPACE_BASE_PATH = process.env.VITE_SPACE_BASE_PATH || "";
export const SITES_URL = encodeURI(`${SPACE_BASE_URL}${SPACE_BASE_PATH}`);
// Live App Base Url
export const LIVE_BASE_URL = process.env.VITE_LIVE_BASE_URL || "";
export const LIVE_BASE_PATH = process.env.VITE_LIVE_BASE_PATH || "";
export const LIVE_URL = encodeURI(`${LIVE_BASE_URL}${LIVE_BASE_PATH}`);
// Web App Base Url
export const WEB_BASE_URL = process.env.VITE_WEB_BASE_URL || "";
export const WEB_BASE_PATH = process.env.VITE_WEB_BASE_PATH || "";
export const WEB_URL = encodeURI(`${WEB_BASE_URL}${WEB_BASE_PATH}`);
// product website url
export const WEBSITE_URL = process.env.VITE_WEBSITE_URL || "https://oneplace.roinetinsurance.in";
// support email
export const SUPPORT_EMAIL = process.env.VITE_SUPPORT_EMAIL || "insurancesupport@roinetinsurance.in";
// marketing / help links (white-label: Oneplace / Roinet — not Plane)
export const MARKETING_PRICING_PAGE_LINK = process.env.VITE_MARKETING_PRICING_PAGE_LINK || WEBSITE_URL;
export const MARKETING_CONTACT_US_PAGE_LINK = process.env.VITE_MARKETING_CONTACT_US_PAGE_LINK || WEBSITE_URL;
export const MARKETING_PLANE_ONE_PAGE_LINK = process.env.VITE_MARKETING_PLANE_ONE_PAGE_LINK || WEBSITE_URL;
export const DOCS_URL = process.env.VITE_DOCS_URL || WEBSITE_URL;
export const FORUM_URL = process.env.VITE_FORUM_URL || WEBSITE_URL;
export const CHANGELOG_URL = process.env.VITE_CHANGELOG_URL || WEBSITE_URL;
export const TERMS_OF_SERVICE_URL = process.env.VITE_TERMS_OF_SERVICE_URL || WEBSITE_URL;
export const PRIVACY_POLICY_URL = process.env.VITE_PRIVACY_POLICY_URL || WEBSITE_URL;