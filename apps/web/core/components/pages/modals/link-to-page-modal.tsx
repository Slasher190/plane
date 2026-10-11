/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { Button } from "@plane/propel/button";
import { Logo } from "@plane/propel/emoji-icon-picker";
import { PageIcon } from "@plane/propel/icons";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
import { getPageName } from "@plane/utils";
// hooks
import type { EPageStoreType } from "@/hooks/store";
import { usePageStore } from "@/hooks/store";
// store
import type { TPageInstance } from "@/store/pages/base-page";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  page: TPageInstance;
  storeType: EPageStoreType;
};

const PAGE_MAX_DEPTH = 10;

export const LinkToPageModal = observer(function LinkToPageModal(props: Props) {
  const { isOpen, onClose, page, storeType } = props;
  const [query, setQuery] = useState("");
  const { data, isDescendantPage, updatePageParent, getPageAncestorIds } = usePageStore(storeType);

  const candidates = useMemo(() => {
    if (!page.id) return [];
    const q = query.trim().toLowerCase();
    return Object.values(data || {}).filter((candidate) => {
      if (!candidate.id || candidate.id === page.id) return false;
      if (candidate.archived_at) return false;
      if (isDescendantPage(page.id!, candidate.id)) return false;
      const depth = getPageAncestorIds(candidate.id).length;
      if (depth + 1 > PAGE_MAX_DEPTH) return false;
      if (q && !getPageName(candidate.name).toLowerCase().includes(q)) return false;
      return true;
    });
  }, [data, getPageAncestorIds, isDescendantPage, page.id, query]);

  const handleSelect = async (parentId: string) => {
    if (!page.id) return;
    try {
      await updatePageParent(page.id, parentId);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Page nested",
        message: "The page is now nested under the selected page.",
      });
      onClose();
    } catch (error: any) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error",
        message: error?.error || "Could not nest the page. Please try again.",
      });
    }
  };

  const handleMakeTopLevel = async () => {
    if (!page.id || !page.parent) return;
    try {
      await updatePageParent(page.id, null);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Page moved",
        message: "The page is now a top-level page.",
      });
      onClose();
    } catch (error: any) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Error",
        message: error?.error || "Could not move the page. Please try again.",
      });
    }
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.CENTER} width={EModalWidth.LG}>
      <div className="space-y-4 p-5">
        <div>
          <h3 className="text-16 font-medium">Link to page</h3>
          <p className="mt-1 text-13 text-secondary">Nest this page under another page in the project.</p>
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search pages"
          className="focus:border-accent w-full rounded-md border border-subtle bg-transparent px-3 py-2 text-13 outline-none"
        />
        <div className="max-h-72 space-y-1 overflow-y-auto">
          {page.parent && (
            <Button variant="ghost" size="lg" onClick={handleMakeTopLevel} className="w-full justify-start">
              Move to top level
            </Button>
          )}
          {candidates.map((candidate) => (
            <Button
              key={candidate.id}
              variant="ghost"
              size="lg"
              onClick={() => candidate.id && handleSelect(candidate.id)}
              className="w-full justify-start"
            >
              {candidate.logo_props?.in_use ? (
                <Logo logo={candidate.logo_props} size={16} type="lucide" />
              ) : (
                <PageIcon className="h-4 w-4 shrink-0 text-tertiary" />
              )}
              <span className="truncate">{getPageName(candidate.name)}</span>
            </Button>
          ))}
          {candidates.length === 0 && (
            <p className="px-2 py-4 text-center text-13 text-secondary">No pages available to nest under.</p>
          )}
        </div>
      </div>
    </ModalCore>
  );
});
