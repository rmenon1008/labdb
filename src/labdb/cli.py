import argparse
import sys

from labdb.cli_commands import (
    cli_cd,
    cli_edit,
    cli_ls,
    cli_mkdir,
    cli_mv,
    cli_pwd,
    cli_rm,
    cli_setup,
    cli_show,
)
from labdb.cli_completions import (
    get_path_completions,
    install_completions,
    setup_completions,
)
from labdb.cli_interactive import interactive_mode


def add_command(subparsers, name, func, help_text, **kwargs):
    parser = subparsers.add_parser(name, help=help_text)
    for arg_name, arg_props in kwargs.items():
        # Add path completer to path arguments
        if arg_name in ["path", "src_path", "dest_path"]:
            parser.add_argument(arg_name, **arg_props).completer = get_path_completions
        else:
            parser.add_argument(arg_name, **arg_props)
    parser.set_defaults(func=func)
    return parser


def main():
    parser = argparse.ArgumentParser(description="MongoDB experiment database tool")

    # Add global options
    parser.add_argument(
        "--config",
        action="store_true",
        help="Setup database connection and configuration",
    )
    parser.add_argument(
        "--setup-completions",
        action="store_true",
        help="Install tab completion for the current shell",
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add all the commands (reusing the same definitions as in create_parser)
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
        "edit",
        cli_edit,
        "Edit notes for a path (directory or experiment)",
        **{"path": {"help": "Path to edit notes for"}},
    )

    add_command(
        subparsers,
        "show",
        cli_show,
        "Show detailed information about a path (directory or experiment)",
        **{"path": {"help": "Path to show information for"}},
    )

    # Enable tab completion
    setup_completions(parser)

    # If no arguments provided, check if it should enter interactive mode
    if len(sys.argv) == 1:
        interactive_mode()
        return

    args = parser.parse_args()

    # Handle --setup-completions option
    if hasattr(args, "setup_completions") and args.setup_completions:
        install_completions()
        return

    # Handle --config option
    if args.config:
        cli_setup(args)
        return

    # Handle case when no command is provided
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
