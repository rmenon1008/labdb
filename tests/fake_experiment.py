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
logger = ExperimentLogger(session_id="ssytvfsvc3")

for i in range(10):
    experiment_id = logger.new_experiment(interactive=False)

    # Set some values
    t = np.int32
    size = 10_000_000
    numpy_array = np.random.randint(np.iinfo(t).min, np.iinfo(t).max, size=size, dtype=t)
    logger.log_data("test", numpy_array)
    logger.log_note("notes", "This is a test experiment")

# Disable profiler and print stats
profiler.disable()
s = StringIO()
ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
ps.print_stats(20)  # Print top 20 functions by cumulative time
print(s.getvalue())
