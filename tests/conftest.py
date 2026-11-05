from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    application = create_app("sqlite://")
    with TestClient(application) as test_client:
        yield test_client
    application.state.engine.dispose()
