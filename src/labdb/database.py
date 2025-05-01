from datetime import datetime
import importlib.metadata

from pymongo import MongoClient

from labdb.config import load_config
from labdb.serialization import cleanup_array_files, deserialize, serialize
from labdb.utils import (
    escape_regex_path,
    get_parent_path,
    get_path_name,
    is_parent_path,
    join_path,
    merge_mongo_queries,
    short_directory_id,
    short_experiment_id,
    split_path,
    validate_path,
)

# Get version from package metadata
__version__ = importlib.metadata.version("labdb")

DEBUG = False

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
        except Exception as e:
            raise Exception(f"Failed to connect to database: {e}")

        # Get collections
        self.experiments = self.db.get_collection("experiments")
        self.directories = self.db.get_collection("directories")

        # Check if version is compatible
        if self.experiments.find_one({"_id": "version"}) is None:
            self.experiments.insert_one({"_id": "version", "version": __version__})
            self.experiments.create_index("path_str")
            self.directories.create_index("path_str")
        version = self.experiments.find_one({"_id": "version"})["version"]

        if version.split(".")[0] != __version__.split(".")[0]:
            raise Exception(f"Version mismatch: database@{version} != labdb@{__version__} (up/downgrade labdb to continue, or select/create a different database)")

    def create_dir(self, path: str, notes: dict = {}):
        """
        Create a new directory at the specified path.
        
        Args:
            path: The path to create (string)
            notes: Optional notes to associate with the directory
        """
        validate_path(path)

        if self.path_exists(path):
            raise Exception(f"Path {path} already exists")

        if path == "/":
            raise Exception("Cannot create path at root")

        # Verify all parent directories exist
        parent_path = get_parent_path(path)
        if not self.dir_exists(parent_path):
            raise Exception(f"Parent path {parent_path} does not exist")

        # Store path components for backward compatibility
        path_components = split_path(path)
        
        self.directories.insert_one(
            {
                "_id": short_directory_id(),
                "type": "directory",
                "path": path_components,
                "path_str": path,
                "notes": notes,
                "created_at": datetime.now(),
            }
        )
        return path

    def path_exists(self, path: str):
        """
        Check if a path exists (either directory or experiment).
        
        Args:
            path: The path to check (string)
            
        Returns:
            True if the path exists
        """
        if path == "/":
            return True
            
        return (
            self.directories.count_documents({"path_str": path}) > 0
            or self.experiments.count_documents({"path_str": path}) > 0
        )

    def ensure_path_exists(self, path: str):
        """
        Verify a path exists and raise an exception if it doesn't.
        
        Args:
            path: The path to verify (string)
        """
        if not self.path_exists(path):
            raise Exception(f"Path {path} does not exist")

    def dir_exists(self, path: str):
        """
        Check if a directory exists at the given path.
        
        Args:
            path: The directory path to check (string)
            
        Returns:
            True if the directory exists
        """
        if path == "/":
            return True
            
        return self.directories.count_documents({"path_str": path}) > 0

    def list_dir(self, path: str, only_project_paths: bool = False):
        """
        List all items in a directory.
        
        Args:
            path: The directory path to list (string)
            
        Returns:
            List of items (directories and experiments)
        """
        if not self.dir_exists(path):
            raise Exception(f"Directory {path} does not exist")

        # Make sure path ends with a slash for prefix matching
        parent_path = path if path.endswith("/") else path + "/"
        
        # Escape special regex characters for safety
        escaped_parent_path = escape_regex_path(parent_path)
        
        # Query for direct children using string path prefix
        # The regex matches paths that:
        # 1. Start with the parent path
        # 2. Have one additional path segment with no more slashes
        base_query = {"path_str": {"$regex": f"^{escaped_parent_path}[^/]+$"}}

        # Only project the fields we need
        if only_project_paths:
            projection = {"_id": 0, "type": 1, "path_str": 1, "created_at": 1}
        else:
            projection = {"_id": 0, "type": 1, "path_str": 1, "created_at": 1, "notes": 1}

        # Combine results from both collections
        dir_results = list(
            self.directories.find(base_query, projection).sort("created_at", -1)
        )
        exp_results = list(
            self.experiments.find(base_query, projection).sort("created_at", -1)
        )

        if DEBUG:
            import pprint
            explain_dir = self.directories.find(base_query, projection).sort("created_at", -1).explain()
            explain_exp = self.experiments.find(base_query, projection).sort("created_at", -1).explain()
            pprint.pprint(explain_dir)
            pprint.pprint(explain_exp)
        
        return dir_results + exp_results

    def update_dir_notes(self, path: str, notes: dict):
        """
        Update notes for a directory.
        
        Args:
            path: The directory path (string)
            notes: The new notes to set
        """
        self.directories.update_one({"path_str": path}, {"$set": {"notes": notes}})

    def create_experiment(
        self,
        path: str,
        name: str | None = None,
        data: dict = {},
        notes: dict = {},
    ):
        """
        Create a new experiment in the specified directory.
        
        Args:
            path: The directory path to create the experiment in (string)
            name: Optional name for the experiment
            data: Initial experiment data
            notes: Experiment notes
            
        Returns:
            The name/ID of the created experiment
        """
        if not self.dir_exists(path):
            raise Exception(f"Directory {path} does not exist")
            
        # Generate or validate the experiment ID
        if name:
            experiment_path = f"{path}/{name}" if path != "/" else f"/{name}"
            if self.path_exists(experiment_path):
                raise Exception(f"Experiment {name} already exists at {path}")
            experiment_id = name
        else:
            # Auto-increment number as ID
            experiment_id = str(self.count_experiments(path))
            experiment_path = f"{path}/{experiment_id}" if path != "/" else f"/{experiment_id}"
        
        # Store path components for backward compatibility
        path_components = split_path(experiment_path)
        
        self.experiments.insert_one(
            {
                "_id": short_experiment_id(),
                "type": "experiment",
                "path": path_components,
                "path_str": experiment_path,
                "created_at": datetime.now(),
                "data": serialize(data, self.db),
                "notes": notes,
            }
        )
        return experiment_path, experiment_id

    def update_experiment_notes(self, path: str, notes: dict):
        """
        Update notes for an experiment.
        
        Args:
            path: The experiment path (string)
            notes: The new notes to set
        """
        self.ensure_path_exists(path)
        self.experiments.update_one({"path_str": path}, {"$set": {"notes": notes}})

    def add_experiment_data(self, path: str, key: str, value: any):
        """
        Add data to an experiment.
        
        Args:
            path: The experiment path (string)
            key: The data key
            value: The value to store
        """
        self.ensure_path_exists(path)
        self.experiments.update_one(
            {"path_str": path}, {"$set": {f"data.{key}": serialize(value, self.db)}}
        )

    def add_experiment_note(self, path: str, key: str, value: any):
        """
        Add a note to an experiment.
        
        Args:
            path: The experiment path (string)
            key: The note key
            value: The value to store
        """
        self.ensure_path_exists(path)
        self.experiments.update_one(
            {"path_str": path}, {"$set": {f"notes.{key}": value}}
        )
    

    def count_experiments(self, path: str) -> int:
        """
        Count experiments in a directory.
        
        Args:
            path: The directory path (string)
            
        Returns:
            The number of experiments in the directory
        """
        # Make sure path ends with a slash for prefix matching
        parent_path = path if path.endswith("/") else path + "/"
        
        # Escape special regex characters for safety
        escaped_parent_path = escape_regex_path(parent_path)
        
        query = {"path_str": {"$regex": f"^{escaped_parent_path}[^/]+$"}}
        return self.experiments.count_documents(query)

    def _build_path_prefix_query(self, path: str) -> dict:
        if path == "/":
            return {"path_str": {"$ne": None}}
        
        prefix = path if path.endswith("/") else path + "/"
        end_prefix = prefix[:-1] + chr(ord(prefix[-1]) + 1)
        
        return {
            "$or": [
                {"path_str": path},
                {"path_str": {"$gte": prefix, "$lt": end_prefix}}
            ]
        }

    def _get_collection_counts(self, dir_query: dict, exp_query: dict) -> dict:
        """
        Get counts of directories and experiments matching given queries.
        
        Args:
            dir_query: Query for directories collection
            exp_query: Query for experiments collection
            
        Returns:
            Dict with counts of directories and experiments
        """
        return {
            "directories": self.directories.count_documents(dir_query),
            "experiments": self.experiments.count_documents(exp_query),
        }

    def _update_paths(
        self, collection, query: dict, src_path: str, dest_path: str
    ):
        """
        Update paths for all documents matching the query.
        
        Args:
            collection: The MongoDB collection to update
            query: Query to match documents
            src_path: Source path prefix
            dest_path: Destination path prefix
        """
        for doc in collection.find(query, {"_id": 1, "path_str": 1}):
            # Calculate the new path by replacing the src_path prefix with dest_path
            new_path_str = doc["path_str"].replace(src_path, dest_path, 1)
            
            # Also update the path array for backward compatibility
            new_path = split_path(new_path_str)
            
            collection.update_one(
                {"_id": doc["_id"]}, 
                {"$set": {"path": new_path, "path_str": new_path_str}}
            )

    def delete(self, path: str, dry_run: bool = False):
        """
        Delete a path and all its children.
        
        Args:
            path: The path to delete (string)
            dry_run: If True, only count affected items without deleting
            
        Returns:
            Dict with counts of affected items if dry_run is True
        """
        # Check for wildcard to delete all items in a directory
        if path.endswith("/*"):
            # Ensure wildcard is only used at the end of the path
            if "*" in path[:-2]:
                raise Exception(
                    f"Wildcard (*) can only be used at the end of a path"
                )

            dir_path = path[:-2]
            if not self.dir_exists(dir_path):
                raise Exception(f"Directory {dir_path} does not exist")

            # Get all immediate children and count/delete them
            items = self.list_dir(dir_path)
            if dry_run:
                affected_counts = {"experiments": 0, "directories": 0}
                for item in items:
                    item_counts = self.delete(item["path_str"], dry_run=True)
                    affected_counts["experiments"] += item_counts["experiments"]
                    affected_counts["directories"] += item_counts["directories"]
                return affected_counts
            else:
                for item in items:
                    self.delete(item["path_str"])
                return None

        # Unified query building using path_str
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

    def move(self, src_path: str, dest_path: str, dry_run: bool = False):
        """
        Move a path and all its children to a new location.
        
        Args:
            src_path: The source path to move (string)
            dest_path: The destination path to move to (string)
            dry_run: If True, only count affected items without moving
            
        Returns:
            Dict with counts of affected items if dry_run is True
        """
        if src_path == "/":
            raise Exception("Cannot move the root directory")

        # Handle wildcard in source path
        if src_path.endswith("/*"):
            # Ensure wildcard is only used at the end of the path
            if "*" in src_path[:-2]:
                raise Exception(
                    f"Wildcard (*) can only be used at the end of a path"
                )

            src_dir_path = src_path[:-2]
            if not self.dir_exists(src_dir_path):
                raise Exception(
                    f"Source directory {src_dir_path} does not exist"
                )

            # Ensure destination is a directory
            if not self.dir_exists(dest_path):
                raise Exception(
                    f"Destination {dest_path} must be an existing directory when moving with wildcard"
                )

            # Move all immediate children
            items = self.list_dir(src_dir_path)
            if dry_run:
                affected_counts = {"experiments": 0, "directories": 0}
                for item in items:
                    item_path = item["path_str"]
                    item_name = get_path_name(item_path)
                    dest_item_path = f"{dest_path}/{item_name}"
                    
                    item_counts = self.move(
                        item_path, dest_item_path, dry_run=True
                    )
                    affected_counts["experiments"] += item_counts["experiments"]
                    affected_counts["directories"] += item_counts["directories"]
                return affected_counts
            else:
                for item in items:
                    item_path = item["path_str"]
                    item_name = get_path_name(item_path)
                    dest_item_path = f"{dest_path}/{item_name}"
                    
                    self.move(item_path, dest_item_path)
                return None

        # Unified query building using path_str
        path_query = self._build_path_prefix_query(src_path)

        if dry_run:
            return self._get_collection_counts(path_query, path_query)

        # Unified path updates
        self._update_paths(self.directories, path_query, src_path, dest_path)
        self._update_paths(self.experiments, path_query, src_path, dest_path)
        return None

    def get_experiments(
        self,
        path: str,
        recursive: bool = False,
        query: dict = None,
        projection: dict = None,
        sort: list = None,
        limit: int = None,
    ):
        """
        Get experiments at a path.
        
        Args:
            path: The path to get experiments from (string)
            recursive: If True, include experiments in subdirectories
            query: Additional query conditions
            projection: Fields to include in the results
            sort: Sort specification
            limit: Maximum number of results
            
        Returns:
            List of experiments
        """
        final_projection = projection if projection else {}

        # Special case: single experiment by exact path
        exp = self.experiments.find_one({"path_str": path}, final_projection)
        if exp:
            # Only deserialize the data field
            if 'data' in exp:
                exp['data'] = deserialize(exp['data'], self.db)
            return [exp]

        if not self.dir_exists(path):
            raise Exception(f"Path {path} does not exist")

        # Simplified query building using path_str
        if recursive:
            # Match all paths that have this path as prefix
            base_query = self._build_path_prefix_query(path)
        else:
            # Match only direct children
            parent_path = path if path.endswith("/") else path + "/"
            escaped_parent_path = escape_regex_path(parent_path)
            base_query = {"path_str": {"$regex": f"^{escaped_parent_path}[^/]+$"}}

        final_query = merge_mongo_queries(base_query, query)
        count = self.experiments.count_documents(final_query)
        cursor = self.experiments.find(final_query, final_projection)

        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)

        # Return experiments with only the data field deserialized
        result = []
        total = min(count, limit) if limit else count
        for i, exp in enumerate(cursor):
            if total > 1:
                print(f"\rFetching experiments... {i+1}/{total}", end="", flush=True)
            # Only deserialize the data field
            if 'data' in exp:
                exp['data'] = deserialize(exp['data'], self.db)
            result.append(exp)
        if total > 1:
            print()  # Add a newline after the status line
        return result
