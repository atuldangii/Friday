"""
Constants and design tokens for FRIDAY AI.
Orange Sci-Fi Theme — v1.2.0
"""

from enum import Enum
from pathlib import Path

APP_NAME = "FRIDAY"
APP_VERSION = "1.2.0"
APP_SUBTITLE = "YOUR PERSONAL ASSISTANT"

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Ensure data and logs directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

SETTINGS_FILE = DATA_DIR / "settings.json"
MEMORY_DB_FILE = DATA_DIR / "friday_memory.db"
AUDIT_LOG_FILE = LOGS_DIR / "audit_log.jsonl"

# Icon paths
ICON_PNG = ASSETS_DIR / "icon.png"
ICON_ICO = ASSETS_DIR / "friday_icon.ico"

# Risk Levels for Security & Permission Architecture
class RiskLevel(str, Enum):
    LOW = "LOW"             # Can run automatically
    MODERATE = "MODERATE"   # Needs confirmation/preview
    HIGH = "HIGH"           # Explicit confirmation required

# ══════════════════════════════════════════════════
#  ORANGE SCI-FI COLOR PALETTE
# ══════════════════════════════════════════════════
COLOR_BG_DARK        = "#0A0A0C"    # Near-black primary background
COLOR_BG_SECONDARY   = "#111114"    # Secondary background
COLOR_BG_CARD        = "#151515"    # Dark charcoal card surfaces
COLOR_BG_INPUT       = "#1A1A1E"    # Input field background

COLOR_ORANGE         = "#FF7900"    # Vivid orange — primary accent
COLOR_AMBER          = "#FFAA33"    # Amber glow accent
COLOR_ORANGE_PALE    = "#FFD08A"    # Pale orange highlight
COLOR_ORANGE_DIM     = "#CC5500"    # Dimmed orange for inactive

COLOR_TEXT_PRIMARY   = "#F5F5F5"    # Warm white
COLOR_TEXT_SECONDARY = "#A6A6A6"    # Muted gray

COLOR_SUCCESS        = "#22C55E"    # Green — success
COLOR_ERROR          = "#EF4444"    # Red — error
COLOR_WARNING        = "#FBBF24"    # Yellow — warning

COLOR_BORDER         = "rgba(255,121,0,0.22)"   # Orange-tinted border
COLOR_BORDER_FOCUS   = "#FF7900"                # Focus orange

# Legacy aliases so existing files don't break immediately
COLOR_PRIMARY_CYAN   = COLOR_ORANGE
COLOR_ACCENT_BLUE    = COLOR_AMBER
COLOR_NEON_GREEN     = COLOR_SUCCESS
COLOR_NEON_RED       = COLOR_ERROR
COLOR_NEON_YELLOW    = COLOR_WARNING
COLOR_BORDER_FOCUS_LEGACY = COLOR_BORDER_FOCUS
