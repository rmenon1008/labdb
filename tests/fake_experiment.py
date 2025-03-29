import cProfile
import pstats
import time
from io import StringIO

import numpy as np

from labdb.api import ExperimentLogger

# Create a profiler
profiler = cProfile.Profile()
profiler.enable()

# Create a new experiment
logger = ExperimentLogger(ask_for_outputs=False, session_id="1al4sf42")
experiment_id = logger.experiment["_id"]

# Set some values
t = np.int32
size = 100_000_000
numpy_array = np.random.randint(np.iinfo(t).min, np.iinfo(t).max, size=size, dtype=t)
logger.set("test", numpy_array)
logger.set("notes", "This is a test experiment")

# Get values back
array_value = logger.get("test")
notes = logger.get("notes")
print(f"Retrieved notes: {notes}")

# Edit the experiment
logger.edit()

# Create a new logger instance to access the same experiment
logger2 = ExperimentLogger(experiment_id=experiment_id)
array_value2 = logger2.get("test")
print(f"Retrieved array from new logger: {array_value2}")

# Disable profiler and print stats
profiler.disable()
s = StringIO()
ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
ps.print_stats(20)  # Print top 20 functions by cumulative time
print(s.getvalue())
