import argparse
import sys

from labdb.cli_commands import (
    cli_connection_check,
    cli_connection_setup,
    cli_connection_show,
    cli_experiment_create,
    cli_experiment_delete,
    cli_experiment_edit,
    cli_experiment_list,
    cli_session_create,
    cli_session_delete,
    cli_session_edit,
    cli_session_list,
)
from labdb.cli_formatting import error


class CommandError(Exception):
    """Exception raised for CLI command errors"""

    pass


def add_command(subparsers, name, func, help_text, **kwargs):
    parser = subparsers.add_parser(name, help=help_text)
    for arg_name, arg_props in kwargs.items():
        parser.add_argument(arg_name, **arg_props)
    parser.set_defaults(func=func)
    return parser


def main():
    parser = argparse.ArgumentParser(description="MongoDB experiment tool")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Connection command
    connection_parser = subparsers.add_parser("connection", help="Connection management")
    connection_subs = connection_parser.add_subparsers(dest="subcommand")
    add_command(
        connection_subs,
        "setup",
        cli_connection_setup,
        "Setup a new MongoDB connection with connection string and database name",
    )
    add_command(
        connection_subs,
        "check",
        cli_connection_check,
        "Verify the MongoDB connection is working properly",
    )
    add_command(
        connection_subs,
        "show",
        cli_connection_show,
        "Display the current MongoDB connection settings including URI and database",
    )

    # Connection command alias
    conn_parser = subparsers.add_parser(
        "conn", help="Connection management (alias for 'connection')"
    )
    conn_subs = conn_parser.add_subparsers(dest="subcommand")
    add_command(
        conn_subs,
        "setup",
        cli_connection_setup,
        "Setup a new MongoDB connection with connection string and database name",
    )
    add_command(
        conn_subs,
        "check",
        cli_connection_check,
        "Verify the MongoDB connection is working properly",
    )
    add_command(
        conn_subs,
        "show",
        cli_connection_show,
        "Display the current MongoDB connection settings including URI and database",
    )

    # Session command - singular form
    session_parser = subparsers.add_parser("session", help="Session management")
    session_subs = session_parser.add_subparsers(dest="subcommand")
    add_command(
        session_subs,
        "list",
        cli_session_list,
        "List all available sessions with their IDs and names",
    )
    add_command(
        session_subs,
        "delete",
        cli_session_delete,
        "Delete a session by its ID, including all associated experiments",
        **{"id": {"help": "Session ID to delete"}},
    )
    add_command(session_subs, "create", cli_session_create, "Create a new session with metadata")
    add_command(
        session_subs,
        "edit",
        cli_session_edit,
        "Edit an existing session's properties by ID",
        **{"id": {"help": "Session ID to edit", "nargs": "?"}},
    )

    # Session command alias
    sess_parser = subparsers.add_parser("sess", help="Session management (alias for 'session')")
    sess_subs = sess_parser.add_subparsers(dest="subcommand")
    add_command(
        sess_subs, "list", cli_session_list, "List all available sessions with their IDs and names"
    )
    add_command(
        sess_subs,
        "delete",
        cli_session_delete,
        "Delete a session by its ID, including all associated experiments",
        **{"id": {"help": "Session ID to delete"}},
    )
    add_command(sess_subs, "create", cli_session_create, "Create a new session with metadata")
    add_command(
        sess_subs,
        "edit",
        cli_session_edit,
        "Edit an existing session's properties by ID",
        **{"id": {"help": "Session ID to edit", "nargs": "?"}},
    )

    # Experiment command - singular form
    experiment_parser = subparsers.add_parser("experiment", help="Experiment management")
    experiment_subs = experiment_parser.add_subparsers(dest="subcommand")
    add_command(
        experiment_subs,
        "list",
        cli_experiment_list,
        "List all experiments, optionally filtered by session ID",
        **{"session_id": {"help": "Session ID to list experiments for", "nargs": "?"}},
    )
    add_command(
        experiment_subs,
        "delete",
        cli_experiment_delete,
        "Delete an experiment by its ID, including all related data",
        **{"id": {"help": "Experiment ID to delete"}},
    )
    add_command(
        experiment_subs,
        "create",
        cli_experiment_create,
        "Create a new experiment with parameters in an existing session",
        **{
            "session_id": {
                "help": "Session ID to create the experiment in",
                "nargs": "?",
            }
        },
    )
    add_command(
        experiment_subs,
        "edit",
        cli_experiment_edit,
        "Edit an existing experiment's properties by ID",
        **{"id": {"help": "Experiment ID to edit", "nargs": "?"}},
    )

    # Experiment command alias
    exp_parser = subparsers.add_parser("exp", help="Experiment management (alias for 'experiment')")
    exp_subs = exp_parser.add_subparsers(dest="subcommand")
    add_command(
        exp_subs,
        "list",
        cli_experiment_list,
        "List all experiments, optionally filtered by session ID",
        **{"session_id": {"help": "Session ID to list experiments for", "nargs": "?"}},
    )
    add_command(
        exp_subs,
        "delete",
        cli_experiment_delete,
        "Delete an experiment by its ID, including all related data",
        **{"id": {"help": "Experiment ID to delete"}},
    )
    add_command(
        exp_subs,
        "create",
        cli_experiment_create,
        "Create a new experiment with parameters in an existing session",
        **{
            "session_id": {
                "help": "Session ID to create the experiment in",
                "nargs": "?",
            }
        },
    )
    add_command(
        exp_subs,
        "edit",
        cli_experiment_edit,
        "Edit an existing experiment's properties by ID",
        **{"id": {"help": "Experiment ID to edit", "nargs": "?"}},
    )

    args = parser.parse_args()

    # Handle case when a command is provided but no subcommand
    if args.command and not hasattr(args, "func"):
        if args.command in ["connection", "conn"]:
            connection_parser.print_help()
        elif args.command in ["session", "sessions", "sess"]:
            session_parser.print_help()
        elif args.command in ["experiment", "experiments", "exp"]:
            experiment_parser.print_help()
        print(f"\nError: A subcommand is required for '{args.command}'", file=sys.stderr)
        sys.exit(1)

    # Handle case when no command is provided
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
