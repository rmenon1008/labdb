import random
import string
from datetime import datetime


def short_id():
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(8))


def merge_dicts(dict1, dict2):
    """Merge two dictionaries recursively"""
    # Initialize dict1 as empty dict if it's None
    if dict1 is None:
        dict1 = {}
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
            merge_dicts(dict1[key], value)
        else:
            dict1[key] = value
    return dict1
