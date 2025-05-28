import datetime
import random
import string
import uuid


def _short_id():
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(15))


def short_directory_id():
    return "d" + _short_id()


def short_experiment_id():
    return "e" + _short_id()


def long_id():
    return str(uuid.uuid4())


def merge_dicts(dict1, dict2):
    if dict1 is None:
        dict1 = {}
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
            merge_dicts(dict1[key], value)
        else:
            dict1[key] = value
    return dict1


def date_to_relative_time(date):
    now = datetime.datetime.now()
    diff = now - date

    seconds = diff.total_seconds()

    if seconds < 60:
        return f"{int(seconds)} {'second' if int(seconds) == 1 else 'seconds'} ago"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} {'minute' if minutes == 1 else 'minutes'} ago"
    elif seconds < 43200:  # 12 hours
        hours = int(seconds // 3600)
        return f"{hours} {'hour' if hours == 1 else 'hours'} ago"
    else:
        return date.strftime("%b %d, %Y at %I:%M %p").replace(" 0", " ")


ALLOWED_PATH_CHARS = (
    string.ascii_lowercase + string.ascii_uppercase + string.digits + ".-_/*$()"
)


def split_path(path: str):
    """
    Split a string path into a list of segments.
    Consider using string paths directly when possible.

    Args:
        path: A path string starting with a slash

    Returns:
        A list of path segments
    """
    if not isinstance(path, str):
        raise TypeError("Path must be a string")
    if not path.startswith("/"):
        raise ValueError("Path must start with a slash")

    # Special handling for wildcard - only allowed as standalone at end of path
    if "*" in path and not path.endswith("/*"):
        raise ValueError(
            "Wildcard (*) can only be used as a standalone character at the end of a path"
        )

    if not all(char in ALLOWED_PATH_CHARS for char in path):
        raise ValueError("Path contains invalid characters")

    split = path.split("/")
    # Filter out empty segments (handles consecutive slashes)
    split = [s for s in split if s]
    return split


def join_path(path_segments):
    """
    Join path segments into a string path.

    Args:
        path_segments: List of path segments or a single string (returned as-is if valid)

    Returns:
        A string path starting with a slash
    """
    # If already a string, validate and return it
    if isinstance(path_segments, str):
        if not path_segments.startswith("/"):
            raise ValueError("String path must start with a slash")
        # Validate path
        split_path(path_segments)
        return path_segments

    if not all(isinstance(s, str) for s in path_segments):
        raise TypeError("All path segments must be strings")
    if any(not s for s in path_segments):  # Check for empty segments
        raise ValueError("Path segments cannot be empty strings")

    # Special handling for wildcard - check this BEFORE general character validation
    for i, segment in enumerate(path_segments):
        if "*" in segment:
            if i != len(path_segments) - 1 or segment != "*":
                raise ValueError(
                    "Wildcard (*) can only be used as a standalone character at the end of a path"
                )

    # Now check other invalid characters excluding the wildcard which has already been validated
    for segment in path_segments:
        for char in segment:
            if char != "*" and char not in ALLOWED_PATH_CHARS:
                raise ValueError("Path segments contain invalid characters")

    return "/" + "/".join(path_segments)


def validate_path(path: str | list[str]):
    """
    Validate a path meets the formatting requirements.

    Args:
        path: A string path or list of path segments
    """
    # Convert to string path if it's a list
    if isinstance(path, list):
        path_str = join_path(path)
    else:
        path_str = path

    # Validate by splitting and joining
    segments = split_path(path_str)
    joined = join_path(segments)

    # Check if the path is unchanged after normalize
    if joined != path_str:
        raise ValueError(f"Path failed validation: {path_str} -> {joined}")

    # Check for wildcards
    if "*" in path_str and not path_str.endswith("/*"):
        raise ValueError(
            "Wildcard (*) can only be used as a standalone character at the end of a path"
        )


def resolve_path(current_path: str, target_path: str) -> str:
    """
    Resolve a target path against the current path, handling:
    - Absolute paths (starting with slash)
    - Relative paths (not starting with slash)
    - Parent directory references (..)
    - Trailing slashes (normalized away)

    Args:
        current_path: The current directory path as a string
        target_path: The target path to resolve as a string

    Returns:
        The resolved path as a string
    """
    # Remove trailing slashes except for root path "/"
    if target_path.endswith("/") and target_path != "/":
        target_path = target_path.rstrip("/")

    if current_path.endswith("/") and current_path != "/":
        current_path = current_path.rstrip("/")

    # Handle absolute paths
    if target_path.startswith("/"):
        # Return the target path directly
        try:
            # Validate by splitting and re-joining
            segments = split_path(target_path)
            return join_path(segments)
        except Exception as e:
            raise ValueError(f"Invalid absolute path: {e}")

    # For relative path, first get the current path segments
    current_segments = split_path(current_path)

    # Split the target path for processing
    target_segments = [s for s in target_path.split("/") if s]

    # Check for wildcards in target_segments (except as standalone at end)
    for i, segment in enumerate(target_segments):
        if "*" in segment:
            if i != len(target_segments) - 1 or segment != "*":
                raise ValueError(
                    "Wildcard (*) can only be used as a standalone character at the end of a path"
                )

    # Start with the current path for relative paths
    result_segments = current_segments.copy()

    # Process each segment
    for segment in target_segments:
        if segment == "..":
            # Go up one directory level
            if result_segments:
                result_segments.pop()
        elif segment and segment != ".":
            # Skip empty segments and current directory references
            # Validate segment characters
            if not all(char in ALLOWED_PATH_CHARS for char in segment):
                raise ValueError(
                    f"Path segment '{segment}' contains invalid characters"
                )
            result_segments.append(segment)

    # Return as string path
    return join_path(result_segments)


def is_parent_path(parent_path: str, child_path: str) -> bool:
    """
    Check if one path is a parent of another.

    Args:
        parent_path: Potential parent path
        child_path: Potential child path

    Returns:
        True if parent_path is a parent of child_path
    """
    if parent_path == "/":
        return child_path != "/"

    parent_with_slash = parent_path if parent_path.endswith("/") else parent_path + "/"
    return child_path.startswith(parent_with_slash)


def get_path_name(path: str) -> str:
    """
    Get the name component of a path (last segment).

    Args:
        path: A string path

    Returns:
        The last segment of the path
    """
    segments = split_path(path)
    return segments[-1] if segments else ""


def get_parent_path(path: str) -> str:
    """
    Get the parent path of the given path.

    Args:
        path: A string path

    Returns:
        The parent path as a string
    """
    if path == "/":
        return "/"

    segments = split_path(path)
    if len(segments) <= 1:
        return "/"

    return join_path(segments[:-1])


def escape_regex_path(path: str) -> str:
    """
    Escape special regex characters in a path for safe use in regex patterns.

    Args:
        path: A string path to escape

    Returns:
        Escaped path safe for use in regex patterns
    """
    special_chars = ".^$*+?()[]{}|\\-"
    result = ""
    for char in path:
        if char in special_chars:
            result += f"\\{char}"
        else:
            result += char
    return result


def merge_mongo_queries(base_query: dict, additional_query: dict) -> dict:
    """
    Intelligently merge MongoDB queries, handling special operators like $expr and $and.

    Args:
        base_query: The original query to merge into
        additional_query: Additional query conditions to apply

    Returns:
        A merged query combining both inputs
    """
    if not additional_query:
        return base_query

    result = base_query.copy()
    query = additional_query.copy()

    # Handle special case for $expr operator
    if "$expr" in result and "$expr" in query:
        base_expr = result["$expr"]
        query_expr = query.pop("$expr")

        if "$and" in base_expr and "$and" in query_expr:
            # Combine the $and conditions
            base_expr["$and"].extend(query_expr["$and"])
        elif "$and" in base_expr:
            # Add the query expression to the base $and array
            base_expr["$and"].append(query_expr)
        else:
            # Convert both expressions to an $and
            result["$expr"] = {"$and": [base_expr, query_expr]}

    # Merge the rest of the query
    for key, value in query.items():
        if key in result:
            # If key exists in both, we need more complex merging
            if isinstance(result[key], dict) and isinstance(value, dict):
                # For nested dictionaries, recursively merge them
                result[key] = merge_mongo_queries(result[key], value)
            elif isinstance(result[key], list) and isinstance(value, list):
                # For lists, extend the base list
                result[key].extend(value)
            else:
                # For conflicting simple values, prefer the additional query param
                result[key] = value
        else:
            # Simple addition of the query parameter
            result[key] = value

    return result


def dict_str(d: dict):
    return ", ".join([f"{key}: {value}" for key, value in d.items()])

def best_effort_serialize(obj):
    if isinstance(obj, dict):

        if any("__numpy_array__" in str(key) for key in obj.keys()):
            result = "[Numpy Array]"
            return result

        result = {}
        for key, value in obj.items():
            try:
                # Try to serialize the value
                result[key] = best_effort_serialize(value)
            except (TypeError, ValueError):
                # If serialization fails, use string representation
                result[key] = str(type(value).__name__)
        return result
    elif isinstance(obj, list):
        result = []
        for item in obj:
            try:
                result.append(best_effort_serialize(item))
            except (TypeError, ValueError):
                result.append(str(type(item).__name__))
        return result
    else:
        try:
            # Try to serialize directly
            import json
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            # Return type name if not serializable
            return str(type(obj).__name__)
