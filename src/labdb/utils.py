import datetime
import random
import string
import uuid


def _short_id():
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(9))


def short_session_id():
    return "s" + _short_id()


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
