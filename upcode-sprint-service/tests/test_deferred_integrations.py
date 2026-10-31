import pytest
from fastapi.testclient import TestClient

from app.core.installation import installation_store
from app.main import app


@pytest.mark.parametrize(
    ("method", "suffix"),
    [
        ("GET", ""),
        ("POST", ""),
        ("DELETE", ""),
        ("GET", "/identity"),
        ("POST", "/pair"),
        ("POST", "/test"),
        ("GET", "/peer"),
        ("DELETE", "/peer"),
    ],
)
def test_deferred_pairing_endpoints_are_unavailable(method, suffix, tmp_path, monkeypatch):
    monkeypatch.setattr(installation_store, "path", tmp_path / "installation.json")
    with TestClient(app) as client:
        assert client.request(method, f"/api/v1/integrations/instance{suffix}").status_code == 404
        paths = client.get("/openapi.json").json()["paths"]
        assert not any("/integrations/" in path for path in paths)
