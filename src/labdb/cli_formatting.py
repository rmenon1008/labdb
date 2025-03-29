from rich import print as rprint
from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

console = Console()


def error(message):
    """Display an error message in red with an X emoji"""
    console.print(f"\U0000274C [bold red]{message}[/bold red]")


def success(message):
    """Display a success message in green with a checkmark emoji"""
    console.print(f"\U00002705 [green]{message}[/green]")


def info(message):
    """Display an info message in blue with an info emoji"""
    console.print(f"\U00002139\U0000FE0F  [blue]{message}[/blue]")


def warning(message):
    """Display a warning message in yellow with a warning emoji"""
    console.print(f"\U0001FAD7  [yellow]{message}[/yellow]")


def get_input(prompt_text, default=None):
    """Get user input with a nicely formatted prompt"""
    return Prompt.ask(f"[yellow]{prompt_text}[/yellow]", default=default)


def display_table(headers, rows):
    """Display data in a nicely formatted table"""
    table = Table(show_header=True, box=ROUNDED)

    for header in headers:
        table.add_column(header)

    for row in rows:
        table.add_row(*[str(item) for item in row])

    console.print(table)


def display_config(config_path, config_data):
    """Display configuration data in a panel"""
    content = "\n".join([f"{key}: {value}" for key, value in config_data.items()])
    panel = Panel(
        content,
        title=f"Config file: {config_path}",
        border_style="blue",
    )
    console.print(panel)
