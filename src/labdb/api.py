import sys
import json

import numpy as np

from labdb.array_utils import deserialize_numpy_containers, serialize_numpy_containers
from labdb.cli_formatting import (
    display_config,
    display_table,
    error,
    get_input,
    info,
    success,
    warning,
)
from labdb.cli_json_editor import edit
from labdb.config import load_config
from labdb.database import ConfigError, DatabaseError, check_db, get_db
from labdb.experiment import Experiment, ExperimentError, NoExperimentsError
from labdb.session import NoSessionsError, Session, SessionError


def is_serializable(obj):
    """Check if an object is JSON serializable"""
    try:
        json.dumps(obj)
        return True
    except (TypeError, ValueError):
        return False


class LoggerError(Exception):
    pass


class ExperimentLogger:
    def __init__(self, experiment_id=None, session_id=None, user_details=True):
        self.db = get_db()
        self.config = load_config()
        if not self.config:
            raise ConfigError("No configuration found")
        
        if experiment_id:
            # Get existing experiment
            self.experiment = Experiment.get(self.db, experiment_id)
            self.session = Session.get(self.db, self.experiment["session_id"])
            info(f"Using existing experiment: {experiment_id}")
        else:
            # Create new experiment
            self.session = self._get_session(session_id)
            info(f"Using session: {self.session['name']} ({self.session['_id']})")
            self.experiment = self._create_experiment(user_details)
            info(f"Created experiment: {self.experiment.id}")

    def _create_experiment(self, user_details):
        outputs = {}
        if user_details:
            outputs = edit(
                {},
                title=f"New experiment: {self.session['name']} ({self.session['_id']})",
                description=f"Session: {self.session['name']} ({self.session['_id']})",
            )
        return Experiment(self.db, self.session["_id"], outputs)

    def _get_session(self, session_id):
        if session_id:
            return Session.get(self.db, session_id)
        else:
            return Session.get_most_recent(self.db)

    def set(self, key, value):
        """Set a value in the experiment's outputs"""
        storage_type = self.config.get("large_file_storage", "none")
        serialized_value = serialize_numpy_containers(value, self.db, storage_type=storage_type)
        Experiment.merge_output(self.db, self.experiment["_id"], {key: serialized_value})

    def get(self, key, default=None):
        """Get a value from the experiment's outputs"""
        if "outputs" not in self.experiment:
            return default
        value = self.experiment["outputs"].get(key, default)
        if value is not None and isinstance(value, dict) and value.get("__numpy_array__"):
            return deserialize_numpy_containers(value, self.db)
        return value

class ExperimentQuery:
    def __init__(self):
        self.db = get_db()
        self.config = load_config()

    def _get_session(self, session_id):
        if session_id:
            return Session.get(self.db, session_id)
        else:
            return Session.get_most_recent(self.db)
        
    def get_all(self, query=None, projection=None):
        cursor = self.db.get_collection("experiments").find(query or {}, projection)
        
        for doc in cursor:
            if "outputs" in doc:
                doc["outputs"] = deserialize_numpy_containers(doc["outputs"], self.db)
            yield doc

    def get_all_from_session(self, session=None, query=None, projection=None):
        session = self._get_session(session)
        combined_query = {"session_id": session["_id"]}
        combined_query.update(query or {})
        cursor = self.db.get_collection("experiments").find(combined_query, projection)
        
        for doc in cursor:
            if "outputs" in doc:
                doc["outputs"] = deserialize_numpy_containers(doc["outputs"], self.db)
            yield doc
