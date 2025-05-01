# `labdb`

A simple CLI tool for managing MongoDB experiments.

## Installation and Setup

Install with:
```bash
pip install .
```

Then, setup with:
```bash
labdb --config
```
## Overview

## CLI Usage

The `labdb` CLI provides several commands for interacting with the experiment database:

- `ls [path]` - List contents of a path
- `mkdir path` - Create a new directory
- `rm path` - Remove a path (always recursive)
- `mv src_path dest_path` - Move a path to a new location
- `pwd` - Show current path
- `cd [path]` - Change current directory
- `edit path` - Edit notes for a path (directory or experiment)

### Tab Completion

The `labdb` CLI supports tab completion for paths. You can install it automatically with:

```bash
labdb --setup-completions
```

This will automatically detect your shell and add the necessary configuration to your shell's configuration file.

Alternatively, you can manually set it up:

#### Bash

Add the following to your `~/.bashrc` file:

```bash
eval "$(register-python-argcomplete labdb)"
```

#### Zsh

Add the following to your `~/.zshrc` file:

```zsh
autoload -Uz compinit
compinit
autoload -U bashcompinit
bashcompinit
eval "$(register-python-argcomplete labdb)"
```

#### Fish

Add the following to your `~/.config/fish/config.fish` file:

```fish
register-python-argcomplete --shell fish labdb | source
```

## API Usage

When logging and querying real experimental data, it's more than likely you'll want to do so programatically. The `ExperimentLogger` and `ExperimentQuery` classes can be used for this.

## Testing

This project uses pytest for testing with a real MongoDB test database. To run the tests:

1. Install the test dependencies:

```bash
pip install -r requirements-test.txt
```

2. Set the MongoDB password as an environment variable (replacing 'your_password' with the actual password):

```bash
export MONGODB_TEST_PASSWORD=your_password
```

3. Run the tests:

```bash
pytest tests/
```

For test coverage report:

```bash
pytest --cov=labdb tests/
```

The tests connect to a dedicated test database (`testDb`) on the production server. All test data is automatically cleaned up after each test.
