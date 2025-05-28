import argparse
import os
import readline
import shlex
import traceback

from labdb.cli_commands import (
    cli_cd,
    cli_edit,
    cli_ls,
    cli_mkdir,
    cli_mv,
    cli_pwd,
    cli_rm,
    cli_show,
)
from labdb.cli_completions import get_path_completions
from labdb.cli_formatting import BLUE, RED, RESET, error
from labdb.config import get_current_path


def add_command(subparsers, name, func, help_text, **kwargs):
    """Add a command to the argument parser with path completion for relevant arguments."""
    parser = subparsers.add_parser(name, help=help_text)
    for arg_name, arg_props in kwargs.items():
        # Add path completer to path arguments
        if arg_name in ["path", "src_path", "dest_path"]:
            parser.add_argument(arg_name, **arg_props).completer = get_path_completions
        else:
            parser.add_argument(arg_name, **arg_props)
    parser.set_defaults(func=func)
    return parser


def create_parser():
    """Create and return the argument parser with all commands configured."""
    parser = argparse.ArgumentParser(description="MongoDB experiment database tool")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Filesystem-like commands
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

    return parser


class InteractiveCompleter:
    """Tab completion for the interactive mode."""

    def __init__(self):
        self.commands = [
            "ls",
            "cd",
            "pwd",
            "mkdir",
            "rm",
            "mv",
            "edit",
            "show",
            "help",
            "exit",
            "quit",
        ]
        self.path_commands = [
            "ls",
            "cd",
            "mkdir",
            "rm",
            "edit",
            "show",
        ]  # Commands that take path arguments
        self.two_path_commands = ["mv"]  # Commands that take two path arguments

    def complete(self, text, state):
        """Main completion function called by readline."""
        try:
            line = readline.get_line_buffer()
            begin = readline.get_begidx()
            end = readline.get_endidx()

            # Parse the current line up to the cursor
            try:
                # Try to parse the tokens, but handle incomplete quotes gracefully
                tokens = shlex.split(line[:begin])
            except ValueError:
                # If shlex fails (e.g., unclosed quote), fall back to simple split
                tokens = line[:begin].split()

            current_token = line[begin:end]

            # Determine what we're completing
            if not tokens:
                # Completing command name
                options = [
                    cmd for cmd in self.commands if cmd.startswith(current_token)
                ]
            else:
                command = tokens[0]
                if command in self.commands:
                    # Count non-flag arguments to determine position
                    non_flag_tokens = [t for t in tokens[1:] if not t.startswith("-")]
                    arg_position = len(non_flag_tokens)

                    if current_token.startswith("-"):
                        # Completing flags
                        if command in ["rm", "mv"]:
                            options = (
                                ["--dry-run"]
                                if "--dry-run".startswith(current_token)
                                else []
                            )
                        else:
                            options = []
                    elif command in self.two_path_commands:
                        # mv command - needs two path arguments
                        if arg_position == 0:
                            # First path argument
                            options = self._get_path_completions(current_token)
                        elif arg_position == 1:
                            # Second path argument
                            options = self._get_path_completions(current_token)
                        else:
                            options = []
                    elif command in self.path_commands:
                        # Commands that take one path argument
                        if arg_position == 0:
                            options = self._get_path_completions(current_token)
                        else:
                            options = []
                    else:
                        options = []
                else:
                    options = []

            # Return the state-th option
            if state < len(options):
                return options[state]
            else:
                return None

        except Exception:
            # Silently fail for completion errors
            return None

    def _get_path_completions(self, prefix):
        """Get path completions using the existing completion system."""
        try:
            # Create a dummy parsed_args object
            class DummyArgs:
                pass

            parsed_args = DummyArgs()

            # Use the existing path completion function
            completions = get_path_completions(prefix, parsed_args)
            return completions or []
        except Exception:
            return []


def setup_interactive_completion():
    """Set up tab completion for interactive mode."""
    completer = InteractiveCompleter()
    readline.set_completer(completer.complete)

    # Configure readline for better completion behavior
    readline.parse_and_bind("tab: complete")
    readline.set_completer_delims(" \t\n`!@#$%^&*()=+[{]}\\|;:'\",<>?")

    # Enable history
    try:
        import atexit
        import os

        histfile = os.path.expanduser("~/.labdb_history")
        try:
            readline.read_history_file(histfile)
            # Limit history size
            readline.set_history_length(1000)
        except FileNotFoundError:
            pass
        atexit.register(readline.write_history_file, histfile)
    except Exception:
        # History is nice to have but not essential
        pass


def interactive_mode():
    """Run the interactive mode with labdb> prompt."""
    parser = create_parser()

    # Set up tab completion
    setup_interactive_completion()

    print("labdb interactive mode. Type 'help' for available commands, 'exit' to exit.")

    while True:
        try:
            # Show current path in prompt with colors
            current_path = get_current_path()
            prompt = f"labdb {BLUE}{current_path}{RESET} > "

            # Get user input
            try:
                command_line = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{RED}Exiting interactive mode...{RESET}")
                break

            # Skip empty lines
            if not command_line:
                continue

            # Handle exit commands
            if command_line.lower() in ["exit", "quit"]:
                print(f"{RED}Exiting interactive mode...{RESET}")
                break

            # Handle help command
            if command_line.lower() in ["help", "?"]:
                print("Available commands:")
                print("  ls [path]              - List contents of a path")
                print("  cd [path]              - Change current directory")
                print("  pwd                    - Show current path")
                print("  mkdir <path>           - Create a new directory")
                print("  rm <path> [--dry-run]  - Remove a path (always recursive)")
                print("  mv <src> <dest> [--dry-run] - Move a path to a new location")
                print("  edit <path>            - Edit notes for a path")
                print(
                    "  show <path>            - Show detailed information about a path"
                )
                print("  help, ?                - Show this help message")
                print("  exit, quit             - Exit interactive mode")
                continue

            # Parse the command line
            try:
                # Use shlex to properly handle quoted arguments
                args_list = shlex.split(command_line)
            except ValueError as e:
                error(f"Error parsing command: {e}")
                continue

            # Parse arguments
            try:
                args = parser.parse_args(args_list)
            except SystemExit:
                # argparse calls sys.exit on error, we want to continue the loop
                continue
            except Exception as e:
                error(f"Error parsing arguments: {e}")
                continue

            # Execute the command if it has a function
            if hasattr(args, "func"):
                try:
                    args.func(args)
                except SystemExit:
                    # Handle cases where commands call sys.exit() (like cancelled operations)
                    # Just continue with the interactive loop
                    pass
                except Exception as e:
                    error(f"Error executing command: {e}")
                    if os.getenv("DEBUG"):
                        traceback.print_exc()
            else:
                error("Unknown command. Type 'help' for available commands.")

        except Exception as e:
            error(f"Unexpected error: {e}")
            if os.getenv("DEBUG"):
                traceback.print_exc()
