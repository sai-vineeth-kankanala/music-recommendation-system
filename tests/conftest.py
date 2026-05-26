import pytest
from app import create_app
from config import TestingConfig
from models import db

@pytest.fixture
def app():
    # Use TestingConfig to run in-memory SQLite
    app = create_app(TestingConfig)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
