import numpy as np
from pymongo.cursor import Cursor

from labdb.cli_formatting import info, key_value
from labdb.cli_json_editor import edit
from labdb.config import get_current_path
from labdb.database import Database
from labdb.serialization import deserialize, serialize
from labdb.utils import join_path, split_path, resolve_path


class ExperimentLogger:
    def __init__(
        self, path: str = None, notes_mode: str = "ask-every"
    ) -> None:
        self.db = Database()

        if path is None:
            path = get_current_path()
        elif isinstance(path, list):
            # Convert list to string path for backward compatibility
            path = join_path(path)

        self.path = path
        if not self.db.dir_exists(self.path):
            raise Exception(f"Path {self.path} does not exist")

        key_value("Working directory", self.path)
        self.current_experiment_path = None
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
        # Get previous experiment's notes if needed
        last_notes = {}
        if self.notes_mode != "none" or (self.notes_mode == "ask-once" and self.notes_completed):
            exp_count = self.db.count_experiments(self.path)
            if exp_count > 0:
                # Get previous experiment's notes to use as template
                projection = {"notes": 1}
                sort = [("created_at", -1)]
                exps = self.db.get_experiments(self.path, recursive=False, limit=1, projection=projection, sort=sort)
                last_notes = exps[0].get("notes", {}) if exps else {}

        # Handle notes based on mode
        if self.notes_mode == "ask-every" or (self.notes_mode == "ask-once" and not self.notes_completed):
            notes = edit(
                last_notes,
                "New experiment notes",
                f"Path: {self.path}",
            )
            self.notes_completed = True
        elif self.notes_mode == "ask-once" and self.notes_completed:
            notes = last_notes
        elif self.notes_mode == "none":
            notes = {}
        else:
            raise Exception(f"Invalid notes mode: {self.notes_mode}")

        # Create the experiment
        experiment_path, experiment_id = self.db.create_experiment(
            self.path, name, {}, notes
        )
                
        key_value(
            "Created experiment",
            experiment_path
        )

        self.current_experiment_path = experiment_path
        return experiment_path

    def log_data(self, key: str, value: any) -> None:
        """
        Log data to the current experiment

        Args:
            key: The key to store the data under
            value: The value to store (can be any serializable object)
        """
        if not self.current_experiment_path:
            raise Exception("No experiment started. Use `new_experiment()` first.")
        
        self.db.add_experiment_data(self.current_experiment_path, key, value)

    def log_note(self, key: str, value: any) -> None:
        """
        Add a note to the current experiment's notes

        Args:
            key: The key to store the note under
            value: The value to store (must be JSON serializable)
        """
        if not self.current_experiment_path:
            raise Exception("No experiment started. Use `new_experiment()` first.")

        self.db.add_experiment_note(self.current_experiment_path, key, value)


class ExperimentQuery:
    def __init__(self) -> None:
        self.db = Database()

    def _normalize_path(self, path: str | list[str] | None = None) -> str:
        """Convert a path parameter to a string path format

        Args:
            path: Path as string or list, or None to use current path

        Returns:
            Path as a string
        """
        if path is None:
            return get_current_path()
        elif isinstance(path, list):
            return join_path(path)
        return resolve_path(get_current_path(), path)

    def _expand_paths(self, paths: list[str]) -> list[str]:
        """Expand paths that contain range patterns

        For example, if the path is "exp_$(1-3)/", the function will return
        ["exp_1/", "exp_2/", "exp_3/"].

        Args:
            paths: List of paths to expand

        Returns:
            List of expanded paths
        """
        result = []
        for path in paths:
            # Check if the path contains any pattern
            if "$(" in path and ")" in path:
                # Extract the first range pattern
                start_idx = path.find("$(")
                end_idx = path.find(")", start_idx)
                if start_idx >= 0 and end_idx > start_idx:
                    range_expr = path[start_idx+2:end_idx]
                    if "-" in range_expr:
                        try:
                            # Parse range boundaries
                            start_val, end_val = map(int, range_expr.split("-"))
                            base_path = path[:start_idx]
                            suffix = path[end_idx+1:]
                            
                            # Generate paths for each value in the range
                            for i in range(start_val, end_val + 1):
                                expanded_path = f"{base_path}{i}{suffix}"
                                # Recursively expand any remaining patterns
                                if "$(" in expanded_path and ")" in expanded_path:
                                    result.extend(self._expand_paths([expanded_path]))
                                else:
                                    result.append(expanded_path)
                            continue  # Skip adding the original path
                        except ValueError:
                            # If parsing fails, treat as a regular path
                            pass
                        
            # If no patterns or parsing failed, add the path as is
            result.append(path)
        return result

    def get_experiments(
        self,
        path: str | list[str] = None,
        recursive: bool = False,
        query: dict = None,
        projection: dict = None,
        sort: list = None,
        limit: int = None,
    ):
        """
        Query experiments at the specified path

        Args:
            path: Path to query (string or list path)
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

    def get_experiments_in_list(self, paths: list[str], sort: list = None, projection: dict = None):
        """
        Get experiments from a list of paths. It supports range patterns
        in the paths, e.g. "/path/exp_$(1-3)/".

        Args:
            paths: List of paths to query
            sort: MongoDB sort specification
            projection: MongoDB projection to specify which fields to return

        Returns:
            List of experiment data
        """
        paths_expanded = self._expand_paths(paths)
        paths_normalized = [self._normalize_path(path) for path in paths_expanded]
        query = {"path_str": {"$in": paths_normalized}}
        return self.get_experiments(path="/", query=query, sort=sort, projection=projection, recursive=True)

    def get_experiment(self, path: str | list[str]):
        """
        Get data for a specific experiment path

        Args:
            path: Full path to the experiment (string or list)

        Returns:
            Experiment data object
        """
        path = self._normalize_path(path)

        experiments = self.db.get_experiments(path)
        if not experiments:
            raise Exception(f"No experiment found at {path}")

        return experiments[0]

    def experiment_log_data(self, path: str | list[str], key: str, value: any) -> None:
        """
        Log data to an experiment
        
        Args:
            path: Path to the experiment (string or list)
            key: The data key
            value: The data value
        """
        path = self._normalize_path(path)
        self.db.add_experiment_data(path, key, value)

    def experiment_log_note(self, path: str | list[str], key: str, value: any) -> None:
        """
        Log a note to an experiment
        
        Args:
            path: Path to the experiment (string or list)
            key: The note key
            value: The note value
        """
        path = self._normalize_path(path)
        self.db.update_experiment_notes(path, {key: value})
