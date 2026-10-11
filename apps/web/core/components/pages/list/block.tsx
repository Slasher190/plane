/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import { combine } from "@atlaskit/pragmatic-drag-and-drop/combine";
import { draggable, dropTargetForElements } from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { attachInstruction, extractInstruction } from "@atlaskit/pragmatic-drag-and-drop-hitbox/tree-item";
import { observer } from "mobx-react";
import { useParams, useRouter } from "next/navigation";
import { ChevronDown, ChevronRight, Plus } from "lucide-react";
// plane imports
import { EPageAccess } from "@plane/constants";
import { Logo } from "@plane/propel/emoji-icon-picker";
import { IconButton } from "@plane/propel/icon-button";
import { PageIcon } from "@plane/propel/icons";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TPage, TPageNavigationTabs } from "@plane/types";
import { cn, getPageName } from "@plane/utils";
// components
import { ListItem } from "@/components/core/list";
import { BlockItemAction } from "@/components/pages/list/block-item-action";
// hooks
import { usePlatformOS } from "@/hooks/use-platform-os";
import type { EPageStoreType } from "@/hooks/store";
import { usePage, usePageStore } from "@/hooks/store";

type TPageListBlock = {
  pageId: string;
  storeType: EPageStoreType;
  pageType: TPageNavigationTabs;
  depth?: number;
  isFlat?: boolean;
};

const PAGE_MAX_DEPTH = 10;

