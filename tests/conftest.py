import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Isolate tests to test_missing_persons.db so it never conflicts with running dev server
TEST_DB_PATH = ROOT_DIR / "test_missing_persons.db"
os.environ["DATABASE_PATH"] = str(TEST_DB_PATH)

import backend.config
backend.config.DATABASE_PATH = str(TEST_DB_PATH)
import backend.database
backend.database.DATABASE_PATH = str(TEST_DB_PATH)

import pytest
from backend.seed_data import seed_database

@pytest.fixture(autouse=True)
def reset_db_before_test(request):
    if "test_face_engine" not in str(request.node.fspath):
        seed_database(reset=True)
