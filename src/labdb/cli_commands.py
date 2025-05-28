import functools
import os
import sys
import traceback

from labdb.cli_formatting import bold, error, get_input, info, key_value, success, json_print
from labdb.cli_json_editor import edit
from labdb.config import (
    CONFIG_DEPENDENCIES,
    CONFIG_FILE,
    CONFIG_SCHEMA,
    CONFIG_SETUP_ORDER,
    get_current_path,
    load_config,
    save_config,
    update_current_path,
)
from labdb.database import Database
from labdb.utils import (
    best_effort_serialize,
    date_to_relative_time,
    dict_str,
    get_path_name,
    resolve_path,
)


def cli_operation(func):
    """Decorator for CLI commands that handles the common try-except-else pattern"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            traceback.print_exc()
            error(str(e))
            sys.exit(1)

    return wrapper


def cli_setup(args):
    try:
        old_config = load_config(should_validate=False) or {}
    except Exception:
        print("ERROR LOADING CONFIG")
        old_config = {}

    # Initialize new config with any internal properties
    new_config = {}
    for prop, details in CONFIG_SCHEMA["properties"].items():
        if details.get("internal", False) and prop in old_config:
            new_config[prop] = old_config[prop]

    # Gather user input for each configuration property
    for prop in CONFIG_SETUP_ORDER:
        # Skip if property is not in schema
        if prop not in CONFIG_SCHEMA["properties"]:
            continue

        details = CONFIG_SCHEMA["properties"][prop]

        # Skip internal properties
        if details.get("internal", False):
            continue

        # Check if this property has dependencies
        if prop in CONFIG_DEPENDENCIES:
            dependency = CONFIG_DEPENDENCIES[prop]
            dep_field = dependency["field"]
            dep_value = dependency["value"]

            # Skip if the dependent field doesn't have the required value
            if dep_field not in new_config or new_config[dep_field] != dep_value:
                continue

        # Prepare default value
        default_value = None
        if prop in old_config:
            default_value = old_config[prop]
        elif "default" in details:
            default_value = details["default"]

        # Prepare prompt
        description = details.get("description", prop)
        prompt = description

        if "enum" in details:
            prompt += f" ({'/'.join(details['enum'])})"

        # Handle different property types
        if details.get("type") == "boolean":
            prompt += " (y/n)"
            default_display = "y" if default_value else "n"
            input_val = get_input(prompt, default_display)
            new_config[prop] = input_val.lower() == "y"
        elif details.get("type") == "number":
            new_config[prop] = int(get_input(prompt, default_value))
        else:
            new_config[prop] = get_input(prompt, default_value)

    # Ensure dependent fields have proper default values when not asked
    # For non-gridfs storage, explicitly set local_cache_enabled to False
    if new_config.get("large_file_storage") != "gridfs":
        new_config["local_cache_enabled"] = False

    # If local cache is disabled, set sensible defaults for cache properties
    if not new_config.get("local_cache_enabled", False):
        if "local_cache_path" in CONFIG_SCHEMA["properties"]:
            new_config["local_cache_path"] = CONFIG_SCHEMA["properties"][
                "local_cache_path"
            ].get("default", "")
        if "local_cache_max_size_mb" in CONFIG_SCHEMA["properties"]:
            new_config["local_cache_max_size_mb"] = CONFIG_SCHEMA["properties"][
                "local_cache_max_size_mb"
            ].get("default", 1024)

    try:
        save_config(new_config)
        _ = Database(new_config)
    except Exception as e:
        save_config(old_config)
        error("Configuration setup failed")
        error(str(e))
        sys.exit(1)
    else:
        success("Configuration updated successfully")


@cli_operation
def cli_config_check(args):
    config = load_config()
    db = Database(config)
    # Explicitly test connection with a lightweight operation
    db.db.command("ping")
    success("MongoDB connection is working properly")


@cli_operation
def cli_config_show(args):
    info(f"Configuration stored in [blue]{CONFIG_FILE}[/blue]")
    config = load_config()
    for key, value in config.items():
        if key in CONFIG_SCHEMA["properties"] and CONFIG_SCHEMA["properties"][key].get(
            "internal", False
        ):
            continue
        print(f"{key}: {value}")


@cli_operation
def cli_ls(args):
    config = load_config()
    db = Database(config)
    current_path = get_current_path()

    # If path is provided, resolve it against current path
    if args.path:
        try:
            path = resolve_path(current_path, args.path)
        except ValueError as e:
            error(f"Invalid path: {e}")
            return
    else:
        path = current_path

    items = db.list_dir(path)
    if not items:
        info(f"No items in {path}")
        return

    # Print header for the table
    max_width = os.get_terminal_size().columns
    path_display = path
    max_item_name_width = max(
        max(len(get_path_name(item["path_str"])) for item in items), len("Name")
    )
    max_date_width = max(
        max(len(date_to_relative_time(item["created_at"])) for item in items),
        len("Created"),
    )
    key_value("Listing", path_display)
    bold(
        f"{'Name':<{max_item_name_width + 2}} {'Created':<{max_date_width + 2}} {'Notes':<{max_width - max_item_name_width - max_date_width - 6}}"
    )
    for item in items:
        item_name = get_path_name(item["path_str"])
        item_name += "/" if item["type"] == "directory" else ""
        print(
            f"{item_name:<{max_item_name_width + 2}} {date_to_relative_time(item['created_at']):<{max_date_width + 2}} {(dict_str(item['notes']) if item['notes'] else '')[: max_width - max_item_name_width - max_date_width - 6]}"
        )


@cli_operation
def cli_mkdir(args):
    config = load_config()
    db = Database(config)
    current_path = get_current_path()

    try:
        path = resolve_path(current_path, args.path)
        db.create_dir(path)
        info(f"Created directory {path}")
    except ValueError as e:
        error(f"Invalid path: {e}")
    except Exception as e:
        error(f"Error creating directory: {e}")


@cli_operation
def cli_rm(args):
    config = load_config()
    db = Database(config)
    current_path = get_current_path()

    try:
        # Handle path resolution with potential range patterns
        if "$(" in args.path and ")" in args.path:
            # Path contains range patterns, handle specially
            if args.path.startswith("/"):
                path = args.path  # Absolute path with range pattern
            else:
                # Relative path with range pattern, resolve manually
                if current_path == "/":
                    path = f"/{args.path}"
                else:
                    path = f"{current_path}/{args.path}"

            # Expand the path patterns
            expanded_paths = db._expand_paths([path])

            # Calculate total affected items across all expanded paths
            total_affected_counts = {"experiments": 0, "directories": 0}
            for expanded_path in expanded_paths:
                try:
                    affected_counts = db.delete(expanded_path, dry_run=True)
                    total_affected_counts["experiments"] += affected_counts[
                        "experiments"
                    ]
                    total_affected_counts["directories"] += affected_counts[
                        "directories"
                    ]
                except Exception:
                    # Skip paths that don't exist or can't be accessed
                    continue

            total_affected = (
                total_affected_counts["experiments"]
                + total_affected_counts["directories"]
            )

            if total_affected == 0:
                error("No items affected")
                return

            # If in dry-run mode, just show the count and exit
            if hasattr(args, "dry_run") and args.dry_run:
                exp_text = f"{total_affected_counts['experiments']} experiment{'s' if total_affected_counts['experiments'] != 1 else ''}"
                dir_text = f"{total_affected_counts['directories']} director{'ies' if total_affected_counts['directories'] != 1 else 'y'}"
                info(f"Would delete {exp_text} and {dir_text} from pattern {args.path}")
                return

            # Confirm with user before proceeding
            exp_text = f"{total_affected_counts['experiments']} experiment{'s' if total_affected_counts['experiments'] != 1 else ''}"
            dir_text = f"{total_affected_counts['directories']} director{'ies' if total_affected_counts['directories'] != 1 else 'y'}"
            confirm_message = f'Deleting pattern "{args.path}" will result in {exp_text} and {dir_text} being deleted'

            error(confirm_message)
            confirmation = input("Proceed? (y/n): ").strip().lower()
            if confirmation != "y":
                info("Operation canceled")
                return

            # Proceed with actual deletion for each expanded path
            deleted_count = 0
            for expanded_path in expanded_paths:
                try:
                    db.delete(expanded_path)
                    deleted_count += 1
                except Exception as e:
                    error(f"Failed to delete {expanded_path}: {e}")

            info(f"Removed {deleted_count} path(s) from pattern {args.path}")
        else:
            # Regular single path deletion (existing logic)
            path = resolve_path(current_path, args.path)

            # Run in dry-run mode first to get count of affected items
            affected_counts = db.delete(path, dry_run=True)
            total_affected = (
                affected_counts["experiments"] + affected_counts["directories"]
            )

            if total_affected == 0:
                error("No items affected")
                return

            # If in dry-run mode, just show the count and exit
            if hasattr(args, "dry_run") and args.dry_run:
                exp_text = f"{affected_counts['experiments']} experiment{'s' if affected_counts['experiments'] != 1 else ''}"
                dir_text = f"{affected_counts['directories']} director{'ies' if affected_counts['directories'] != 1 else 'y'}"
                info(f"Would delete {exp_text} and {dir_text} from {path}")
                return

            # Confirm with user before proceeding
            exp_text = f"{affected_counts['experiments']} experiment{'s' if affected_counts['experiments'] != 1 else ''}"
            dir_text = f"{affected_counts['directories']} director{'ies' if affected_counts['directories'] != 1 else 'y'}"
            confirm_message = f'Deleting "{path}" will result in {exp_text} and {dir_text} being deleted'

            error(confirm_message)
            confirmation = input("Proceed? (y/n): ").strip().lower()
            if confirmation != "y":
                info("Operation canceled")
                return

            # Proceed with actual deletion
            db.delete(path)
            info(f"Removed {path}")
    except ValueError as e:
        error(f"Invalid path: {e}")
    except Exception as e:
        error(f"Error removing path: {e}")


@cli_operation
def cli_mv(args):
    config = load_config()
    db = Database(config)
    current_path = get_current_path()

    try:
        src_path = resolve_path(current_path, args.src_path)
        dest_path = resolve_path(current_path, args.dest_path)

        # Run in dry-run mode first to get count of affected items
        affected_counts = db.move(src_path, dest_path, dry_run=True)
        total_affected = affected_counts["experiments"] + affected_counts["directories"]

        if total_affected == 0:
            error("No items affected")
            return

        # If in dry-run mode, just show the count and exit
        if hasattr(args, "dry_run") and args.dry_run:
            exp_text = f"{affected_counts['experiments']} experiment{'s' if affected_counts['experiments'] != 1 else ''}"
            dir_text = f"{affected_counts['directories']} director{'ies' if affected_counts['directories'] != 1 else 'y'}"
            info(f"Would move {exp_text} and {dir_text} from {src_path} to {dest_path}")
            return

        # Confirm with user before proceeding
        exp_text = f"{affected_counts['experiments']} experiment{'s' if affected_counts['experiments'] != 1 else ''}"
        dir_text = f"{affected_counts['directories']} director{'ies' if affected_counts['directories'] != 1 else 'y'}"
        confirm_message = (
            f'Moving "{src_path}" to "{dest_path}" will move {exp_text} and {dir_text}'
        )

        print(confirm_message)
        confirmation = input("Proceed? (y/n): ").strip().lower()
        if confirmation != "y":
            info("Operation canceled")
            return

        # Proceed with actual move
        db.move(src_path, dest_path)
        info(f"Moved {src_path} to {dest_path}")
    except ValueError as e:
        error(f"Invalid path: {e}")
    except Exception as e:
        error(f"Error moving path: {e}")


@cli_operation
def cli_pwd(args):
    current_path = get_current_path()
    info(current_path)


@cli_operation
def cli_cd(args):
    config = load_config()
    db = Database(config)
    current_path = get_current_path()

    if not args.path:
        # Reset to root
        update_current_path("/")
        info("Changed to /")
        return

    try:
        path = resolve_path(current_path, args.path)

        # Check if directory exists
        if not db.dir_exists(path):
            error(f"Directory {path} does not exist")
            return

        update_current_path(path)
        info(f"Changed to {path}")
    except ValueError as e:
        error(f"Invalid path: {e}")


def _find_common_notes(notes_list):
    """Find notes that are common across all experiments with the same values."""
    if not notes_list:
        return {}

    # Start with the first experiment's notes
    common_notes = notes_list[0].copy()

    # For each subsequent experiment, keep only keys that exist with the same value
    for notes in notes_list[1:]:
        keys_to_remove = []
        for key, value in common_notes.items():
            if key not in notes or notes[key] != value:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del common_notes[key]

    return common_notes


@cli_operation
def cli_edit(args):
    config = load_config()
    db = Database(config)
    current_path = get_current_path()

    if not args.path:
        error("No path specified")
        return

    try:
        # Handle path resolution with potential range patterns
        if "$(" in args.path and ")" in args.path:
            # Path contains range patterns, handle bulk editing
            if args.path.startswith("/"):
                path = args.path  # Absolute path with range pattern
            else:
                # Relative path with range pattern, resolve manually
                if current_path == "/":
                    path = f"/{args.path}"
                else:
                    path = f"{current_path}/{args.path}"

            # Expand the path patterns
            expanded_paths = db._expand_paths([path])

            # Get all experiments that exist from the expanded paths
            existing_experiments = []
            experiment_paths = []

            for expanded_path in expanded_paths:
                try:
                    exp_doc = db.experiments.find_one({"path_str": expanded_path})
                    if exp_doc:
                        existing_experiments.append(exp_doc)
                        experiment_paths.append(expanded_path)
                except Exception:
                    # Skip paths that can't be accessed
                    continue

            if not existing_experiments:
                error(f"No experiments found matching pattern {args.path}")
                return

            # Extract notes from all experiments
            all_notes = [exp.get("notes", {}) for exp in existing_experiments]

            # Find common notes across all experiments
            common_notes = _find_common_notes(all_notes)

            # Edit the common notes
            edited_notes = edit(
                common_notes,
                title=f"Edit notes for {args.path} - {len(existing_experiments)} experiments",
            )

            # Apply the edited notes to all experiments
            updated_count = 0
            for exp_path in experiment_paths:
                try:
                    # Get current notes for this experiment
                    current_exp = db.experiments.find_one({"path_str": exp_path})
                    current_notes = current_exp.get("notes", {})

                    # Merge edited notes with existing notes (edited notes take precedence)
                    updated_notes = current_notes.copy()
                    updated_notes.update(edited_notes)

                    # Update the experiment
                    db.update_experiment_notes(exp_path, updated_notes)
                    updated_count += 1
                except Exception as e:
                    error(f"Failed to update {exp_path}: {e}")

            success(
                f"Updated notes for {updated_count} experiments matching pattern {args.path}"
            )
        else:
            # Regular single path editing (existing logic)
            path = resolve_path(current_path, args.path)

            # Check if it's a directory or experiment
            if db.dir_exists(path):
                # Get the current notes for this directory
                dir_doc = db.directories.find_one({"path_str": path})
                if not dir_doc:
                    error(f"Directory {path} not found")
                    return

                notes = dir_doc.get("notes", {})
                edited_notes = edit(
                    notes,
                    title=f"Edit directory notes: {path}",
                )
                db.update_dir_notes(path, edited_notes)
                success(f"Updated notes for directory {path}")
            else:
                # It's an experiment
                exp_doc = db.experiments.find_one({"path_str": path})
                if not exp_doc:
                    error(f"Path {path} not found")
                    return

                notes = exp_doc.get("notes", {})
                edited_notes = edit(
                    notes,
                    title=f"Edit experiment notes: {path}",
                )
                db.update_experiment_notes(path, edited_notes)
                success(f"Updated notes for experiment {path}")
    except ValueError as e:
        error(f"Invalid path: {e}")
    except Exception as e:
        error(f"Error editing notes: {e}")


@cli_operation
def cli_show(args):
    config = load_config()
    db = Database(config)
    current_path = get_current_path()

    try:
        path = resolve_path(current_path, args.path)

        # Check if it's a directory
        if db.dir_exists(path):
            # Get the directory document
            dir_doc = db.directories.find_one({"path_str": path})
            if not dir_doc:
                # It's the root directory or a directory without explicit document
                if path == "/":
                    bold(f"Directory: {path}")
                    info("Type: Root directory")
                    info("Created: N/A")

                    # Count contents
                    items = db.list_dir(path)
                    exp_count = sum(1 for item in items if item["type"] == "experiment")
                    dir_count = sum(1 for item in items if item["type"] == "directory")
                    info(f"Contains: {exp_count} experiments, {dir_count} directories")
                    info("Notes: None")
                else:
                    error(f"Directory {path} not found")
                return

            # Display directory information
            key_value("Directory", f"{path} ({dir_doc['_id']})")
            key_value("Created", date_to_relative_time(dir_doc["created_at"]))

            # Count contents
            items = db.list_dir(path)
            exp_count = sum(1 for item in items if item["type"] == "experiment")
            dir_count = sum(1 for item in items if item["type"] == "directory")
            key_value("Contains", f"{exp_count} experiments, {dir_count} directories")

            # Display notes
            notes = dir_doc.get("notes", {})
            if notes:
                bold("Notes:")
                json_print(best_effort_serialize(notes))
            else:
                info("Notes: None")
        else:
            # Check if it's an experiment
            experiments = db.get_experiments(path, deserialize=False)
            if not experiments or len(experiments) == 0:
                error(f"Path {path} not found")
                return

            exp_doc = experiments[0]

            # Display experiment information
            key_value("Experiment", f"{path} ({exp_doc['_id']})")
            key_value("Created", date_to_relative_time(exp_doc["created_at"]))

            # Display notes
            notes = exp_doc.get("notes", {})
            if notes:
                bold("Notes:")
                json_print(best_effort_serialize(notes))
            else:
                info("Notes: None")

            # Display data (already not deserialized)
            data = exp_doc.get("data", {})
            if data:
                bold("Data:")
                json_print(best_effort_serialize(data))
            else:
                info("Data: None")

    except ValueError as e:
        error(f"Invalid path: {e}")
    except Exception as e:
        error(f"Error showing path: {e}")
