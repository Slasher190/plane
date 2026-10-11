/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { marked } from "marked";

marked.setOptions({ gfm: true, breaks: true });

function sanitizeHtml(html: string): string {
  return html
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/javascript:/gi, "");
}

function escapeAttr(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function equationHtml(latex: string, display: boolean): string {
  return `<span data-type="equation" data-latex="${escapeAttr(latex)}" data-display="${display ? "true" : "false"}"></span>`;
}

/**
 * Pull math out of markdown before `marked` runs, so `$...$` / `$$...$$` /
 * `\begin{align}` become TipTap equation nodes instead of literal text.
 * Full `\documentclass` LaTeX fences stay as code blocks.
 */
function extractMathPlaceholders(markdown: string): { markdown: string; equations: string[] } {
  const equations: string[] = [];
  const codeBlocks: string[] = [];

  const stashEquation = (latex: string, display: boolean) => {
    const token = `@@EQ${equations.length}@@`;
    equations.push(equationHtml(latex.trim(), display));
    return token;
  };

  const stashCode = (block: string) => {
    const token = `@@CODE${codeBlocks.length}@@`;
    codeBlocks.push(block);
    return token;
  };

  let md = markdown || "";

  // Keep full LaTeX documents as fenced code; convert math-only latex/tex fences.
  md = md.replace(/```(latex|tex|math)\r?\n([\s\S]*?)```/gi, (full, _lang: string, body: string) => {
    if (/\\documentclass\b/.test(body)) return stashCode(full);
    const trimmed = body.trim();
    if (!trimmed) return stashCode(full);
    return stashEquation(trimmed, true);
  });

  // Protect remaining fences + inline code from math transforms.
  md = md.replace(/```[\s\S]*?```/g, (block) => stashCode(block));
  md = md.replace(/`[^`\n]+`/g, (block) => stashCode(block));

  // Mild LaTeX prose → markdown (outside protected code).
  md = md.replace(/\\section\*?\{([^}]+)\}/g, "\n\n## $1\n\n");
  md = md.replace(/\\subsection\*?\{([^}]+)\}/g, "\n\n### $1\n\n");
  md = md.replace(/\\begin\{itemize\}/g, "\n");
  md = md.replace(/\\end\{itemize\}/g, "\n");
  md = md.replace(/\\item\s+/g, "\n- ");
  md = md.replace(/\\texttt\{([^}]+)\}/g, "`$1`");
  md = md.replace(/\\end\{document\}/g, "\n");
  md = md.replace(/\\begin\{document\}/g, "\n");
  md = md.replace(/\\maketitle/g, "\n");

  // Display / environments first, then inline.
  md = md.replace(/\$\$([\s\S]+?)\$\$/g, (_, latex: string) => stashEquation(latex, true));
  md = md.replace(/\\\[([\s\S]+?)\\\]/g, (_, latex: string) => stashEquation(latex, true));
  md = md.replace(
    /\\begin\{(align\*?|equation\*?|gather\*?|cases|multline\*?)\}([\s\S]*?)\\end\{\1\}/g,
    (full: string) => stashEquation(full, true)
  );
  md = md.replace(/(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)/g, (_, latex: string) => stashEquation(latex, false));
  md = md.replace(/\\\(([\s\S]+?)\\\)/g, (_, latex: string) => stashEquation(latex, false));

  // Restore code before marked so fences parse normally.
  md = md.replace(/@@CODE(\d+)@@/g, (_, index: string) => codeBlocks[Number(index)] ?? "");

  return { markdown: md, equations };
}

/**
 * Convert LLM markdown to TipTap-friendly HTML.
 * Prefer this over naive newline → <br/> replacement, which destroys fenced code/Mermaid.
 */
export function convertMarkdownToHtml(markdown: string): string {
  const { markdown: withPlaceholders, equations } = extractMathPlaceholders(markdown);
  let html = marked.parse(withPlaceholders, { async: false }) as string;
  html = sanitizeHtml(html);
  html = html.replace(/@@EQ(\d+)@@/g, (_, index: string) => equations[Number(index)] ?? "");
  return html;
}
