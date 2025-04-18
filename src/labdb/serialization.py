import io
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import numpy as np
from webdav3.client import Client as WebDAVClient
from bson.binary import Binary
from gridfs import GridFS
from pymongo import MongoClient

from labdb.config import load_config
from labdb.utils import long_id


def serialize_numpy_array(
    arr: np.ndarray, db: MongoClient = None, storage_type: str = None
) -> Dict[str, Any]:
    # Get compression setting from config
    config = load_config()
    if not config:
        raise ValueError("No configuration found")
    compress = config.get("compress_arrays", True)

    # Create a buffer to store the array
    buffer = io.BytesIO()
    if compress:
        np.savez_compressed(buffer, arr=arr)
    else:
        np.save(buffer, arr)

    # Get the data
    buffer.seek(0)
    data = buffer.getvalue()

    # Check if the data exceeds 16MB (MongoDB's BSON document size limit)
    if len(data) > 16 * 1024 * 1024:
        # If no storage type specified, get it from config
        if storage_type is None:
            storage_type = config.get("large_file_storage", "none")

        if storage_type == "none":
            raise ValueError(
                "Large arrays are not allowed (large_file_storage is set to 'none')"
            )
        elif storage_type == "local":
            if "local_file_storage_path" not in config:
                raise ValueError(
                    "Local file storage path not configured. Please set 'local_file_storage_path' in config."
                )

            storage_path = Path(config["local_file_storage_path"])
            if not storage_path.exists():
                storage_path.mkdir(parents=True, exist_ok=True)

            file_name = f"numpy_array_{long_id()}.{'npz' if compress else 'npy'}"
            file_path = storage_path / file_name

            # Write the data directly to file
            with open(file_path, "wb") as f:
                f.write(data)

            return {
                "__numpy_array__": True,
                "__storage_type__": "local",
                "file_path": str(file_path),
                "dtype": str(arr.dtype),
                "shape": arr.shape,
                "__compressed__": compress,
            }
        elif storage_type == "webdav":
            if not all(k in config for k in ["webdav_url", "webdav_username", "webdav_password", "webdav_root"]):
                raise ValueError(
                    "WebDAV storage not configured correctly. Please set 'webdav_url', 'webdav_username', 'webdav_password', and 'webdav_root' in config."
                )
            
            webdav_options = {
                'webdav_hostname': config["webdav_url"],
                'webdav_login': config["webdav_username"],
                'webdav_password': config["webdav_password"],
            }
            
            client = WebDAVClient(webdav_options)
            root_path = config["webdav_root"]
            
            # Ensure the root directory exists
            if not client.check(root_path):
                client.mkdir(root_path)
            
            file_name = f"numpy_array_{long_id()}.{'npz' if compress else 'npy'}"
            remote_path = f"{root_path}/{file_name}"
            
            # Upload to WebDAV
            buffer.seek(0)
            temp_file_path = f"/tmp/numpy_array_{long_id()}.{'npz' if compress else 'npy'}"
            with open(temp_file_path, 'wb') as f:
                f.write(buffer.getvalue())
            
            try:
                client.upload(remote_path, temp_file_path)
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            
            return {
                "__numpy_array__": True,
                "__storage_type__": "webdav",
                "webdav_url": config["webdav_url"],
                "webdav_username": config["webdav_username"],
                "webdav_password": config["webdav_password"],
                "remote_path": remote_path,
                "dtype": str(arr.dtype),
                "shape": arr.shape,
                "__compressed__": compress,
            }
        elif storage_type == "gridfs" and db is not None:
            # Use GridFS for large arrays
            fs = GridFS(db)
            file_id = fs.put(
                data, filename=f"numpy_array_{long_id()}.{'npz' if compress else 'npy'}"
            )

            return {
                "__numpy_array__": True,
                "__storage_type__": "gridfs",
                "file_id": file_id,
                "dtype": str(arr.dtype),
                "shape": arr.shape,
                "__compressed__": compress,
            }
        else:
            raise ValueError(
                f"Invalid storage type '{storage_type}' or missing database connection"
            )
    else:
        # Use standard BSON Binary for smaller arrays
        return {
            "__numpy_array__": True,
            "__storage_type__": "binary",
            "data": Binary(data),
            "dtype": str(arr.dtype),
            "shape": arr.shape,
            "__compressed__": compress,
        }


