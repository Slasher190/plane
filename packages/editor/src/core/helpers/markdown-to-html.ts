/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { marked } from "marked";

marked.setOptions({ gfm: true, breaks: true });

/**
 * Convert LLM markdown to TipTap-friendly HTML.
 * Prefer this over naive newline → <br/> replacement, which destroys fenced code/Mermaid.
 */
export function convertMarkdownToHtml(markdown: string): string {
  const html = marked.parse(markdown || "", { async: false }) as string;
  return html
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/javascript:/gi, "");
}
