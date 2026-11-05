# Oneplace Docs on AFFiNE — design

Date: 2026-11-05 · Status: draft for approval

## 1. Intent

Oneplace (our Plane CE fork, branch `oneplace-ce`, pinned to upstream `v1.4.2`, deployed on the
UAT box `192.168.1.177`) has a **Pages** feature. The team finds it too weak for real
documentation. We are replacing it with **AFFiNE** (https://github.com/toeverything/affine),
self-hosted next to Oneplace.

It must feel like one product:

- **Docs** sits in the workspace sidebar next to **Chat**. One click opens AFFiNE already signed
  in as the same person, the same way Chat opens Rocket.Chat today. There is no second login.
- Every existing page moves to AFFiNE. After that, the old Pages feature is removed.
- AFFiNE's AI runs on **our** provider: the same Ollama Cloud credentials an admin already sets in
  god-mode → AI. Keys are managed in one place.
- The `oneplace` MCP gains doc tools. AI clients (Cursor, Claude) can then create and edit AFFiNE
  docs through the same MCP connection and API token they already use for work items.
- All pricing, upgrade and paid-plan prompts are removed from **Oneplace**.

## 2. Goals

1. Deploy AFFiNE in the existing `plane-app` compose stack on UAT, behind the existing host nginx.
2. Single sign-on, with Oneplace as the only identity source. AFFiNE accounts are created
   automatically. Nobody types an AFFiNE password.
3. Each Oneplace workspace has one AFFiNE workspace. Membership is kept in sync automatically
   (join, leave), the same way the Rocket.Chat team sync works.
4. Migrate all Oneplace pages into AFFiNE. The migration can be rerun safely and writes a report
   for each page.
5. Remove Pages from Oneplace (UI, routes, project feature toggle, MCP `page` tool) once the
   migration is verified.
6. Wire AFFiNE AI to the god-mode LLM settings (Ollama Cloud).
7. Add MCP doc tools to the `oneplace` MCP server.
8. Remove the Oneplace pricing, upgrade and plan UI.

## 3. Non-goals

- **Do not hide or strip any AFFiNE feature.** Use the stock AFFiNE image with every feature
  available. Only the AI provider is ours.
- Do not migrate page version history (`PageVersion`). Only current content moves.
- No two-way sync between Pages and AFFiNE. Pages is retired, not mirrored.
- No changes to Rocket.Chat.

## 4. Anti-goals (failure even if it "works")

- A user sees an AFFiNE login form or has to set an AFFiNE password.
- A page is silently lost or silently truncated during migration. Every conversion loss must
  appear in the report.
- A private page becomes visible to anyone other than its owner.
- Old page data is deleted from the Oneplace database.
- AI keys are copied by hand into a second place that drifts from god-mode.
- Existing uncommitted work in `plane-src` is overwritten (see §11).
- Internal "act as user" machinery (§6.3) is reachable from outside the server.

## 5. Decided by the user

- Entry point: a sidebar **Docs** item that works like **Chat** (SSO redirect, already signed in).
- Old Pages are removed after migration, not kept read-only.
- Pricing and premium buttons are removed in Oneplace.
- AFFiNE keeps every feature. The AI provider is ours (Ollama credentials from Oneplace).
- The `oneplace` MCP can create and edit AFFiNE docs.

## 6. Architecture

```
browser ── host nginx :443
  oneplace.roinetinsurance.in  ├─ /chat → Rocket.Chat
                               ├─ /mcp/ → plane-mcp (+ new doc tools)
                               └─ /     → Plane Caddy (web, api, admin, live, space)
  docs.roinetinsurance.in      └─ /     → affine :3010            (new)

affine ──OIDC (login)──────────► Oneplace API (new OIDC provider)
affine ──BYOK LLM──────────────► Ollama Cloud https://ollama.com/v1
Oneplace API ──HTTP (internal)──► affine-bridge (new, Node) ──GraphQL + socket.io──► affine
plane-mcp doc tools ──HTTP──────► Oneplace API /api/v1/workspaces/{slug}/docs/...
```

AFFiNE target version: **v0.27.4** (latest stable, 2026-08-18), pinned by tag. Do not use
`:stable`. AFFiNE facts behind this design are in §12.

### 6.1 Hosting

- **Own subdomain `docs.roinetinsurance.in`.** AFFiNE cannot run under a sub-path:
  `AFFINE_SERVER_SUB_PATH` breaks the web frontend (upstream issue #13341). The existing
  `*.roinetinsurance.in` certificate covers it. It needs DNS records like Oneplace's (office DNS
  `192.168.1.250` and public, → `49.249.45.99`). Until then, a hosts-file line works.
- New nginx server block `plane-selfhost/scripts/oneplace-docs.nginx.conf`, proxying to
  `127.0.0.1:<port>`, with WebSocket upgrade (`/socket.io/`) and a large `client_max_body_size`
  (100 MB blobs).
- New compose services in `plane-selfhost/plane-app/docker-compose.yaml`:
  - `affine` (`ghcr.io/toeverything/affine:0.27.4`). Published on `127.0.0.1` only, on a free port
    (check the port table in `UAT-SERVER.md`).
  - `affine-migration`, the one-shot `node ./scripts/self-host-predeploy.js` job.
  - `affine-db` (`pgvector/pgvector:pg16`). AFFiNE needs pgvector, so it gets its own Postgres
    instead of sharing Plane's.
  - Reuse Plane's Redis with DB index `3` (`0` Plane, `1` Rocket.Chat, `2` MCP OAuth).
  - `affine-bridge` (§6.3), internal network only, never published.
- Data under `/home/plane/data/affine/{storage,config,postgres}`, using the same bind-volume style
  as Rocket.Chat. Blobs go in local storage (builder may switch to MinIO if AFFiNE's S3 storage
  provider works cleanly with it).
- The AFFiNE container must resolve `oneplace.roinetinsurance.in` to reach the OIDC issuer. Use an
  `extra_hosts` entry pointing at the host gateway, and set `allowPrivateNetwork: true` in the OIDC
  config.
- The UAT host can't reliably pull from public registries. Pull and `docker save` the images
  off-box, then load them, the same way as the custom Oneplace images.
- Compose resource limits as for Rocket.Chat. About 14 GB of RAM is free.
- Update `UAT-SERVER.md`: URL, ports, data paths, Redis index, service account, how to recover.

### 6.2 SSO

Rocket.Chat SSO writes Meteor resume tokens straight into Mongo. AFFiNE uses the supported path
instead: **Oneplace becomes an OpenID Connect provider**, and AFFiNE's OIDC login points at it.

- Oneplace API: add an OIDC provider. Recommended: `django-oauth-toolkit` with OIDC on, RS256
  signing key from env.
  - Discovery at `<issuer>/.well-known/openid-configuration`. The issuer string must match exactly.
  - PKCE is supported.
  - Userinfo returns `sub` (Oneplace user id), `email`, `email_verified: true` and `name`.
  - One confidential client is registered for AFFiNE, auto-approved (no consent screen), with
    redirect `https://docs.roinetinsurance.in/oauth/callback`.
  - The exact issuer path is the builder's call. It must not collide with existing `/auth/` routes.
- AFFiNE `config.json` settings:
  - `oauth.providers.oidc` = issuer, client id/secret, scope `openid profile email`, default claim
    mapping, `allowPrivateNetwork: true`.
  - `auth.allowSignup: false` (no password or magic-link sign-up).
  - `auth.allowSignupForOauth: true`.
  - `auth.newAccountShareActionDelay: 0`.
  - AFFiNE has no switch to turn off password sign-in. OIDC-created accounts have no password, so
    in practice OIDC is the only way in. Don't patch the image for this.
- New endpoint `GET /api/workspaces/{slug}/docs/sso/`, mirroring `WorkspaceChatSSOEndpoint`:
  1. It makes sure the user has an AFFiNE account and is a member of the linked workspace (§6.4).
  2. It redirects to
     `https://docs.roinetinsurance.in/oauth/login?provider=OIDC&redirect_uri=/workspace/<affine_ws_id>`.
  3. AFFiNE starts OIDC. The user already has a Oneplace session, so authorize completes with no
     prompt, and they land in the workspace signed in.
- Sidebar: add a new static nav item `docs` next to `chat` in `packages/constants/src/workspace.ts`,
  resolved like chat in `sidebar-item.tsx`. The i18n key `sidebar.docs` is "Docs".
- Feature switch: `AFFINE_ENABLED` and `AFFINE_PUBLIC_URL` in env, like `ROCKETCHAT_ENABLED`. The
  Docs item is hidden when the switch is off.

### 6.3 affine-bridge (acting inside AFFiNE)

AFFiNE 0.27 has no personal access tokens. It has no API to import Markdown, and no API to add a
member directly. Docs, folders and timestamps can only be written by a signed-in client pushing
Yjs updates over socket.io. Oneplace therefore needs a small internal **Node** service that holds
AFFiNE sessions and does that work.

- New package `plane-selfhost/plane-app/affine-bridge/` (TypeScript, Dockerfile). It reuses the
  Markdown→Yjs and socket.io code from **DAWNCR0W/affine-mcp-server v3.11.0 (MIT)**, vendored or as
  a dependency, with attribution.
- How it gets a session for a Oneplace user:
  - It runs AFFiNE's OIDC login itself (preflight → Oneplace authorize → AFFiNE callback) and
    captures the session cookie.
  - The Oneplace authorize step identifies the user through an **internal-only impersonation
    grant**. The grant is a short-lived token signed with a shared secret (`AFFINE_BRIDGE_SECRET`)
    and accepted only from the compose network. nginx must not route it.
  - Sessions are cached in Redis (DB 3, separate key prefix) until expiry.
- **Service account `oneplace-bot`**: an AFFiNE administrator account created at bootstrap. It owns
  every synced AFFiNE workspace, so ownership doesn't depend on any one person.
- API, called only by Oneplace API with the shared secret:
  - ensure user
  - ensure workspace
  - add/remove member
  - set BYOK profile
  - create, read, update, append, move and delete a doc
  - search
  - list folders/docs
  - set folder tree entries
  - set doc meta (title, tags, createDate, createdBy, icon)
- Every write runs **as the Oneplace user**, so AFFiNE shows the right author. Workspace and admin
  operations run as `oneplace-bot`.

### 6.4 Workspace and member sync

New `plane/app/services/affine.py` and models, mirroring `rocketchat.py`:

- `AffineWorkspaceLink(workspace → affine_workspace_id)` and `AffineUserLink(user → affine_user_id)`.
- Workspace: created by `oneplace-bot` with the same name as the Oneplace workspace, and renamed
  when the Oneplace workspace is renamed.
- Member add:
  1. The bridge makes sure the AFFiNE user exists (admin `createUser`, or OIDC first login).
  2. `oneplace-bot` calls `inviteMembers`.
  3. The bridge accepts with the user's own session (`acceptInviteById`).
  4. The member is now active, before they ever click Docs.
- Member remove: revoke via `oneplace-bot`.
- Roles: a non-team AFFiNE workspace only has Owner (`oneplace-bot`) and Collaborator, so **every
  Oneplace member and guest becomes a Collaborator.** AFFiNE can't make guests read-only at
  workspace level without a team license. This is noted as a known limitation.
- Hook points are where the Rocket.Chat sync is already called (`invite.py`, `member.py`,
  workspace `base.py`). Failures are logged and never block Oneplace actions. They are retried by
  a Celery task.
- `GET/POST /api/workspaces/{slug}/docs/status/`, like chat status. A workspace admin can force a
  re-sync.
- **Seat limit:** self-hosted AFFiNE without a license caps each workspace at **10 members**.
  [OPEN — see §13 Q1]

### 6.5 AI (Ollama)

- God-mode → AI stays the source of truth (`LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY`,
  `LLM_MODEL`, Ollama provider in `apps/api/plane/app/views/external/base.py`).
- AFFiNE server config:
  - `copilot.enabled: true`
  - `copilot.byok.enabled: true`
  - `copilot.byok.allowCustomEndpoint: true`
  - `copilot.byok.allowedProviders: ["openai"]`
- On self-host, AFFiNE only routes AI through **workspace BYOK profiles**. Oneplace sets a profile
  on every linked AFFiNE workspace through the bridge as `oneplace-bot`, using
  `createWorkspaceByokProfile`:
  - provider `openai`
  - endpoint `openai_compatible` at `LLM_BASE_URL`, dialect `chat_completions`
  - model `LLM_MODEL` with text input/output capabilities
- The profile is pushed when the workspace is created, when god-mode AI is saved, and on a
  startup/periodic reconcile.
- With a BYOK target present, the self-host AI action quota is not applied, so every member gets
  AI.
- Features that need image output, embeddings, rerank or audio input have no route with a
  text-only Ollama model (image generation, workspace indexing/embedding search, transcription).
  We leave them as AFFiNE ships them and don't hide them. List which features work in
  `UAT-SERVER.md`.
- The provider wiring hasn't been run live yet. The first implementation step is a manual smoke
  test against Ollama Cloud.

### 6.6 Migration (Pages → AFFiNE)

Run the Django management command
`python manage.py migrate_pages_to_affine [--workspace slug] [--dry-run] [--force]` in the `api`
container. It calls the bridge.

Mapping:

| Oneplace                    | AFFiNE                                                                                                                                                                                                                                                                                                          |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Workspace                   | Linked AFFiNE workspace (§6.4)                                                                                                                                                                                                                                                                                  |
| Project (via `ProjectPage`) | Folder named after the project (`db$folders`)                                                                                                                                                                                                                                                                   |
| Page with no project        | Folder **General**                                                                                                                                                                                                                                                                                              |
| Page in several projects    | Doc created once; a doc entry added in each project's folder                                                                                                                                                                                                                                                    |
| `parent` page               | Child doc. The parent doc gets a linked-doc reference to it, so AFFiNE shows it nested under the parent. Only top-level pages go directly in the folder.                                                                                                                                                        |
| `archived_at` set           | Sub-folder **Archived** inside its folder                                                                                                                                                                                                                                                                       |
| `access = Private`          | **Not** in the shared workspace (Owner/Admin always see every doc, and doc titles can leak through workspace meta). Goes into a private AFFiNE workspace owned by the page owner: "<Workspace> · Private", created only for users who have private pages, with the same project folders. Also linked from Docs. |
| `labels`                    | AFFiNE tags                                                                                                                                                                                                                                                                                                     |
| `owned_by`                  | Doc written as that user through the bridge (real author)                                                                                                                                                                                                                                                       |
| `created_at`, `updated_at`  | `createDate` in workspace meta and `createdBy` in doc properties set through Yjs. If AFFiNE ignores or overwrites them, add a first line "Originally created by X on date in Oneplace".                                                                                                                         |
| `logo_props` emoji          | Doc icon, if supported. Otherwise noted in the report.                                                                                                                                                                                                                                                          |
| `is_locked`                 | No equivalent. Noted in the report.                                                                                                                                                                                                                                                                             |
| Images/attachments in MinIO | Uploaded as AFFiNE blobs, references rewritten. Files over 100 MB are linked back and reported.                                                                                                                                                                                                                 |
| Links between pages         | Rewritten to AFFiNE linked-doc references                                                                                                                                                                                                                                                                       |
| Work-item mentions/embeds   | Plain links back to the Oneplace work item                                                                                                                                                                                                                                                                      |
| Mermaid                     | Code block, language `mermaid`                                                                                                                                                                                                                                                                                  |
| KaTeX equations             | AFFiNE inline/block equation (LaTeX)                                                                                                                                                                                                                                                                            |
| HTML artifacts              | Code block, language `html`                                                                                                                                                                                                                                                                                     |

- Content source: `description_html`, converted to Markdown in Python and sent to the bridge for
  Markdown→Yjs. Any node the converter doesn't understand is kept as text and listed in the
  report.
- Idempotent: a new table `AffinePageLink(page → affine_workspace_id, affine_doc_id, migrated_at,
source_hash)` records progress. Reruns skip pages already done unless `--force` is passed.
- `--dry-run` prints the plan and warnings without writing anything.
- Report per run (CSV plus summary): page id, name, project, AFFiNE URL, warnings.
- Nothing in the page tables is deleted.

### 6.7 Removing Pages from Oneplace (after a verified migration)

- Remove Pages from project navigation and the project features list
  (`packages/constants/src/project.ts` `PAGES`, `features-list.tsx`), from workspace navigation
  (`packages/constants/src/workspace.ts`), and from its routes in `apps/web/app/routes/core.ts`.
- Old page URLs redirect to the migrated AFFiNE doc (looked up in `AffinePageLink`). Anything not
  found goes to the Docs home.
- Page entry points elsewhere are removed or redirected: work-item "link to page", command
  palette, search, home widgets.
- Page API endpoints become read-only, kept for migration reruns and redirect lookups.
- The builder checks whether `live` still has non-page duties before stopping it.
- MCP: stop exposing the upstream `page` tool.

### 6.8 MCP doc tools

The MCP image is `plane-mcp-server==0.3.4`, started by
`plane-selfhost/plane-app/plane-mcp/api_key_http.py`. Register our own tools on the FastMCP server
object before it is mounted. Keep the upstream tools, except remove `page`.

- Tools, prefixed `doc`: list folders/docs, search, read (as Markdown), create from Markdown (into
  a project folder or General), replace content, append, rename/move, delete.
- Auth stays as it is today: `Authorization: Bearer <Oneplace API token>` plus `X-Workspace-slug`.
- The tools call **new Oneplace API endpoints** `/api/v1/workspaces/{slug}/docs/...`. These
  endpoints:
  1. authenticate the token;
  2. check that the user is a workspace member;
  3. resolve the linked AFFiNE workspace;
  4. call the bridge **as that user**.
- AFFiNE credentials never reach the MCP container or the client.
- AFFiNE's built-in MCP (`/api/workspaces/:id/mcp`) is read-only on stable, and its write tools
  exist only on canary builds, so it isn't used.

### 6.9 Oneplace pricing and upgrade removal

Remove every plan, pricing, checkout, "talk to sales", upgrade badge/banner/modal and paid-feature
teaser from web, admin (god-mode) and space. Starting list, from `grep -ri "upgrade|pricing"`:

- `components/license/modal/**`
- `workspace/billing/**` and the billing settings routes
- `workspace/upgrade-badge.tsx`, `workspace/edition-badge.tsx`
- `issues/bulk-operations/upgrade-banner.tsx`
- `active-cycles/workspace-active-cycles-upgrade.tsx`
- `estimates/create/stage-one.tsx`
- `project/settings/features-list.tsx`
- sidebar `workspace-menu-item.tsx` and `extended-sidebar-item.tsx`

Teasers for paid-only features disappear. Nothing that works today is removed. AFFiNE itself is
left stock: `payment.enabled` is off by default on self-host.

## 7. Constraints

- On-prem UAT server only. LAN SSH is `root@192.168.1.177`. Images are built or loaded locally
  (`build-images.sh`, `PULL_POLICY=never`).
- Secrets live only in `/home/plane/plane-app/plane.env` on the server and are never committed.
  New secrets:
  - OIDC signing key
  - AFFiNE client secret
  - `AFFINE_BRIDGE_SECRET`
  - `oneplace-bot` password
  - `AFFINE_PRIVATE_KEY`
  - AFFiNE DB password
- Don't disturb Rocket.Chat, the insurance stack, or their ports.
- Upstream Plane is pinned to `v1.4.2`. Keep changes in Oneplace-specific files where possible, as
  the Rocket.Chat work does.

## 8. Rollout order

1. The owner commits the existing uncommitted `plane-src` work (§11).
2. Remove Oneplace pricing (independent, low risk).
3. Stand up AFFiNE, its DB and nginx on `docs.roinetinsurance.in`. Bootstrap `oneplace-bot`.
   Smoke-test BYOK with Ollama Cloud by hand.
4. Add the OIDC provider and the Docs SSO endpoint and sidebar item. Verify with a test user.
5. Build `affine-bridge` and the workspace/member sync. Push BYOK profiles.
6. Add the MCP doc tools. Verify create/read/update from Cursor.
7. Migration: dry run on UAT, then review the report with the user, then the real run, then
   spot-checks.
8. Remove Pages and add the redirects. Deploy.

Each step can be deployed on its own. Pages stays live until step 8.

## 9. Verification

- SSO: a new Oneplace user that AFFiNE has never seen clicks Docs and lands in the right AFFiNE
  workspace, signed in, with no prompt. A member who is removed loses AFFiNE access.
- Impersonation grant: it is rejected when sent through nginx or without the secret.
- Private pages: the owner sees them in their private workspace. Another member and `oneplace-bot`
  workspace browsing don't show their titles in the shared workspace.
- Migration: counts match (pages per project = docs per folder). Compare five hand-picked pages
  side by side, covering Mermaid, KaTeX, HTML, images and nested children.
- AI: run an AFFiNE AI action as a normal member and confirm it uses the Ollama model.
- MCP: create a doc through MCP in a project folder, read it back, and check the author.
- Pricing: grep for upgrade/pricing strings finds nothing user-visible. Click through settings,
  the sidebar, bulk ops, cycles and estimates.

## 10. Left to the builder

- exact OIDC library and paths
- bridge internals and which parts of affine-mcp-server to reuse
- the HTML→Markdown converter
- the nginx specifics
- the free host port for AFFiNE
- compose resource limits
- test layout

## 11. Existing uncommitted work

`plane-src` (`oneplace-ce`) has 24 modified files that aren't committed: the Rocket.Chat
integration, attachment changes, the sidebar chat item and editor config. This design builds on
them. The owner must commit them before implementation starts.

## 12. AFFiNE facts (v0.27.4 source, verified 2026-11-05)

- Sub-path is unsupported in the frontend (issue #13341), so it needs its own domain.
- OIDC:
  - Config is in `oauth.providers.oidc`. Discovery is required and the issuer must match exactly.
    PKCE is required. Callback is `/oauth/callback`.
  - Email is required, and `email_verified: false` is rejected.
  - Users are auto-created when `auth.allowSignupForOauth` is on, and matched by email.
  - Deep link: `/oauth/login?provider=OIDC&redirect_uri=<relative>`.
  - Password sign-in can't be disabled.
- AI:
  - Self-host routes only through workspace BYOK profiles (`createWorkspaceByokProfile`).
    `openai_compatible` endpoints need `copilot.byok.allowCustomEndpoint`.
  - The quota is bypassed when a BYOK target exists.
  - Embedding, rerank, indexing and transcript need server-stored keys, which self-host doesn't
    route.
- The `selfhost_free` plan allows 10 members per workspace, 100 GB storage, 100 MB per blob and 30
  days of history. Only a paid `selfhost_team` license lifts these. Admin grants are refused
  without one.
- No personal access tokens (removed in 0.27). No Markdown import endpoint. The built-in MCP
  writes only on canary. Writes go through Yjs over socket.io (`space:push-doc-update`).
- Membership: `inviteMembers` creates a Pending invite, which `acceptInviteById` must accept with the
  invitee's session. In a non-team workspace, `grantMember` can only transfer ownership.
- Doc roles: `updateDocDefaultRole(None)` plus `grantDocUserRoles`. Workspace Owner and Admin
  always keep access.
- Folders live in workspace DB doc `db$folders`, and doc properties in `db$docProperties`. Doc
  list and tags live in root-doc `meta.pages`. Child docs are linked-doc references, not a stored
  hierarchy.

## 13. Calls made by Claude (check these)

These are Claude's calls. Each one settles a question the builder check raised.

1. **Private workspaces** ("<Workspace> · Private") are owned by the page owner. `oneplace-bot` is
   never added, and the bridge does every operation there as the owner, including the BYOK
   profile. If the owner leaves or is deactivated in Oneplace, their private workspace is kept as
   is. Nobody else gains access, and no automatic handover happens.
2. **Cutover:**
   - Dry runs happen while Pages is still live.
   - The real run first switches Pages to **read-only**: an `AFFINE_PAGES_FROZEN` instance flag
     plus a banner saying "Pages moved to Docs", with a link.
   - No edits can then happen after migration, and no delta logic is needed.
   - `--force` never overwrites an AFFiNE doc that changed after migration. It skips the doc and
     reports it. It only re-creates docs that are untouched (checked against the AFFiNE snapshot
     timestamp stored in `AffinePageLink`).
3. **AI provider rule:**
   - AFFiNE uses whatever god-mode → AI holds at the time, which is the stored instance config, not
     the `plane.env` fallback.
   - Ollama, OpenRouter, Azure and LiteLLM are all OpenAI-compatible, so all four are pushed as
     BYOK. For LiteLLM (`http://litellm:4000/v1`), set `copilot.byok.allowPrivateEndpoint: true`.
   - Bedrock is not pushed. God-mode shows a note: "Docs AI needs an OpenAI-compatible provider".
4. **Authors who are no longer members:** pages owned by deactivated or removed users are written
   by `oneplace-bot`, with a first line "Originally by <name>". They are never re-added to AFFiNE.
5. **Bot API tokens through MCP** (`APIToken.user_type=1`): docs are written as `oneplace-bot`.
6. **Project folders** are kept in sync after migration. They are created on project create,
   renamed on rename, and moved to **Archived** on archive. On delete, the folder stays (docs are
   never deleted). MCP "create in project folder" also creates a missing folder.

## 14. Open questions for the user

- Q1. The 10-seat limit per AFFiNE workspace. `oneplace-bot` uses one seat, so 9 people fit.
  - Status 2026-11-05: Oneplace has 18 active people, and Insurance tech alone has 14.
  - Patching the limit out is **not an option**. The AFFiNE server (`packages/backend`) is under
    the AFFiNE EE license, which allows production use only with a subscription for the correct
    number of seats.
  - The way forward is either a paid `selfhost_team` license, or a different docs tool with no
    seat cap. Alternatives are being researched.
- Q2. Visibility of pages in Secret projects, and of pages that guests can't see today.
