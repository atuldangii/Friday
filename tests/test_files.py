"""
Unit tests for FileController and organization preview.
"""

from pathlib import Path
import pytest
from automation.files import FileController


@pytest.fixture
def files_ctrl():
    return FileController()


def test_standard_folders_lookup(files_ctrl):
    dl = files_ctrl.get_standard_folder("downloads")
    assert dl is not None
    assert "downloads" in str(dl).lower()

    docs = files_ctrl.get_standard_folder("documents")
    assert docs is not None


def test_preview_organize_folder(files_ctrl, tmp_path):
    # Create sample dummy files
    (tmp_path / "test1.pdf").touch()
    (tmp_path / "test2.jpg").touch()
    (tmp_path / "test3.mp3").touch()
    (tmp_path / "test4.zip").touch()
    (tmp_path / "test5.py").touch()

    preview = files_ctrl.preview_organize_folder_by_type(tmp_path)
    assert "Documents" in preview and "test1.pdf" in preview["Documents"]
    assert "Images" in preview and "test2.jpg" in preview["Images"]
    assert "Audio" in preview and "test3.mp3" in preview["Audio"]
    assert "Archives" in preview and "test4.zip" in preview["Archives"]
    assert "Code" in preview and "test5.py" in preview["Code"]
