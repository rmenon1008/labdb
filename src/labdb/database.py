from datetime import datetime

from pymongo import MongoClient

from labdb.config import load_config
from labdb.serialization import cleanup_array_files, serialize, deserialize
from labdb.utils import (
    join_path,
    merge_mongo_queries,
    short_directory_id,
    short_experiment_id,
    split_path,
    validate_path,
)


class Database:
    def __init__(self, config: dict):
        # Connect to database
        self.config = config
        conn_string = self.config["conn_string"]
        db_name = self.config["db_name"]
        try:
            self.db = MongoClient(conn_string, serverSelectionTimeoutMS=5000)[db_name]
            self.db.command("ping")
            self.db.list_collection_names()
        except Exception as e:
            raise Exception(f"Failed to connect to database: {e}")

        # Get collections
        self.experiments = self.db.get_collection("experiments")
        self.directories = self.db.get_collection("directories")

    def create_dir(self, path: list[str], notes: dict = {}):
        validate_path(path)

        if self.path_exists(path):
            raise Exception(f"Path {path} already exists")

        if len(path) == 0:
            raise Exception("Cannot create path at root")

        for i in range(len(path) - 1):
            if not self.dir_exists(path[: i + 1]):
                raise Exception(f"Parent path {path[:i+1]} does not exist")

        self.directories.insert_one(
            {
                "_id": short_directory_id(),
                "path": path,
                "notes": notes,
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
            raise Exception(f"Path {path} does not exist")

    def dir_exists(self, path: list[str]):
        if len(path) == 0:
            return True
        return self.directories.count_documents({"path": path}) > 0

    def list_dir(self, path: list[str]):
        if not self.dir_exists(path):
            raise Exception(f"Directory {path} does not exist")

        base_query = {"path": {"$size": len(path) + 1}}
        if len(path) > 0:
            base_query["path"]["$all"] = path
            base_query[f"path.{len(path) - 1}"] = path[-1]

        # Combine results from both collections
        dir_results = list(self.directories.find(base_query))
        exp_results = list(self.experiments.find(base_query))

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
            raise Exception(f"Directory {path} does not exist")
        if name:
            if self.path_exists(path + [name]):
                raise Exception(f"Experiment {name} already exists at {path}")
            experiment_id = name
        else:
            experiment_id = str(self.count_experiments(path))
        full_path = path + [experiment_id]

        self.experiments.insert_one(
            {
                "_id": short_experiment_id(),
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
        self.experiments.update_one({"path": path}, {"$set": {f"data.{key}": serialize(value, self.db)}})

    def count_experiments(self, path: list[str]) -> int:
        query = {
            "path": {"$size": len(path) + 1},
        }
        if len(path) > 0:
            query["path"] = {"$all": path}
            query[f"path.{len(path) - 1}"] = path[-1]
        return self.experiments.count_documents(query)

    def delete(self, path: list[str]):
        dir_doc = self.directories.find_one({"path": path})
        if dir_doc:
            dir_query = {
                "$expr": {
                    "$and": [
                        {"$gte": [{"$size": "$path"}, len(path)]},
                        {"$eq": [{"$slice": ["$path", len(path)]}, path]},
                    ]
                }
            }
            self.directories.delete_many(dir_query)

            exp_query = {
                "$expr": {
                    "$and": [
                        {"$gte": [{"$size": "$path"}, len(path)]},
                        {"$eq": [{"$slice": ["$path", len(path)]}, path]},
                    ]
                }
            }
            exps = list(self.experiments.find(exp_query))
            for exp in exps:
                cleanup_array_files(exp, self.db)
            self.experiments.delete_many(exp_query)
            return

        exp_doc = self.experiments.find_one({"path": path})
        if exp_doc:
            cleanup_array_files(exp_doc, self.db)
            self.experiments.delete_one({"path": path})
            return

        raise Exception(f"Path {path} does not exist")

    def move(self, src_path: list[str], dest_path: list[str]):
        if len(src_path) == 0:
            raise Exception("Cannot move the root directory")

        src_dir = self.directories.find_one({"path": src_path})
        src_exp = None
        if not src_dir:
            src_exp = self.experiments.find_one({"path": src_path})
            if not src_exp:
                raise Exception(f"Source path {src_path} does not exist")

        if len(dest_path) > 0 and not self.dir_exists(dest_path[:-1]):
            raise Exception(
                f"Destination parent directory {dest_path[:-1]} does not exist"
            )

        dest_exists = self.path_exists(dest_path)

        if dest_exists:
            dest_dir = self.directories.find_one({"path": dest_path})
            if dest_dir:
                new_dest_path = dest_path + [src_path[-1]]

                if self.path_exists(new_dest_path):
                    raise Exception(f"Destination path {new_dest_path} already exists")

                dest_path = new_dest_path
            else:
                raise Exception(
                    f"Destination path {dest_path} already exists and is not a directory"
                )

        if src_dir:
            dir_query = {
                "$expr": {
                    "$and": [
                        {"$gte": [{"$size": "$path"}, len(src_path)]},
                        {"$eq": [{"$slice": ["$path", len(src_path)]}, src_path]},
                    ]
                }
            }
            dirs = list(self.directories.find(dir_query))
            for d in dirs:
                old_path = d["path"]
                new_path = dest_path + old_path[len(src_path) :]
                self.directories.update_one(
                    {"_id": d["_id"]}, {"$set": {"path": new_path}}
                )

            exp_query = {
                "$expr": {
                    "$and": [
                        {"$gte": [{"$size": "$path"}, len(src_path)]},
                        {"$eq": [{"$slice": ["$path", len(src_path)]}, src_path]},
                    ]
                }
            }
            exps = list(self.experiments.find(exp_query))
            for e in exps:
                old_path = e["path"]
                new_path = dest_path + old_path[len(src_path) :]
                self.experiments.update_one(
                    {"_id": e["_id"]}, {"$set": {"path": new_path}}
                )
        else:
            self.experiments.update_one(
                {"_id": src_exp["_id"]}, {"$set": {"path": dest_path}}
            )

    def get_experiments(
        self,
        path: list[str],
        recursive: bool = True,
        query: dict = None,
        projection: dict = None,
        sort: list = None,
        limit: int = None,
    ):
        # Special case: single experiment by exact path
        exp = self.experiments.find_one({"path": path})
        if exp:
            if projection:
                exp = self.experiments.find_one({"path": path}, projection)
            # Deserialize the data field
            if "data" in exp:
                exp["data"] = deserialize(exp["data"], self.db)
                # For direct experiment access, promote the data fields to top level
                return [deserialize(exp["data"], self.db)]
            return [{}]  # Return empty data if no data field found

        if not self.dir_exists(path):
            raise Exception(f"Path {path} does not exist")

        base_query = {}
        if recursive:
            base_query = {
                "$expr": {
                    "$and": [
                        {"$gt": [{"$size": "$path"}, len(path)]},
                        {"$eq": [{"$slice": ["$path", len(path)]}, path]},
                    ]
                }
            }
        else:
            base_query = {"path": {"$size": len(path) + 1}}
            if len(path) > 0:
                base_query["path"] = {"$all": path, "$size": len(path) + 1}
                base_query[f"path.{len(path) - 1}"] = path[-1]

        final_query = merge_mongo_queries(base_query, query)
        cursor = self.experiments.find(final_query, projection)

        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)

        # Return only the deserialized data fields from all experiments
        result = []
        for exp in cursor:
            if "data" in exp:
                result.append(deserialize(exp["data"], self.db))
            else:
                result.append({})
        return result
