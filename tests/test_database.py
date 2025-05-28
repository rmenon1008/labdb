import pytest


def test_create_directory(mock_db):
    """Test directory creation"""
    # Create root directory (should already exist)
    assert mock_db.dir_exists("/")

    # Create a new directory
    path = mock_db.create_dir("/test_dir_create")
    assert path == "/test_dir_create"
    assert mock_db.dir_exists("/test_dir_create")

    # Create a nested directory
    path = mock_db.create_dir("/test_dir_create/nested")
    assert path == "/test_dir_create/nested"
    assert mock_db.dir_exists("/test_dir_create/nested")

    # Try to create a directory that already exists
    with pytest.raises(Exception):
        mock_db.create_dir("/test_dir_create")

    # Try to create a directory with a non-existent parent
    with pytest.raises(Exception):
        mock_db.create_dir("/non_existent/test")


def test_create_experiment(mock_db):
    """Test experiment creation"""
    # Create a directory for the experiments
    mock_db.create_dir("/experiments_create")

    # Create an experiment with auto-generated name
    exp_path, exp_id = mock_db.create_experiment("/experiments_create")
    assert exp_path == "/experiments_create/0"
    assert exp_id == "0"

    # Create another experiment with auto-generated name (should increment)
    exp_path, exp_id = mock_db.create_experiment("/experiments_create")
    assert exp_path == "/experiments_create/1"
    assert exp_id == "1"

    # Create an experiment with a specified name
    exp_path, exp_id = mock_db.create_experiment(
        "/experiments_create", name="custom_name"
    )
    assert exp_path == "/experiments_create/custom_name"
    assert exp_id == "custom_name"

    # Try to create an experiment with a name that already exists
    with pytest.raises(Exception):
        mock_db.create_experiment("/experiments_create", name="custom_name")

    # Try to create an experiment in a non-existent directory
    with pytest.raises(Exception):
        mock_db.create_experiment("/non_existent")


def test_experiment_data(mock_db):
    """Test experiment data operations"""
    mock_db.create_dir("/data_test_dir")

    # Create an experiment with initial data
    initial_data = {"key1": "value1", "key2": 42}
    exp_path, _ = mock_db.create_experiment("/data_test_dir", data=initial_data)

    # Get the experiment and check data
    exps = mock_db.get_experiments(exp_path)
    assert len(exps) == 1
    assert exps[0]["data"]["key1"] == "value1"
    assert exps[0]["data"]["key2"] == 42

    # Add more data
    mock_db.add_experiment_data(exp_path, "key3", "value3")
    mock_db.add_experiment_data(exp_path, "key4", [1, 2, 3])

    # Get the updated experiment and check data
    exps = mock_db.get_experiments(exp_path)
    assert len(exps) == 1
    assert exps[0]["data"]["key3"] == "value3"
    assert exps[0]["data"]["key4"] == [1, 2, 3]

    # Override existing data
    mock_db.add_experiment_data(exp_path, "key1", "new_value")
    exps = mock_db.get_experiments(exp_path)
    assert exps[0]["data"]["key1"] == "new_value"


def test_experiment_notes(mock_db):
    """Test experiment notes operations"""
    mock_db.create_dir("/notes_test_dir")

    # Create an experiment with initial notes
    initial_notes = {"note1": "value1", "note2": 42}
    exp_path, _ = mock_db.create_experiment("/notes_test_dir", notes=initial_notes)

    # Get the experiment and check notes
    exps = mock_db.get_experiments(exp_path)
    assert len(exps) == 1
    assert exps[0]["notes"]["note1"] == "value1"
    assert exps[0]["notes"]["note2"] == 42

    # Add more notes
    mock_db.add_experiment_note(exp_path, "note3", "value3")

    # Get the updated experiment and check notes
    exps = mock_db.get_experiments(exp_path)
    assert len(exps) == 1
    assert exps[0]["notes"]["note3"] == "value3"

    # Update all notes
    new_notes = {"new_note": "new_value"}
    mock_db.update_experiment_notes(exp_path, new_notes)

    exps = mock_db.get_experiments(exp_path)
    assert exps[0]["notes"] == new_notes


