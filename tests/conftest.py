import os
import socket

import pytest

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture(autouse=True)
def _offline_fixtures(monkeypatch):
    """Point all data loaders at local fixtures and forbid any network access."""
    monkeypatch.setenv("MARKETMACHINE_DATA_DIR", FIXTURES_DIR)

    def _blocked(*args, **kwargs):
        raise RuntimeError("Network access is disabled in tests.")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    yield
