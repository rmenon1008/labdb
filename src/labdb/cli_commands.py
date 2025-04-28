import functools
import json
import sys
import traceback

from labdb.cli_formatting import (
    display_table,
    error,
    get_input,
    info,
    key_value,
    success,
    warning,
)
from labdb.cli_json_editor import edit
from labdb.config import CONFIG_FILE, CONFIG_SCHEMA, load_config, save_config
from labdb.database import Database
from labdb.utils import date_to_relative_time


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


def cli_config_setup(args):
    try:
        old_config = load_config() or {}
    except Exception:
        old_config = {}

    defaults = {
        "conn_string": "localhost:27017",
        "db_name": "labdb",
        "large_file_storage": "gridfs",
        "local_file_storage_path": "",
        "webdav_url": "http://localhost:8080/webdav/",
        "webdav_username": "",
        "webdav_password": "",
        "webdav_root": "/labdb/",
        "compress_arrays": False,
    }

    for key in defaults:
        if key in old_config:
            defaults[key] = old_config[key]

    new_config = {}
    storage_type = None

    # First, ask for properties that are always required
    for prop, details in CONFIG_SCHEMA["properties"].items():
        if details.get("always_required", False):
            description = details.get("description", prop)
            prompt = description

            if "enum" in details:
                prompt += f" ({'/'.join(details['enum'])})"

            if details.get("type") == "boolean":
                prompt += " (y/n)"
                input_val = get_input(prompt, "y" if defaults[prop] == True else "n")
                new_config[prop] = input_val == "y"
            else:
                new_config[prop] = get_input(prompt, defaults[prop])

            # Store the storage type to use later
            if prop == "large_file_storage":
                storage_type = new_config[prop]

    # Then, ask for properties that are required for the selected storage type
    for prop, details in CONFIG_SCHEMA["properties"].items():
        required_for = details.get("required_for", [])
        if storage_type in required_for:
            description = details.get("description", prop)

            if details.get("type") == "boolean":
                input_val = get_input(
                    f"{description} (y/n)", "y" if defaults[prop] == True else "n"
                )
                new_config[prop] = input_val == "y"
            else:
                new_config[prop] = get_input(description, defaults[prop])

    try:
        save_config(new_config)
        db = Database()
    except Exception as e:
        save_config(old_config)
        error("Configuration setup failed")
        error(str(e))
        sys.exit(1)
    else:
        success("Configuration updated successfully")


@cli_operation
def cli_setup_check(args):
    db = Database()
    success("MongoDB connection is working properly")


@cli_operation
def cli_setup_show(args):
    info(f"Configuration stored in [blue]{CONFIG_FILE}[/blue]")
    config = load_config()
    for key, value in config.items():
        key_value(key, value)


def cli_session_list(args):
    db = Database()
    sessions = list(
        db.sessions.find({}, {"_id": 1, "name": 1, "created_at": 1})
        .sort("created_at", -1)
        .limit(11)
    )
    if not sessions:
        warning("No sessions found")
        return
    headers = ["Created at", "ID", "Name", "Experiments"]
    rows = [
        [
            date_to_relative_time(sess["created_at"]),
            sess["_id"],
            sess["name"],
            db.experiments.count_documents({"session_id": sess["_id"]}),
        ]
        for sess in sessions[:10]
    ]
    if len(sessions) > 10:
        rows.append(["...", "...", "...", "..."])
    display_table(headers, rows)


@cli_operation
def cli_session_delete(args):
    db = Database()
    experiment_count = db.experiments.count_documents({"session_id": args.id})
    if experiment_count > 0:
        warning(f"Session {args.id} has {experiment_count} experiments")
        if get_input("Delete session and all associated experiments? (y/n)") != "y":
            return
    db.delete_session_with_cleanup(args.id)
    success(f"Session {args.id} deleted successfully")


@cli_operation
def cli_session_create(args):
    db = Database()
    name = get_input("Enter session name")
    details = edit({"description": ""}, title=f"New session: {name}")
    session_id = db.create_session(name, details)
    success(f"Session '{name} ({session_id})' created successfully")


@cli_operation
def cli_session_edit(args):
    db = Database()
    proj = {"name": 1, "details": 1}
    if not args.id:
        sess = db.get_most_recent_session(projection=proj)
    else:
        sess = db.get_session(args.id, projection=proj)

    details = edit(
        sess["details"],
        title=f"Edit session: {sess['name']} ({sess['_id']})",
    )
    db.update_session_details(sess["_id"], details)
    success(f"Session {sess['name']} ({sess['_id']}) updated successfully")


@cli_operation
def cli_experiment_list(args):
    db = Database()

    if args.session_id:
        sess = db.get_session(args.session_id)
        info(f"Experiments for session: {sess['name']} ({sess['_id']})")
        query = {"session_id": sess["_id"]}
    else:
        info("All experiments")
        query = {}

    experiments = list(
        db.experiments.find(
            query,
            {"_id": 1, "created_at": 1, "notes": 1, "session_id": 1},
        )
        .sort("created_at", -1)
        .limit(11)
    )

    if not experiments:
        warning("No experiments found")
        return

    headers = ["Created at", "ID"]
    if not args.session_id:
        headers.append("Session")
    headers.append("Notes")

    rows = []
    for exp in experiments[:10]:
        row = [
            date_to_relative_time(exp["created_at"]),
            exp["_id"],
        ]
        if not args.session_id:
            proj = {"name": 1}
            row.append(
                f"{db.get_session(exp['session_id'], projection=proj)['name']} ({exp['session_id']})"
            )
        row.append(exp.get("notes", {}))
        rows.append(row)

    if len(experiments) > 10:
        ellipsis_row = ["..."] * len(headers)
        rows.append(ellipsis_row)

    display_table(headers, rows)


@cli_operation
def cli_experiment_delete(args):
    db = Database()
    db.delete_experiment_with_cleanup(args.id)
    success(f"Experiment '{args.id}' deleted successfully")


@cli_operation
def cli_experiment_create(args):
    db = Database()
    proj = {"name": 1}
    sess = (
        db.get_session(args.session_id, projection=proj)
        if args.session_id
        else db.get_most_recent_session(projection=proj)
    )
    last_notes = db.get_last_notes(sess["_id"])
    notes = edit(
        last_notes,
        title=f"New experiment",
        description=f"Session: {sess['name']} ({sess['_id']})",
    )
    experiment_id = db.create_experiment(sess["_id"], {}, notes)
    success(f"Experiment '{experiment_id}' created successfully")


@cli_operation
def cli_experiment_edit(args):
    db = Database()
    proj = {"session_id": 1, "notes": 1}
    exp = (
        db.get_experiment(args.id, projection=proj)
        if args.id
        else db.get_most_recent_experiment(projection=proj)
    )
    sess = db.get_session(exp["session_id"], projection={"name": 1})
    notes = edit(
        exp.get("notes", {}),
        title=f"Edit experiment notes: {exp['_id']}",
        description=f"Session: {sess['name']} ({sess['_id']})",
    )
    experiment_id = exp["_id"]
    db.update_experiment_notes(experiment_id, notes)
    success(f"Experiment '{experiment_id}' updated successfully")
