from datetime import datetime

import numpy as np
import pytest

from labdb.database import Database


def test_create_dir(test_db):
    """Test creating a directory."""
    # Create root directory first
    test_db.create_dir(["test_dir"], {"note": "test note"})

    # Verify directory exists
    assert test_db.dir_exists(["test_dir"])

    # Verify path exists
    assert test_db.path_exists(["test_dir"])

    # Test creating nested directory
    test_db.create_dir(["test_dir", "nested_dir"])
    assert test_db.dir_exists(["test_dir", "nested_dir"])


def test_create_dir_error_path_exists(test_db):
    """Test error when creating a directory that already exists."""
    test_db.create_dir(["test_dir"])

    # Should raise an exception when trying to create the same directory
    with pytest.raises(Exception, match="already exists"):
        test_db.create_dir(["test_dir"])


def test_list_dir(test_db):
    """Test listing directory contents."""
    # Create a directory structure
    test_db.create_dir(["parent"])
    test_db.create_dir(["parent", "child1"])
    test_db.create_dir(["parent", "child2"])

    # Create an experiment
    test_db.create_experiment(["parent"], "exp1")

    # List contents
    contents = test_db.list_dir(["parent"])

    # Should have 3 items (2 directories and 1 experiment)
    assert len(contents) == 3


def test_delete(test_db):
    """Test deleting a directory or experiment."""
    # Create a directory structure
    test_db.create_dir(["parent"])
    test_db.create_dir(["parent", "child"])

    # Delete the child directory
    test_db.delete(["parent", "child"])

    # Child should no longer exist
    assert not test_db.dir_exists(["parent", "child"])

    # Parent should still exist
    assert test_db.dir_exists(["parent"])

    # Create an experiment and then delete it
    test_db.create_experiment(["parent"], "exp1")
    assert test_db.path_exists(["parent", "exp1"])

    test_db.delete(["parent", "exp1"])
    assert not test_db.path_exists(["parent", "exp1"])


def test_move(test_db):
    """Test moving a directory or experiment."""
    # Create directories
    test_db.create_dir(["source"])
    test_db.create_dir(["dest"])
    test_db.create_dir(["source", "child"])

    # Move a directory
    test_db.move(["source", "child"], ["dest"])

    # Source child should no longer exist
    assert not test_db.dir_exists(["source", "child"])

    # Destination should have the child
    assert test_db.dir_exists(["dest", "child"])

    # Test moving an experiment
    test_db.create_experiment(["source"], "exp1")
    test_db.move(["source", "exp1"], ["dest"])

    # Experiment should be moved
    assert not test_db.path_exists(["source", "exp1"])
    assert test_db.path_exists(["dest", "exp1"])


def test_create_experiment(test_db):
    """Test creating an experiment with different options."""
    # Create a directory for the experiments
    test_db.create_dir(["experiments"])

    # Create experiment with a specified name
    exp_id = test_db.create_experiment(
        ["experiments"],
        "test_exp",
        {"param1": 10, "param2": "test"},
        {"note": "Test experiment"},
    )

    # Verify the experiment was created
    assert exp_id == "test_exp"
    assert test_db.path_exists(["experiments", "test_exp"])

    # Create experiment with auto-generated name
    exp_id = test_db.create_experiment(["experiments"])

    # Verify the experiment was created
    assert test_db.path_exists(["experiments", exp_id])

    # Create another experiment with auto-generated name
    exp_id = test_db.create_experiment(["experiments"])

    # Verify the experiment was created
    assert test_db.path_exists(["experiments", exp_id])


def test_get_experiments(test_db):
    """Test retrieving experiments with various query options."""
    # Create a directory for the experiments
    test_db.create_dir(["experiments"])

    # Create some experiments with different data
    test_db.create_experiment(["experiments"], "exp1", {"score": 10, "algorithm": "A"})

    test_db.create_experiment(["experiments"], "exp2", {"score": 20, "algorithm": "B"})

    test_db.create_experiment(["experiments"], "exp3", {"score": 15, "algorithm": "A"})

    # Create a nested directory with experiments
    test_db.create_dir(["experiments", "nested"])
    test_db.create_experiment(
        ["experiments", "nested"], "exp4", {"score": 25, "algorithm": "C"}
    )

    # Test retrieving all experiments
    exps = test_db.get_experiments(["experiments"])
    assert len(exps) == 4  # Should include nested experiment

    # Test retrieving with non-recursive search
    exps = test_db.get_experiments(["experiments"], recursive=False)
    assert len(exps) == 3  # Should not include nested experiment

    # Test query filtering
    exps = test_db.get_experiments(["experiments"], query={"data.algorithm": "A"})
    assert len(exps) == 2  # Only experiments with algorithm A

    # Test sorting
    exps = test_db.get_experiments(
        ["experiments"], sort=[("data.score", 1)]  # Sort by score ascending
    )
    assert len(exps) == 4
    assert exps[0]["data"]["score"] == 10  # Lowest score first

    # Test limit
    exps = test_db.get_experiments(["experiments"], limit=2)
    assert len(exps) == 2

    # Test projection
    exps = test_db.get_experiments(["experiments"], projection={"data.score": 1})
    assert "score" in exps[0]["data"]
    assert "algorithm" not in exps[0]["data"]


