import io
import random
from pathlib import Path
from typing import Any, Dict

import lz4.frame
import numpy as np
from bson.binary import Binary
from gridfs import GridFS
from pymongo import MongoClient

from labdb.config import load_config
from labdb.utils import long_id

DEBUG = False


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
    # Always save as uncompressed numpy first
    np.save(buffer, arr)
    buffer.seek(0)
    raw_data = buffer.getvalue()
    
    # Apply lz4 compression if enabled
    if compress:
        data = lz4.frame.compress(raw_data)
    else:
        data = raw_data

    if DEBUG:
        compression_ratio = len(raw_data) / len(data) if compress else 1.0
        print(
            f"Serializing numpy array of shape {arr.shape}, dtype {arr.dtype}, "
            f"raw size {len(raw_data) / 1024:.2f} KB, "
            f"compressed size {len(data) / 1024:.2f} KB "
            f"(ratio: {compression_ratio:.2f}x)" if compress else f"size {len(data) / 1024:.2f} KB"
        )

    # Check if the data exceeds 5MB
    if len(data) > 5 * 1024 * 1024:
        # If no storage type specified, get it from config
        if storage_type is None:
            storage_type = config.get("large_file_storage", "none")

        if DEBUG:
            print(
                f"Large array detected ({len(data) / 1048576:.2f} MB), using storage type: {storage_type}"
            )

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

            file_name = f"numpy_array_{long_id()}.{'lz4' if compress else 'npy'}"
            file_path = storage_path / file_name

            # Write the data directly to file
            with open(file_path, "wb") as f:
                f.write(data)

            if DEBUG:
                print(
                    f"Saved array to local file: {file_path} ({len(data) / 1024:.2f} KB)"
                )

            return {
                "__numpy_array__": True,
                "__storage_type__": "local",
                "file_path": str(file_path),
                "dtype": str(arr.dtype),
                "shape": arr.shape,
                "__compressed__": compress,
            }
        elif storage_type == "gridfs" and db is not None:
            # Use GridFS for large arrays
            fs = GridFS(db)
            file_id = fs.put(
                data, filename=f"numpy_array_{long_id()}.{'lz4' if compress else 'npy'}"
            )

            if DEBUG:
                print(
                    f"Saved array to GridFS with ID: {file_id} ({len(data) / 1024:.2f} KB)"
                )

            # Add to cache if using GridFS
            config = load_config() or {}
            if config.get("local_cache_enabled"):
                _save_to_cache(data, file_id, config)

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
        if DEBUG:
            print(f"Using BSON Binary storage for array ({len(data) / 1024:.2f} KB)")

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

    if DEBUG:
        shape = data.get("shape")
        dtype = data.get("dtype")
        print(
            f"Deserializing numpy array of shape {shape}, dtype {dtype}, storage type: {storage_type}"
        )

    if storage_type == "gridfs" and db is not None:
        config = load_config() or {}

        # Try cache first
        cached_data = _read_from_cache(data["file_id"], config)
        if cached_data:
            array_data = cached_data
            if DEBUG:
                print(
                    f"Loaded array from cache, file_id: {data['file_id']} ({len(array_data) / 1024:.2f} KB)"
                )
        else:
            # Retrieve from GridFS
            fs = GridFS(db)
            grid_out = fs.get(data["file_id"])
            array_data = grid_out.read()

            if DEBUG:
                print(
                    f"Loaded array from GridFS, file_id: {data['file_id']} ({len(array_data) / 1024:.2f} KB)"
                )

            # Save to cache
            if config.get("local_cache_enabled"):
                _save_to_cache(array_data, data["file_id"], config)

        # Load array from the data
        buffer = io.BytesIO(array_data)
        if is_compressed:
            # Decompress with lz4 first, then load numpy array
            decompressed_data = lz4.frame.decompress(array_data)
            buffer = io.BytesIO(decompressed_data)
            arr = np.load(buffer)
        else:
            arr = np.load(buffer)
    elif storage_type == "local":
        # Load directly from local file
        file_path = Path(data["file_path"])
        if not file_path.exists():
            raise FileNotFoundError(f"Array file not found at {file_path}")

        if DEBUG:
            file_size = file_path.stat().st_size
            print(
                f"Loading array from local file: {file_path} ({file_size / 1024:.2f} KB)"
            )

        if is_compressed:
            # Read compressed file and decompress with lz4
            compressed_data = file_path.read_bytes()
            decompressed_data = lz4.frame.decompress(compressed_data)
            buffer = io.BytesIO(decompressed_data)
            arr = np.load(buffer)
        else:
            arr = np.load(file_path)
    else:
        # Get the binary data directly from BSON
        array_data = data["data"]

        if DEBUG:
            print(f"Loading array from BSON Binary ({len(array_data) / 1024:.2f} KB)")

        buffer = io.BytesIO(array_data)
        if is_compressed:
            # Decompress with lz4 first, then load numpy array
            decompressed_data = lz4.frame.decompress(array_data)
            buffer = io.BytesIO(decompressed_data)
            arr = np.load(buffer)
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

    if DEBUG:
        print(
            f"Successfully deserialized array with shape {arr.shape}, dtype {arr.dtype}"
        )

    return arr


