from unittest.mock import patch

import numpy as np
import pytest

from labdb.api import ExperimentLogger, ExperimentQuery


@pytest.fixture
def mock_logger(mock_db):
    """Create a test ExperimentLogger with the mock database"""
    with patch("labdb.api.Database") as mock_db_class:
        mock_db_class.return_value = mock_db
        with patch("labdb.api.get_current_path", return_value="/test"):
            with patch("labdb.api.key_value"):  # Mock key_value to avoid printing
                logger = ExperimentLogger(path="/test", notes_mode="none")
                yield logger


@pytest.fixture
def mock_query(mock_db):
    """Create a test ExperimentQuery with the mock database"""
    with patch("labdb.api.Database") as mock_db_class:
        mock_db_class.return_value = mock_db
        query = ExperimentQuery()
        yield query


def test_experiment_logger_init(mock_db):
    """Test ExperimentLogger initialization"""
    with patch("labdb.api.Database") as mock_db_class:
        mock_db_class.return_value = mock_db
        with patch("labdb.api.get_current_path", return_value="/test"):
            with patch("labdb.api.key_value"):  # Mock key_value to avoid printing
                # Test with default parameters
                logger = ExperimentLogger()
                assert logger.path == "/test"
                assert logger.notes_mode == "ask-every"
                assert logger.current_experiment_path is None

                # Test with explicit path
                logger = ExperimentLogger(path="/test", notes_mode="none")
                assert logger.path == "/test"
                assert logger.notes_mode == "none"

                # Test with non-existent path
                with pytest.raises(Exception):
                    ExperimentLogger(path="/nonexistent")


def test_new_experiment(mock_logger, mock_db):
    """Test creating a new experiment"""
    # Mock edit function to avoid interactive editor
    with patch("labdb.api.edit", return_value={"note": "test"}):
        # Test with notes_mode="none"
        # This should create a new experiment without opening editor
        exp_path = mock_logger.new_experiment(name="test_exp_1")
        assert exp_path == "/test/test_exp_1"
        assert mock_logger.current_experiment_path == "/test/test_exp_1"

        # Check the experiment was created in the database
        exp = mock_db.get_experiments("/test/test_exp_1")[0]
        assert exp["notes"] == {}  # Empty notes because notes_mode="none"


def test_log_data(mock_logger, mock_db):
    """Test logging data to an experiment"""
    # Create a new experiment
    with patch("labdb.api.edit", return_value={}):
        exp_path = mock_logger.new_experiment(name="data_test_1")

    # Log some data
    mock_logger.log_data("string_data", "test_value")
    mock_logger.log_data("numeric_data", 42)
    mock_logger.log_data("array_data", np.array([1, 2, 3]))
    mock_logger.log_data("dict_data", {"key": "value"})

    # Check the data was stored
    exp = mock_db.get_experiments(exp_path)[0]
    assert exp["data"]["string_data"] == "test_value"
    assert exp["data"]["numeric_data"] == 42
    assert np.array_equal(exp["data"]["array_data"], np.array([1, 2, 3]))
    assert exp["data"]["dict_data"] == {"key": "value"}

    # Test error when no experiment started
    mock_logger.current_experiment_path = None
    with pytest.raises(Exception, match="No experiment started"):
        mock_logger.log_data("key", "value")


def test_log_note(mock_logger, mock_db):
    """Test logging notes to an experiment"""
    # Create a new experiment
    with patch("labdb.api.edit", return_value={}):
        exp_path = mock_logger.new_experiment(name="note_test_1")

    # Log some notes
    mock_logger.log_note("note1", "test_value")
    mock_logger.log_note("note2", 42)

    # Check the notes were stored
    exp = mock_db.get_experiments(exp_path)[0]
    assert exp["notes"]["note1"] == "test_value"
    assert exp["notes"]["note2"] == 42

    # Test error when no experiment started
    mock_logger.current_experiment_path = None
    with pytest.raises(Exception, match="No experiment started"):
        mock_logger.log_note("key", "value")


def test_experiment_query_init(mock_db):
    """Test ExperimentQuery initialization"""
    with patch("labdb.api.Database") as mock_db_class:
        mock_db_class.return_value = mock_db
        query = ExperimentQuery()
        assert query.db == mock_db


