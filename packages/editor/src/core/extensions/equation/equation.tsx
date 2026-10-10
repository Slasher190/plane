/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { mergeAttributes, Node, nodeInputRule } from "@tiptap/core";
import { ReactNodeViewRenderer, NodeViewWrapper } from "@tiptap/react";
import katex from "katex";
import { useMemo } from "react";
import "katex/dist/katex.min.css";

type EquationAttrs = { latex: string; display: boolean };

function EquationView({ node }: { node: { attrs: EquationAttrs } }) {
  const { latex, display } = node.attrs;
  const html = useMemo(() => {
    try {
      return katex.renderToString(latex || "", {
        throwOnError: false,
        displayMode: display,
      });
    } catch (error) {
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
  group: "block",
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
      display: { default: true },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-type="equation"]' }, { tag: 'span[data-type="equation"]' }];
  },

  renderHTML({ node, HTMLAttributes }) {
    const tag = node.attrs.display ? "div" : "span";
    return [
      tag,
      mergeAttributes(this.options.HTMLAttributes, HTMLAttributes, {
        "data-type": "equation",
        "data-latex": node.attrs.latex,
        "data-display": node.attrs.display ? "true" : "false",
      }),
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(EquationView);
  },

  addCommands() {
    return {
      setEquation:
        (attrs: Partial<EquationAttrs>) =>
        ({ commands }) =>
          commands.insertContent({
            type: this.name,
            attrs: { latex: attrs.latex ?? "", display: attrs.display ?? true },
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
