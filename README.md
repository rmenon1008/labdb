# MongoDB Experiment Tool

A simple CLI tool for managing MongoDB experiments.

## Installation

```bash
pip install -e .
```

Or install in development mode with dependencies:

```bash
pip install -e ".[dev]"
```

## Dependencies

This tool requires:
- Python 3.8 or higher
- pymongo
- rich (for improved CLI formatting)

## Usage

```bash
# Setup MongoDB connection
python -m src.mongo-experiment.cli connection setup

# Check MongoDB connection
python -m src.mongo-experiment.cli connection check

# Show connection settings
python -m src.mongo-experiment.cli connection show

# Session management
python -m src.mongo-experiment.cli session list
python -m src.mongo-experiment.cli session create
python -m src.mongo-experiment.cli session edit [id]
python -m src.mongo-experiment.cli session delete <id>

# Experiment management
python -m src.mongo-experiment.cli experiment list [session_id]
python -m src.mongo-experiment.cli experiment create [session_id]
python -m src.mongo-experiment.cli experiment edit [id]
python -m src.mongo-experiment.cli experiment delete <id>
```
