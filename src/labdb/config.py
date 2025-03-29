import json
import os
from pathlib import Path

from jsonschema import validate, ValidationError

CONFIG_FILE = Path.home() / ".labdb.json"
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "conn_string": {
            "type": "string",
            "description": "MongoDB connection string"
        },
        "db_name": {
            "type": "string", 
            "description": "Database name"
        },
        "large_file_storage": {
            "type": "string",
            "enum": ["none", "local", "gridfs"],
            "description": "Storage type for large files: 'none' (no large files allowed), 'local' (store on disk), or 'gridfs' (store in MongoDB GridFS)"
        },
        "large_file_storage_path": {
            "type": "string",
            "description": "Path to the directory for storing large files (required if large_file_storage is 'local')"
        },
        "compress_arrays": {
            "type": "boolean",
            "description": "Whether to compress arrays when storing them (applies to all storage types)",
        }
    },
    "required": ["conn_string", "db_name", "large_file_storage"],
    "allOf": [
        {
            "if": {
                "properties": {"large_file_storage": {"const": "local"}},
                "required": ["large_file_storage"]
            },
            "then": {
                "required": ["large_file_storage_path"]
            }
        }
    ]
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
        raise ConfigError(f"Invalid configuration: {str(e)}. Please run 'labdb connection setup' to reconfigure.") from e


def save_config(config: dict):
    try:
        validate(config, CONFIG_SCHEMA)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except ValidationError as e:
        raise ConfigError(f"Invalid configuration: {str(e)}. Please run 'labdb connection setup' to reconfigure.") from e
