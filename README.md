# Combatron Reader

Unofficial web reader for Project Combatron chapters.

## Features

- Discover chapters from Project Combatron labels
- Read chapter pages in sequence
- Keyboard navigation for chapter/page controls
- Page progress and page counter in top toolbar
- One-time disclaimer on first load
- Premium export flow with donation prompt

## Project Structure

- `main.py` - app entry point
- `combatron_reader/server.py` - HTTP server + embedded UI
- `combatron_reader/scraper.py` - chapter/page scraping logic
- `combatron_reader/models.py` - data models
- `tests/test_scraper.py` - scraper tests

## Requirements

- Python 3.11+

## Local Run (Windows PowerShell)

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Run the app:

```powershell
python main.py
```

3. Open:

- `http://127.0.0.1:8000`

## Local Run (using existing workspace venv)

If your workspace already uses `.venv-1`:

```powershell
.\.venv-1\Scripts\Activate.ps1
python main.py
```

## Keyboard Shortcuts

- `/` focus search
- `N`/`P` next/previous chapter
- `J`/`K` next/previous page
- `+`/`-` zoom in/out
- `F` fit width
- `D` open export premium prompt

## Tests

```powershell
.\.venv-1\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -q
```

## Deploy on Render

This repository includes `render.yaml`.

### Option A: Blueprint (recommended)

1. Push this repository to GitHub.
2. In Render, click **New +** -> **Blueprint**.
3. Connect your repo and select it.
4. Render reads `render.yaml` and creates the web service.

### Option B: Manual Web Service

Use these settings:

- Runtime: `Python`
- Build Command: `pip install -r requirements.txt`
- Start Command: `python main.py`

## Runtime Configuration

Server host/port are environment-aware:

- `HOST` default: `0.0.0.0`
- `PORT` default: `8000`

Render automatically provides `PORT`.

## Disclaimer

This is an unofficial fan tool. The comic is written by Berlin Manalaysay. Please support the original creators.
