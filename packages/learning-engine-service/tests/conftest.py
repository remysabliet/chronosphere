import pytest
from fastapi.testclient import TestClient

from learning_engine_service.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
