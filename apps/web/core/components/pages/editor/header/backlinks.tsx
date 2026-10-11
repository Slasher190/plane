/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { useParams } from "next/navigation";
// plane imports
import { Button } from "@plane/propel/button";
import { Logo } from "@plane/propel/emoji-icon-picker";
import { PageIcon } from "@plane/propel/icons";
import type { TPageBacklink } from "@plane/types";
import { getPageName } from "@plane/utils";
// hooks
import type { EPageStoreType } from "@/hooks/store";
import { usePageStore } from "@/hooks/store";

type Props = {
  pageId: string;
  storeType: EPageStoreType;
};

export const PageEditorBacklinks = observer(function PageEditorBacklinks(props: Props) {
  const { pageId, storeType } = props;
  const { workspaceSlug, projectId } = useParams();
  const { fetchBacklinks } = usePageStore(storeType);
  const [backlinks, setBacklinks] = useState<TPageBacklink[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    fetchBacklinks(pageId)
      .then((result) => {
        if (!cancelled) setBacklinks(result || []);
        return result;
      })
      .catch(() => {
        if (!cancelled) setBacklinks([]);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [fetchBacklinks, pageId]);

  if (isLoading || backlinks.length === 0) return null;

  return (
    <div className="mb-3">
      <Button variant="ghost" size="sm" onClick={() => setIsOpen((prev) => !prev)}>
        {backlinks.length} {backlinks.length === 1 ? "backlink" : "backlinks"}
      </Button>
      {isOpen && workspaceSlug && projectId && (
        <div className="mt-2 space-y-1 rounded-md border border-subtle bg-surface-1 p-2">
          {backlinks.map((backlink) => (
            <Link
              key={backlink.id}
              href={`/${workspaceSlug}/projects/${projectId}/pages/${backlink.id}`}
              className="flex items-center gap-2 rounded-sm px-2 py-1.5 text-13 hover:bg-layer-1"
            >
              {backlink.logo_props?.in_use ? (
                <Logo logo={backlink.logo_props} size={14} type="lucide" />
              ) : (
                <PageIcon className="h-3.5 w-3.5 text-tertiary" />
              )}
              <span className="truncate">{getPageName(backlink.name)}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
});
