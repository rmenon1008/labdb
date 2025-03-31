import argparse
import sys

from labdb.cli_commands import (
    cli_config_setup,
    cli_experiment_create,
    cli_experiment_delete,
    cli_experiment_edit,
    cli_experiment_list,
    cli_session_create,
    cli_session_delete,
    cli_session_edit,
    cli_session_list,
    cli_setup_check,
    cli_setup_show,
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

    # Config command
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_subs = config_parser.add_subparsers(dest="subcommand")
    add_command(
        config_subs,
        "setup",
        cli_config_setup,
        "Setup a new MongoDB connection with connection string, database name, and storage options",
    )
    add_command(
        config_subs,
        "check",
        cli_setup_check,
        "Verify the MongoDB connection is working properly with the current configuration",
    )
    add_command(
        config_subs,
        "show",
        cli_setup_show,
        "Display the current MongoDB connection settings including URI, database, and storage options",
    )

    # Session command - singular form
    session_parser = subparsers.add_parser("session", help="Session management")
    session_subs = session_parser.add_subparsers(dest="subcommand")
    add_command(
        session_subs,
        "list",
        cli_session_list,
        "List all available sessions with their IDs, names, creation dates, and experiment counts",
    )
    add_command(
        session_subs,
        "delete",
        cli_session_delete,
        "Delete a session by its ID, including all associated experiments and their data",
        **{"id": {"help": "Session ID to delete"}},
    )
    add_command(
        session_subs, 
        "create", 
        cli_session_create, 
        "Create a new session with a name and optional description in the JSON editor",
    )
    add_command(
        session_subs,
        "edit",
        cli_session_edit,
        "Edit an existing session's properties by ID using the JSON editor (uses most recent session if ID not provided)",
        **{"id": {"help": "Session ID to edit (optional, defaults to most recent)", "nargs": "?"}},
    )

    # Experiment command - singular form
    experiment_parser = subparsers.add_parser(
        "experiment", help="Experiment management"
    )
    experiment_subs = experiment_parser.add_subparsers(dest="subcommand")
    add_command(
        experiment_subs,
        "list",
        cli_experiment_list,
        "List all experiments with creation dates, IDs, and notes, optionally filtered by session ID",
        **{"session_id": {"help": "Optional session ID to list only experiments for that session", "nargs": "?"}},
    )
    add_command(
        experiment_subs,
        "delete",
        cli_experiment_delete,
        "Delete an experiment by its ID, including all related data and measurements",
        **{"id": {"help": "Experiment ID to delete"}},
    )
    add_command(
        experiment_subs,
        "create",
        cli_experiment_create,
        "Create a new experiment with notes in an existing session using the JSON editor",
        **{
            "session_id": {
                "help": "Optional session ID to create the experiment in (defaults to most recent session)",
                "nargs": "?",
            }
        },
    )
    add_command(
        experiment_subs,
        "edit",
        cli_experiment_edit,
        "Edit an existing experiment's notes by ID using the JSON editor (uses most recent experiment if ID not provided)",
        **{"id": {"help": "Experiment ID to edit (optional, defaults to most recent)", "nargs": "?"}},
    )

    args = parser.parse_args()

    # Handle case when a command is provided but no subcommand
    if args.command and not hasattr(args, "func"):
        if args.command in ["config"]:
            config_parser.print_help()
        elif args.command in ["session"]:
            session_parser.print_help()
        elif args.command in ["experiment"]:
            experiment_parser.print_help()
        print(
            f"\nError: A subcommand is required for '{args.command}'", file=sys.stderr
        )
        sys.exit(1)

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