def test_list_dir(mock_db):
    """Test directory listing"""
    # Create a test directory structure
    mock_db.create_dir("/list_test_dir")
    mock_db.create_dir("/list_test_dir/dir1")
    mock_db.create_dir("/list_test_dir/dir2")

    # Create experiments
    mock_db.create_experiment("/list_test_dir", name="exp1")
    mock_db.create_experiment("/list_test_dir", name="exp2")

    # List the directory
    items = mock_db.list_dir("/list_test_dir")

    # Check that all items are present
    assert len(items) == 4

    # Check types
    dir_count = 0
    exp_count = 0
    for item in items:
        if item["type"] == "directory":
            dir_count += 1
        elif item["type"] == "experiment":
            exp_count += 1

    assert dir_count == 2
    assert exp_count == 2


def test_delete(mock_db):
    """Test deletion of paths"""
    # Create a test directory structure
    mock_db.create_dir("/delete_test_dir")
    mock_db.create_dir("/delete_test_dir/dir1")
    mock_db.create_dir("/delete_test_dir/dir2")
    mock_db.create_experiment("/delete_test_dir", name="exp1")
    mock_db.create_experiment("/delete_test_dir/dir1", name="nested_exp")

    # Delete a single experiment
    mock_db.delete("/delete_test_dir/exp1")
    assert not mock_db.path_exists("/delete_test_dir/exp1")

    # Delete a directory and its contents (recursive)
    mock_db.delete("/delete_test_dir/dir1")
    assert not mock_db.path_exists("/delete_test_dir/dir1")
    assert not mock_db.path_exists("/delete_test_dir/dir1/nested_exp")

    # Delete all contents of a directory using wildcard
    mock_db.delete("/delete_test_dir/*")
    assert mock_db.dir_exists("/delete_test_dir")  # Directory itself still exists
    assert len(mock_db.list_dir("/delete_test_dir")) == 0  # But it's empty


def test_move(mock_db):
    """Test moving of paths"""
    # Create a test directory structure
    mock_db.create_dir("/move_test_dir")
    mock_db.create_dir("/move_test_dir/source")
    mock_db.create_dir("/move_test_dir/dest")
    mock_db.create_experiment("/move_test_dir/source", name="exp1")

    # Move a single experiment
    mock_db.move("/move_test_dir/source/exp1", "/move_test_dir/dest/exp1")
    assert not mock_db.path_exists("/move_test_dir/source/exp1")
    assert mock_db.path_exists("/move_test_dir/dest/exp1")

    # Move all contents using wildcard
    mock_db.create_experiment("/move_test_dir/source", name="exp2")
    mock_db.create_dir("/move_test_dir/source/subdir")

    mock_db.move("/move_test_dir/source/*", "/move_test_dir/dest")
    assert not mock_db.path_exists("/move_test_dir/source/exp2")
    assert not mock_db.path_exists("/move_test_dir/source/subdir")
    assert mock_db.path_exists("/move_test_dir/dest/exp2")
    assert mock_db.path_exists("/move_test_dir/dest/subdir")


def test_get_experiments(mock_db):
    """Test querying experiments"""
    # Create a test directory structure
    mock_db.create_dir("/query_test_dir")
    mock_db.create_dir("/query_test_dir/dir1")
    mock_db.create_dir("/query_test_dir/dir2")

    # Create experiments with different data
    mock_db.create_experiment(
        "/query_test_dir", name="exp1", data={"value": 10}, notes={"category": "A"}
    )
    mock_db.create_experiment(
        "/query_test_dir", name="exp2", data={"value": 20}, notes={"category": "B"}
    )
    mock_db.create_experiment(
        "/query_test_dir/dir1", name="exp3", data={"value": 30}, notes={"category": "A"}
    )

    # Test non-recursive query (only direct children)
    exps = mock_db.get_experiments("/query_test_dir", recursive=False)
    assert len(exps) == 2

    # Test recursive query (all descendants)
    exps = mock_db.get_experiments("/query_test_dir", recursive=True)
    assert len(exps) == 3

    # Test with additional query conditions
    exps = mock_db.get_experiments(
        "/query_test_dir", recursive=True, query={"notes.category": "A"}
    )
    assert len(exps) == 2

    # Test with projection
    exps = mock_db.get_experiments(
        "/query_test_dir", recursive=False, projection={"notes": 1, "_id": 0}
    )
    assert len(exps) == 2
    assert "notes" in exps[0]
    assert "data" not in exps[0]

    # Test with sorting
    exps = mock_db.get_experiments(
        "/query_test_dir", recursive=True, sort=[("data.value", 1)]
    )
    assert exps[0]["data"]["value"] == 10
    assert exps[1]["data"]["value"] == 20
    assert exps[2]["data"]["value"] == 30

    # Test with limit
    exps = mock_db.get_experiments("/query_test_dir", recursive=True, limit=2)
    assert len(exps) == 2


