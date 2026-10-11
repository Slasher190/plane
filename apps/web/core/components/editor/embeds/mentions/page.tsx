/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { useParams } from "next/navigation";
// plane imports
import { Logo } from "@plane/propel/emoji-icon-picker";
import { PageIcon } from "@plane/propel/icons";
import { getPageName } from "@plane/utils";
// hooks
import { EPageStoreType, usePage } from "@/hooks/store";

type Props = {
  id: string;
};

export const EditorPageMention = observer(function EditorPageMention(props: Props) {
  const { id } = props;
  const { workspaceSlug, projectId } = useParams();
  const page = usePage({ pageId: id, storeType: EPageStoreType.PROJECT });
  const href = workspaceSlug && projectId ? `/${workspaceSlug}/projects/${projectId}/pages/${id}` : undefined;
  const title = getPageName(page?.name);

  const content = (
    <span className="inline-flex items-center gap-1 rounded-sm bg-layer-1 px-1 py-0.5 text-13 text-accent-primary">
      {page?.logo_props?.in_use ? (
        <Logo logo={page.logo_props} size={12} type="lucide" />
      ) : (
        <PageIcon className="size-3" />
      )}
      <span className="truncate">{title || "Page"}</span>
    </span>
  );

  if (!href) return content;

  return (
    <Link href={href} className="no-underline">
      {content}
    </Link>
  );
});
