import cProfile
import pstats
import time
from io import StringIO

import numpy as np

from labdb.api import ExperimentQuery

# Create a profiler
profiler = cProfile.Profile()
profiler.enable()


query = ExperimentQuery()

# Get all experiments from the most recent session
experiments = query.get_all_from_session("1al4sf42")

# Access the numpy arrays from each experiment
for exp in experiments:
    start_time = time.time()

    if "outputs" in exp and "test" in exp["outputs"]:
        numpy_array = exp["outputs"]["test"]
        # Do something with the array to ensure it's loaded
        array_sum = np.sum(numpy_array)
        print(f"Experiment {exp['_id']}: Array sum = {array_sum}")

    elapsed = time.time() - start_time
    print(f"Iteration completed in {elapsed:.2f} seconds")

# Disable profiler and print stats
profiler.disable()
s = StringIO()
ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
ps.print_stats(20)  # Print top 20 functions by cumulative time
print(s.getvalue())