def test_update_dir_notes(test_db):
    """Test updating directory notes."""
    # Create a directory
    test_db.create_dir(["test_dir"], {"initial": "note"})

    # Update the notes
    test_db.update_dir_notes(["test_dir"], {"updated": "note", "added": "field"})

    # Retrieve the directory and check notes
    dir_doc = test_db.directories.find_one({"path": ["test_dir"]})
    assert dir_doc["notes"]["updated"] == "note"
    assert dir_doc["notes"]["added"] == "field"
    assert "initial" not in dir_doc["notes"]


def test_large_numpy_array_experiment(test_db):
    """Test storing and retrieving an experiment with a large numpy array (>16MB)."""
    # Create a directory for the experiment
    test_db.create_dir(["numpy_tests"])

    # Create a large numpy array (>16MB)
    # A float64 array of size (2000, 2000) is about 32MB
    large_array = np.random.random((2000, 2000))
    assert large_array.nbytes > 16 * 1024 * 1024, "Array should be larger than 16MB"

    # Create experiment with the large array
    exp_id = test_db.create_experiment(
        ["numpy_tests"], "large_array_test", {"large_array": large_array}
    )

    # Retrieve the experiment
    experiments = test_db.get_experiments(["numpy_tests", "large_array_test"])

    # Verify the array was correctly stored and retrieved
    assert len(experiments) == 1
    retrieved_experiment = experiments[0]
    print(retrieved_experiment)
    retrieved_data = retrieved_experiment["data"]
    assert "large_array" in retrieved_data

    # Compare the arrays
    retrieved_array = retrieved_data["large_array"]
    assert isinstance(retrieved_array, np.ndarray)
    assert retrieved_array.shape == large_array.shape
    assert retrieved_array.dtype == large_array.dtype
    assert np.allclose(retrieved_array, large_array)


def test_mixed_data_with_arrays(test_db):
    """Test storing and retrieving complex nested data with numpy arrays."""
    # Create a directory
    test_db.create_dir(["complex_data"])

    # Create regular and large arrays
    small_array = np.array([1, 2, 3, 4, 5])
    medium_array = np.random.random((100, 100))  # ~80KB
    large_array = np.random.random((1500, 1500))  # ~18MB

    # Create complex nested data structure
    complex_data = {
        "metadata": {
            "name": "Complex test",
            "timestamp": datetime.now().isoformat(),
            "parameters": {"learning_rate": 0.001, "batch_size": 32},
        },
        "results": {
            "small_array": small_array,
            "medium_array": medium_array,
            "large_array": large_array,
            "metrics": {"accuracy": 0.95, "precision": 0.92, "recall": 0.91},
        },
    }

    # Store the data
    exp_id = test_db.create_experiment(
        ["complex_data"],
        "mixed_data_test",
        complex_data,
        {"note": "Complex experiment with nested numpy arrays of various sizes"},
    )

    # Retrieve the data
    experiments = test_db.get_experiments(["complex_data", "mixed_data_test"])

    # Verify the data was correctly stored and retrieved
    assert len(experiments) == 1
    retrieved_experiment = experiments[0]

    # Check that the note was stored correctly
    assert (
        retrieved_experiment["notes"]["note"]
        == "Complex experiment with nested numpy arrays of various sizes"
    )

    # Get data from the experiment
    retrieved_data = retrieved_experiment["data"]

    # Check nested structure and scalar values
    assert retrieved_data["metadata"]["name"] == "Complex test"
    assert retrieved_data["results"]["metrics"]["accuracy"] == 0.95

    # Check arrays
    retrieved_small = retrieved_data["results"]["small_array"]
    retrieved_medium = retrieved_data["results"]["medium_array"]
    retrieved_large = retrieved_data["results"]["large_array"]

    assert np.array_equal(retrieved_small, small_array)
    assert np.array_equal(retrieved_medium, medium_array)
    assert retrieved_large.shape == large_array.shape
    assert np.allclose(retrieved_large, large_array)


