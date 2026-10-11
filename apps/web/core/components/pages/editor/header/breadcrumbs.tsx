/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronRight } from "lucide-react";
// plane imports
import { getPageName } from "@plane/utils";
// hooks
import type { EPageStoreType } from "@/hooks/store";
import { usePageStore } from "@/hooks/store";

type Props = {
  pageId: string;
  storeType: EPageStoreType;
};

export const PageEditorBreadcrumbs = observer(function PageEditorBreadcrumbs(props: Props) {
  const { pageId, storeType } = props;
  const { workspaceSlug, projectId } = useParams();
  const { getPageAncestorIds, getPageById } = usePageStore(storeType);

  const crumbs = useMemo(() => {
    const ancestorIds = getPageAncestorIds(pageId);
    if (ancestorIds.length === 0) return [];

    const mapped = ancestorIds.map((id) => ({
      id,
      name: getPageName(getPageById(id)?.name),
    }));

    if (mapped.length <= 3) return mapped;

    return [mapped[0], { id: "__ellipsis__", name: "..." }, ...mapped.slice(-2)];
  }, [getPageAncestorIds, getPageById, pageId]);

  if (!crumbs.length || !workspaceSlug || !projectId) return null;

  return (
    <nav className="mb-2 flex flex-wrap items-center gap-1 text-12 text-secondary" aria-label="Breadcrumb">
      {crumbs.map((crumb, index) => {
        const isLast = index === crumbs.length - 1;
        if (crumb.id === "__ellipsis__") {
          return (
            <span key="breadcrumb-ellipsis" className="flex items-center gap-1">
              <span>{crumb.name}</span>
              {!isLast && <ChevronRight className="size-3" />}
            </span>
          );
        }
        return (
          <span key={crumb.id} className="flex items-center gap-1">
            <Link
              href={`/${workspaceSlug}/projects/${projectId}/pages/${crumb.id}`}
              className="truncate hover:text-primary"
            >
              {crumb.name}
            </Link>
            {!isLast && <ChevronRight className="size-3" />}
          </span>
        );
      })}
    </nav>
  );
});
