import os
import json
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer


no_color = os.environ.get("NO_COLOR") or os.environ.get("NO_COLOR_LABDB")

# ANSI color codes
RED = "\033[91m" if not no_color else ""
GREEN = "\033[92m" if not no_color else ""
YELLOW = "\033[93m" if not no_color else ""
BLUE = "\033[94m" if not no_color else ""
BOLD = "\033[1m" if not no_color else ""
RESET = "\033[0m" if not no_color else ""


def error(message):
    print(f"{BOLD}{RED}{message}{RESET}")


def success(message):
    print(f"{GREEN}{message}{RESET}")


def warning(message):
    print(f"{YELLOW}{message}{RESET}")


def info(message):
    print(message)


def key_value(key, value):
    print(f"{key}: {BLUE}{value}{RESET}")


def bold(message):
    print(f"{BOLD}{message}{RESET}")


def get_input(prompt_text, default=None):
    if default is not None:
        user_input = input(f"{prompt_text} {BLUE}[default: {default}]{RESET}: ")
        return user_input if user_input else default
    else:
        return input(f"{prompt_text}: ")

def json_print(obj):
    """Pretty print a JSON object with syntax highlighting"""

    json_str = json.dumps(obj, indent=2)
    print(highlight(json_str, JsonLexer(), TerminalFormatter()))