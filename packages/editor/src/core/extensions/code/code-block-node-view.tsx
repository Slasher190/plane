/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { NodeViewWrapper, NodeViewContent, type NodeViewProps } from "@tiptap/react";
import bash from "highlight.js/lib/languages/bash";
import css from "highlight.js/lib/languages/css";
import go from "highlight.js/lib/languages/go";
import java from "highlight.js/lib/languages/java";
import javascript from "highlight.js/lib/languages/javascript";
import json from "highlight.js/lib/languages/json";
import markdown from "highlight.js/lib/languages/markdown";
import python from "highlight.js/lib/languages/python";
import sql from "highlight.js/lib/languages/sql";
import ts from "highlight.js/lib/languages/typescript";
import xml from "highlight.js/lib/languages/xml";
import yaml from "highlight.js/lib/languages/yaml";
import { common, createLowlight } from "lowlight";
import { CheckIcon } from "lucide-react";
import { marked } from "marked";
import { useEffect, useMemo, useState } from "react";
import { CopyIcon } from "@plane/propel/icons";
import { Tooltip } from "@plane/propel/tooltip";
import { CustomSelect } from "@plane/ui";
import { cn } from "@plane/utils";
import type { TCodeBlockAttributes } from "./types";
import { ECodeBlockAttributeNames } from "./types";

const lowlight = createLowlight(common);
lowlight.register("ts", ts);
lowlight.register("typescript", ts);
lowlight.register("js", javascript);
lowlight.register("javascript", javascript);
lowlight.register("python", python);
lowlight.register("py", python);
lowlight.register("go", go);
lowlight.register("java", java);
lowlight.register("sql", sql);
lowlight.register("bash", bash);
lowlight.register("shell", bash);
lowlight.register("json", json);
lowlight.register("yaml", yaml);
lowlight.register("yml", yaml);
lowlight.register("markdown", markdown);
lowlight.register("md", markdown);
lowlight.register("css", css);
lowlight.register("html", xml);
lowlight.register("xml", xml);

marked.setOptions({ gfm: true, breaks: true });

function renderMarkdown(source: string) {
  const html = marked.parse(source || "", { async: false }) as string;
  return html
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/javascript:/gi, "");
}

const LANGUAGE_OPTIONS = [
  "plaintext",
  "typescript",
  "javascript",
  "python",
  "go",
  "java",
  "sql",
  "bash",
  "json",
  "yaml",
  "markdown",
  "css",
  "html",
  "xml",
  "mermaid",
];

function stopEditorEvent(event: React.SyntheticEvent) {
  event.stopPropagation();
}

