# `labdb`

A simple CLI tool for managing MongoDB experiments.

## Installation

Install with:
```bash
pip install .
```

Then, setup with:
```bash
labdb --config
```

## CLI

- no arguments - Start interactive mode
- `pwd` - Show current path
- `ls [path]` - List contents of a path
- `mkdir path` - Create a new directory
- `rm path` - Remove a path (always recursive)
- `mv src_path dest_path` - Move a path to a new location
- `cd [path]` - Change current directory
- `edit path` - Edit notes for a path (directory or experiment)

### Tab Completion

The `labdb` CLI supports tab completion for paths. You can install it automatically with:

```bash
labdb --setup-completions
```

This will automatically detect your shell and add the necessary configuration to your shell's configuration file.

Alternatively, you can manually set it up:
Add the following to your `~/.bashrc` (or similar):
```bash
eval "$(register-python-argcomplete labdb)"
```

## API

Use `ExperimentLogger` and `ExperimentQuery` to programatically log and query experimental data.
