"""
Performance Benchmark Suite for FRIDAY AI Multi-Step Commands.
Measures execution time for compound and local intent commands.
"""

import time
import pytest
from core.assistant import FridayCore


def test_benchmark_multi_step_calculator():
    core = FridayCore()
    t0 = time.perf_counter()
    res = core.process_command("calculate 250 multiplied by 48")
    t1 = time.perf_counter()
    duration_ms = (t1 - t0) * 1000

    print(f"\n[BENCHMARK] 'calculate 250 multiplied by 48': {duration_ms:.2f}ms | Result: {res}")
    assert "12,000" in res or "12000" in res
    assert duration_ms < 500  # Local evaluation should complete in under 500ms


def test_benchmark_compound_math_command():
    core = FridayCore()
    t0 = time.perf_counter()
    res = core.process_command("open Calculator and calculate 125 * 8")
    t1 = time.perf_counter()
    duration_ms = (t1 - t0) * 1000

    print(f"\n[BENCHMARK] 'open Calculator and calculate 125 * 8': {duration_ms:.2f}ms | Result: {res}")
    assert duration_ms < 3000


def test_benchmark_decomposition_speed():
    core = FridayCore()
    t0 = time.perf_counter()
    steps = core.planner.decompose("Open Chrome, search for Python tutorials, and open YouTube")
    t1 = time.perf_counter()
    duration_ms = (t1 - t0) * 1000

    print(f"\n[BENCHMARK] Decompose 3-step command: {duration_ms:.2f}ms | Steps: {steps}")
    assert len(steps) == 3
    assert duration_ms < 5  # Parsing should be sub-5ms
