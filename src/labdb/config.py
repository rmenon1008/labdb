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
        },
        "db_name": {
            "type": "string",
            "description": "Database name",
        },
        "large_file_storage": {
            "type": "string",
            "enum": ["none", "local", "gridfs"],
            "description": "Storage type for large files",
        },
        "local_file_storage_path": {
            "type": "string",
            "description": "Local file storage path",
        },
        "compress_arrays": {
            "type": "boolean",
            "description": "Compress large files when storing them",
        },
        "local_cache_enabled": {
            "type": "boolean",
            "description": "Enable local caching of GridFS files",
            "default": False,
        },
        "local_cache_path": {
            "type": "string",
            "description": "Path for local cache storage",
            "default": "/tmp/labdb-cache",
        },
        "local_cache_max_size_mb": {
            "type": "number",
            "description": "Maximum cache size in megabytes",
            "default": 1024,
        },
        "current_path": {
            "type": "string",
            "description": "Current working path",
            "internal": True,
            "default": "/",
        },
    },
    "required": [
        "conn_string",
        "db_name",
        "large_file_storage",
        "compress_arrays",
        "local_cache_enabled",
    ],
    "dependentRequired": {
        "large_file_storage:local": ["local_file_storage_path"],
        "local_cache_enabled:true": ["local_cache_path", "local_cache_max_size_mb"],
    },
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
                "properties": {"local_cache_enabled": {"const": True}},
                "required": ["local_cache_enabled"],
            },
            "then": {"required": ["local_cache_path", "local_cache_max_size_mb"]},
        },
    ],
}

# Define metadata to help with the CLI setup
CONFIG_SETUP_ORDER = [
    "conn_string",
    "db_name",
    "large_file_storage",
    "local_file_storage_path",
    "compress_arrays",
    "local_cache_enabled",
    "local_cache_path",
    "local_cache_max_size_mb",
]

# Define dependencies for conditional display during setup
CONFIG_DEPENDENCIES = {
    "local_file_storage_path": {"field": "large_file_storage", "value": "local"},
    "local_cache_enabled": {"field": "large_file_storage", "value": "gridfs"},
    "local_cache_path": {"field": "local_cache_enabled", "value": True},
    "local_cache_max_size_mb": {"field": "local_cache_enabled", "value": True},
}


class ConfigError(Exception):
    """Exception raised for configuration errors."""

    pass


def load_config(should_validate: bool = True):
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

            # Handle migration from array-based paths to string paths
            if "current_path" in config and isinstance(config["current_path"], list):
                from labdb.utils import join_path

                config["current_path"] = join_path(config["current_path"])

            if should_validate:
                validate(config, CONFIG_SCHEMA)
            return config
    except (json.JSONDecodeError, ValidationError) as e:
        raise ConfigError(
            f"Invalid configuration: {str(e)}. Please run 'labdb connection setup' to reconfigure."
        ) from e


def save_config(config: dict):
    """Save configuration to file with validation

    Validates the configuration against the schema and saves it to the config file.
    Provides helpful error messages for missing required fields or conditional validation failures.
    """
    try:
        # Pre-validation check for required fields
        missing_fields = []
        for field in CONFIG_SCHEMA["required"]:
            if field not in config:
                missing_fields.append(field)

        if missing_fields:
            raise ConfigError(
                f"Missing required configuration fields: {', '.join(missing_fields)}"
            )

        # Check conditional requirements
        if (
            config.get("large_file_storage") == "local"
            and "local_file_storage_path" not in config
        ):
            raise ConfigError(
                "When using local file storage, you must specify a local_file_storage_path"
            )

        if config.get("local_cache_enabled"):
            missing_cache_fields = []
            for field in ["local_cache_path", "local_cache_max_size_mb"]:
                if field not in config:
                    missing_cache_fields.append(field)

            if missing_cache_fields:
                raise ConfigError(
                    f"When local cache is enabled, you must specify: {', '.join(missing_cache_fields)}"
                )

        # Full schema validation
        validate(config, CONFIG_SCHEMA)

        # Save to file
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


def update_current_path(path: str):
    """
    Update the current path in the config file

    Args:
        path: The new current path as a string
    """
    # Ensure path is a string
    if not isinstance(path, str):
        from labdb.utils import join_path

        path = join_path(path)

    config = load_config() or {}
    config["current_path"] = path
    save_config(config)


def get_current_path() -> str:
    """
    Get the current path from the config file

    Returns:
        The current path as a string
    """
    config = load_config() or {}

    # Handle migration from array paths
    if "current_path" not in config:
        return "/"

    if isinstance(config["current_path"], list):
        # Convert from array to string
        from labdb.utils import join_path

        path = join_path(config["current_path"])
        # Update the config with the string path
        update_current_path(path)
        return path

    return config.get("current_path", "/")
