import sys
import json

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
from labdb.config import CONFIG_FILE, load_config, save_config
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


def cli_connection_setup(args):
    # Load existing config if it exists
    existing_config = load_config() or {}
    
    # Create default config with existing values or empty strings
    default_config = {
        "conn_string": existing_config.get("conn_string", ""),
        "db_name": existing_config.get("db_name", ""),
        "large_file_storage": existing_config.get("large_file_storage", "none"),
        "large_file_storage_path": existing_config.get("large_file_storage_path", ""),
        "compress_arrays": existing_config.get("compress_arrays", False),
    }
    
    # Edit the config
    config = edit(
        default_config,
        title="MongoDB Connection Setup",
        description="Edit the configuration below. All fields are required except large_file_storage_path (only needed for local storage)."
    )

    try:
        check_db(config)
        save_config(config)
        success("Connection setup completed successfully")
    except ConnectionError as e:
        error(str(e))
        sys.exit(1)


def cli_connection_check(args):
    try:
        config = load_config()
        check_db(config)
        success("Connection is working properly")
    except (ConfigError, ConnectionError) as e:
        error(str(e))
        sys.exit(1)


def cli_connection_show(args):
    try:
        config = load_config()
        if not config:
            raise ConfigError("No configuration found")
        display_config(CONFIG_FILE, config)
    except ConfigError as e:
        error(str(e))
        sys.exit(1)


def cli_session_list(args):
    try:
        db = get_db()
        sessions = list(Session.list(db, 11, ["_id", "name", "created_at"]))
        if not sessions or len(sessions) == 0:
            warning("No sessions found")
            return

        headers = ["Created at", "ID", "Name"]
        rows = [[sess["created_at"], sess["_id"], sess["name"]] for sess in sessions[:10]]

        if len(sessions) > 10:
            rows.append(["...", "...", "..."])

        display_table(headers, rows)

    except DatabaseError as e:
        error(str(e))
        sys.exit(1)


def cli_session_delete(args):
    try:
        db = get_db()
        Session.delete(db, args.id)
        success(f"Session '{args.id}' deleted successfully")
    except (DatabaseError, SessionError) as e:
        error(str(e))
        sys.exit(1)


def cli_session_create(args):
    try:
        db = get_db()
        name = get_input("Enter session name")
        details = edit({"description": ""}, title=f"New session: {name}")
        Session(db, name, details)
        success(f"Session '{name}' created successfully")
    except DatabaseError as e:
        error(str(e))
        sys.exit(1)


def cli_session_edit(args):
    try:
        db = get_db()

        if not args.id:
            sess = Session.get_most_recent(db)
        else:
            sess = Session.get(db, args.id)

        details = edit(
            sess["details"],
            title=f"Edit session: {sess['name']} ({sess['_id']})",
        )
        Session.replace_details(db, sess["_id"], details)
        success(f"Session {sess['name']} ({sess['_id']}) updated successfully")
    except (DatabaseError, SessionError) as e:
        error(str(e))
        sys.exit(1)


def cli_experiment_list(args):
    try:
        db = get_db()
        if not args.session_id:
            sess = Session.get_most_recent(db)
        else:
            sess = Session.get(db, args.session_id)

        info(f"Experiments for session: {sess['name']} ({sess['_id']})")
        experiments = list(Experiment.list(db, sess["_id"], 11, ["_id", "created_at", "outputs"]))
        if not experiments:
            warning("No experiments found")
            return

        headers = ["Created at", "ID", "Outputs"]
        rows = [[exp["created_at"], exp["_id"], exp["outputs"]] for exp in experiments[:10]]

        if len(experiments) > 10:
            rows.append(["...", "...", "..."])

        display_table(headers, rows)

    except (DatabaseError, SessionError, ExperimentError) as e:
        error(str(e))
        sys.exit(1)


def cli_experiment_delete(args):
    try:
        db = get_db()
        Experiment.delete(db, args.id)
        success(f"Experiment '{args.id}' deleted successfully")
    except (DatabaseError, ExperimentError) as e:
        error(str(e))
        sys.exit(1)


def cli_experiment_create(args):
    try:
        db = get_db()
        if not args.session_id:
            sess = Session.get_most_recent(db)
        else:
            sess = Session.get(db, args.session_id)

        # Start with empty outputs and let user edit
        outputs = edit(
            {},
            title=f"New experiment",
            description=f"Session: {sess['name']} ({sess['_id']})",
        )
        
        Experiment(db, sess["_id"], outputs)
        success("Experiment created successfully")
    except (DatabaseError, SessionError) as e:
        error(str(e))
        sys.exit(1)


def cli_experiment_edit(args):
    try:
        db = get_db()
        if not args.id:
            exp = Experiment.get_most_recent(db)
        else:
            exp = Experiment.get(db, args.id)

        sess = Session.get(db, exp["session_id"])
        
        # Split outputs into serializable and non-serializable
        serializable_outputs = {}
        non_serializable_outputs = {}
        
        for key, value in exp["outputs"].items():
            if is_serializable(value):
                serializable_outputs[key] = value
            else:
                non_serializable_outputs[key] = value
        
        # Edit only serializable outputs
        edited_outputs = edit(
            serializable_outputs,
            title=f"Edit experiment outputs: {exp['_id']}",
            description=f"Session: {sess['name']} ({sess['_id']})",
        )
        
        # Merge with non-serializable outputs
        final_outputs = {**non_serializable_outputs, **edited_outputs}
        
        Experiment.update_outputs(db, exp["_id"], final_outputs)
        success(f"Experiment '{exp['_id']}' updated successfully")
    except (DatabaseError, ExperimentError) as e:
        error(str(e))
        sys.exit(1)
