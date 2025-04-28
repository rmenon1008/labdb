# `labdb`

A simple CLI tool for managing MongoDB experiments.

## Installation and Setup

Install with:
```bash
pip install .
```

Then, setup with:
```bash
labdb config setup
```
## Overview

## CLI Usage


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
