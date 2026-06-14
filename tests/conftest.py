"""Shared pytest fixtures.

Each test runs against a fresh temporary SQLite database so tests are
isolated from one another and from the developer's real timeledger.db.
``models.get_db`` reads ``models.DB_PATH`` at call time, so monkeypatching
that attribute is enough to redirect every query (route handlers included).
"""

import os
import tempfile

# Redirect the database before importing the app, since app.py runs
# models.init_db() at import time. Without this, importing the app would
# create a stray timeledger.db in the repo. Per-test isolation is still
# provided by the `db` fixture below.
os.environ.setdefault("TIMELEDGER_DB", os.path.join(tempfile.mkdtemp(), "import.db"))

import pytest

import app as app_module
import models


@pytest.fixture
def db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(models, "DB_PATH", db_file)
    models.init_db()
    return db_file


@pytest.fixture
def client(db):
    app_module.app.config.update(TESTING=True, SECRET_KEY="test")
    return app_module.app.test_client()


@pytest.fixture
def project(db):
    """A single saved project; returns its id."""
    models.create_project("Acme", "Test project")
    return models.get_projects()[0]["id"]
