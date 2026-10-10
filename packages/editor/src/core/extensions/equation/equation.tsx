/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { mergeAttributes, Node, nodeInputRule } from "@tiptap/core";
import { ReactNodeViewRenderer, NodeViewWrapper, type NodeViewProps } from "@tiptap/react";
import katex from "katex";
import { useMemo } from "react";
import "katex/dist/katex.min.css";

type EquationAttrs = { latex: string; display: boolean };

function EquationView({ node }: NodeViewProps) {
  const latex = String(node.attrs.latex ?? "");
  const display = Boolean(node.attrs.display);
  const html = useMemo(() => {
    try {
      return katex.renderToString(latex || "", {
        throwOnError: false,
        displayMode: display,
      });
    } catch {
      return `<span class="text-danger-primary">Invalid LaTeX</span>`;
    }
  }, [latex, display]);

  return (
    <NodeViewWrapper
      as={display ? "div" : "span"}
      className={display ? "my-3 text-center overflow-x-auto" : "inline-block px-0.5"}
      data-type="equation"
    >
      <span contentEditable={false} dangerouslySetInnerHTML={{ __html: html }} />
    </NodeViewWrapper>
  );
}

export const EquationExtension = Node.create({
  name: "equation",
  group: "inline",
  inline: true,
  atom: true,
  selectable: true,

  addOptions() {
    return {
      HTMLAttributes: {},
    };
  },

  addAttributes() {
    return {
      latex: { default: "" },
      display: { default: false },
    };
  },

  parseHTML() {
    return [{ tag: 'span[data-type="equation"]' }, { tag: 'div[data-type="equation"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      "span",
      mergeAttributes(this.options.HTMLAttributes, HTMLAttributes, {
        "data-type": "equation",
      }),
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(EquationView);
  },

  addCommands() {
    return {
      setEquation:
        (attrs?: Partial<EquationAttrs>) =>
        ({ commands }) =>
          commands.insertContent({
            type: this.name,
            attrs: { latex: attrs?.latex ?? "", display: attrs?.display ?? false },
          }),
    };
  },

  addInputRules() {
    return [
      nodeInputRule({
        find: /\$\$([^$]+)\$\$$/,
        type: this.type,
        getAttributes: (match) => ({
          latex: match[1]?.trim() ?? "",
          display: true,
        }),
      }),
      nodeInputRule({
        find: /(?:^|[^$])\$([^$\n]+)\$$/,
        type: this.type,
        getAttributes: (match) => ({
          latex: match[1]?.trim() ?? "",
          display: false,
        }),
      }),
    ];
  },
});

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    equation: {
      setEquation: (attrs?: Partial<EquationAttrs>) => ReturnType;
    };
  }
}
