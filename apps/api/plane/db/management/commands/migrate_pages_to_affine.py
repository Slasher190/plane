# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Move Oneplace Pages into Oneplace Docs (AFFiNE).

    python manage.py migrate_pages_to_affine --workspace roinet-tech --dry-run
    python manage.py migrate_pages_to_affine --workspace roinet-tech

Layout in AFFiNE:
- one folder per project
- a "<Project> · Pages" index doc first in each folder
- a page with sub-pages becomes a folder holding the page and its children
- archived pages go into an "Archived" sub-folder

Private pages are skipped and reported, because every AFFiNE workspace member
can see every doc. Reruns skip pages already migrated. Nothing in Oneplace is
deleted; the page rows stay as a backup.
"""

import csv
import hashlib
import os
import re
from collections import defaultdict
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from plane.app.services.affine import AffineImportClient, doc_url, new_doc_id, order_key
from plane.db.models import (
    AffinePageLink,
    AffineProjectLink,
    AffineWorkspaceLink,
    Page,
    ProjectPage,
    Workspace,
)
from plane.utils.affine_markdown import html_to_markdown

PAGE_LINK_RE = re.compile(r"/projects/[0-9a-f-]{36}/pages/([0-9a-f-]{36})")


def short(uuid_value) -> str:
    return uuid_value.hex[:18]


def display(user) -> str:
    if not user:
        return "unknown"
    first, last = (user.first_name or "").strip(), (user.last_name or "").strip()
    name = first if last and first.endswith(last) else " ".join(p for p in (first, last) if p)
    return name or user.display_name or user.email


class Command(BaseCommand):
    help = "Migrate Oneplace Pages into Oneplace Docs (AFFiNE)."

    def add_arguments(self, parser):
        parser.add_argument("--workspace", required=True, help="Oneplace workspace slug")
        parser.add_argument("--owner-email", help="AFFiNE workspace owner (default: Oneplace workspace owner)")
        parser.add_argument("--affine-workspace", help="AFFiNE workspace id (default: the owner's only workspace)")
        parser.add_argument("--dry-run", action="store_true", help="Convert and report, write nothing")
        parser.add_argument("--report", help="CSV report path (default: plane/logs/affine-migration-<ts>.csv)")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        try:
            ws = Workspace.objects.get(slug=opts["workspace"])
        except Workspace.DoesNotExist:
            raise CommandError(f"No Oneplace workspace with slug {opts['workspace']!r}")
        owner_email = opts.get("owner_email") or ws.owner.email

        client = None
        affine_ws = opts.get("affine_workspace")
        try:
            client = AffineImportClient()
            if not affine_ws:
                link = AffineWorkspaceLink.objects.filter(workspace=ws).first()
                affine_ws = link.affine_workspace_id if link else None
            if not affine_ws:
                owned = client.owned_workspaces(owner_email)
                if len(owned) == 1:
                    affine_ws = owned[0]["id"]
                elif not dry:
                    names = ", ".join(f"{w['id']} ({w.get('name')})" for w in owned) or "none"
                    raise CommandError(
                        f"Pick the AFFiNE workspace with --affine-workspace. {owner_email} owns: {names}. "
                        "Create one in Docs first if there are none."
                    )
        except RuntimeError as exc:
            if not dry:
                raise CommandError(str(exc))
            self.stdout.write(self.style.WARNING(f"AFFiNE not reachable, dry run only converts: {exc}"))
            client = None
        affine_ws = affine_ws or "<affine-workspace>"

        pages = list(
            Page.objects.filter(workspace=ws, deleted_at__isnull=True)
            .select_related("owned_by", "parent")
            .order_by("sort_order", "created_at")
        )
        page_project = {}
        for pp in ProjectPage.objects.filter(page__in=pages, deleted_at__isnull=True).select_related("project"):
            page_project.setdefault(pp.page_id, pp.project)

        existing = {link.page_id: link for link in AffinePageLink.objects.filter(page__in=pages)}
        doc_ids = {p.id: (existing[p.id].affine_doc_id if p.id in existing else new_doc_id()) for p in pages}
        migratable = {p.id for p in pages if p.access != Page.PRIVATE_ACCESS}

        def rewrite(href: str) -> str:
            m = PAGE_LINK_RE.search(href)
            if m:
                for p in pages:
                    if str(p.id) == m.group(1) and p.id in migratable:
                        return doc_url(affine_ws, doc_ids[p.id])
            return href

        children = defaultdict(list)
        for p in pages:
            if p.parent_id and p.parent_id in migratable and p.id in migratable:
                children[p.parent_id].append(p)

        author_exists = {}

        def has_affine_account(email):
            if client is None or not email:
                return False
            if email not in author_exists:
                author_exists[email] = client.user_exists(email)
            return author_exists[email]

        rows = []
        created = 0
        for p in pages:
            title = (p.name or "").strip() or "Untitled"
            project = page_project.get(p.id)
            row = {
                "page_id": str(p.id), "title": title, "project": project.name if project else "",
                "owner": p.owned_by.email if p.owned_by_id else "", "status": "", "affine_url": "", "warnings": "",
            }
            if p.id not in migratable:
                row["status"] = "skipped: private page (stays in Oneplace)"
                rows.append(row)
                continue
            if p.id in existing:
                row.update(status="already migrated", affine_url=doc_url(affine_ws, doc_ids[p.id]))
                rows.append(row)
                continue

            body, warnings = html_to_markdown(p.description_html or "", rewrite)
            notes = []
            owner_email_p = p.owned_by.email if p.owned_by_id else None
            if not has_affine_account(owner_email_p):
                notes.append(f"Originally written by {display(p.owned_by)} on {p.created_at:%d %b %Y} in Oneplace Pages.")
            if p.archived_at:
                notes.append(f"Archived in Oneplace on {p.archived_at:%d %b %Y}.")
            if p.is_locked:
                notes.append("This page was locked in Oneplace.")
                warnings.append("page was locked (Docs has no lock)")
            parts = [f"*{n}*" for n in notes]
            if body.strip():
                parts.append(body.strip())
            if children.get(p.id):
                links = "\n".join(
                    f"- [{(c.name or '').strip() or 'Untitled'}]({doc_url(affine_ws, doc_ids[c.id])})"
                    for c in children[p.id]
                )
                parts.append("## Sub-pages\n\n" + links)
            markdown = "\n\n".join(parts) + "\n" if parts else ""
            if not project:
                warnings.append("page belongs to no project (placed in General)")
            row["warnings"] = "; ".join(warnings)
            row["affine_url"] = doc_url(affine_ws, doc_ids[p.id])

            if dry:
                row["status"] = f"would create ({len(markdown)} chars)"
                rows.append(row)
                continue

            client.create_doc(
                affine_ws, doc_ids[p.id], title, markdown or " ",
                editor_email=owner_email_p, create_date_ms=int(p.created_at.timestamp() * 1000),
            )
            AffinePageLink.objects.create(
                page=p, affine_workspace_id=affine_ws, affine_doc_id=doc_ids[p.id],
                source_hash=hashlib.sha256((p.description_html or "").encode()).hexdigest(),
                warnings=row["warnings"],
            )
            created += 1
            row["status"] = "created"
            rows.append(row)

        # ---------- folders + project index docs ----------
        by_project = defaultdict(list)
        for p in pages:
            if p.id in migratable:
                by_project[page_project.get(p.id)].append(p)

        nodes = []
        for pi, (project, plist) in enumerate(sorted(by_project.items(), key=lambda kv: kv[0].name if kv[0] else "~")):
            key = short(project.id) if project else "general" + short(ws.id)[:11]
            folder_id = "opf" + key
            nodes.append({"id": folder_id, "parentId": None, "type": "folder",
                          "data": project.name if project else "General", "index": order_key(pi)})

            plink = AffineProjectLink.objects.filter(project=project).first() if project else None
            index_doc = plink.index_doc_id if plink else new_doc_id()
            top = [p for p in plist if not (p.parent_id and p.parent_id in migratable)]
            live = [p for p in top if not p.archived_at]
            archived = [p for p in top if p.archived_at]
            if not plink:
                lines = [f"Pages of **{project.name if project else 'General'}**, moved from Oneplace Pages."]
                if live:
                    lines.append("\n".join(f"- [{(p.name or '').strip() or 'Untitled'}]({doc_url(affine_ws, doc_ids[p.id])})" for p in live))
                if archived:
                    lines.append("## Archived\n\n" + "\n".join(
                        f"- [{(p.name or '').strip() or 'Untitled'}]({doc_url(affine_ws, doc_ids[p.id])})" for p in archived))
                if not dry:
                    client.create_doc(affine_ws, index_doc, f"{project.name if project else 'General'} · Pages",
                                      "\n\n".join(lines) + "\n", editor_email=owner_email)
                    if project:
                        AffineProjectLink.objects.create(project=project, affine_workspace_id=affine_ws,
                                                         folder_id=folder_id, index_doc_id=index_doc)
                rows.append({"page_id": "", "title": f"{project.name if project else 'General'} · Pages",
                             "project": project.name if project else "", "owner": owner_email,
                             "status": "would create index" if dry else "created index",
                             "affine_url": doc_url(affine_ws, index_doc), "warnings": ""})
            nodes.append({"id": "opi" + key, "parentId": folder_id, "type": "doc", "data": index_doc, "index": order_key(0)})

            def place(page, parent_id, idx):
                if children.get(page.id):
                    sub_id = "opg" + short(page.id)
                    nodes.append({"id": sub_id, "parentId": parent_id, "type": "folder",
                                  "data": (page.name or "").strip() or "Untitled", "index": order_key(idx)})
                    nodes.append({"id": "opd" + short(page.id), "parentId": sub_id, "type": "doc",
                                  "data": doc_ids[page.id], "index": order_key(0)})
                    for ci, child in enumerate(children[page.id], start=1):
                        place(child, sub_id, ci)
                else:
                    nodes.append({"id": "opd" + short(page.id), "parentId": parent_id, "type": "doc",
                                  "data": doc_ids[page.id], "index": order_key(idx)})

            for i, p in enumerate(live, start=1):
                place(p, folder_id, i)
            if archived:
                arch_id = "opa" + key
                nodes.append({"id": arch_id, "parentId": folder_id, "type": "folder", "data": "Archived",
                              "index": order_key(len(live) + 1)})
                for i, p in enumerate(archived):
                    place(p, arch_id, i)

        if not dry:
            client.upsert_folders(affine_ws, nodes)
            AffineWorkspaceLink.objects.update_or_create(workspace=ws, defaults={"affine_workspace_id": affine_ws})

        # ---------- report ----------
        path = opts.get("report") or os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "logs", f"affine-migration-{datetime.now():%Y%m%d-%H%M%S}.csv"
        )
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["page_id", "title", "project", "owner", "status", "affine_url", "warnings"])
            writer.writeheader()
            writer.writerows(rows)

        for r in rows:
            self.stdout.write(f"{r['status'][:28]:28} | {r['project'][:16]:16} | {r['title'][:44]:44} | {r['warnings']}")
        skipped = sum(1 for r in rows if r["status"].startswith("skipped"))
        self.stdout.write(self.style.SUCCESS(
            f"{'DRY RUN — nothing written. ' if dry else ''}pages: {len(pages)}, created: {created}, "
            f"skipped: {skipped}, folder nodes: {len(nodes)}, AFFiNE workspace: {affine_ws}. Report: {path}"
        ))
