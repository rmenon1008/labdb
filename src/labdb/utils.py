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
        return date.strftime("%B %d, %Y at %I:%M %p").replace(" 0", " ")


ALLOWED_PATH_CHARS = string.ascii_lowercase + string.digits + ".-_/*"


def split_path(path: str):
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


def join_path(split: list[str]):
    if not all(isinstance(s, str) for s in split):
        raise TypeError("All path segments must be strings")
    if any(not s for s in split):  # Check for empty segments
        raise ValueError("Path segments cannot be empty strings")

    # Special handling for wildcard - check this BEFORE general character validation
    for i, segment in enumerate(split):
        if "*" in segment:
            if i != len(split) - 1 or segment != "*":
                raise ValueError(
                    "Wildcard (*) can only be used as a standalone character at the end of a path"
                )

    # Now check other invalid characters excluding the wildcard which has already been validated
    for segment in split:
        for char in segment:
            if char != "*" and char not in ALLOWED_PATH_CHARS:
                raise ValueError("Path segments contain invalid characters")

    return "/" + "/".join(split)


def validate_path(path: list[str]):
    # Check for wildcard in non-final positions or embedded in names
    for i, segment in enumerate(path):
        if "*" in segment:
            if i != len(path) - 1 or segment != "*":
                raise ValueError(
                    f"Wildcard (*) can only be used as a standalone character in the last position of a path"
                )

    # Only validate joined path if no wildcards are present
    # or if the only wildcard is in the last position and is exactly "*"
    if not (len(path) > 0 and path[-1] == "*"):
        try:
            split = split_path(join_path(path))
            assert split == path
        except ValueError as e:
            # Re-raise with more specific error about wildcards if appropriate
            if "*" in str(e):
                raise ValueError(
                    f"Wildcard (*) can only be used as a standalone character in the last position of a path"
                )
            raise


def resolve_path(current_path: list[str], target_path: str | list[str]) -> list[str]:
    """
    Resolve a target path against the current path, handling:
    - Absolute paths (starting with slash)
    - Relative paths (not starting with slash)
    - Parent directory references (..)

    Args:
        current_path: The current directory path as a list of segments
        target_path: The target path to resolve (string or list)

    Returns:
        The resolved path as a list of segments
    """
    # Handle absolute paths as strings (starting with /)
    if isinstance(target_path, str) and target_path.startswith("/"):
        try:
            return split_path(target_path)
        except Exception as e:
            raise ValueError(f"Invalid absolute path: {e}")

    # Convert target_path to segments if it's a relative path string
    if isinstance(target_path, str):
        target_segments = [s for s in target_path.split("/") if s]
    else:
        # Already a list
        target_segments = target_path

    # Check for wildcards in target_segments (except as standalone at end)
    for i, segment in enumerate(target_segments):
        if "*" in segment:
            if i != len(target_segments) - 1 or segment != "*":
                raise ValueError(
                    f"Wildcard (*) can only be used as a standalone character at the end of a path"
                )

    # Start with the current path for relative paths
    result_path = current_path.copy()

    # Process each segment
    for segment in target_segments:
        if segment == "..":
            # Go up one directory level
            if result_path:
                result_path.pop()
        elif segment and segment != ".":
            # Skip empty segments and current directory references
            # Validate segment characters
            if not all(char in ALLOWED_PATH_CHARS for char in segment):
                raise ValueError(
                    f"Path segment '{segment}' contains invalid characters"
                )
            result_path.append(segment)

    return result_path


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
