import os
import tempfile

import pytest


@pytest.fixture(scope="session")
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["UCO_DB_PATH"] = path
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c

    os.remove(path)
