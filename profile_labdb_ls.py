#!/usr/bin/env python
import cProfile
import io
import pstats
import sys
import time
from argparse import Namespace

# Import the necessary functions from labdb
from labdb.cli import cli_ls


def profile_ls(path=None):
    """Profile the labdb ls command with optional path argument"""
    # Create args object similar to what argparse would create
    args = Namespace()
    args.path = path

    # First, measure the total time with simple timing
    start_time = time.time()
    cli_ls(args)
    total_time = time.time() - start_time
    print(f"\nTotal execution time: {total_time:.4f} seconds")

    # Now run the profiler for detailed analysis
    print("\nDetailed profile analysis:")
    pr = cProfile.Profile()
    pr.enable()

    # Run the ls command
    cli_ls(args)

    # Disable profiler and print stats
    pr.disable()
    s = io.StringIO()

    # Sort by cumulative time
    print("\nTop functions by cumulative time:")
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(20)
    print(s.getvalue())

    # Sort by internal time
    s = io.StringIO()
    print("\nTop functions by internal time:")
    ps = pstats.Stats(pr, stream=s).sort_stats("time")
    ps.print_stats(20)
    print(s.getvalue())

    # Sort by number of calls
    s = io.StringIO()
    print("\nTop functions by call count:")
    ps = pstats.Stats(pr, stream=s).sort_stats("calls")
    ps.print_stats(20)
    print(s.getvalue())


if __name__ == "__main__":
    # Get path from command line args if provided
    path = sys.argv[1] if len(sys.argv) > 1 else None
    profile_ls(path)