def test_experiment_id_generation(mock_db):
    """Test experiment ID generation with deletions"""
    # Create a directory for testing
    mock_db.create_dir("/id_test_dir")

    # Test case 1: No experiments exist, should start with 0
    exp_path, exp_id = mock_db.create_experiment("/id_test_dir")
    assert exp_id == "0"
    assert exp_path == "/id_test_dir/0"

    # Test case 2: Create sequential experiments
    exp_path, exp_id = mock_db.create_experiment("/id_test_dir")
    assert exp_id == "1"
    assert exp_path == "/id_test_dir/1"

    exp_path, exp_id = mock_db.create_experiment("/id_test_dir")
    assert exp_id == "2"
    assert exp_path == "/id_test_dir/2"

    # Test case 3: Delete experiment in the middle
    mock_db.delete("/id_test_dir/1")

    # Next experiment should use max + 1 (not fill the gap)
    exp_path, exp_id = mock_db.create_experiment("/id_test_dir")
    assert exp_id == "3"  # Should be 3, not 1 (gap filling)
    assert exp_path == "/id_test_dir/3"

    # Test case 4: Mix of numeric and non-numeric experiments
    mock_db.create_experiment("/id_test_dir", name="custom_exp")
    exp_path, exp_id = mock_db.create_experiment("/id_test_dir")
    assert exp_id == "4"  # Should ignore non-numeric experiments

    # Test case 5: Delete all numeric experiments
    mock_db.delete("/id_test_dir/0")
    mock_db.delete("/id_test_dir/2")
    mock_db.delete("/id_test_dir/3")
    mock_db.delete("/id_test_dir/4")

    # Should start from 0 again when no numeric experiments exist
    exp_path, exp_id = mock_db.create_experiment("/id_test_dir")
    assert exp_id == "0"
    assert exp_path == "/id_test_dir/0"

    # Test case 6: Direct call to get_next_experiment_id
    next_id = mock_db.get_next_experiment_id("/id_test_dir")
    assert next_id == "1"  # Should be 1 since we have 0

    # Test case 7: Empty directory
    mock_db.create_dir("/empty_id_test")
    next_id = mock_db.get_next_experiment_id("/empty_id_test")
    assert next_id == "0"  # Should start with 0 for empty directory


