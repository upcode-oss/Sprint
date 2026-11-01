# MCP access

Sprint exposes a Streamable HTTP MCP server at
`https://sprint.example.com/api/v1/mcp`. Use the same public origin as
the application.

## Create a key

MCP is **disabled by default**, including when upgrading an existing installation.
An administrator must enable it under **Administration → System → MCP access** first.
The opt-in flag is persisted in the existing installation configuration and defaults to false when absent.

While disabled, the profile hides MCP key management, new keys cannot be created,
and every MCP request returns HTTP 404, even with an existing valid key. Disabling
the feature takes effect on subsequent requests immediately. Existing keys remain
stored; they can be revoked while disabled and work again after re-enabling only
if still unrevoked, unexpired, and authorized.

Open **Profile → MCP access keys → Generate MCP key**.

1. Give the key a name and choose an expiration (30 days, 90 days, or one year in
   the interface; the API accepts 1–365 days).
2. Select the permissions needed by your MCP client. Only permissions your account
   currently has are offered. Read permissions are selected initially; write,
   create, maintain, and delete permissions require explicit selection.
3. Confirm your current password. If you use 2FA, also enter a new authenticator
   code or unused recovery code.
4. Save the personal key when it is displayed. It cannot be displayed again.
5. Configure a client that supports Streamable HTTP with a custom
   `Authorization: Bearer <YOUR_PERSONAL_MCP_KEY>` header.

Keys are personal: you can list and revoke only your own keys. Revocation and
expiration apply to every subsequent request, including requests from clients
that already connected. Password changes, password resets where supported, and
2FA configuration changes invalidate previously generated MCP keys. Generate a new
key after these account-security changes.

Personal keys remain available for clients that support supplying a bearer
header. Clients such as ChatGPT can use the OAuth flow below instead.

## Connect ChatGPT with OAuth

1. Enable **Administration → System → MCP access** in Sprint.
2. In ChatGPT, add a custom MCP server using
   `https://sprint.example.com/api/v1/mcp` and select OAuth authentication.
3. Let ChatGPT discover the OAuth settings and dynamically register its client;
   no personal MCP key or manually created OAuth client secret is needed.
4. Sign in to Sprint when prompted. On **Connect your Sprint account**, check
   the client name and callback address, select permissions, and confirm your
   Sprint password. Accounts with 2FA must also provide a fresh authenticator or
   recovery code. Read permissions are selected initially; writes require
   explicit selection.
5. Select **Allow access** to return to ChatGPT. Selecting **Deny** creates no
   authorization or token.

OAuth connections appear as `OAuth: <client name>` under **Profile → MCP access
keys** and can be revoked there. The connection expires after 90 days. Access
tokens last at most 30 minutes; refresh tokens rotate on use. Reusing a consumed
refresh token or authorization code revokes the complete connection. Password
and 2FA changes, account deactivation, permission changes, and disabling MCP have
the same effect as for personal keys. OAuth tokens are not browser sessions or
general REST API credentials.

The OAuth `mcp` scope represents the specific operation permissions approved by
the user. It does not grant every MCP permission. Every request still intersects
the approved permission ceiling with the owner's current permissions and project
membership.

Sprint uses the official MCP SDK's authorization-code handlers with mandatory
S256 PKCE, exact registered callback matching, client authentication, and
single-use authorization codes. Access and refresh tokens are random, stored
only as digests, and bound to this instance's canonical MCP resource URL.
Client secrets are encrypted using the installation secret. Registrations,
consent requests, codes, tokens, and revocable grants persist across restarts and
are shared across workers through the existing database.

### Discovery and reverse proxies

Set `PUBLIC_APP_URL` to the public HTTPS origin and use `COOKIE_SECURE=true` for
HTTPS deployments. The public endpoints include:

| Endpoint | Purpose |
| --- | --- |
| `/.well-known/oauth-protected-resource/api/v1/mcp` | MCP resource metadata |
| `/.well-known/oauth-authorization-server/api/v1/oauth` | OAuth server metadata |
| `/api/v1/oauth/register` | Dynamic client registration |
| `/api/v1/oauth/authorize` | Authorization-code request |
| `/oauth/authorize` | Sprint login and permission consent |
| `/api/v1/oauth/token` | Code exchange and token refresh |
| `/api/v1/oauth/revoke` | Token revocation |

Root discovery aliases are also available. Discovery and OAuth requests return
404 while MCP is disabled. Metadata advertises public URLs from the installation's
public origin; it does not derive them from untrusted forwarded headers.

