# Forge connection

Open **Administration → Integrations** with an account that has `settings.manage`. Check **This Sprint instance's URL**, then enter your Forge instance's public URL and administrator credentials. Alternatively, open **Instance & System → Sprint connection** in Forge and check its own URL before entering the Sprint URL and credentials. One setup stores the connection on both instances. Update both applications to use the latest connection dialog.

The dialog displays the configured local public URL. When that is a loopback default such as `localhost`, it suggests the origin currently open in the browser, preserving its port. You can correct it before connecting. Sprint saves this address in its existing installation configuration; it takes precedence over `PUBLIC_APP_URL` for pairing identity and password reset email links and survives restarts. Existing installations without an override continue to use `PUBLIC_APP_URL`. Forge saves it as its existing public instance URL.

Both URLs must be HTTP(S) origins without paths and reachable from the other backend, including the verification callback. In Docker, `localhost` refers to the individual container, so use names or server addresses reachable from both deployments. Use HTTPS across untrusted networks. Redirects are rejected and TLS certificates are verified.

For two applications on one server, for example:

| Field in Sprint | Example |
| --- | --- |
| This Sprint instance's URL | `http://192.168.122.45:3000` |
| Forge public URL | `http://192.168.122.45:3001` |

Also check that Forge's public URL is `http://192.168.122.45:3001` in its instance settings. Reachability in a browser alone does not establish reachability from the backend containers.

The administrator password authorizes pairing once and is not stored. Each instance stores its own encrypted copy of a separate random connection key. The receiving server checks credentials and calls back to verify the initiating origin before saving the connection. The key authorizes only the specific connection's identity, connectivity check and removal. It does not grant access to application data.

**Check connection** verifies both directions. If a request is interrupted after the other server accepted it, retry setup or check the connection to finish the pending setup. **Disconnect** removes the connection on both instances. When the other server cannot be reached, **Remove locally** becomes available; remove the other server's remaining entry separately. A configured connection cannot be silently replaced.

For **Setup incomplete**, correct the local instance URL and use **Retry connection** with the other administrator's credentials. The pending connection ID/key is retained. There is no need to delete application data or rerun setup. If the other side already has a different connection, disconnect that entry first.

Errors identify unreachable addresses, failed verification callbacks, mismatched advertised URLs, missing endpoints (HTTP 404), throttling, and other HTTP status codes. Remote response bodies and credentials are not displayed. A corrected URL is saved even if a later network or authentication step fails, so it remains available for retry.

The existing startup migration workflow creates `instance_connections`. The protocol is implemented in `app/instance_link.py`, which is identical in Forge and Sprint; keep both copies aligned. Sprint's adapter uses its existing organization identity, `settings.manage`, login rate limit, API error format, and installation encryption.

This first implementation establishes an instance connection only. Project, repository, issue, and user synchronization can be added separately.
