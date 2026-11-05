/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// hooks
import { useMultipleSelectStore } from "@/hooks/store/use-multiple-select-store";
import type { TSelectionHelper } from "@/hooks/use-multiple-select";

type Props = {
  className?: string;
  selectionHelpers: TSelectionHelper;
};

// Oneplace: bulk operations are not part of CE; the upsell banner is removed.
export const IssueBulkOperationsRoot = observer(function IssueBulkOperationsRoot(_props: Props) {
  // store hooks (kept so selection state stays observed)
  useMultipleSelectStore();
  return null;
});
