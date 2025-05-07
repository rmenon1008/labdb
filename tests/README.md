# LabDB Tests

This directory contains tests for the LabDB package.

## Running Tests

To run the tests, make sure you have the test dependencies installed:

```bash
pip install -r requirements-test.txt
```

Then run pytest:

```bash
pytest
```

To run with code coverage:

```bash
pytest --cov=labdb
```

## Test Structure

- `conftest.py`: Common pytest fixtures
- `test_database.py`: Tests for the Database class
- `test_api.py`: Tests for the ExperimentLogger and ExperimentQuery classes

## Mock Database

The tests use `mongomock` to mock MongoDB, allowing tests to run without a real database connection. This makes the tests faster and more isolated. 