def test_range_patterns(mock_db):
    """Test range pattern expansion for both dash and comma-separated patterns"""
    # Create test directory structure
    mock_db.create_dir("/pattern_test")
    mock_db.create_dir("/pattern_test/exp1")
    mock_db.create_dir("/pattern_test/exp2")
    mock_db.create_dir("/pattern_test/exp3")
    mock_db.create_dir("/pattern_test/exp5")
    mock_db.create_dir("/pattern_test/exp7")

    # Create experiments in each directory
    mock_db.create_experiment("/pattern_test/exp1", name="data", data={"value": 1})
    mock_db.create_experiment("/pattern_test/exp2", name="data", data={"value": 2})
    mock_db.create_experiment("/pattern_test/exp3", name="data", data={"value": 3})
    mock_db.create_experiment("/pattern_test/exp5", name="data", data={"value": 5})
    mock_db.create_experiment("/pattern_test/exp7", name="data", data={"value": 7})

    # Test dash range pattern (existing functionality)
    exps = mock_db.get_experiments("/pattern_test/exp$(1-3)/data")
    assert len(exps) == 3
    values = sorted([exp["data"]["value"] for exp in exps])
    assert values == [1, 2, 3]

    # Test comma-separated pattern (new functionality)
    exps = mock_db.get_experiments("/pattern_test/exp$(1,3,5)/data")
    assert len(exps) == 3
    values = sorted([exp["data"]["value"] for exp in exps])
    assert values == [1, 3, 5]

    # Test comma-separated pattern with spaces
    exps = mock_db.get_experiments("/pattern_test/exp$(1, 3, 5)/data")
    assert len(exps) == 3
    values = sorted([exp["data"]["value"] for exp in exps])
    assert values == [1, 3, 5]

    # Test comma-separated pattern with different order
    exps = mock_db.get_experiments("/pattern_test/exp$(5,1,3)/data")
    assert len(exps) == 3
    values = sorted([exp["data"]["value"] for exp in exps])
    assert values == [1, 3, 5]

    # Test comma-separated pattern with duplicates (should not duplicate results)
    exps = mock_db.get_experiments("/pattern_test/exp$(1,1,3,3)/data")
    assert len(exps) == 2  # Should not include duplicates in expansion
    values = sorted([exp["data"]["value"] for exp in exps])
    assert values == [1, 3]

    # Test comma-separated pattern with non-existent paths
    exps = mock_db.get_experiments("/pattern_test/exp$(1,4,5)/data")
    assert len(exps) == 2  # Only exp1 and exp5 exist, exp4 doesn't
    values = sorted([exp["data"]["value"] for exp in exps])
    assert values == [1, 5]

    # Test list of paths with comma-separated patterns
    paths = ["/pattern_test/exp$(1,3)/data", "/pattern_test/exp$(5,7)/data"]
    exps = mock_db.get_experiments(paths)
    assert len(exps) == 4
    values = sorted([exp["data"]["value"] for exp in exps])
    assert values == [1, 3, 5, 7]

    # Test nested patterns (comma-separated in directory and experiment names)
    mock_db.create_dir("/pattern_test/dir1")
    mock_db.create_dir("/pattern_test/dir3")
    mock_db.create_experiment("/pattern_test/dir1", name="exp1", data={"nested": 11})
    mock_db.create_experiment("/pattern_test/dir3", name="exp3", data={"nested": 33})

    exps = mock_db.get_experiments("/pattern_test/dir$(1,3)/exp$(1,3)")
    assert len(exps) == 2
    values = sorted([exp["data"]["nested"] for exp in exps])
    assert values == [11, 33]


def test_expand_paths_method(mock_db):
    """Test the _expand_paths method directly"""
    # Test dash range expansion
    expanded = mock_db._expand_paths(["/test/exp$(1-3)"])
    assert expanded == ["/test/exp1", "/test/exp2", "/test/exp3"]

    # Test comma-separated expansion
    expanded = mock_db._expand_paths(["/test/exp$(1,3,5)"])
    assert expanded == ["/test/exp1", "/test/exp3", "/test/exp5"]

    # Test comma-separated with spaces
    expanded = mock_db._expand_paths(["/test/exp$(1, 3, 5)"])
    assert expanded == ["/test/exp1", "/test/exp3", "/test/exp5"]

    # Test multiple patterns in one path
    expanded = mock_db._expand_paths(["/test/exp$(1,2)/sub$(3,4)"])
    expected = [
        "/test/exp1/sub3",
        "/test/exp1/sub4",
        "/test/exp2/sub3",
        "/test/exp2/sub4",
    ]
    assert sorted(expanded) == sorted(expected)

    # Test mixed pattern types
    paths = ["/test/exp$(1-2)", "/test/exp$(5,7)"]
    expanded = mock_db._expand_paths(paths)
    expected = ["/test/exp1", "/test/exp2", "/test/exp5", "/test/exp7"]
    assert sorted(expanded) == sorted(expected)

    # Test no patterns (should return as-is)
    expanded = mock_db._expand_paths(["/test/exp1", "/test/exp2"])
    assert expanded == ["/test/exp1", "/test/exp2"]

    # Test invalid patterns (should return as-is)
    expanded = mock_db._expand_paths(["/test/exp$(invalid)"])
    assert expanded == ["/test/exp$(invalid)"]

    # Test empty list
    expanded = mock_db._expand_paths([])
    assert expanded == []
