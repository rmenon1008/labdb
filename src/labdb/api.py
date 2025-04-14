from labdb.database import Database
from labdb.cli_formatting import info, key_value
from labdb.cli_json_editor import edit
from labdb.serialization import serialize, deserialize
from pymongo.cursor import Cursor

class ExperimentLogger:
    def __init__(self, session_id: str = None) -> None:
        self.db = Database()
        self.sessions = self.db.sessions
        self.experiments = self.db.experiments

        if session_id:
            self.session = self.db.get_session(session_id, projection={"name": 1})
        else:
            self.session = self.db.get_most_recent_session()
            key_value(
                "No session ID provided, using most recent session",
                f"{self.session['name']} ({self.session['_id']})",
            )
        self.current_experiment_id = None

    def new_experiment(self, interactive: bool = True) -> str:
        if interactive:
            last_notes = self.db.get_last_notes(self.session["_id"])
            notes = edit(last_notes, "New experiment notes", f"Session {self.session['name']} ({self.session['_id']})")
        else:
            notes = {}
        
        self.current_experiment_id = self.db.create_experiment(self.session["_id"], {}, notes)
        print(f"Started experiment {self.current_experiment_id}")
        return self.current_experiment_id

    def log_data(self, key: str, value: any) -> None:
        if not self.current_experiment_id:
            raise Exception("No experiment started. Use `new_experiment()` first.")
        serialized_value = serialize(value, self.db.db, self.db.config["large_file_storage"])
        self.db.experiment_log_data(self.current_experiment_id, key, serialized_value)

    def log_note(self, key: str, value: any) -> None:
        if not self.current_experiment_id:
            raise Exception("No experiment started. Use `new_experiment()` first.")
        self.db.experiment_log_note(self.current_experiment_id, key, value)


class ExperimentQuery:
    def __init__(self) -> None:
        self.db = Database()
        self.sessions = self.db.sessions
        self.experiments = self.db.experiments
    
    def get_experiments(self, query: dict = {}, projection: dict = {}):
        cursor = self.experiments.find(query, projection).sort("created_at", -1)
        for doc in cursor:
            yield deserialize(doc, self.db.db)

    def get_experiments_from_session(self, session_id: str, query: dict = {}, projection: dict = {}):
        combined_query = {"session_id": session_id}
        combined_query.update(query)
        cursor = self.experiments.find(combined_query, projection).sort("created_at", -1)
        for doc in cursor:
            yield deserialize(doc, self.db.db)
    
    def experiment_log_data(self, experiment_id: str, key: str, value: any) -> None:
        serialized_value = serialize(value, self.db.db, self.db.config["large_file_storage"])
        self.db.experiment_log_data(experiment_id, key, serialized_value)

    def experiment_log_note(self, experiment_id: str, key: str, value: any) -> None:
        self.db.experiment_log_note(experiment_id, key, value)
