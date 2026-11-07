# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Convert Oneplace page HTML (TipTap output) to the Markdown AFFiNE imports.

Covers what the Oneplace editor emits:
- headings, paragraphs, bold/italic/strike/inline code, links
- bullet, numbered and task lists (nested)
- fenced code (Mermaid and LaTeX stay as code blocks with their language)
- tables, quotes, rules

Anything else keeps its text and is recorded in ``warnings``, so nothing is
dropped silently.
"""

import re
from typing import Callable, List, Optional

from bs4 import BeautifulSoup, NavigableString, Tag

BLOCK_TAGS = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "pre", "blockquote",
    "table", "hr", "div", "img", "figure",
}
KNOWN_INLINE = {
    "strong", "b", "em", "i", "s", "del", "strike", "code", "a", "span", "br",
    "u", "mark", "sub", "sup", "label", "input",
}


class Converter:
    def __init__(self, rewrite_link: Optional[Callable[[str], str]] = None):
        self.rewrite_link = rewrite_link or (lambda href: href)
        self.warnings: List[str] = []

    def warn(self, msg: str):
        if msg not in self.warnings:
            self.warnings.append(msg)

    # ---------- inline ----------
    def inline(self, node) -> str:
        if isinstance(node, NavigableString):
            text = str(node)
            return re.sub(r"\s+", " ", text)
        if not isinstance(node, Tag):
            return ""
        name = node.name.lower()
        inner = "".join(self.inline(c) for c in node.children)
        if name in ("strong", "b"):
            return f"**{inner.strip()}**" if inner.strip() else inner
        if name in ("em", "i"):
            return f"*{inner.strip()}*" if inner.strip() else inner
        if name in ("s", "del", "strike"):
            return f"~~{inner.strip()}~~" if inner.strip() else inner
        if name == "code":
            text = node.get_text()
            fence = "``" if "`" in text else "`"
            return f"{fence}{text}{fence}"
        if name == "a":
            href = (node.get("href") or "").strip()
            label = inner.strip() or href
            return f"[{label}]({self.rewrite_link(href)})" if href else label
        if name == "br":
            return "  \n"
        if name == "img":
            src = node.get("src") or ""
            self.warn("image kept as a link (re-upload in Docs if needed)")
            return f"[{node.get('alt') or 'image'}]({src})"
        if name in ("label", "input"):
            return ""  # task-list checkbox chrome
        if name not in KNOWN_INLINE:
            self.warn(f"unsupported inline element <{name}> kept as text")
        return inner

    def inline_children(self, node: Tag) -> str:
        return "".join(self.inline(c) for c in node.children).strip()

    # ---------- blocks ----------
    def blocks(self, node: Tag, indent: str = "") -> List[str]:
        out: List[str] = []
        buffer = ""
        for child in node.children:
            if isinstance(child, Tag) and child.name.lower() in BLOCK_TAGS:
                if buffer.strip():
                    out.append(indent + buffer.strip())
                    buffer = ""
                out.extend(self.block(child, indent))
            else:
                buffer += self.inline(child)
        if buffer.strip():
            out.append(indent + buffer.strip())
        return out

    def block(self, node: Tag, indent: str = "") -> List[str]:
        name = node.name.lower()
        if name == "p":
            text = self.inline_children(node)
            return [indent + text] if text else []
        if re.fullmatch(r"h[1-6]", name):
            text = self.inline_children(node)
            return [indent + "#" * int(name[1]) + " " + text] if text else []
        if name in ("ul", "ol"):
            return [self.list_block(node, indent)]
        if name == "pre":
            code = node.find("code")
            lang = ""
            if code is not None:
                for cls in code.get("class") or []:
                    if cls.startswith("language-"):
                        lang = cls[len("language-"):]
            text = (code or node).get_text().rstrip("\n")
            fence = "~~~" if "```" in text else "```"
            body = "\n".join(indent + line for line in text.split("\n"))
            return [f"{indent}{fence}{lang}\n{body}\n{indent}{fence}"]
        if name == "blockquote":
            inner = self.blocks(node)
            return ["\n".join(indent + "> " + line if line else indent + ">" for line in "\n\n".join(inner).split("\n"))]
        if name == "hr":
            return [indent + "---"]
        if name == "table":
            return [self.table(node, indent)]
        if name == "img":
            return [indent + self.inline(node)]
        # div / figure / wrappers
        return self.blocks(node, indent)

    def list_block(self, node: Tag, indent: str) -> str:
        ordered = node.name.lower() == "ol"
        is_task = node.get("data-type") == "taskList"
        lines: List[str] = []
        n = 1
        for li in node.find_all("li", recursive=False):
            if is_task or li.get("data-type") == "taskItem":
                checked = str(li.get("data-checked", "")).lower() == "true"
                marker = "- [x] " if checked else "- [ ] "
            else:
                marker = f"{n}. " if ordered else "- "
            n += 1
            first = ""
            rest: List[str] = []
            for child in li.children:
                if isinstance(child, Tag) and child.name.lower() in ("ul", "ol"):
                    rest.append(self.list_block(child, indent + "  "))
                elif isinstance(child, Tag) and child.name.lower() in BLOCK_TAGS:
                    parts = self.blocks(child) if child.name.lower() == "div" else self.block(child)
                    for part in parts:
                        if not first:
                            first = part.strip()
                        elif part.lstrip().startswith(("- ", "1. ")) or part.startswith("  "):
                            rest.append(part if part.startswith(indent + "  ") else indent + "  " + part.strip())
                        else:
                            rest.append(indent + "  " + part.strip())
                elif isinstance(child, Tag) and child.name.lower() in ("label", "input"):
                    continue
                else:
                    first += self.inline(child)
            lines.append(indent + marker + first.strip())
            lines.extend(r for r in rest if r.strip())
        return "\n".join(lines)

    def table(self, node: Tag, indent: str) -> str:
        rows = []
        for tr in node.find_all("tr"):
            cells = []
            for cell in tr.find_all(["th", "td"], recursive=False):
                text = " ".join(self.blocks(cell)).replace("\n", " ")
                cells.append(text.replace("|", "\\|").strip())
            if cells:
                rows.append(cells)
        if not rows:
            return ""
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        head, body = rows[0], rows[1:]
        lines = [
            indent + "| " + " | ".join(head) + " |",
            indent + "|" + "|".join(" --- " for _ in head) + "|",
        ]
        lines += [indent + "| " + " | ".join(r) + " |" for r in body]
        return "\n".join(lines)


def html_to_markdown(html: str, rewrite_link: Optional[Callable[[str], str]] = None):
    """Return (markdown, warnings)."""
    conv = Converter(rewrite_link)
    soup = BeautifulSoup(html or "", "lxml")
    root = soup.body or soup
    parts = conv.blocks(root)
    markdown = "\n\n".join(p for p in parts if p.strip())
    return markdown.strip() + ("\n" if markdown.strip() else ""), conv.warnings
