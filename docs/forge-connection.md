# Forge connection

Open **Administration → Integrations** with an account that has `settings.manage`, then enter your Forge instance's public URL and administrator credentials. Alternatively, open **Instance & System → Sprint connection** in Forge and enter the Sprint URL and credentials there. One setup stores the connection on both instances. Both applications must include this feature.

Sprint advertises `PUBLIC_APP_URL`; Forge advertises the public URL configured in its settings. Both URLs must be HTTP(S) origins without paths and reachable from the other backend, including the verification callback. In Docker, `localhost` refers to the individual container, so use names reachable from both deployments. Use HTTPS across untrusted networks. Redirects are rejected and TLS certificates are verified.

The administrator password authorizes pairing once and is not stored. Each instance stores its own encrypted copy of a separate random connection key. The receiving server checks credentials and calls back to verify the initiating origin before saving the connection. The key authorizes only the specific connection's identity, connectivity check and removal. It does not grant access to application data.

**Check connection** verifies both directions. If a request is interrupted after the other server accepted it, retry setup or check the connection to finish the pending setup. **Disconnect** removes the connection on both instances. When the other server cannot be reached, **Remove locally** becomes available; remove the other server's remaining entry separately. A configured connection cannot be silently replaced.

The existing startup migration workflow creates `instance_connections`. The protocol is implemented in `app/instance_link.py`, which is identical in Forge and Sprint; keep both copies aligned. Sprint's adapter uses its existing organization identity, `settings.manage`, login rate limit, API error format, and installation encryption.

This first implementation establishes an instance connection only. Project, repository, issue, and user synchronization can be added separately.
