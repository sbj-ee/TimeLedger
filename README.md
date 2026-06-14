# Time Ledger

A personal time tracking app built with Flask and SQLite.

## Features

- **Dashboard** — Today, week, and month hour totals with per-project bar chart
- **Timer** — Start/stop timer with live elapsed clock, auto-logs hours on stop
- **Entries** — Add, edit, delete time entries with project, date, hours, and optional notes
- **Projects** — Create, edit, and archive projects
- **Reports** — Filter by week, month, or custom date range; per-project and daily breakdowns
- **CSV Export** — Export filtered entries for external use

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Open http://localhost:5050

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests also run automatically on every push and pull request via GitHub Actions.

## Tech Stack

- Python / Flask
- SQLite
- Jinja2 templates
- Vanilla JS (timer only)
