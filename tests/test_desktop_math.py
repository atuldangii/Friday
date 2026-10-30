"""
Unit tests for DesktopController safe math calculations.
"""

import pytest
from automation.desktop import DesktopController


@pytest.fixture
def desktop():
    return DesktopController()


def test_multiplication(desktop):
    ok, res = desktop.calculate("250 * 48")
    assert ok is True
    assert "12000" in res


def test_natural_language_math(desktop):
    ok, res = desktop.calculate("250 multiplied by 48")
    assert ok is True
    assert "12000" in res


def test_safe_functions(desktop):
    ok, res = desktop.calculate("sqrt(144) + 10")
    assert ok is True
    assert "22" in res


def test_dangerous_code_rejected(desktop):
    ok, res = desktop.calculate("__import__('os').system('dir')")
    assert ok is False