def deserialize_numpy_array(data: Dict[str, Any], db: MongoClient = None) -> np.ndarray:
    if not data.get("__numpy_array__"):
        return data
    storage_type = data.get("__storage_type__", "binary")
    is_compressed = data.get(
        "__compressed__", True
    )  # Default to True for backward compatibility

    if storage_type == "gridfs" and db is not None:
        # Retrieve from GridFS
        fs = GridFS(db)
        grid_out = fs.get(data["file_id"])
        array_data = grid_out.read()

        # Load the array from the data
        buffer = io.BytesIO(array_data)
        if is_compressed:
            arr = np.load(buffer)["arr"]
        else:
            arr = np.load(buffer)
    elif storage_type == "local":
        # Load directly from local file
        file_path = Path(data["file_path"])
        if not file_path.exists():
            raise FileNotFoundError(f"Array file not found at {file_path}")
        if is_compressed:
            arr = np.load(file_path)["arr"]
        else:
            arr = np.load(file_path)
    elif storage_type == "webdav":
        # Load from WebDAV
        webdav_options = {
            'webdav_hostname': data["webdav_url"],
            'webdav_login': data["webdav_username"],
            'webdav_password': data["webdav_password"],
        }
        
        client = WebDAVClient(webdav_options)
        remote_path = data["remote_path"]
        
        # Download from WebDAV
        temp_file_path = f"/tmp/numpy_array_{long_id()}.{'npz' if is_compressed else 'npy'}"
        try:
            client.download(remote_path, temp_file_path)
            
            # Load the array from the temporary file
            if is_compressed:
                arr = np.load(temp_file_path)["arr"]
            else:
                arr = np.load(temp_file_path)
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    else:
        # Get the binary data directly from BSON
        array_data = data["data"]
        buffer = io.BytesIO(array_data)
        if is_compressed:
            arr = np.load(buffer)["arr"]
        else:
            arr = np.load(buffer)

    # Ensure the array has the original shape and dtype
    shape = data.get("shape")
    dtype_str = data.get("dtype")

    if shape and dtype_str:
        # Reshape if needed and cast to original dtype
        arr = arr.reshape(shape)
        if dtype_str != str(arr.dtype):
            arr = arr.astype(np.dtype(dtype_str))

    return arr


def serialize(
    obj: Any, db: MongoClient = None, storage_type: str = None
) -> Any:
    if isinstance(obj, np.ndarray):
        return serialize_numpy_array(obj, db, storage_type)
    elif isinstance(obj, dict):
        return {
            k: serialize(v, db, storage_type) for k, v in obj.items()
        }
    elif isinstance(obj, (list, tuple)):
        return [serialize(v, db, storage_type) for v in obj]
    return obj


def deserialize(obj: Any, db: MongoClient = None) -> Any:
    if isinstance(obj, dict):
        if obj.get("__numpy_array__"):
            return deserialize_numpy_array(obj, db)
        return {k: deserialize(v, db) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [deserialize(v, db) for v in obj]
    return obj


def cleanup_array_files(obj: Any, db: MongoClient = None) -> None:
    """Clean up any files associated with array storage (GridFS or local files)"""
    if isinstance(obj, dict):
        if obj.get("__numpy_array__"):
            storage_type = obj.get("__storage_type__", "binary")
            if storage_type == "gridfs" and db is not None:
                # Delete from GridFS
                fs = GridFS(db)
                try:
                    fs.delete(obj["file_id"])
                except Exception:
                    pass  # Ignore errors if file doesn't exist
            elif storage_type == "local":
                # Delete local file
                try:
                    file_path = Path(obj["file_path"])
                    if file_path.exists():
                        file_path.unlink()
                except Exception:
                    pass  # Ignore errors if file doesn't exist
            elif storage_type == "webdav":
                # Delete from WebDAV
                try:
                    webdav_options = {
                        'webdav_hostname': obj["webdav_url"],
                        'webdav_login': obj["webdav_username"],
                        'webdav_password': obj["webdav_password"],
                    }
                    client = WebDAVClient(webdav_options)
                    remote_path = obj["remote_path"]
                    if client.check(remote_path):
                        client.clean(remote_path)
                except Exception:
                    pass  # Ignore errors if file doesn't exist
        else:
            # Recursively clean up nested containers
            for value in obj.values():
                cleanup_array_files(value, db)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            cleanup_array_files(value, db)
