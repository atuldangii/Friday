"""
FRIDAY - Advanced Personal Desktop Assistant for Windows 11
Main Entry Point
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.constants import APP_NAME, APP_VERSION
from core.assistant import FridayCore


def run_gui():
    """Launches the PySide6 Futuristic HUD Application."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QPixmap
    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow

    # Set explicit Windows AppUserModelID so custom icon appears on the taskbar
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Friday.Assistant.HUD.v1")
    except Exception:
        pass

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    icon_path = Path(__file__).resolve().parent / "assets" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    core = FridayCore()
    window = MainWindow(core)
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()

    sys.exit(app.exec())


def run_cli():
    """Headless interactive CLI mode for terminal use or automated testing."""
    print("=" * 60)
    print(f" {APP_NAME} v{APP_VERSION} [Headless CLI Mode]")
    print(" Type a command or 'exit' / 'quit' to close.")
    print("=" * 60)

    core = FridayCore()
    while True:
        try:
            cmd = input("\n[YOU] > ").strip()
            if not cmd:
                continue
            if cmd.lower() in ("exit", "quit"):
                print("Shutting down FRIDAY...")
                break

            response = core.process_command(cmd)
            print(f"[FRIDAY] > {response}")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break


def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} - Windows 11 Desktop Assistant")
    parser.add_argument("--cli", "--no-gui", dest="cli", action="store_true", help="Run in CLI headless mode")
    parser.add_argument("--test-cmd", type=str, help="Execute a single command and exit")
    args = parser.parse_args()

    if args.test_cmd:
        core = FridayCore()
        res = core.process_command(args.test_cmd)
        print(f"Result: {res}")
        return

    if args.cli:
        run_cli()
    else:
        run_gui()


if __name__ == "__main__":
    main()
