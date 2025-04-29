import numpy as np
from pymongo.cursor import Cursor

from labdb.cli_formatting import info, key_value
from labdb.cli_json_editor import edit
from labdb.config import get_current_path
from labdb.database import Database
from labdb.serialization import deserialize, serialize
from labdb.utils import join_path, split_path


class ExperimentLogger:
    def __init__(
        self, path: list[str] | str = None, notes_mode: str = "ask-every"
    ) -> None:
        self.db = Database()

        if path is None:
            path = get_current_path()
        elif isinstance(path, str):
            path = split_path(path)

        self.path = path
        if not self.db.dir_exists(self.path):
            raise Exception(f"Path {join_path(self.path)} does not exist")

        key_value("Working directory", join_path(self.path))
        self.current_experiment_name = None
        self.notes_mode = notes_mode  # "ask-every", "ask-once", "none"
        self.notes_completed = False

    def new_experiment(self, name: str = None) -> str:
        """
        Create a new experiment in the current path

        Args:
            name: Optional name for the experiment
            notes: Notes to associate with the experiment (dict)
                - If None: opens editor to input notes
                - If "none": uses empty notes
                - If "use_last": uses notes from last experiment in this path

        Returns:
            Name of the created experiment
        """
        # Handle notes
        if self.notes_mode == "ask-every" or (
            self.notes_mode == "ask-once" and not self.notes_completed
        ):
            # Get experiment count to determine if there are previous experiments
            exp_count = self.db.count_experiments(self.path)
            if exp_count > 0:
                # Get previous experiment's notes to use as template
                exps = self.db.get_experiments(self.path, recursive=False, limit=1)
                last_notes = exps[0].get("notes", {}) if exps else {}
            else:
                last_notes = {}

            notes = edit(
                last_notes,
                "New experiment notes",
                f"Path: {join_path(self.path)}",
            )
            self.notes_completed = True

        elif self.notes_mode == "none":
            notes = {}

        # Create the experiment
        self.current_experiment_name = self.db.create_experiment(
            self.path, name, {}, notes
        )
        key_value(
            "Created experiment",
            f"{join_path(self.path)}/{self.current_experiment_name}",
        )
        return self.current_experiment_name

    def log_data(self, key: str, value: any) -> None:
        """
        Log data to the current experiment

        Args:
            key: The key to store the data under
            value: The value to store (can be any serializable object)
        """
        if not self.current_experiment_name:
            raise Exception("No experiment started. Use `new_experiment()` first.")

        experiment_path = self.path + [self.current_experiment_name]
        self.db.add_experiment_data(experiment_path, key, value)

    def log_note(self, key: str, value: any) -> None:
        """
        Add a note to the current experiment's notes

        Args:
            key: The key to store the note under
            value: The value to store (must be JSON serializable)
        """
        if not self.current_experiment_name:
            raise Exception("No experiment started. Use `new_experiment()` first.")

        experiment_path = self.path + [self.current_experiment_name]
        exp_doc = self.db.experiments.find_one({"path": experiment_path})
        if not exp_doc:
            raise Exception(f"Experiment at {join_path(experiment_path)} not found")

        notes = exp_doc.get("notes", {})
        notes[key] = value
        self.db.update_experiment_notes(experiment_path, notes)


class ExperimentQuery:
    def __init__(self) -> None:
        self.db = Database()

    def _normalize_path(self, path: list[str] | str | None = None):
        """Convert a path parameter to a list path format

        Args:
            path: Path as string or list, or None to use current path

        Returns:
            Path as a list
        """
        if path is None:
            return get_current_path()
        elif isinstance(path, str):
            return split_path(path)
        return path

    def get_experiments(
        self,
        path: list[str] | str = None,
        recursive: bool = True,
        query: dict = None,
        projection: dict = None,
        sort: list = None,
        limit: int = None,
    ):
        """
        Query experiments at the specified path

        Args:
            path: Path to query (list or string path)
            recursive: If True, includes experiments in subdirectories
            query: Additional MongoDB query to filter results
            projection: MongoDB projection to specify which fields to return
            sort: MongoDB sort specification
            limit: Maximum number of results to return

        Returns:
            List of experiment data
        """
        path = self._normalize_path(path)

        return self.db.get_experiments(
            path,
            recursive=recursive,
            query=query,
            projection=projection,
            sort=sort,
            limit=limit,
        )

    def get_experiment(self, path: list[str] | str):
        """
        Get data for a specific experiment path

        Args:
            path: Full path to the experiment

        Returns:
            Experiment data object
        """
        path = self._normalize_path(path)

        experiments = self.db.get_experiments(path)
        if not experiments:
            raise Exception(f"No experiment found at {join_path(path)}")

        return experiments[0]

    def experiment_log_data(self, path: list[str] | str, key: str, value: any) -> None:
        """
        Log data to an experiment
        """
        path = self._normalize_path(path)
        self.db.add_experiment_data(path, key, value)

    def experiment_log_note(self, path: list[str] | str, key: str, value: any) -> None:
        """
        Log a note to an experiment
        """
        path = self._normalize_path(path)
        self.db.update_experiment_notes(path, {key: value})
