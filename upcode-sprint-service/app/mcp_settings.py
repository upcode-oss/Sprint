from app.core.installation import installation_store


def enabled(db):
    del db
    return installation_store.load().get("mcp_enabled") is True


def set_enabled(db, value):
    del db
    installation_store.save({**installation_store.load(), "mcp_enabled": value})
    return {"enabled": value}