export function CodeBlockComponent({ node, updateAttributes, editor }: NodeViewProps) {
  const [copied, setCopied] = useState(false);
  const [showPreview, setShowPreview] = useState(true);
  const [mermaidSvg, setMermaidSvg] = useState<string>("");
  const [mermaidError, setMermaidError] = useState<string>("");
  const attrs = node.attrs as TCodeBlockAttributes;
  const language = (attrs.language || "plaintext") as string;
  const isMermaid = language === "mermaid";
  const isMarkdown = language === "markdown" || language === "md";
  const source = node.textContent;
  const markdownHtml = useMemo(
    () => (isMarkdown && showPreview ? renderMarkdown(source) : ""),
    [isMarkdown, showPreview, source]
  );

  useEffect(() => {
    if (!isMermaid || !showPreview) {
      setMermaidSvg("");
      setMermaidError("");
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const mermaid = (await import("mermaid")).default;
          mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "neutral" });
          const id = `mermaid-${Math.random().toString(36).slice(2)}`;
          const { svg } = await mermaid.render(id, source || "graph TD;A[Start];");
          if (!cancelled) {
            setMermaidSvg(svg);
            setMermaidError("");
          }
        } catch (error) {
          if (!cancelled) {
            setMermaidSvg("");
            setMermaidError(error instanceof Error ? error.message : "Failed to render Mermaid");
          }
        }
      })();
    }, 300);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [isMermaid, showPreview, source]);

  useEffect(() => {
    if (showPreview || (!isMarkdown && !isMermaid)) return;
    const onSelection = () => {
      const { $from } = editor.state.selection;
      let inside = false;
      for (let depth = $from.depth; depth > 0; depth -= 1) {
        if ($from.node(depth).type.name === node.type.name) {
          inside = true;
          break;
        }
      }
      if (!inside) setShowPreview(true);
    };
    editor.on("selectionUpdate", onSelection);
    return () => {
      editor.off("selectionUpdate", onSelection);
    };
  }, [editor, isMarkdown, isMermaid, node.type.name, showPreview]);

  const enterSource = (event: React.MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setShowPreview(false);
  };

  const languageList = useMemo(() => {
    if (LANGUAGE_OPTIONS.includes(language)) return LANGUAGE_OPTIONS;
    return [language, ...LANGUAGE_OPTIONS];
  }, [language]);

  const copyToClipboard = async (e: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
    try {
      await navigator.clipboard.writeText(node.textContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 1000);
    } catch {
      setCopied(false);
    }
    e.preventDefault();
    e.stopPropagation();
  };

  return (
    <NodeViewWrapper className="code-block group/code relative" data-code-id={attrs[ECodeBlockAttributeNames.ID]}>
      <div
        role="group"
        aria-label="Code block controls"
        className="code-block-chrome absolute top-2 left-2 z-10 flex items-center gap-1"
        contentEditable={false}
        onMouseDown={stopEditorEvent}
        onPointerDown={stopEditorEvent}
      >
        <CustomSelect
          value={language}
          onChange={(next: string) => updateAttributes({ language: next })}
          label={language}
          buttonClassName="border border-subtle bg-layer-1 !rounded-md px-2 py-1 text-xs"
          maxHeight="lg"
        >
          {languageList.map((lang) => (
            <CustomSelect.Option key={lang} value={lang}>
              {lang}
            </CustomSelect.Option>
          ))}
        </CustomSelect>
      </div>
      <Tooltip tooltipContent="Copy code">
        <button
          type="button"
          className={cn(
            "group/button absolute top-2 right-2 z-10 hidden size-8 items-center justify-center rounded-md border border-subtle bg-layer-1 backdrop-blur-sm transition duration-150 ease-in-out group-hover/code:flex",
            {
              "bg-success-subtle hover:bg-success-subtle-1 active:bg-success-subtle-1": copied,
            }
          )}
          onClick={(e) => void copyToClipboard(e)}
        >
          {copied ? (
            <CheckIcon className="h-3 w-3 text-success-primary" strokeWidth={3} />
          ) : (
            <CopyIcon className="h-3 w-3 text-tertiary group-hover/button:text-primary" />
          )}
        </button>
      </Tooltip>

      {isMermaid && showPreview ? (
        <div
          className="mt-2 overflow-x-auto rounded-t-lg bg-layer-2 p-4 text-primary"
          contentEditable={false}
          onDoubleClick={enterSource}
        >
          {mermaidError ? (
            <pre className="text-xs whitespace-pre-wrap text-danger-primary">{mermaidError}</pre>
          ) : (
            <div dangerouslySetInnerHTML={{ __html: mermaidSvg }} />
          )}
        </div>
      ) : null}

      {isMarkdown && showPreview ? (
        <div
          className="markdown-preview prose-sm my-2 max-w-none cursor-text rounded-lg bg-layer-2 p-4 pt-12 text-primary prose"
          contentEditable={false}
          title="Double-click to edit"
          onDoubleClick={enterSource}
          dangerouslySetInnerHTML={{ __html: markdownHtml }}
        />
      ) : null}

      <pre
        className={cn(
          "my-2 rounded-lg bg-layer-3 p-4 pt-10 text-primary",
          (isMermaid || isMarkdown) && showPreview && "code-block-source-hidden"
        )}
      >
        <NodeViewContent as="code" className="whitespace-pre-wrap" />
      </pre>
    </NodeViewWrapper>
  );
}
