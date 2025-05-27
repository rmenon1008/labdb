import os
import subprocess
import sys

import argcomplete

from labdb.cli_formatting import error, info, success
from labdb.config import get_current_path, load_config
from labdb.database import Database
from labdb.utils import resolve_path


def install_completions():
    """
    Install tab completion for the current shell.
    Supports bash, zsh, and fish.
    """
    # Detect shell with multiple methods
    shell_detected = False
    shell_name = ""

    # Method 1: Check for shell-specific environment variables
    if os.environ.get("ZSH_VERSION"):
        shell_name = "zsh"
        shell_detected = True
    elif os.environ.get("BASH_VERSION"):
        shell_name = "bash"
        shell_detected = True
    elif os.environ.get("FISH_VERSION"):
        shell_name = "fish"
        shell_detected = True

    # Method 2: Check SHELL environment variable if not detected yet
    if not shell_detected:
        shell = os.environ.get("SHELL", "")
        if shell:
            shell_name = os.path.basename(shell)
            if shell_name in ["zsh", "bash", "fish"]:
                shell_detected = True

    # Method 3: Try to detect through process information
    if not shell_detected:
        try:
            # Get the parent process executable
            parent_pid = os.getppid()
            if sys.platform == "darwin" or sys.platform.startswith("linux"):
                # Use ps on Unix-like systems
                proc = subprocess.run(
                    ["ps", "-p", str(parent_pid), "-o", "comm="],
                    capture_output=True,
                    text=True,
                )
                parent_proc = proc.stdout.strip()
                if "zsh" in parent_proc:
                    shell_name = "zsh"
                    shell_detected = True
                elif "bash" in parent_proc:
                    shell_name = "bash"
                    shell_detected = True
                elif "fish" in parent_proc:
                    shell_name = "fish"
                    shell_detected = True
        except Exception:
            # Silently fail if we can't get process info
            pass

    # Method 4: Ask the user if shell is still not detected
    if not shell_detected:
        print("Could not automatically detect your shell.")
        print("1. bash")
        print("2. zsh")
        print("3. fish")
        choice = input("Select your shell (1/2/3): ").strip()
        if choice == "1":
            shell_name = "bash"
            shell_detected = True
        elif choice == "2":
            shell_name = "zsh"
            shell_detected = True
        elif choice == "3":
            shell_name = "fish"
            shell_detected = True
        else:
            error("Invalid selection")
            return False

    # Handle different shells
    if shell_name == "bash":
        config_file = os.path.expanduser("~/.bashrc")
        completion_line = 'eval "$(register-python-argcomplete labdb)"'
    elif shell_name == "zsh":
        config_file = os.path.expanduser("~/.zshrc")
        completion_line = """
# Enable labdb completions
autoload -Uz compinit
compinit
autoload -U bashcompinit
bashcompinit
eval "$(register-python-argcomplete labdb)"
"""
    elif shell_name == "fish":
        config_file = os.path.expanduser("~/.config/fish/config.fish")
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        completion_line = "register-python-argcomplete --shell fish labdb | source"
    else:
        error(f"Unsupported shell: {shell_name}")
        info("Please see the README for manual installation instructions.")
        return False

    # Check if completion is already installed
    try:
        with open(config_file, "r") as f:
            content = f.read()
            if "register-python-argcomplete labdb" in content:
                info(f"Completion already installed in {config_file}")
                return True
    except FileNotFoundError:
        # Config file doesn't exist yet, we'll create it
        pass

    # Append completion to config file
    try:
        with open(config_file, "a") as f:
            f.write("\n# Added by labdb --install-completions\n")
            f.write(completion_line + "\n")
        success(f"Tab completion installed in {config_file}")
        info("Please restart your shell or run:")
        if shell_name in ["bash", "zsh"]:
            info(f"  source {config_file}")
        elif shell_name == "fish":
            info(f"  source {config_file}")
        return True
    except Exception as e:
        error(f"Failed to install completions: {e}")
        return False


def get_path_completions(prefix, parsed_args, **kwargs):
    """
    Get completions for paths in the database.

    This function is called by argcomplete to provide completions for path arguments.
    It queries the database for existing paths that match the prefix.

    Args:
        prefix: The prefix to complete
        parsed_args: The parsed arguments so far

    Returns:
        List of path completions
    """
    try:
        config = load_config()
        db = Database(config)
        current_path = get_current_path()

        # If prefix starts with /, treat as absolute path
        if prefix.startswith("/"):
            base_path = "/"
            remaining = prefix[1:]
        else:
            # Handle relative paths
            base_path = current_path
            remaining = prefix

        # Handle path components one at a time
        path_parts = remaining.split("/")
        if len(path_parts) > 1:
            # For multi-level paths, navigate down to the last complete directory
            for i in range(len(path_parts) - 1):
                if path_parts[i]:  # Skip empty parts (consecutive slashes)
                    base_path = resolve_path(base_path, path_parts[i])

            # The last part is what we're completing
            completion_prefix = path_parts[-1]
        else:
            completion_prefix = remaining

        # List contents of the base path
        items = db.list_dir(base_path, only_project_paths=True)

        # Filter and format completions
        completions = []
        for item in items:
            name = item["path_str"].split("/")[-1]
            if name.startswith(completion_prefix):
                # Add trailing slash for directories
                if item["type"] == "directory":
                    completions.append(f"{name}/")
                else:
                    completions.append(name)

        # Handle the special case for empty prefix in the current directory
        if not prefix:
            return [
                f"{name}/" if item["type"] == "directory" else name
                for item, name in [
                    (item, item["path_str"].split("/")[-1]) for item in items
                ]
            ]

        # Format completions based on the input prefix
        if prefix.startswith("/"):
            # Absolute path
            if "/" in prefix[1:]:
                # Multi-level path
                base_prefix = "/".join(prefix.split("/")[:-1]) + "/"
                return [f"{base_prefix}{c}" for c in completions]
            else:
                # Root level
                return [f"/{c}" for c in completions]
        else:
            # Relative path
            if "/" in prefix:
                # Multi-level path
                base_prefix = "/".join(prefix.split("/")[:-1]) + "/"
                return [f"{base_prefix}{c}" for c in completions]
            else:
                # Current directory
                return completions

    except Exception:
        # Silently fail for completion - don't disrupt the command line
        return []


def setup_completions(parser):
    """
    Set up tab completion for the parser.

    Args:
        parser: The argparse parser to set up completions for
    """
    argcomplete.autocomplete(parser, always_complete_options=False, exclude=["--help"])
