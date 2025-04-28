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


ALLOWED_PATH_CHARS = string.ascii_lowercase + string.digits + ".-_/"


def split_path(path: str):
    if not isinstance(path, str):
        raise TypeError("Path must be a string")
    if not path.startswith("/"):
        raise ValueError("Path must start with a slash")
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
    if any(not all(char in ALLOWED_PATH_CHARS for char in s) for s in split):
        raise ValueError("Path segments contain invalid characters")
    return "/" + "/".join(split)


def validate_path(path: list[str]):
    split = split_path(join_path(path))
    assert split == path


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