export const PageListBlock = observer(function PageListBlock(props: TPageListBlock) {
  const { pageId, storeType, pageType, depth = 0, isFlat = false } = props;
  const parentRef = useRef<HTMLDivElement>(null);
  const [isExpanded, setIsExpanded] = useState(depth < 1);
  const [isDragging, setIsDragging] = useState(false);
  const [dropInstruction, setDropInstruction] = useState<"make-child" | "reorder-above" | "reorder-below" | null>(null);
  const [isCreatingChild, setIsCreatingChild] = useState(false);

  const page = usePage({ pageId, storeType });
  const { isMobile } = usePlatformOS();
  const { getChildPageIds, isDescendantPage, updatePageParent, createPage, canCurrentUserCreatePage } =
    usePageStore(storeType);
  const router = useRouter();
  const { workspaceSlug, projectId } = useParams();

  const childIds = isFlat ? [] : getChildPageIds(pageId, pageType);
  const hasChildren = childIds.length > 0;

  useEffect(() => {
    const element = parentRef.current;
    if (!element || !page?.id || isFlat) return;

    return combine(
      draggable({
        element,
        getInitialData: () => ({ id: pageId, dragInstanceId: "PAGES" }),
        onDragStart: () => setIsDragging(true),
        onDrop: () => setIsDragging(false),
      }),
      dropTargetForElements({
        element,
        canDrop: ({ source }) =>
          source?.data?.dragInstanceId === "PAGES" &&
          typeof source?.data?.id === "string" &&
          source.data.id !== pageId &&
          !isDescendantPage(source.data.id as string, pageId),
        getData: ({ input, element: el }) =>
          attachInstruction(
            { id: pageId },
            {
              input,
              element: el,
              currentLevel: depth,
              indentPerLevel: 16,
              mode: "standard",
              block: depth >= PAGE_MAX_DEPTH - 1 ? ["make-child"] : [],
            }
          ),
        onDrag: ({ self }) => {
          const instruction = extractInstruction(self.data);
          if (!instruction) {
            setDropInstruction(null);
            return;
          }
          if (instruction.type === "make-child") setDropInstruction("make-child");
          else if (instruction.type === "reorder-above") setDropInstruction("reorder-above");
          else if (instruction.type === "reorder-below") setDropInstruction("reorder-below");
          else setDropInstruction(null);
        },
        onDragLeave: () => setDropInstruction(null),
        onDrop: async ({ source, self }) => {
          setDropInstruction(null);
          const sourceId = source?.data?.id as string | undefined;
          const instruction = extractInstruction(self.data);
          if (!sourceId || !instruction || !page) return;

          try {
            if (instruction.type === "make-child") {
              if (depth + 1 > PAGE_MAX_DEPTH) {
                setToast({
                  type: TOAST_TYPE.ERROR,
                  title: "Too deep",
                  message: `Pages cannot be nested more than ${PAGE_MAX_DEPTH} levels.`,
                });
                return;
              }
              await updatePageParent(sourceId, pageId);
              setIsExpanded(true);
            } else if (instruction.type === "reorder-above" || instruction.type === "reorder-below") {
              const siblingSort = page.sort_order ?? 65535;
              const nextSort = instruction.type === "reorder-above" ? siblingSort - 1000 : siblingSort + 1000;
              await updatePageParent(sourceId, page.parent ?? null, nextSort);
            }
          } catch (error: any) {
            setToast({
              type: TOAST_TYPE.ERROR,
              title: "Error",
              message: error?.error || "Could not move the page.",
            });
          }
        },
      })
    );
  }, [depth, isDescendantPage, isFlat, page, pageId, updatePageParent]);

  if (!page) return null;

  const { name, logo_props, getRedirectionLink } = page;

  const handleCreateChild = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!canCurrentUserCreatePage || depth + 1 > PAGE_MAX_DEPTH) {
      if (depth + 1 > PAGE_MAX_DEPTH) {
        setToast({
          type: TOAST_TYPE.ERROR,
          title: "Too deep",
          message: `Pages cannot be nested more than ${PAGE_MAX_DEPTH} levels.`,
        });
      }
      return;
    }
    setIsCreatingChild(true);
    const payload: Partial<TPage> = {
      parent: pageId,
      access: pageType === "private" ? EPageAccess.PRIVATE : EPageAccess.PUBLIC,
    };
    try {
      const created = await createPage(payload);
      setIsExpanded(true);
      if (created?.id && workspaceSlug && projectId) {
        router.push(`/${workspaceSlug}/projects/${projectId}/pages/${created.id}`);
      }
    } catch (error: any) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error",
        message: error?.error || "Page could not be created.",
      });
    } finally {
      setIsCreatingChild(false);
    }
  };

  return (
    <div>
      <div
        className={cn("relative", {
          "opacity-50": isDragging,
          "bg-accent-primary/10": dropInstruction === "make-child",
        })}
      >
        {dropInstruction === "reorder-above" && (
          <div className="absolute top-0 right-0 left-0 z-10 h-0.5 bg-accent-primary" />
        )}
        {dropInstruction === "reorder-below" && (
          <div className="absolute right-0 bottom-0 left-0 z-10 h-0.5 bg-accent-primary" />
        )}
        <ListItem
          prependTitleElement={
            <div className="flex items-center gap-1" style={{ paddingLeft: isFlat ? 0 : depth * 16 }}>
              {!isFlat ? (
                <IconButton
                  variant="ghost"
                  size="sm"
                  icon={isExpanded ? ChevronDown : ChevronRight}
                  className={cn("text-tertiary", !hasChildren && "invisible")}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setIsExpanded((prev) => !prev);
                  }}
                  aria-label={isExpanded ? "Collapse subpages" : "Expand subpages"}
                />
              ) : null}
              {logo_props?.in_use ? (
                <Logo logo={logo_props} size={16} type="lucide" />
              ) : (
                <PageIcon className="h-4 w-4 text-tertiary" />
              )}
            </div>
          }
          title={getPageName(name)}
          itemLink={getRedirectionLink()}
          appendTitleElement={
            canCurrentUserCreatePage && !isFlat && pageType !== "archived" ? (
              <IconButton
                variant="ghost"
                size="sm"
                icon={Plus}
                className="invisible text-tertiary group-hover:visible"
                onClick={handleCreateChild}
                disabled={isCreatingChild}
                aria-label="Add subpage"
              />
            ) : undefined
          }
          actionableItems={<BlockItemAction page={page} parentRef={parentRef} storeType={storeType} />}
          isMobile={isMobile}
          parentRef={parentRef}
        />
      </div>
      {!isFlat &&
        isExpanded &&
        childIds.map((childId) => (
          <PageListBlock key={childId} pageId={childId} storeType={storeType} pageType={pageType} depth={depth + 1} />
        ))}
    </div>
  );
});
