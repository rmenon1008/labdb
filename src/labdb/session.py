from datetime import datetime

from pymongo import MongoClient

from labdb.utils import short_id
from labdb.array_utils import cleanup_array_files


class SessionError(Exception):
    """Base exception for session-related errors"""

    pass


class SessionNotFoundError(SessionError):
    """Exception raised when a session is not found"""

    pass


class NoSessionsError(SessionError):
    """Exception raised when no sessions exist"""

    pass


class Session:
    def __init__(self, db: MongoClient, name: str, details: dict):
        self.id = short_id()
        self.name = name
        self.details = details
        self.created_at = datetime.now()
        self.db = db
        self._save()

    def _save(self):
        self.db.get_collection("sessions").insert_one(
            {
                "_id": self.id,
                "name": self.name,
                "created_at": self.created_at,
                "details": self.details,
            }
        )

    @classmethod
    def list(cls, db: MongoClient, limit: int = None, fields: list[str] = None):
        if fields:
            projection = {field: 1 for field in fields}
            projection["_id"] = 1
            query = db.get_collection("sessions").find({}, projection).sort("created_at", -1)
        else:
            query = db.get_collection("sessions").find().sort("created_at", -1)
        if limit:
            return query.limit(limit)
        return query

    @classmethod
    def get(cls, db: MongoClient, id: str):
        session = db.get_collection("sessions").find_one({"_id": id})
        if not session:
            raise SessionNotFoundError(f"Session with ID '{id}' not found")
        return session

    @classmethod
    def delete(cls, db: MongoClient, id: str):
        # First verify the session exists
        cls.get(db, id)
        
        # Get all experiments in this session
        experiments = db.get_collection("experiments").find({"session_id": id})
        
        # Clean up array files from each experiment
        for experiment in experiments:
            if "outputs" in experiment:
                cleanup_array_files(experiment["outputs"], db)
        
        # Delete all experiments in this session
        db.get_collection("experiments").delete_many({"session_id": id})
        
        # Finally delete the session itself
        db.get_collection("sessions").delete_one({"_id": id})

    @classmethod
    def replace_details(cls, db: MongoClient, id: str, details: dict):
        # First verify the session exists
        cls.get(db, id)
        db.get_collection("sessions").update_one({"_id": id}, {"$set": {"details": details}})

    @classmethod
    def get_most_recent(cls, db: MongoClient):
        if not db.get_collection("sessions").count_documents({}):
            raise NoSessionsError(
                "Tried using most recent session as default, but no sessions found. Create one first with `session create`"
            )
        session = db.get_collection("sessions").find().sort("created_at", -1).limit(1)[0]
        return session
