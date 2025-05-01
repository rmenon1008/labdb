import string

import pytest

from labdb.utils import (
    ALLOWED_PATH_CHARS,
    join_path,
    resolve_path,
    split_path,
    validate_path,
)


class TestPathSplitting:
    def test_basic_path_splitting(self):
        """Test basic path splitting functionality"""
        assert split_path("/a/b/c") == ["a", "b", "c"]
        assert split_path("/single") == ["single"]
        assert split_path("/") == []

    def test_path_splitting_with_consecutive_slashes(self):
        """Test splitting paths with consecutive slashes"""
        assert split_path("/a//b///c") == ["a", "b", "c"]
        assert split_path("////a/b") == ["a", "b"]

    def test_invalid_path_splitting(self):
        """Test splitting invalid paths"""
        # Path must be a string
        with pytest.raises(TypeError, match="must be a string"):
            split_path(123)

        # Path must start with a slash
        with pytest.raises(ValueError, match="must start with a slash"):
            split_path("a/b/c")

        # Path must only contain allowed characters
        with pytest.raises(ValueError, match="invalid characters"):
            split_path("/a/b@/c")

    def test_wildcard_path_splitting(self):
        """Test splitting paths with wildcards"""
        # Wildcard at the end is valid
        assert split_path("/a/b/*") == ["a", "b", "*"]

        # Wildcard in the middle or embedded in a name is invalid
        with pytest.raises(ValueError, match="Wildcard"):
            split_path("/a/*/c")

        with pytest.raises(ValueError, match="Wildcard"):
            split_path("/a/b*c")


class TestPathJoining:
    def test_basic_path_joining(self):
        """Test basic path joining functionality"""
        assert join_path(["a", "b", "c"]) == "/a/b/c"
        assert join_path(["single"]) == "/single"
        assert join_path([]) == "/"

    def test_invalid_path_joining(self):
        """Test joining invalid paths"""
        # Path segments must be strings
        with pytest.raises(TypeError, match="must be strings"):
            join_path(["a", 123, "c"])

        # Path segments cannot be empty
        with pytest.raises(ValueError, match="cannot be empty"):
            join_path(["a", "", "c"])

        # Path segments must only contain allowed characters
        with pytest.raises(ValueError, match="invalid characters"):
            join_path(["a", "b@", "c"])

    def test_wildcard_path_joining(self):
        """Test joining paths with wildcards"""
        # Wildcard at the end is valid
        assert join_path(["a", "b", "*"]) == "/a/b/*"

        # Wildcard in the middle is invalid
        with pytest.raises(ValueError, match="Wildcard"):
            join_path(["a", "*", "c"])

        # Embedded wildcard is invalid
        with pytest.raises(ValueError, match="Wildcard"):
            join_path(["a", "b*c"])


class TestPathValidation:
    def test_valid_paths(self):
        """Test validation of valid paths"""
        # These should not raise exceptions
        validate_path(["a", "b", "c"])
        validate_path(["single"])
        validate_path([])
        validate_path(["a", "b", "*"])  # Valid wildcard at end

    def test_invalid_paths(self):
        """Test validation of invalid paths"""
        # Wildcard in the middle
        with pytest.raises(ValueError, match="Wildcard"):
            validate_path(["a", "*", "c"])

        # Embedded wildcard
        with pytest.raises(ValueError, match="Wildcard"):
            validate_path(["a", "b*c"])

        # Invalid characters
        with pytest.raises(ValueError, match="invalid characters"):
            validate_path(["a", "b@", "c"])


class TestPathResolution:
    def test_absolute_path_resolution(self):
        """Test resolution of absolute paths"""
        current_path = ["x", "y", "z"]

        # Absolute paths ignore the current path
        assert resolve_path(current_path, "/a/b/c") == ["a", "b", "c"]
        assert resolve_path(current_path, "/") == []

    def test_relative_path_resolution(self):
        """Test resolution of relative paths"""
        current_path = ["x", "y", "z"]

        # Simple relative paths are appended to current path
        assert resolve_path(current_path, "a/b") == ["x", "y", "z", "a", "b"]
        assert resolve_path(current_path, ["a", "b"]) == ["x", "y", "z", "a", "b"]

        # Parent directory references (..)
        assert resolve_path(current_path, "..") == ["x", "y"]
        assert resolve_path(current_path, "../a") == ["x", "y", "a"]
        assert resolve_path(current_path, "../../a") == ["x", "a"]

        # Current directory references (.) should be ignored
        assert resolve_path(current_path, "./a") == ["x", "y", "z", "a"]

        # Too many parent references should not go above root
        assert resolve_path(["x"], "../../a") == ["a"]

    def test_wildcard_path_resolution(self):
        """Test resolution of paths with wildcards"""
        current_path = ["x", "y", "z"]

        # Wildcard at the end is valid
        assert resolve_path(current_path, "*/") == ["x", "y", "z", "*"]
        assert resolve_path(current_path, "../*") == ["x", "y", "*"]

        # Wildcard in the middle or embedded should fail
        with pytest.raises(ValueError, match="Wildcard.*only.*end"):
            resolve_path(current_path, "a/*/b")

        with pytest.raises(ValueError, match="Wildcard.*only.*end"):
            resolve_path(current_path, "a*b")


class TestEdgeCases:
    def test_allowed_characters(self):
        """Test all allowed characters in paths"""
        # Test lowercase letters
        for char in string.ascii_lowercase:
            assert join_path([f"test{char}"]) == f"/test{char}"

        # Test digits
        for char in string.digits:
            assert join_path([f"test{char}"]) == f"/test{char}"

        # Test special characters
        for char in ".-_":
            assert join_path([f"test{char}"]) == f"/test{char}"

    def test_disallowed_characters(self):
        """Test disallowed characters in paths"""
        disallowed = set(string.printable) - set(ALLOWED_PATH_CHARS)

        for char in disallowed:
            if char == "*":  # Skip wildcard which is handled separately
                continue

            with pytest.raises(ValueError, match="invalid characters"):
                join_path([f"test{char}"])

    def test_join_split_roundtrip(self):
        """Test that joining and then splitting returns the original path"""
        paths = [[], ["single"], ["a", "b", "c"], ["a", "b", "*"]]

        for path in paths:
            joined = join_path(path)
            split = split_path(joined)
            assert split == path

    def test_split_join_roundtrip(self):
        """Test that splitting and then joining returns the original path"""
        paths = ["/", "/single", "/a/b/c", "/a/b/*"]

        for path in paths:
            split = split_path(path)
            joined = join_path(split)
            assert joined == path