def test_normalize_path(mock_query):
    """Test path normalization in ExperimentQuery"""
    with patch("labdb.api.get_current_path", return_value="/current"):
        # Test with None (should use current path)
        assert mock_query._normalize_path(None) == "/current"

        # Test with string path
        assert mock_query._normalize_path("/test") == "/test"

        # Test with relative path
        with patch("labdb.api.resolve_path", return_value="/current/subdir"):
            assert mock_query._normalize_path("subdir") == "/current/subdir"


def test_get_experiments(mock_query, mock_db):
    """Test getting experiments by path"""
    # Create test data
    mock_db.create_dir("/query_test")
    mock_db.create_dir("/query_test/subdir")

    mock_db.create_experiment(
        "/query_test", name="exp1", data={"value": 10}, notes={"category": "A"}
    )
    mock_db.create_experiment(
        "/query_test", name="exp2", data={"value": 20}, notes={"category": "B"}
    )
    mock_db.create_experiment(
        "/query_test/subdir", name="exp3", data={"value": 30}, notes={"category": "A"}
    )

    # Test non-recursive query
    with patch("labdb.api.get_current_path", return_value="/query_test"):
        exps = mock_query.get_experiments(recursive=False)
        assert len(exps) == 2

        # Test with explicit path
        exps = mock_query.get_experiments("/query_test/subdir")
        assert len(exps) == 1
        assert exps[0]["path_str"] == "/query_test/subdir/exp3"

        # Test with recursive flag
        exps = mock_query.get_experiments("/query_test", recursive=True)
        assert len(exps) == 3

        # Test with query condition
        exps = mock_query.get_experiments(
            "/query_test", recursive=True, query={"notes.category": "A"}
        )
        assert len(exps) == 2


def test_get_experiments_with_list(mock_query, mock_db):
    """Test getting experiments from a list of paths"""
    # Create test data
    mock_db.create_dir("/exp_list_test")
    mock_db.create_dir("/exp_list_test/dir1")
    mock_db.create_dir("/exp_list_test/dir2")
    mock_db.create_dir("/exp_list_test/dir3")

    mock_db.create_experiment("/exp_list_test/dir1", name="exp1")
    mock_db.create_experiment("/exp_list_test/dir2", name="exp2")
    mock_db.create_experiment("/exp_list_test/dir3", name="exp3")

    # Test with explicit paths
    paths = ["/exp_list_test/dir1/exp1", "/exp_list_test/dir2/exp2"]
    with patch("labdb.api.get_current_path", return_value="/exp_list_test"):
        exps = mock_query.get_experiments(paths)
        assert len(exps) == 2

        # Test with range pattern
        paths = ["/exp_list_test/dir$(1-3)/exp$(1-3)"]
        exps = mock_query.get_experiments(paths)
        assert len(exps) == 3  # dir1/exp1, dir2/exp2, dir3/exp3


def test_get_experiment(mock_query, mock_db):
    """Test getting a specific experiment"""
    # Create test data
    mock_db.create_dir("/single_test")
    mock_db.create_experiment("/single_test", name="exp1", data={"value": 10})

    # Test with valid path
    with patch("labdb.api.get_current_path", return_value="/single_test"):
        exp = mock_query.get_experiment("/single_test/exp1")
        assert exp["path_str"] == "/single_test/exp1"
        assert exp["data"]["value"] == 10

        # Test with non-existent path
        with pytest.raises(Exception):
            mock_query.get_experiment("/single_test/nonexistent")


def test_experiment_log_data(mock_query, mock_db):
    """Test logging data to an experiment using ExperimentQuery"""
    # Create test data
    mock_db.create_dir("/log_data_test")
    mock_db.create_experiment("/log_data_test", name="exp1")

    # Log data
    with patch("labdb.api.get_current_path", return_value="/log_data_test"):
        mock_query.experiment_log_data("/log_data_test/exp1", "key1", "value1")

        # Check data was logged
        exp = mock_db.get_experiments("/log_data_test/exp1")[0]
        assert exp["data"]["key1"] == "value1"


def test_experiment_log_note(mock_query, mock_db):
    """Test logging notes to an experiment using ExperimentQuery"""
    # Create test data
    mock_db.create_dir("/log_note_test")
    mock_db.create_experiment("/log_note_test", name="exp1")

    # Log note
    with patch("labdb.api.get_current_path", return_value="/log_note_test"):
        mock_query.experiment_log_note("/log_note_test/exp1", "note1", "value1")

        # Check note was logged
        exp = mock_db.get_experiments("/log_note_test/exp1")[0]
        assert exp["notes"]["note1"] == "value1"
