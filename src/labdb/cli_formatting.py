from rich import print as rprint
from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

console = Console()


def error(message):
    console.print(f"[bold red]{message}[/bold red]")


def success(message):
    console.print(f"[green]{message}[/green]")


def warning(message):
    console.print(f"[yellow]{message}[/yellow]")


def info(message):
    console.print(message)


def key_value(key, value):
    console.print(f"{key}: [blue]{value}[/blue]")


def get_input(prompt_text, default=None):
    if default is not None:
        return (
            Prompt.ask(f"{prompt_text} [blue]\[default: {default}][/blue]") or default
        )
    else:
        return Prompt.ask(f"{prompt_text}")


def display_table(headers, rows):
    table = Table(show_header=True, box=ROUNDED)

    for header in headers:
        table.add_column(header)

    for row in rows:
        table.add_row(*[str(item) for item in row])

    console.print(table)
