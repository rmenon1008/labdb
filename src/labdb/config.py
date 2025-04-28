import json
import os
from pathlib import Path

from jsonschema import ValidationError, validate
from pymongo import MongoClient

CONFIG_FILE = Path.home() / ".labdb.json"
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "conn_string": {
            "type": "string",
            "description": "MongoDB connection string",
            "always_required": True,
        },
        "db_name": {
            "type": "string",
            "description": "Database name",
            "always_required": True,
        },
        "large_file_storage": {
            "type": "string",
            "enum": ["none", "local", "gridfs", "webdav"],
            "description": "Storage type for large files",
            "always_required": True,
        },
        "local_file_storage_path": {
            "type": "string",
            "description": "Local file storage path",
            "required_for": ["local"],
        },
        "webdav_url": {
            "type": "string",
            "description": "WebDAV server URL",
            "required_for": ["webdav"],
        },
        "webdav_username": {
            "type": "string",
            "description": "WebDAV username",
            "required_for": ["webdav"],
        },
        "webdav_password": {
            "type": "string",
            "description": "WebDAV password",
            "required_for": ["webdav"],
        },
        "webdav_root": {
            "type": "string",
            "description": "WebDAV root directory",
            "required_for": ["webdav"],
        },
        "compress_arrays": {
            "type": "boolean",
            "description": "Compress large files when storing them",
            "always_required": True,
        },
    },
    "required": ["conn_string", "db_name", "large_file_storage"],
    "allOf": [
        {
            "if": {
                "properties": {"large_file_storage": {"const": "local"}},
                "required": ["large_file_storage"],
            },
            "then": {"required": ["local_file_storage_path"]},
        },
        {
            "if": {
                "properties": {"large_file_storage": {"const": "webdav"}},
                "required": ["large_file_storage"],
            },
            "then": {
                "required": [
                    "webdav_url",
                    "webdav_username",
                    "webdav_password",
                    "webdav_root",
                ]
            },
        },
    ],
}


class ConfigError(Exception):
    """Exception raised for configuration errors."""

    pass


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            validate(config, CONFIG_SCHEMA)
            return config
    except (json.JSONDecodeError, ValidationError) as e:
        raise ConfigError(
            f"Invalid configuration: {str(e)}. Please run 'labdb connection setup' to reconfigure."
        ) from e


def save_config(config: dict):
    try:
        validate(config, CONFIG_SCHEMA)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except ValidationError as e:
        raise ConfigError(f"Invalid configuration: {str(e)}")


def get_db(config: dict | None = None) -> MongoClient:
    if config is None:
        config = load_config()
    if not config:
        raise Exception(
            "No database configuration found. Set up a connection first with `connection setup`"
        )
    conn_string = config["conn_string"]
    db_name = config["db_name"]
    return MongoClient(conn_string, serverSelectionTimeoutMS=5000)[db_name]


def check_db(config: dict | None = None) -> None:
    if config is None:
        config = load_config()
    db = get_db(config)
    db.command("ping")
