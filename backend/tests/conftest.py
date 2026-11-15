"""Shared fixtures: an API client on a temporary database filled with the simulated data."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine

import app.database as database
from app.main import app


@pytest.fixture(autouse=True)
def _no_live_devices(monkeypatch):
    """The optional live device mode (HP_SIMULATE_DEVICES=1) is always off in tests."""
    monkeypatch.delenv("HP_SIMULATE_DEVICES", raising=False)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(database, "engine", engine)
    import scripts.generate_data as gen
    monkeypatch.setattr(gen, "engine", engine)
    SQLModel.metadata.create_all(engine)
    gen.main()
    with TestClient(app) as c:
        yield c