def test_update_experiment_with_array(test_db):
    """Test updating an experiment by adding a large array."""
    # Create a directory
    test_db.create_dir(["update_tests"])

    # Create initial experiment with simple data
    exp_id = test_db.create_experiment(
        ["update_tests"], "update_test", {"initial_value": 42}
    )

    # Create a large array to add
    large_array = np.random.random((1800, 1800))  # ~25MB

    # Add the array to the experiment
    test_db.add_experiment_data(
        ["update_tests", "update_test"], "large_array", large_array
    )

    # Retrieve the updated experiment
    experiments = test_db.get_experiments(["update_tests", "update_test"])

    # Verify both the original data and new array are present
    assert len(experiments) == 1
    retrieved_experiment = experiments[0]
    retrieved_data = retrieved_experiment["data"]

    assert retrieved_data["initial_value"] == 42
    assert "large_array" in retrieved_data

    retrieved_array = retrieved_data["large_array"]
    assert retrieved_array.shape == large_array.shape
    assert np.allclose(retrieved_array, large_array)


def test_path_handling_and_wildcards(test_db):
    """Test path handling with wildcards and various error conditions."""

    # 1. Test invalid path creation attempts

    # Test creating a directory with a wildcard in the name
    with pytest.raises(ValueError, match="invalid characters|Wildcard"):
        test_db.create_dir(["test", "*invalid"])

    with pytest.raises(ValueError, match="invalid characters|Wildcard"):
        test_db.create_dir(["test*invalid"])

    # Test creating a directory with invalid characters
    with pytest.raises(ValueError, match="invalid characters"):
        test_db.create_dir(["test@invalid"])

    # Test creating an empty directory name
    with pytest.raises(ValueError, match="cannot be empty"):
        test_db.create_dir(["test", ""])

    # Test creating a directory at root
    with pytest.raises(Exception, match="Path / already exists"):
        test_db.create_dir([])

    # 2. Test wildcard deletion functionality

    # Create a test directory structure
    test_db.create_dir(["wildcard_test"])
    test_db.create_dir(["wildcard_test", "subdir1"])
    test_db.create_dir(["wildcard_test", "subdir2"])
    test_db.create_experiment(["wildcard_test"], "exp1")
    test_db.create_experiment(["wildcard_test"], "exp2")

    # Verify structure before deletion
    contents = test_db.list_dir(["wildcard_test"])
    assert len(contents) == 4

    # Delete all items using wildcard
    test_db.delete(["wildcard_test", "*"])

    # Verify all contents are deleted but directory remains
    contents = test_db.list_dir(["wildcard_test"])
    assert len(contents) == 0
    assert test_db.dir_exists(["wildcard_test"])

    # Try deleting with wildcard from non-existent directory
    with pytest.raises(Exception, match="does not exist"):
        test_db.delete(["nonexistent", "*"])

    # 3. Test wildcard move functionality

    # Create a source directory with content
    test_db.create_dir(["move_source"])
    test_db.create_dir(["move_source", "dir1"])
    test_db.create_dir(["move_source", "dir2"])
    test_db.create_experiment(["move_source"], "exp1", {"data": "test1"})
    test_db.create_experiment(["move_source"], "exp2", {"data": "test2"})

    # Create a destination directory
    test_db.create_dir(["move_dest"])

    # Move all contents using wildcard
    test_db.move(["move_source", "*"], ["move_dest"])

    # Check source is empty but still exists
    assert len(test_db.list_dir(["move_source"])) == 0

    # Check destination has all items
    dest_contents = test_db.list_dir(["move_dest"])
    assert len(dest_contents) == 4
    assert test_db.dir_exists(["move_dest", "dir1"])
    assert test_db.dir_exists(["move_dest", "dir2"])
    assert test_db.path_exists(["move_dest", "exp1"])
    assert test_db.path_exists(["move_dest", "exp2"])

    # Try moving with wildcard from non-existent directory
    with pytest.raises(Exception, match="does not exist"):
        test_db.move(["nonexistent", "*"], ["move_dest"])

    # Try moving to non-existent destination
    with pytest.raises(Exception, match="must be an existing directory"):
        test_db.move(["move_dest", "*"], ["nonexistent_dest"])

    # 4. Test wildcard in wrong position

    # Try using wildcard in middle of path
    with pytest.raises(Exception, match="Wildcard"):
        test_db.delete(["move_dest", "*", "something"])

    with pytest.raises(Exception, match="Wildcard"):
        test_db.move(["move_dest", "*", "something"], ["somewhere"])
