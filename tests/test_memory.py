"""
Unit tests for MemoryManager SQLite store.
"""

import pytest
from core.memory import MemoryManager


@pytest.fixture
def memory():
    mem = MemoryManager()
    mem.clear_all()
    return mem


def test_set_and_get_memory(memory):
    memory.set_memory("preferences", "favorite_browser", "chrome")
    val = memory.get_memory("favorite_browser")
    assert val == "chrome"


def test_delete_memory(memory):
    memory.set_memory("facts", "project_dir", "C:/Projects")
    assert memory.get_memory("project_dir") == "C:/Projects"
    memory.delete_memory("project_dir")
    assert memory.get_memory("project_dir") is None


def test_interaction_history(memory):
    memory.log_interaction("open calculator", "Launched calculator successfully.")
    history = memory.get_recent_interactions(limit=5)
    assert len(history) >= 1
    assert history[0]["command"] == "open calculator"
