/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { mergeAttributes, Node } from "@tiptap/core";
import { ReactNodeViewRenderer, NodeViewWrapper } from "@tiptap/react";
import { useRef } from "react";

type HtmlArtifactAttrs = {
  src: string;
  title: string;
  height: number;
};

function HtmlArtifactView({
  node,
  updateAttributes,
  deleteNode,
}: {
  node: { attrs: HtmlArtifactAttrs };
  updateAttributes: (attrs: Partial<HtmlArtifactAttrs>) => void;
  deleteNode: () => void;
}) {
  const { src, title, height } = node.attrs;
  const fileRef = useRef<HTMLInputElement>(null);

  const onFile = async (file: File | null) => {
    if (!file) return;
    if (!/\.html?$/i.test(file.name)) return;
    const text = await file.text();
    const blob = new Blob([text], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    updateAttributes({ src: url, title: file.name });
  };

  return (
    <NodeViewWrapper className="my-3 rounded-lg border border-subtle bg-layer-1 overflow-hidden" data-type="html-artifact">
      <div className="flex items-center justify-between gap-2 border-b border-subtle px-3 py-2 text-xs text-secondary">
        <span className="truncate font-medium text-primary">{title || "HTML artifact"}</span>
        <div className="flex items-center gap-2 shrink-0">
          {src ? (
            <>
              <a className="underline" href={src} target="_blank" rel="noreferrer">
                Open
              </a>
              <button type="button" className="underline" onClick={() => fileRef.current?.click()}>
                Replace
              </button>
              <button type="button" className="underline text-danger-primary" onClick={() => deleteNode()}>
                Delete
              </button>
            </>
          ) : (
            <button type="button" className="underline" onClick={() => fileRef.current?.click()}>
              Upload .html
            </button>
          )}
          <input
            ref={fileRef}
            type="file"
            accept=".html,.htm,text/html"
            className="hidden"
            onChange={(e) => void onFile(e.target.files?.[0] ?? null)}
          />
        </div>
      </div>
      {src ? (
        <iframe
          title={title || "HTML artifact"}
          src={src}
          className="w-full bg-white"
          style={{ height: `${height || 360}px` }}
          sandbox="allow-scripts allow-forms allow-popups allow-modals"
        />
      ) : (
        <div className="px-3 py-8 text-center text-sm text-tertiary">Upload an .html / .htm file to render it here.</div>
      )}
      {src ? (
        <div className="border-t border-subtle px-3 py-1 text-[10px] text-tertiary">
          Sandboxed render (scripts allowed inside iframe only)
          <input
            type="range"
            min={200}
            max={900}
            value={height || 360}
            className="ml-3 align-middle"
            onChange={(e) => updateAttributes({ height: Number(e.target.value) })}
          />
        </div>
      ) : null}
    </NodeViewWrapper>
  );
}

export const HtmlArtifactExtension = Node.create({
  name: "htmlArtifact",
  group: "block",
  atom: true,
  selectable: true,
  draggable: true,

  addAttributes() {
    return {
      src: { default: "" },
      title: { default: "HTML artifact" },
      height: { default: 360 },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-type="html-artifact"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ["div", mergeAttributes(HTMLAttributes, { "data-type": "html-artifact" })];
  },

  addNodeView() {
    return ReactNodeViewRenderer(HtmlArtifactView);
  },

  addCommands() {
    return {
      setHtmlArtifact:
        (attrs?: Partial<HtmlArtifactAttrs>) =>
        ({ commands }) =>
          commands.insertContent({
            type: this.name,
            attrs: {
              src: attrs?.src ?? "",
              title: attrs?.title ?? "HTML artifact",
              height: attrs?.height ?? 360,
            },
          }),
    };
  },
});

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    htmlArtifact: {
      setHtmlArtifact: (attrs?: Partial<HtmlArtifactAttrs>) => ReturnType;
    };
  }
}
