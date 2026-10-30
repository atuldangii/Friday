# FRIDAY — Advanced Personal Desktop Assistant for Windows 11

![Python Version](https://img.shields.io/badge/Python-3.11%20|%203.12-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%2011-0078D4.svg)
![UI Framework](https://img.shields.io/badge/GUI-PySide6%20Qt6-00F0FF.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

> *"Good day, Sir. All systems are online and standing by."*  
> Inspired by the Female Replacement Intelligent Digital Assistant Youth (FRIDAY) from the Marvel Cinematic Universe, **FRIDAY** is a production-minded personal desktop assistant engineered for **Windows 11**.

---

## 1. Overview & Architecture

FRIDAY unites voice interaction, deterministic offline computer control, and optional cloud multimodal intelligence into a sleek, Stark Industries-inspired desktop application.

```
                      +---------------------------------------+
                      |       PySide6 Futuristic HUD          |
                      |  - Arc Reactor 60FPS Core Visualizer  |
                      |  - Real-time Audio Spectrum Equalizer |
                      |  - Live Status & Multi-step Feed      |
                      +-------------------+-------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
              [Voice Interaction Deck]            [Text Command Deck]
              - Wake-Word ("Hey FRIDAY")          - Keyboard Shortcuts (Alt+X)
              - Windows SAPI5 Speech Synthesizer  - Emergency Stop Button
                        |                                   |
                        +-----------------+-----------------+
                                          |
                                          v
                      +---------------------------------------+
                      |           FRIDAY Core Brain           |
                      |  - Task Planner (Compound Step Logic) |
                      |  - Security & Permission Gatekeeper   |
                      |  - SQLite Persistent Memory Engine    |
                      +-------------------+-------------------+
                                          |
                    +---------------------+---------------------+
                    |                                           |
                    v                                           v
    [Deterministic Local Router]                [Cloud AI & Vision Adapter]
    - Zero-latency Offline Rules                - Google Gemini 2.5 Flash
    - Regex & Word-Boundary Heuristics          - Multimodal Screen Understanding
    - Never executes unvalidated code           - Structured Tool Calling JSON
                    |                                           |
                    +---------------------+---------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |      Windows Automation Engine        |
                      |  - App Controller (Chrome, Calc, etc) |
                      |  - Browser & Web Search Automation    |
                      |  - Safe Math AST Evaluator (No eval)  |
                      |  - File Organization & Safe Search    |
                      |  - Screen Capture & Active Window     |
                      +---------------------------------------+
```

---

## 2. Key Features

- **Futuristic Arc Reactor HUD**: Animated, rotating segmented rings and glowing reactor core reacting to system state (IDLE, LISTENING, PROCESSING, EXECUTING, SPEAKING, STOPPED) alongside an audio spectrum equalizer.
- **Dual Voice & Text Input**: Hands-free background wake-word activation (`"Hey FRIDAY"` or `"FRIDAY"`), one-click microphone recording, and an intuitive text input deck.
- **Windows Computer Control**:
  - Launch approved applications: Notepad, Calculator, Google Chrome, Edge, Paint, Settings, Task Manager, File Explorer, and custom registered apps.
  - Web and YouTube searches with instant factual summary retrieval.
  - Safe math computation using abstract syntax tree (AST) arithmetic — never arbitrary `eval()`.
  - File management: locate files (e.g., resumes, documents), open folders, and categorize directory contents by file type.
  - Multi-step compound command planner with step-by-step validation and cancellation support.
- **Security & Permission Guardrails**:
  - **LOW Risk** (tell time, open calculator, search web, system stats): Runs automatically.
  - **MODERATE Risk** (organize files, create documents, type into active windows): Prompts user with an action preview modal.
  - **HIGH Risk** (delete files, terminate applications, modify system configuration): Requires explicit immediate authorization.
  - **Global Emergency Stop**: Instant abort via `■ STOP` button, `Alt+X`, or `Escape`.
  - **Audit Logging**: Every action logged to `logs/audit_log.jsonl` with API keys and secrets automatically redacted.
- **Local SQLite Memory**: Stores user preferences, nicknames ("Sir"), favorite browsers, and tracks interaction history.
- **Multimodal Screen Understanding**: Screen capture and AI visual explanation using Gemini Vision when enabled.

---

## 3. Quick Start (Windows 11)

### Option A: One-Click Launchers (Recommended)
1. **Setup**: Double-click `setup.bat`. This automatically provisions a virtual environment and installs all dependencies.
2. **Launch**: Double-click `run_friday.bat`.

### Option B: Manual Setup
```powershell
# 1. Create a Python 3.11 or 3.12 virtual environment
python -m venv .venv

# 2. Activate the virtual environment
.venv\Scripts\activate

# 3. Upgrade pip and install requirements
pip install -r requirements.txt

# 4. Copy configuration template
copy .env.example .env

# 5. Launch FRIDAY
python friday.py
```

---

## 4. Launch Modes

### 1. Desktop Graphical Interface (Default)
```powershell
.venv\Scripts\python.exe friday.py
```
Launches the full PySide6 cybernetic HUD, system tray integration, and sound-wave visualizer.

### 2. Headless CLI Mode
```powershell
.venv\Scripts\python.exe friday.py --cli
```
Runs FRIDAY in a lightweight interactive terminal session (ideal for low-resource environments or remote SSH).

### 3. Single Command Execution (CLI Test)
```powershell
.venv\Scripts\python.exe friday.py --test-cmd "Calculate 250 multiplied by 48"
```

---

## 5. Example Commands & Voice Instructions

| Command | Action Performed | Risk Level |
|---|---|---|
| `"Hey FRIDAY, open Google Chrome"` | Launches browser executable | LOW |
| `"Open YouTube and search for Python tutorials"` | Opens YouTube with targeted search query | LOW |
| `"Open my Downloads folder"` | Opens Windows Explorer to `%USERPROFILE%\Downloads` | LOW |
| `"Find my resume on my computer"` | Searches user directories for matching files and opens the folder | LOW |
| `"Calculate 250 multiplied by 48"` | Evaluates math safely via AST parser and speaks result (`12,000`) | LOW |
| `"Search the web for the latest AI developments"` | Launches search engine and retrieves instant factual summary | LOW |
| `"Open Notepad and write a short project plan"` | Opens Notepad, focuses window, and types project plan | MODERATE (Confirmation) |
| `"Explain what is displayed on my screen"` | Captures screenshot and analyzes foreground application / vision | LOW |
| `"Organize the files in my Downloads folder by file type"` | Previews file categorization and prompts for confirmation | MODERATE (Confirmation) |
| `"What time is it, and what is today's date"` | Decomposes compound command and executes each step | LOW |
| `"Stop listening, FRIDAY"` | Mutes wake-word detection and pauses voice capture | LOW |

---

## 6. Wake-Word & Offline Speech Recognition

### Hands-Free Wake Phrase
- **Supported Wake Phrases**: `"Hey FRIDAY"`, `"FRIDAY"`, `"OK FRIDAY"`.
- When spoken, FRIDAY chimes, acknowledges *"Yes, I am listening,"* and listens for your instruction.
- **Sensitivity & Privacy**: Toggle the microphone on the HUD or pause wake-word detection anytime.

### Optional 100% Offline Vosk Model
While FRIDAY functions out-of-the-box using Windows SAPI5 and speech recognition, you can enable 100% offline speech recognition:
1. Download the lightweight English model (`vosk-model-small-en-us-0.15.zip`) from [Alpha Cephei](https://alphacephei.com/vosk/models).
2. Extract the archive into a folder named `vosk-model` inside the project root:
   ```
   Friday/
   └── vosk-model/
       ├── am/
       ├── conf/
       └── graph/
   ```
3. FRIDAY will automatically detect and prioritize local offline recognition.

---

## 7. Cloud Intelligence Configuration (Optional)

FRIDAY operates with zero external dependencies by default using its deterministic command router. To unlock conversational flexibility and multimodal screen vision:

1. Open **Settings** (gear icon on the HUD) or edit `.env`.
2. Configure your API key:
   ```ini
   GEMINI_API_KEY=your_gemini_api_key_here
   FRIDAY_ENABLE_CLOUD_AI=true
   FRIDAY_ENABLE_VISION=true
   ```
3. Save settings. FRIDAY will now utilize Gemini for natural language reasoning and visual screen inspection while retaining strict tool validation.

---

## 8. Security & Permissions Architecture

- **No Arbitrary Shell Execution**: FRIDAY never executes raw shell or Python scripts emitted by language models. All interactions must map to typed Pydantic tool schemas (`ai/tool_schemas.py`).
- **Emergency Abort**: Pressing `Escape`, `Ctrl+Alt+X`, `Alt+X`, or clicking `■ STOP` immediately halts any running speech or multi-step action.
- **Audit Logging**: All initiated tools and outcomes are appended to `logs/audit_log.jsonl`. Sensitive tokens (passwords, keys) are automatically sanitized.

---

## 9. Background Voice Listening & Floating HUD Overlay

### Cross-Application Workflow
FRIDAY runs continuously in the Windows background without requiring window switching:
1. **Background Audio Stream**: The wake-word listener runs on a dedicated worker thread, continuously monitoring for `"Hey FRIDAY"`.
2. **Compact Floating HUD Overlay**: When `"Hey FRIDAY"` is detected while working in any other application (Chrome, YouTube, LinkedIn, Notepad, VS Code), FRIDAY surfaces a compact, frameless, translucent orange-and-amber floating HUD overlay (`Qt.Tool | Qt.WindowStaysOnTopHint`).
3. **Live Interaction**: The overlay features an animated mini arc-reactor core, live speech transcription, action result status with checkmarks, microphone mute toggle, emergency stop button, manual command text box, pin-to-screen toggle, and an expand-to-main-window button (`⤢`).
4. **Non-Intrusive Dismissal**: The overlay auto-dismisses after 7 seconds (if unpinned) or can be closed with `Escape` / `✕` without terminating background listening.

### System Tray & Window Lifecycle
- **Minimize to Tray**: Closing (`✕`) or minimizing the main window hides it to the Windows system tray rather than quitting.
- **Tray Menu Actions**:
  - `Show FRIDAY` — Restores full HUD window to foreground.
  - `Hide FRIDAY` — Minimizes full HUD to tray.
  - `Show Overlay` — Opens the compact floating HUD overlay.
  - `Enable listening` — Unpauses microphone audio stream.
  - `Pause listening` — Pauses microphone audio stream.
  - `Stop the current task` — Emergency aborts running operations.
  - `Settings` — Configures voice, browser, and wake-word settings.
  - `Exit FRIDAY completely` — Gracefully terminates microphone, worker threads, and browser sessions.

### Global Windows Hotkeys
Registered via Windows `RegisterHotKey` API without capturing unconfigured keystrokes:
- **`Ctrl + Alt + F`** (fallback: `Ctrl + Shift + F`) — Toggle Floating HUD Overlay / Show FRIDAY.
- **`Ctrl + Alt + M`** (fallback: `Ctrl + Shift + M`) — Mute / Unmute Microphone listening.
- **`Ctrl + Alt + X`** (fallback: `Ctrl + Shift + X`) — Emergency Stop / Cancel task.

### Wake-Word Phrase & Model Configuration
FRIDAY uses a multi-tier wake-word detection pipeline:
- **Phrase Matching**: Configured via `config/settings.json` under `"wake_word.phrase": "hey friday"`. Supports natural spoken variations including `"Hey FRIDAY"`, `"FRIDAY"`, and `"Hi FRIDAY"`.
- **Audio Capture**: Handles device reconnections gracefully with exponential backoff and releases device locks cleanly during mute or pause.

---

## 10. Automated Testing

Run the complete test suite:
```powershell
.venv\Scripts\pytest.exe -v
```
All **60 automated tests** verify:
- Deterministic website navigation and multi-browser resolution (`LinkedIn in Chrome`, `YouTube in Chrome`, `Gmail in Edge`, `GitHub in my browser`)
- Existing browser window reuse and accurate failure reporting (no false success messages)
- Compound command execution and context propagation (`Open LinkedIn and then YouTube in Chrome`)
- Compact floating HUD overlay instantiation, live transcription, and dismiss behavior
- Microphone mute and resume synchronization across tray, hotkeys, and GUI
- Emergency stop resource cleanup and worker thread responsiveness
- Deterministic Command Parsing & Wake Word filtering
- Safety & Permission level validation
- Safe AST math evaluation (rejecting injection attempts)
- File categorization previews
- SQLite Memory persistence & interaction logging
- Multi-step compound task decomposition and cancellation
- Running application window reuse and adaptive verification
- UI rendering, custom reactor animations, and card feed instantiation

### Performance Benchmarks

| Command / Operation | Execution Time | Optimization Highlights |
|---|---|---|
| Command Decomposition (`Open Chrome, search...`) | **0.01 ms** | Single-pass regex splitting |
| Local Math Calculation (`calculate 250 * 48`) | **10.74 ms** | Direct AST evaluation (no cloud lag) |
| Compound App + Math (`open Calc and calculate 125 * 8`) | **2.51 s** | Real Windows process launch + verify |
| App Window Reuse (already running app) | **< 20 ms** | Restores existing HWND (no duplicate window) |

---

## 11. Orange Sci-Fi Visual Identity & Assets

The UI layout and theme accurately reflect the futuristic HUD reference design:
- **Palette**: Near-black (`#0A0A0C`), Dark charcoal (`#151515`), Vivid orange (`#FF7900`), Amber glow (`#FFAA33`), Pale orange (`#FFD08A`), Warm white (`#F5F5F5`).
- **Assets**:
  - `assets/friday_icon.ico` — Multi-resolution Windows application icon (16x16, 32x32, 48x48, 256x256).
  - `assets/friday_icon.png` — High-res HUD diamond icon.
  - `assets/friday_logo.svg` — Scalable vector logo.
  - `assets/icon.png` — Runtime taskbar and window icon.

---

## 12. Project Directory Layout

```
Friday/
├── assets/                  # Icons and visual assets (ICO, PNG, SVG)
├── config/                  # SettingsManager, constants, and risk definitions
├── core/                    # Assistant orchestrator, command router, security, memory, task planner, hotkey
├── voice/                   # Wake-word detector, speech recognizer, text-to-speech engine
├── automation/              # Windows app controller, browser automation, desktop, and file tools
├── ai/                      # Pydantic action schemas and Gemini cloud vision client
├── ui/                      # PySide6 HUD, Floating Overlay, Arc Reactor, chat feed, settings & permission dialogs
├── tests/                   # 60 Pytest test suites including benchmarks
├── friday.py                # Main application entry point (GUI & CLI)
├── setup.bat                # Automated Windows 11 setup script
├── run_friday.bat           # One-click desktop launcher
├── requirements.txt         # Pinned dependency requirements
└── README.md                # Documentation & usage guide
```
