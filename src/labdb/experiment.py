from datetime import datetime

from pymongo import MongoClient

from labdb.utils import short_id
from labdb.array_utils import cleanup_array_files


class ExperimentError(Exception):
    """Base exception for experiment-related errors"""

    pass


class ExperimentNotFoundError(ExperimentError):
    """Exception raised when an experiment is not found"""

    pass


class NoExperimentsError(ExperimentError):
    """Exception raised when no experiments exist"""

    pass


class Experiment:
    def __init__(self, db: MongoClient, session_id: str, outputs: dict = None):
        self.id = short_id()
        self.session_id = session_id
        self.outputs = outputs or {}
        self.created_at = datetime.now()
        self.db = db
        self._save()

    def _save(self):
        self.db.get_collection("experiments").insert_one(
            {
                "_id": self.id,
                "session_id": self.session_id,
                "outputs": self.outputs,
                "created_at": self.created_at,
            }
        )

    @classmethod
    def list(cls, db: MongoClient, session_id: str, limit: int = None, fields: list[str] = None):
        if fields:
            projection = {field: 1 for field in fields}
            projection["_id"] = 1
            query = (
                db.get_collection("experiments")
                .find({"session_id": session_id}, projection)
                .sort("created_at", -1)
            )
        else:
            query = (
                db.get_collection("experiments")
                .find({"session_id": session_id})
                .sort("created_at", -1)
            )
        if limit:
            return query.limit(limit)
        return query

    @classmethod
    def get(cls, db: MongoClient, id: str):
        experiment = db.get_collection("experiments").find_one({"_id": id})
        if not experiment:
            raise ExperimentNotFoundError(f"Experiment with ID '{id}' not found")
        return experiment

    @classmethod
    def delete(cls, db: MongoClient, id: str):
        # First verify the experiment exists and get its data
        experiment = cls.get(db, id)
        
        # Clean up any array files in the outputs
        if "outputs" in experiment:
            cleanup_array_files(experiment["outputs"], db)
        
        # Delete the experiment document
        db.get_collection("experiments").delete_one({"_id": id})

    @classmethod
    def update_outputs(cls, db: MongoClient, id: str, outputs: dict):
        # First verify the experiment exists
        cls.get(db, id)
        # Update the entire outputs dictionary
        db.get_collection("experiments").update_one(
            {"_id": id}, {"$set": {"outputs": outputs}}
        )

    @classmethod
    def merge_output(cls, db: MongoClient, id: str, output: dict):
        # First verify the experiment exists
        cls.get(db, id)
        # Use MongoDB's $merge operator to merge the output dictionary
        for key, value in output.items():
            db.get_collection("experiments").update_one(
                {"_id": id}, {"$set": {f"outputs.{key}": value}}
            )

    @classmethod
    def get_most_recent(cls, db: MongoClient, session_id: str | None = None):
        collection = db.get_collection("experiments")

        if session_id:
            filter_query = {"session_id": session_id}
        else:
            filter_query = {}

        # Check if any experiments exist
        if collection.count_documents(filter_query) == 0:
            raise NoExperimentsError(
                "Tried using most recent experiment as default, but no experiments found. Create one first with `experiment create`"
            )

        # Get the most recent experiment
        experiment = collection.find(filter_query).sort("created_at", -1).limit(1)[0]
        return experiment
