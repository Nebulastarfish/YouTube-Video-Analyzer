# 📝 YouTube Video Analyzer — Project Notes

## Overview

This project is an **AI-powered video analysis engine** that takes any YouTube video URL and automatically produces structured outputs:

1. **Step-by-Step Procedure** — numbered, actionable instructions extracted from the video
2. **Mind Map** — a Mermaid diagram showing key concepts and their relationships
3. **Flowchart** — a Mermaid process diagram showing the workflow/procedure
4. **Obsidian-Ready Documents** — automatic generation of `.md` notes with YAML frontmatter, backlinks, and embedded diagrams
5. **Left History Lane** — interactive sidebar listing past analyses with video thumbnails, live search, instant loading, and deletion

It can be run in **three different modes**:
- **Standalone Desktop Application** (.exe window powered by PyWebView, no browser or terminal needed)
- **Local Web Application** (Flask server in browser at http://localhost:5000)
- **Command-Line Interface** (CLI script with terminal progress bars)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 Desktop Window (PyWebView) or Web Browser                   │
│  ┌────────────────────────┐  ┌───────────────────────────────────────────┐  │
│  │   LEFT HISTORY LANE    │  │               MAIN VIEW                   │  │
│  │  • Video Thumbnails    │  │  • YouTube URL Input                      │  │
│  │  • Video Titles & IDs  │  │  • Real-time SSE Progress Indicators      │  │
│  │  • Instant Cache Load  │  │  • Tabbed Results (Steps, Mindmap, Flow)  │  │
│  │  • Live Search Filter  │  │  • Mermaid.js Live Diagram Renderers      │  │
│  │  • Delete / New Button │  │  • "Open Output Folder" (Obsidian Vault)  │  │
│  │  • Collapsible (◀ / ▶) │  │  • Download .md Action Buttons            │  │
│  └────────────────────────┘  └───────────────────────────────────────────┘  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / SSE (http://127.0.0.1:5000)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Flask Server (app.py)                            │
│  ┌────────────┐  ┌────────────┐  ┌───────────────────────┐  ┌────────────┐  │
│  │ transcript │→ │  analyzer  │→ │      generators       │→ │   utils    │  │
│  │    .py     │  │    .py     │  │ steps / mindmap / fc  │  │ (Obsidian) │  │
│  └────────────┘  └────────────┘  └───────────────────────┘  └────────────┘  │
│       ▲                ▲                                          │         │
│       │                │                                          ▼         │
│  youtube-transcript   Google Gemini API                    output/<video_id>│
│       -api            (google-genai / Interactions)        report.md, steps │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## How to Run

### 1. Setup & Installation

```powershell
cd C:\Users\mniha\OneDrive\EXPERIMENTS\YouTube_Video_Analyzer

# Create virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate

# Install all dependencies (including pywebview & pyinstaller)
pip install -r requirements.txt

# Configure API key
copy .env.example .env
# Edit .env and paste your Gemini API key from https://aistudio.google.com/apikey
```

### 2. Run Options

| Mode | Command | Description |
|------|---------|-------------|
| **Desktop App** | `python desktop_app.py` | Native GUI window via PyWebView (with History lane & diagrams) |
| **Web Server** | `python app.py` | Starts Flask at http://127.0.0.1:5000 |
| **CLI** | `python main.py <url>` | Scriptable terminal command with rich progress output |

---

## Building the Standalone Windows Executable (.exe)

Compile the application into a single `.exe` that launches with a double-click without opening any terminal console:

```powershell
pyinstaller --noconsole --onefile `
  --name "YouTube_Video_Analyzer" `
  --add-data "templates;templates" `
  --add-data "src;src" `
  --hidden-import "google.genai" `
  desktop_app.py
```

After compilation, your executable will be located at:
`dist\YouTube_Video_Analyzer.exe`

---

## How the `.env` File is Handled (Security & Runtime)

### Why `.env` is NOT bundled into the `.exe`
When PyInstaller builds with `--onefile`, all bundled data is unpacked into a temporary folder (`sys._MEIPASS`) on launch and deleted when closed. If an API key or `.env` file were packed into the `.exe`, anyone could easily extract the binary or inspect `%TEMP%` to steal the secret key.

### How the `.exe` finds `.env` at runtime
1. When running as a frozen `.exe`, `sys.frozen` is `True`, and the application directory is detected dynamically using:
   ```python
   app_dir = os.path.dirname(sys.executable)
   ```
2. The analyzer looks for `.env` at `os.path.join(app_dir, ".env")`.
3. If no `.env` file exists yet, `desktop_app.py` automatically generates a template `.env` in the folder where the `.exe` resides so you can simply open and paste your key.
4. Generated output reports (`output/`) are also saved directly next to the `.exe` rather than in temporary storage.

---

## PyInstaller Pathing Details (`sys._MEIPASS`)

In `app.py`, template pathing is resolved dynamically:
```python
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    template_folder = os.path.join(sys._MEIPASS, "templates")
    app = Flask(__name__, template_folder=template_folder)
else:
    app = Flask(__name__, template_folder="templates")
```
This ensures Flask always locates `templates/index.html` whether running from Python source or from within the bundled executable.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `flask` | ≥3.0.0 | Local HTTP and SSE streaming backend |
| `pywebview` | ≥5.0.0 | Native desktop Chromium/Edge window |
| `pyinstaller` | ≥6.0.0 | Compiles project into standalone Windows `.exe` |
| `google-genai` | ≥2.3.0 | Modern Google Gemini API SDK (Interactions API) |
| `youtube-transcript-api` | ≥0.6.0 | Subtitle and transcript extraction |
| `python-dotenv` | ≥1.0.0 | Loads `.env` configuration |
| `rich` | ≥13.0.0 | Terminal UI for CLI runner |

---

*Updated: October 2026*  
*Location: `C:\Users\mniha\OneDrive\EXPERIMENTS\YouTube_Video_Analyzer`*
