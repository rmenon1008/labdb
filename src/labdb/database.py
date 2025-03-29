from pymongo import MongoClient

from labdb.config import load_config


class DatabaseError(Exception):
    """Base exception for database-related errors"""

    pass


class ConnectionError(DatabaseError):
    """Exception raised when connection to database fails"""

    pass


class ConfigError(DatabaseError):
    """Exception raised when configuration is missing or invalid"""

    pass


def get_db(config: dict | None = None) -> MongoClient:
    if config is None:
        config = load_config()
    if not config:
        raise ConfigError(
            "No database configuration found. Set up a connection first with `connection setup`"
        )
    conn_string = config["conn_string"]
    db_name = config["db_name"]
    return MongoClient(conn_string, serverSelectionTimeoutMS=5000)[db_name]


def check_db(config: dict | None = None) -> None:
    if config is None:
        config = load_config()
    try:
        db = get_db(config)
        db.command("ping")
    except Exception as e:
        raise ConnectionError(f"Failed to connect to database: {e}")
