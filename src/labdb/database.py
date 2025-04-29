from datetime import datetime

from pymongo import MongoClient

from labdb.config import load_config
from labdb.serialization import cleanup_array_files, deserialize, serialize
from labdb.utils import (
    join_path,
    merge_mongo_queries,
    short_directory_id,
    short_experiment_id,
    split_path,
    validate_path,
)


class Database:
    def __init__(self, config: dict | None = None):
        # Connect to database
        if config is None:
            config = load_config()

        self.config = config
        conn_string = self.config["conn_string"]
        db_name = self.config["db_name"]
        try:
            self.client = MongoClient(conn_string, serverSelectionTimeoutMS=5000)
            self.db = self.client[db_name]
            # No need to ping or list collections on init - will fail on first actual operation if issue
        except Exception as e:
            raise Exception(f"Failed to connect to database: {e}")

        # Get collections
        self.experiments = self.db.get_collection("experiments")
        self.directories = self.db.get_collection("directories")

    def create_dir(self, path: list[str], notes: dict = {}):
        validate_path(path)

        if self.path_exists(path):
            raise Exception(f"Path {join_path(path)} already exists")

        if len(path) == 0:
            raise Exception("Cannot create path at root")

        for i in range(len(path) - 1):
            if not self.dir_exists(path[: i + 1]):
                raise Exception(f"Parent path {path[:i+1]} does not exist")

        self.directories.insert_one(
            {
                "_id": short_directory_id(),
                "type": "directory",
                "path": path,
                "notes": notes,
                "created_at": datetime.now(),
            }
        )

    def path_exists(self, path: list[str]):
        if len(path) == 0:
            return True
        return (
            self.directories.count_documents({"path": path}) > 0
            or self.experiments.count_documents({"path": path}) > 0
        )

    def ensure_path_exists(self, path: list[str]):
        if not self.path_exists(path):
            raise Exception(f"Path {join_path(path)} does not exist")

    def dir_exists(self, path: list[str]):
        if len(path) == 0:
            return True
        return self.directories.count_documents({"path": path}) > 0

    def list_dir(self, path: list[str]):
        if not self.dir_exists(path):
            raise Exception(f"Directory {join_path(path)} does not exist")

        base_query = {"path": {"$size": len(path) + 1}}
        if len(path) > 0:
            base_query["path"]["$all"] = path
            base_query[f"path.{len(path) - 1}"] = path[-1]

        # Only project the fields we need
        projection = {"_id": 0, "type": 1, "path": 1, "created_at": 1, "notes": 1}

        # Combine results from both collections
        dir_results = list(
            self.directories.find(base_query, projection).sort("created_at", -1)
        )
        exp_results = list(
            self.experiments.find(base_query, projection).sort("created_at", -1)
        )

        return dir_results + exp_results

    def update_dir_notes(self, path: list[str], notes: dict):
        self.directories.update_one({"path": path}, {"$set": {"notes": notes}})

    def create_experiment(
        self,
        path: list[str],
        name: str | None = None,
        data: dict = {},
        notes: dict = {},
    ):
        if not self.dir_exists(path):
            raise Exception(f"Directory {join_path(path)} does not exist")
        if name:
            if self.path_exists(path + [name]):
                raise Exception(
                    f"Experiment {name} already exists at {join_path(path)}"
                )
            experiment_id = name
        else:
            experiment_id = str(self.count_experiments(path))
        full_path = path + [experiment_id]

        self.experiments.insert_one(
            {
                "_id": short_experiment_id(),
                "type": "experiment",
                "path": full_path,
                "created_at": datetime.now(),
                "data": serialize(data, self.db),
                "notes": notes,
            }
        )
        return experiment_id

    def update_experiment_notes(self, path: list[str], notes: dict):
        self.ensure_path_exists(path)
        self.experiments.update_one({"path": path}, {"$set": {"notes": notes}})

    def add_experiment_data(self, path: list[str], key: str, value: any):
        self.ensure_path_exists(path)
        self.experiments.update_one(
            {"path": path}, {"$set": {f"data.{key}": serialize(value, self.db)}}
        )

    def count_experiments(self, path: list[str]) -> int:
        query = {
            "path": {"$size": len(path) + 1},
        }
        if len(path) > 0:
            query["path"] = {"$all": path}
            query[f"path.{len(path) - 1}"] = path[-1]
        return self.experiments.count_documents(query)

    def _build_path_prefix_query(self, path: list[str]) -> dict:
        """Build a query matching documents with paths starting with the given prefix."""
        return {
            "$expr": {
                "$and": [
                    {"$gte": [{"$size": "$path"}, len(path)]},
                    {"$eq": [{"$slice": ["$path", len(path)]}, path]},
                ]
            }
        }

    def _get_collection_counts(self, dir_query: dict, exp_query: dict) -> dict:
        """Get counts of directories and experiments matching given queries."""
        return {
            "directories": self.directories.count_documents(dir_query),
            "experiments": self.experiments.count_documents(exp_query),
        }

    def _update_paths(
        self, collection, query: dict, src_path: list[str], dest_path: list[str]
    ):
        """Update paths for all documents matching the query."""
        for doc in collection.find(query, {"_id": 1, "path": 1}):
            new_path = dest_path + doc["path"][len(src_path) :]
            collection.update_one({"_id": doc["_id"]}, {"$set": {"path": new_path}})

    def delete(self, path: list[str], dry_run: bool = False):
        # Check for wildcard to delete all items in a directory
        if len(path) > 0 and path[-1] == "*":
            # Ensure wildcard is only used in the last position
            for i in range(len(path) - 1):
                if "*" in path[i]:
                    raise Exception(
                        f"Wildcard (*) can only be used in the last position of a path"
                    )

            dir_path = path[:-1]
            if not self.dir_exists(dir_path):
                raise Exception(f"Directory {join_path(dir_path)} does not exist")

            # Get all immediate children and count/delete them
            items = self.list_dir(dir_path)
            if dry_run:
                affected_counts = {"experiments": 0, "directories": 0}
                for item in items:
                    item_counts = self.delete(item["path"], dry_run=True)
                    affected_counts["experiments"] += item_counts["experiments"]
                    affected_counts["directories"] += item_counts["directories"]
                return affected_counts
            else:
                for item in items:
                    self.delete(item["path"])
                return None

        # Unified query building
        path_query = self._build_path_prefix_query(path)

        if dry_run:
            return self._get_collection_counts(path_query, path_query)

        # Unified cleanup and deletion
        exps = list(self.experiments.find(path_query, {"_id": 0, "data": 1}))
        for exp in exps:
            cleanup_array_files(exp, self.db)

        self.experiments.delete_many(path_query)
        self.directories.delete_many(path_query)
        return None

    def move(self, src_path: list[str], dest_path: list[str], dry_run: bool = False):
        if len(src_path) == 0:
            raise Exception("Cannot move the root directory")

        # Handle wildcard in source path
        if len(src_path) > 0 and src_path[-1] == "*":
            src_dir_path = src_path[:-1]
            if not self.dir_exists(src_dir_path):
                raise Exception(
                    f"Source directory {join_path(src_dir_path)} does not exist"
                )

            # Ensure destination is a directory
            if not self.dir_exists(dest_path):
                raise Exception(
                    f"Destination {join_path(dest_path)} must be an existing directory when moving with wildcard"
                )

            # Move all immediate children
            items = self.list_dir(src_dir_path)
            if dry_run:
                affected_counts = {"experiments": 0, "directories": 0}
                for item in items:
                    item_path = item["path"]
                    item_counts = self.move(
                        item_path, dest_path + [item_path[-1]], dry_run=True
                    )
                    affected_counts["experiments"] += item_counts["experiments"]
                    affected_counts["directories"] += item_counts["directories"]
                return affected_counts
            else:
                for item in items:
                    item_path = item["path"]
                    self.move(item_path, dest_path + [item_path[-1]])
                return None

        # Unified query building
        path_query = self._build_path_prefix_query(src_path)

        if dry_run:
            return self._get_collection_counts(path_query, path_query)

        # Unified path updates
        self._update_paths(self.directories, path_query, src_path, dest_path)
        self._update_paths(self.experiments, path_query, src_path, dest_path)
        return None

    def get_experiments(
        self,
        path: list[str],
        recursive: bool = True,
        query: dict = None,
        projection: dict = None,
        sort: list = None,
        limit: int = None,
    ):
        final_projection = projection if projection else {}

        # Special case: single experiment by exact path
        exp = self.experiments.find_one({"path": path}, final_projection)
        if exp:
            return [deserialize(exp, self.db)]

        if not self.dir_exists(path):
            raise Exception(f"Path {join_path(path)} does not exist")

        # Simplified query building
        base_query = (
            self._build_path_prefix_query(path)
            if recursive
            else {"path": {"$size": len(path) + 1, "$all": path}}
        )

        final_query = merge_mongo_queries(base_query, query)
        count = self.experiments.count_documents(final_query)
        cursor = self.experiments.find(final_query, final_projection)

        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)

        # Return only the deserialized fields from all experiments
        result = []
        total = min(count, limit) if limit else count
        for i, exp in enumerate(cursor):
            print(f"\rFetching experiments... {i+1}/{total}", end="", flush=True)
            result.append(deserialize(exp, self.db))
        if total > 0:
            print()  # Add a newline after the status line
        return result
