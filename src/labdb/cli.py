import argparse
import os
import sys
import traceback

from labdb.cli_commands import (
    cli_cd,
    cli_edit,
    cli_ls,
    cli_mkdir,
    cli_mv,
    cli_pwd,
    cli_rm,
    cli_setup,
)
from labdb.cli_formatting import error, info, success, warning
from labdb.cli_json_editor import edit
from labdb.config import (
    CONFIG_FILE,
    CONFIG_SCHEMA,
    get_current_path,
    load_config,
    save_config,
    update_current_path,
)
from labdb.database import Database
from labdb.utils import (
    date_to_relative_time,
    dict_str,
    join_path,
    resolve_path,
    split_path,
)


def add_command(subparsers, name, func, help_text, **kwargs):
    parser = subparsers.add_parser(name, help=help_text)
    for arg_name, arg_props in kwargs.items():
        parser.add_argument(arg_name, **arg_props)
    parser.set_defaults(func=func)
    return parser


def main():
    parser = argparse.ArgumentParser(description="MongoDB experiment database tool")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Setup command
    add_command(
        subparsers,
        "setup",
        cli_setup,
        "Setup database connection and configuration",
    )

    # Filesystem-like commands
    add_command(
        subparsers,
        "ls",
        cli_ls,
        "List contents of a path",
        **{"path": {"help": "Path to list (default: current path)", "nargs": "?"}},
    )

    add_command(
        subparsers,
        "mkdir",
        cli_mkdir,
        "Create a new directory",
        **{"path": {"help": "Path to create"}},
    )

    add_command(
        subparsers,
        "rm",
        cli_rm,
        "Remove a path (always recursive)",
        **{
            "path": {"help": "Path to remove"},
            "--dry-run": {
                "help": "Only show what would be deleted without actually deleting",
                "action": "store_true",
                "dest": "dry_run",
            },
        },
    )

    add_command(
        subparsers,
        "mv",
        cli_mv,
        "Move a path to a new location",
        **{
            "src_path": {"help": "Source path to move"},
            "dest_path": {"help": "Destination path"},
            "--dry-run": {
                "help": "Only show what would be moved without actually moving",
                "action": "store_true",
                "dest": "dry_run",
            },
        },
    )

    add_command(
        subparsers,
        "pwd",
        cli_pwd,
        "Show current path",
    )

    add_command(
        subparsers,
        "cd",
        cli_cd,
        "Change current directory",
        **{"path": {"help": "Path to change to (default: root)", "nargs": "?"}},
    )

    add_command(
        subparsers,
        "edit",
        cli_edit,
        "Edit notes for a path (directory or experiment)",
        **{"path": {"help": "Path to edit notes for"}},
    )

    args = parser.parse_args()

    # Handle case when no command is provided
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