Forward `/api/`, `/oauth/`, and the OAuth `/.well-known/` paths to the frontend
without stripping path prefixes. Next.js forwards the API and discovery paths to
the backend. In Nginx, a `proxy_pass http://frontend:3000;` directive inside
`location /api/` preserves the prefix; `proxy_pass http://frontend:3000/;` removes
it. Do not use `proxy_hide_header WWW-Authenticate;`: the 401 challenge tells
ChatGPT where to discover OAuth metadata. Ensure any ACME location matches only
`/.well-known/acme-challenge/` rather than intercepting OAuth discovery.

See [OpenAI's authentication documentation](https://developers.openai.com/plugins/build/auth)
and [Installation & Deployment](installation.md) for reverse-proxy networking.

## Permission boundaries

Every tool call must satisfy all of these checks:

- The key exists, is unexpired and unrevoked, and its owner is still active with
  unchanged account credentials and 2FA enrollment, with MCP enabled on the instance.
- The operation's permission was selected when this key was created.
- The owner still has that permission now. Forged or excessive scopes are rejected
  by the key-creation API, independently of the interface.
- The application API allows the owner to access the specific project or
  repository and any nested task, document, sprint, file, issue, or pull request.

Project and repository IDs are identifiers, never permission grants. Changing an
ID in a tool call cannot change the acting user or bypass membership checks.
Existing keys do not gain additional operation scopes when a user gains a new
role. Access to individual objects follows the owner's current roles and
memberships, so losing a project/team/repository grant removes access immediately
for subsequent requests.

The MCP dispatcher uses a fixed operation allowlist and dispatches through the
existing application API and its access checks. It does not forward browser
cookies or create browser/JWT sessions, and it does not expose an arbitrary URL,
HTTP method, SQL query, key-management, or authentication tool. User and role
administration use explicit tools gated by the corresponding approved permissions.
An MCP key is not accepted as a browser session or general REST API bearer token.

Sprint retains organization, team/project membership, and per-operation
permissions. Read access to one project gives no access to another project's
tasks, comments, documents, or sprints. Combining a permitted project ID with an
object ID from another project is denied by the existing nested-object checks.
Comments through MCP require `kanban.manage`, keeping read-only keys read-only.

## Available tools

| Scope family | Tools |
| --- | --- |
| `profile.read` | Read the key owner's account |
| `projects.view/create/edit/delete/manage_members` | Projects, overview/activity, members, and assigned teams |
| `kanban.view/manage` | Read boards, columns, tasks, and comments; create/update/delete/move tasks and comment |
| `documents.view/create/edit/delete` | List/read and mutate documents in accessible projects |
| `scrum.view/manage` | List/create/update/start/complete/cancel sprints in accessible projects |
| `calendar.view/manage` | Read the calendar feed and visible events; create/edit/delete owned events |
| `meetings.view/create/edit/delete` | List/read meetings and eligible participants; create/edit/delete meetings |
| `organization.manage` | Read/update organization name and timezone; remove its custom logo; list timezones |
| `roles.view/create/edit/delete` | Permission catalog and role administration, retaining system-role protection |
| `settings.manage` | System information, SMTP settings and explicit delivery tests, and MCP enablement |
| `teams.view/create/edit/delete/manage_members` | Team administration and replacement of team memberships |
| `users.view/create/edit/delete` | List/read/create/update accounts, assign roles, and deactivate accounts |
| `users.profile.view/edit` | Read/update user profiles and remove avatars |
| `users.contacts.view/edit` | Read visible contacts and create/update/delete contact information |
| `users.presence.view/edit` | Read/update manual user presence and status messages |

Only tools allowed by both the key's scope ceiling and the owner's current
permissions appear in `tools/list`. A cached tool definition does not grant
access: `tools/call` checks permissions again.

Tool arguments contain typed IDs, filters, and (for writes) a `payload` matching
the existing API request schema. PATCH requests preserve omitted fields.
Results contain the API `status` and `data`; denied or failed operations set
`isError`.

### Workspace administration

All 40 application permissions are available for selection when creating a
personal key or approving an OAuth connection, alongside `profile.read`. Only
permissions the acting account currently possesses are offered. Read permissions
are initially selected; creation, modification, deletion, membership changes,
organization management, and settings management require explicit approval.
Existing keys and connections retain their original scope ceiling. Reconnect
and approve additional permissions to make newly supported tool families available.

User-targeting tools use `target_user_id` to identify the account being managed;
it never changes the acting identity. Organization and nested-object boundaries,
private calendar/meeting visibility, contact visibility, protected system roles,
self-deactivation prevention, and the last-active-administrator rule continue to
be enforced by the existing application API. User profile reads include the
contacts and memberships visible to that acting user, matching the web API.

`set_team_members` replaces the entire team member list. `set_project_teams`
replaces the entire project team list, from which project membership is derived.
Read the existing team or project first; an empty `payload.ids` clears the list.
The existing user deletion endpoint deactivates an account and preserves its
historical authorship; it does not physically remove the user row.

Initial user passwords and SMTP passwords can be supplied to the corresponding
write tools, but are never returned. SMTP reads expose only `has_password`, not
the saved secret. Omitting the password from an SMTP update preserves it.
`test_smtp_settings` sends an email only to its explicitly supplied recipient.
`update_mcp_settings` with `enabled: false` disables subsequent MCP calls;
re-enable access through Sprint's web administration.

These tools use the JSON administration APIs. Avatar and organization-logo file
uploads continue through the web interface; removing those images is available
through MCP. Session issuance, password resets, 2FA enrollment, OAuth client
registration, and MCP-key creation are not exposed as MCP tools.

### Move tickets on a Kanban board

Use `get_kanban_board` with the project ID to read its columns, including each
column's `id`, `name`, `key`, `position`, and `is_done` flag, and the currently
visible tasks. Use `list_tasks` to also find older completed tasks hidden by the
board's retention setting.

Call `move_task` with `project_id`, `task_id`, and a `payload` containing the
target `column_id`. Omit both neighbor IDs to append the ticket to that column.
To choose its position, include `before_task_id` or `after_task_id` for a ticket
in the target column. The same tool can reorder a ticket within its existing
column. The task's status, completion timestamp, and activity history are updated
through the same API used by drag-and-drop in Sprint.

Reading the board requires `kanban.view`; moving requires `kanban.manage` in
both the user's current role and the personal key or approved OAuth connection.
Project membership and the task, column, and neighbor's project boundaries are
checked on every move. Read-only connections do not advertise `move_task`, and
direct calls cannot bypass that restriction.

After deploying the updated backend, refresh the MCP connection in ChatGPT and
start a new conversation to load the new tools. If the existing OAuth connection
was approved with read permissions only, reconnect and explicitly select
**Kanban Manage** on Sprint's consent page. Refreshing the tool list does not
expand the permissions of an existing authorization.

## Connection example

A client supplies these HTTP headers to the endpoint above:

```http
Authorization: Bearer <YOUR_PERSONAL_MCP_KEY>
Accept: application/json, text/event-stream
Content-Type: application/json
```

The official Python SDK negotiates current and legacy MCP protocol versions:

```python
import asyncio
import os

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with httpx2.AsyncClient(headers={
        "Authorization": "Bearer " + os.environ["SPRINT_MCP_KEY"],
    }) as http:
        async with Client(streamable_http_client(
            "https://sprint.example.com/api/v1/mcp", http_client=http,
        ), cache=None) as client:
            tools = await client.list_tools()
            print([tool.name for tool in tools.tools])

asyncio.run(main())
```

Keep keys in client secret storage or environment variables, never in URLs,
shared configuration, screenshots, or Git. Use HTTPS for remote access. Requests
with a supplied foreign Origin or untrusted Host are rejected. Direct browser
clients must use the application's configured origin.

## Storage, upgrades, and verification

Migration `20261031_0012` creates `mcp_keys` through the existing setup/startup migration
workflow. Rebuild and restart both backend and frontend to install the MCP SDK and
show key management. Existing users and data are preserved.

Migration `20261101_0013` adds persistent OAuth storage. Rebuild both services to
install the OAuth endpoints, frontend consent page, and discovery rewrites:

```bash
docker compose up -d --build backend frontend
```

Only SHA-256 digests of random 256-bit keys are stored, together with the scope
ceiling, expiration, owner, revocation and last-use timestamps, and a fingerprint
of the account credentials and 2FA enrollment. Neither the raw key nor account
password is stored in the key table. Personal-key responses use
`Cache-Control: no-store`.

The server uses the official MCP Python SDK with stateless HTTP and a 1 MiB
request-body limit. The existing frontend API proxy forwards MCP headers and JSON
responses; no extra public backend port or shared instance credential is required.

`tests/test_mcp.py` covers official SDK clients in modern and legacy modes,
disabled-by-default behavior, restricted settings activation and immediate shutdown,
per-user scope issuance, one-time key display and hashing, expiry/revocation,
password and 2FA changes, owner deactivation, private object access, nested-ID
substitution, membership/role removal, narrowed keys, and migration compatibility.
`tests/test_mcp_oauth.py` exercises discovery, client registration, consent and
CSRF protection, PKCE and resource/client/callback bindings, confidential and
public clients, token expiry, refresh rotation/replay, and immediate revocation.

See the [MCP Streamable HTTP specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
and [official Python SDK](https://py.sdk.modelcontextprotocol.io/run/asgi/).
