"""
File Management & System Storage Automation for Windows 11.
Supports folder navigation, file search (e.g., finding resumes/documents),
safe file reading/writing, and file organization with preview & confirmation.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class FileController:
    def __init__(self):
        self.user_home = Path.home()
        self.standard_folders = {
            "downloads": self.user_home / "Downloads",
            "documents": self.user_home / "Documents",
            "desktop": self.user_home / "Desktop",
            "pictures": self.user_home / "Pictures",
            "videos": self.user_home / "Videos",
            "music": self.user_home / "Music",
        }

    def get_standard_folder(self, folder_name: str) -> Optional[Path]:
        name_clean = folder_name.lower().strip()
        return self.standard_folders.get(name_clean)

    def open_path(self, target_path: str) -> Tuple[bool, str]:
        """Opens a file or folder using the default Windows application."""
        clean = target_path.strip().lower()
        if clean in self.standard_folders:
            p = self.standard_folders[clean]
        else:
            p = Path(os.path.expandvars(target_path)).resolve()

        if not p.exists():
            return False, f"Path does not exist: {target_path}"

        try:
            os.startfile(str(p))
            return True, f"Opened {p.name}."
        except Exception as e:
            return False, f"Failed to open path: {e}"

    def search_file(self, query: str, search_roots: Optional[List[Path]] = None, max_results: int = 5) -> List[Path]:
        """
        Searches user folders for files matching the query name or pattern.
        Example: query='resume' searches Desktop, Documents, Downloads for *resume*.*
        """
        if not search_roots:
            search_roots = [
                self.standard_folders["desktop"],
                self.standard_folders["documents"],
                self.standard_folders["downloads"],
            ]

        results = []
        query_lower = query.lower()

        for root in search_roots:
            if not root.exists():
                continue
            try:
                # Limit depth to avoid deep filesystem recursion stalls
                for dirpath, dirnames, filenames in os.walk(root):
                    # Skip hidden or system dirs
                    dirnames[:] = [d for d in dirnames if not d.startswith(".") and not d.startswith("$")]
                    
                    # Calculate depth relative to root
                    rel = Path(dirpath).relative_to(root)
                    if len(rel.parts) > 3:
                        dirnames.clear()
                        continue

                    for f in filenames:
                        if query_lower in f.lower():
                            full_path = Path(dirpath) / f
                            results.append(full_path)
                            if len(results) >= max_results:
                                return results
            except Exception as e:
                print(f"[FileController] Search error in {root}: {e}")

        return results

    def read_text_file(self, file_path: str, max_chars: int = 5000) -> Tuple[bool, str]:
        """Reads content from a text file safely."""
        p = Path(os.path.expandvars(file_path)).resolve()
        if not p.exists() or not p.is_file():
            return False, f"File not found: {file_path}"

        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_chars)
            return True, content
        except Exception as e:
            return False, f"Could not read file: {e}"

    def create_text_file(self, file_path: str, content: str) -> Tuple[bool, str]:
        """Creates or writes a file."""
        p = Path(os.path.expandvars(file_path)).resolve()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            return True, f"File created at {p}."
        except Exception as e:
            return False, f"Failed to create file: {e}"

    def preview_organize_folder_by_type(self, folder_path: Path) -> Dict[str, List[str]]:
        """
        Generates a preview plan of organizing a directory into subfolders by file type:
        Documents, Images, Audio, Video, Archives, Code, Others.
        Does NOT move any files yet.
        """
        category_extensions = {
            "Documents": {".pdf", ".docx", ".doc", ".txt", ".xlsx", ".csv", ".pptx", ".odt"},
            "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"},
            "Audio": {".mp3", ".wav", ".aac", ".flac", ".m4a"},
            "Videos": {".mp4", ".mkv", ".mov", ".avi", ".wmv"},
            "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
            "Code": {".py", ".js", ".html", ".css", ".json", ".cpp", ".c", ".java", ".ts"},
        }

        moves: Dict[str, List[str]] = {}

        if not folder_path.exists() or not folder_path.is_dir():
            return moves

        for item in folder_path.iterdir():
            if item.is_file() and not item.name.startswith("."):
                ext = item.suffix.lower()
                target_category = "Others"
                for cat, extensions in category_extensions.items():
                    if ext in extensions:
                        target_category = cat
                        break
                
                if target_category not in moves:
                    moves[target_category] = []
                moves[target_category].append(item.name)

        return moves

    def execute_organize_folder(self, folder_path: Path, moves_plan: Dict[str, List[str]]) -> Tuple[bool, str]:
        """
        Executes the file reorganization according to the plan after user approval.
        """
        moved_count = 0
        try:
            for category, filenames in moves_plan.items():
                cat_dir = folder_path / category
                cat_dir.mkdir(exist_ok=True)

                for fname in filenames:
                    src = folder_path / fname
                    dst = cat_dir / fname
                    if src.exists() and not dst.exists():
                        shutil.move(str(src), str(dst))
                        moved_count += 1

            return True, f"Organized {moved_count} files in {folder_path.name} into categorised folders."
        except Exception as e:
            return False, f"Error organizing folder: {e}"
