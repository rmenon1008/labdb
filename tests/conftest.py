import os

import pymongo
import pytest

from labdb.database import Database


class TestDatabase(Database):
    """A test version of the Database class for real database testing."""

    def __init__(self, config):
        # Store config
        self.config = config

        # Connect to test database
        conn_string = config["conn_string"]
        db_name = config["db_name"]

        try:
            client = pymongo.MongoClient(conn_string, serverSelectionTimeoutMS=5000)
            self.db = client[db_name]
            self.db.command("ping")  # Verify connection works

            # Get collections
            self.experiments = self.db.get_collection("experiments_test")
            self.directories = self.db.get_collection("directories_test")
        except Exception as e:
            raise Exception(f"Failed to connect to test database: {e}")


@pytest.fixture
def test_db_config():
    """Return configuration for the test database.

    Note: For security, the actual password should be stored in an environment
    variable rather than hardcoded.
    """
    # Get password from environment variable
    password = os.environ.get("MONGODB_TEST_PASSWORD", "")

    return {
        "conn_string": f"mongodb://rohanOceansUser:{password}@sk-exp-server.mit.edu:5000/?tls=true",
        "db_name": "testDb",
        "large_file_storage": "gridfs",
        "compress_arrays": False,
    }


@pytest.fixture
def test_db(test_db_config):
    """Create a TestDatabase instance with a connection to the real test database.

    This fixture will clean up test data after each test.
    """
    # Create the database instance
    db = TestDatabase(test_db_config)

    # Yield the database for test use
    yield db

    # Clean up: delete all test data after test completes
    db.experiments.delete_many({})
    db.directories.delete_many({})

    # Clean up GridFS collections if they exist
    if "fs.chunks" in db.db.list_collection_names():
        db.db.fs.chunks.delete_many({})
    if "fs.files" in db.db.list_collection_names():
        db.db.fs.files.delete_many({})
