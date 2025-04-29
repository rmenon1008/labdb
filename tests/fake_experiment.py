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
logger = ExperimentLogger("/test", notes_mode="none")

for i in range(5):
    experiment_id = logger.new_experiment()

    # Set some values
    t = np.float32
    size = 100_000_000
    numpy_array = np.empty(size, dtype=t)
    numpy_array.fill(0.5)  # Fill with a constant value (fastest option)
    logger.log_data("test", numpy_array)
    logger.log_note("notes", "This is a test experiment")

    # Expected size is 100_000_000 * 4 / 1024 / 1024 = 381.47 MB

# Disable profiler and print stats
profiler.disable()
s = StringIO()
ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
ps.print_stats(20)  # Print top 20 functions by cumulative time
print(s.getvalue())
