from datetime import datetime

from pymongo import MongoClient

from labdb.config import load_config
from labdb.serialization import (
    cleanup_array_files,
)
from labdb.utils import short_experiment_id, short_session_id


class Database:
    def __init__(self):
        # Load config
        self.config = load_config()
        if not self.config:
            raise Exception("No database configuration found. Run `labdb config setup`")

        # Connect to database
        conn_string = self.config["conn_string"]
        db_name = self.config["db_name"]
        try:
            self.db = MongoClient(conn_string, serverSelectionTimeoutMS=5000)[db_name]
            self.db.command("ping")
            self.db.list_collection_names()
        except Exception as e:
            raise Exception(f"Failed to connect to database: {e}")

        # Get collections
        self.sessions = self.db.get_collection("sessions")
        self.experiments = self.db.get_collection("experiments")

    # Session methods
    def create_session(self, name: str, details: dict):
        session_id = short_session_id()
        self.sessions.insert_one(
            {
                "_id": session_id,
                "name": name,
                "created_at": datetime.now(),
                "details": details,
            }
        )
        return session_id

    def session_exists(self, session_id: str):
        return self.sessions.count_documents({"_id": session_id}) > 0

    def get_session(self, session_id: str, projection: dict = {}):
        session = self.sessions.find_one({"_id": session_id}, projection)
        if not session:
            raise Exception(f"Session {session_id} not found")
        return session

    def update_session_details(self, session_id: str, details: dict):
        if not self.session_exists(session_id):
            raise Exception(f"Session {session_id} not found")
        self.sessions.update_one({"_id": session_id}, {"$set": {"details": details}})

    def delete_session_with_cleanup(self, session_id: str):
        if not self.session_exists(session_id):
            raise Exception(f"Session {session_id} not found")
        experiments = self.experiments.find({"session_id": session_id})
        for experiment in experiments:
            cleanup_array_files(experiment, self.db)
        self.experiments.delete_many({"session_id": session_id})
        self.sessions.delete_one({"_id": session_id})

    def get_last_notes(self, session_id: str):
        projection = {"notes": 1}
        experiment = next(
            self.experiments.find({"session_id": session_id}, projection)
            .sort("created_at", -1)
            .limit(1),
            None,
        )
        if not experiment:
            return {}
        return experiment.get("notes", {})

    def get_most_recent_session(self, projection: dict = {}):
        session = next(
            self.sessions.find({}, projection).sort("created_at", -1).limit(1), None
        )
        if not session:
            raise Exception("No sessions found")
        return session

    def create_experiment(self, session_id: str, data: dict, notes: dict = {}):
        experiment_id = short_experiment_id()
        self.experiments.insert_one(
            {
                "_id": experiment_id,
                "session_id": session_id,
                "created_at": datetime.now(),
                "data": data,
                "notes": notes,
            }
        )
        return experiment_id

    def experiment_exists(self, experiment_id: str):
        return self.experiments.count_documents({"_id": experiment_id}) > 0

    def get_experiment(self, experiment_id: str, projection: dict = {}):
        experiment = self.experiments.find_one({"_id": experiment_id}, projection)
        if not experiment:
            raise Exception(f"Experiment {experiment_id} not found")
        return experiment

    def update_experiment_notes(self, experiment_id: str, notes: dict):
        if not self.experiment_exists(experiment_id):
            raise Exception(f"Experiment {experiment_id} not found")
        self.experiments.update_one(
            {"_id": experiment_id},
            {"$set": {"notes": notes}},
        )

    def experiment_log_data(self, experiment_id: str, key: str, value: any):
        if not self.experiment_exists(experiment_id):
            raise Exception(f"Experiment {experiment_id} not found")
        self.experiments.update_one(
            {"_id": experiment_id},
            {"$set": {f"data.{key}": value}},
        )

    def experiment_log_note(self, experiment_id: str, key: str, value: any):
        if not self.experiment_exists(experiment_id):
            raise Exception(f"Experiment {experiment_id} not found")
        self.experiments.update_one(
            {"_id": experiment_id},
            {"$set": {f"notes.{key}": value}},
        )

    def delete_experiment_with_cleanup(self, experiment_id: str):
        experiment = self.experiments.find_one({"_id": experiment_id})
        if not experiment:
            raise Exception(f"Experiment {experiment_id} not found")
        cleanup_array_files(experiment, self.db)
        self.experiments.delete_one({"_id": experiment_id})

    def get_most_recent_experiment(self, projection: dict = {}):
        experiment = next(
            self.experiments.find({}, projection).sort("created_at", -1).limit(1), None
        )
        if not experiment:
            raise Exception("No experiments found")
        return experiment
