import pytest
import mongomock
from unittest.mock import patch

from labdb.database import Database, __version__


@pytest.fixture(scope="function")
def mock_db():
    """Create a test database with mongomock for each test function"""
    with patch("labdb.database.MongoClient") as mock_client:
        # Create a mongomock client instead of a real MongoDB client
        mock_instance = mongomock.MongoClient()
        mock_client.return_value = mock_instance

        # Use a test config
        config = {"conn_string": "mongodb://localhost:27017", "db_name": "labdb_test"}

        db = Database(config=config)

        # Clear all collections before each test
        for collection_name in db.db.list_collection_names():
            if collection_name != "system.indexes":
                db.db[collection_name].delete_many({})

        # Insert version document to avoid version check error
        db.experiments.insert_one({"_id": "version", "version": __version__})

        # Create a basic directory structure for testing
        db.create_dir("/test")

        yield db
