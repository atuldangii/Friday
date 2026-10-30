"""
UI Rendering and Widget Instantiation Test.
Verifies that MainWindow, CoreVisualizerWidget, ChatWidget, and styles load cleanly without crashes.
"""

import os
import sys
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from core.assistant import FridayCore
from ui.core_visualizer import CoreVisualizerWidget
from ui.chat_widget import ChatWidget
from ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_core_visualizer_instantiation(qapp):
    viz = CoreVisualizerWidget()
    assert viz is not None
    viz.set_state("LISTENING")
    assert viz._state == "LISTENING"
    viz.set_state("SPEAKING")
    assert viz._state == "SPEAKING"
    viz.set_state("PROCESSING")
    assert viz._state == "PROCESSING"
    viz.set_state("IDLE")
    assert viz._state == "IDLE"


def test_chat_widget_messages(qapp):
    chat = ChatWidget()
    assert chat is not None
    chat.add_message("USER", "Hey FRIDAY, open Chrome and run YouTube.")
    chat.add_message("FRIDAY", "Opening Google Chrome...\n✔ Google Chrome is open.")
    assert chat.container_layout.count() >= 3  # stretch + 2 bubbles


def test_main_window_instantiation(qapp):
    core = FridayCore()
    win = MainWindow(core)
    assert win is not None
    assert win.visualizer is not None
    assert win.chat_widget is not None
    win.cleanup()
