import json
import sys

import yaml
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea
from pygments.lexers.data import YamlLexer

from labdb.cli_formatting import error


def edit(json_data, title="JSON Editor", description=None):
    """
    Edit a JSON object using a simple text editor.

    Args:
        json_data: A dictionary or JSON-serializable object
        title: Title to display at the top of the editor
        description: Optional description to display below the title

    Returns:
        The edited JSON object
    """
    # Format the JSON for display
    formatted_json = json.dumps(json_data, indent=2)

    # If it's empty brackets, add a newline between them
    if formatted_json == "{}":
        formatted_json = "{\n\n}"
    elif formatted_json == "[]":
        formatted_json = "[\n\n]"

    # Add a newline after the last line if it's not already there
    if formatted_json[-1] != "\n":
        formatted_json += "\n"

    # Create key bindings for the editor
    kb = KeyBindings()

    # Add Ctrl+D to save and exit
    @kb.add("c-d")
    def _(event):
        """Submit the input when Ctrl+D is pressed."""
        # Get the buffer and validate it before exiting
        buffer = event.app.layout.get_buffer_by_name("editor")
        try:
            # Pre-validate using YAML to catch syntax errors
            text = buffer.text
            yaml.safe_load(text)
            # If validation passes, exit with the result
            event.app.exit(result=text)
        except yaml.YAMLError as e:
            # Show validation error message at the bottom
            if hasattr(e, "problem_mark"):
                mark = e.problem_mark
                error_msg = f"Invalid syntax: {e.problem} at line {mark.line + 1}, column {mark.column + 1}"
            else:
                error_msg = f"Invalid syntax: {str(e)}"
            # Don't exit - just show the error
            event.app.layout.get_buffer_by_name("status").text = f"ERROR: {error_msg}"
            # Move cursor to the error position if possible
            if hasattr(e, "problem_mark"):
                mark = e.problem_mark
                # Calculate position in the buffer
                lines = text.split("\n")
                pos = sum(len(line) + 1 for line in lines[: mark.line]) + mark.column
                buffer.cursor_position = pos

    # Add Ctrl+C to cancel
    @kb.add("c-c")
    def _(event):
        """Cancel editing when Ctrl+C is pressed."""
        event.app.exit(None)  # Return None to indicate cancellation

    # Add Tab to insert two spaces
    @kb.add("tab")
    def _(event):
        """Insert two spaces when Tab is pressed."""
        event.app.layout.get_buffer_by_name("editor").insert_text("  ")

    # Create a text area with line numbers
    text_area = TextArea(
        text=formatted_json,
        lexer=PygmentsLexer(YamlLexer),
        multiline=True,
        line_numbers=True,  # TextArea supports line_numbers directly
        name="editor",
    )

    # Prepare layout components
    layout_components = []

    # Add title and description to the layout
    layout_components.append(
        Window(height=1, content=FormattedTextControl(f"{title}"), style="class:title")
    )

    if description:
        layout_components.append(
            Window(
                height=1,
                content=FormattedTextControl(description),
                style="class:description",
            )
        )

    # Add separator after title/description
    layout_components.append(Window(height=1, char="─", style="class:line"))

    # Add main editor area
    layout_components.append(text_area)

    # Add bottom separator and instructions
    layout_components.append(Window(height=1, char="─", style="class:line"))

    # Add status line for validation errors
    status_buffer = Buffer(name="status")
    layout_components.append(
        Window(height=1, content=BufferControl(status_buffer), style="class:error")
    )

    # Add instructions line
    layout_components.append(
        Window(
            height=1,
            content=FormattedTextControl("Ctrl+D to save and exit, Ctrl+C to cancel"),
        )
    )

    # Create a layout with the components
    layout = Layout(HSplit(layout_components))

    # Create the application
    application = Application(
        layout=layout,
        key_bindings=kb,
        style=Style.from_dict(
            {
                "line-numbers": "#ansibrightblack",
                "line": "#ansibrightblack",
                "title": "bold",
                "description": "",
                "error": "#ansired bold",
            }
        ),
        full_screen=True,
        mouse_support=True,
    )

    try:
        # Run the application and get the result
        result = application.run()

        # If result is None, editing was canceled
        if result is None:
            error("Editing cancelled")
            sys.exit(1)

        # Use YAML to parse the result for more forgiving syntax
        parsed_data = yaml.safe_load(result)

        # Return the parsed data (which is compatible with JSON)
        return parsed_data

    except KeyboardInterrupt:
        # Return the original JSON if editing was canceled
        error("Editing cancelled")
        sys.exit(1)


def main():
    starting_json = {"foo": "bar", "baz": "qux"}
    edited_json = edit(
        starting_json,
        title="Sample JSON Editor",
        description="Edit the sample JSON object below",
    )
    print(edited_json)


if __name__ == "__main__":
    main()