def serialize_obj(obj: Any, db: MongoClient, storage_type: str = None) -> Any:
    if isinstance(obj, np.ndarray):
        return serialize_numpy_array(obj, db, storage_type)
    elif isinstance(obj, dict):
        return {k: serialize_obj(v, db, storage_type) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_obj(v, db, storage_type) for v in obj]
    return obj


def deserialize_obj(obj: Any, db: MongoClient) -> Any:
    if isinstance(obj, dict):
        if obj.get("__numpy_array__"):
            return deserialize_numpy_array(obj, db)
        return {k: deserialize_obj(v, db) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [deserialize_obj(v, db) for v in obj]
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
                    if DEBUG:
                        print(f"Deleted array from GridFS, file_id: {obj['file_id']}")
                except Exception:
                    pass  # Ignore errors if file doesn't exist
            elif storage_type == "local":
                # Delete local file
                try:
                    file_path = Path(obj["file_path"])
                    if file_path.exists():
                        if DEBUG:
                            file_size = file_path.stat().st_size
                            print(
                                f"Deleting local array file: {file_path} ({file_size / 1024:.2f} KB)"
                            )
                        file_path.unlink()
                except Exception:
                    pass  # Ignore errors if file doesn't exist
        else:
            # Recursively clean up nested containers
            for value in obj.values():
                cleanup_array_files(value, db)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            cleanup_array_files(value, db)


def _get_cache_path(config: dict, file_id: Any) -> Path:
    """Get cache path for a file ID"""
    cache_dir = Path(config.get("local_cache_path", "/tmp/labdb-cache"))
    return cache_dir / str(file_id)


def _save_to_cache(data: bytes, file_id: Any, config: dict):
    """Save data to local cache"""
    if not config.get("local_cache_enabled"):
        return

    cache_path = _get_cache_path(config, file_id)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    with open(cache_path, "wb") as f:
        f.write(data)

    if DEBUG:
        print(f"Saved array to cache: {cache_path} ({len(data) / 1024:.2f} KB)")

    # Update metadata and manage cache size
    _manage_cache_size(config)


def _read_from_cache(file_id: Any, config: dict) -> bytes | None:
    """Try to read from cache, returns None if not found"""
    if not config.get("local_cache_enabled"):
        return None

    cache_path = _get_cache_path(config, file_id)
    if cache_path.exists():
        # Update access time
        cache_path.touch()
        data = cache_path.read_bytes()
        if DEBUG:
            print(f"Read array from cache: {cache_path} ({len(data) / 1024:.2f} KB)")
        return data
    return None


def _manage_cache_size(config: dict):
    """Enforce cache size limits with LRU-random hybrid policy"""
    cache_dir = Path(config.get("local_cache_path", "/tmp/labdb-cache"))
    max_size = int(config.get("local_cache_max_size_mb", 1024)) * 1024 * 1024

    # Get all cache files with access times
    files = []
    total_size = 0
    for f in cache_dir.glob("*"):
        if f.is_file():
            stat = f.stat()
            files.append((stat.st_atime, f))
            total_size += stat.st_size

    if total_size > max_size:
        if DEBUG:
            print(
                f"Cache size ({total_size / 1048576:.2f} MB) exceeds limit, using LRU-random eviction"
            )

        # Sort by access time (oldest first)
        files.sort()

        # Process in groups of 2 LRU candidates
        while total_size > max_size and files:
            # Take 2 oldest candidates
            candidates = files[:2]
            if not candidates:
                break

            # Randomly select one to evict
            selected = random.choice(candidates)
            selected_time, selected_file = selected

            # Remove from files list and update total size
            files.remove(selected)
            file_size = selected_file.stat().st_size
            total_size -= file_size

            if DEBUG:
                print(
                    f"Evicting randomly selected from 2 LRU candidates: {selected_file.name} ({file_size / 1024:.2f} KB)"
                )

            selected_file.unlink()
