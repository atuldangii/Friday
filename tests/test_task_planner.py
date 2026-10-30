"""
Unit tests for TaskPlanner multi-step command decomposition and execution.
"""

import pytest
from core.task_planner import TaskPlanner


def dummy_executor(action):
    return True, f"Executed {action.action_type}"


@pytest.fixture
def planner():
    return TaskPlanner(action_executor=dummy_executor)


def test_decompose_compound_command(planner):
    compound = "open Chrome, search for the best Python tutorials, and calculate 250 * 48"
    steps = planner.decompose(compound)
    assert len(steps) == 3
    assert "chrome" in steps[0].lower()
    assert "search for" in steps[1].lower()
    assert "calculate" in steps[2].lower()


def test_single_command_decomposition(planner):
    steps = planner.decompose("open calculator")
    assert len(steps) == 1
    assert steps[0] == "open calculator"


def test_cancel_plan(planner):
    planner.cancel()
    assert planner._is_cancelled is True
