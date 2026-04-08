# CLAUDE.md

## Project Overview

TimeLedger is a personal time tracking Flask app with SQLite storage. Single user, no auth.

## Structure

```
TimeLedger/
├── app.py              # Flask routes and view logic
├── models.py           # SQLite data access layer
├── requirements.txt    # Python dependencies
├── static/
│   └── style.css       # Dark theme stylesheet
└── templates/
    ├── base.html       # Layout with nav and flash messages
    ├── dashboard.html  # Home page with summaries and timer
    ├── entries.html    # Entry list with add form and filters
    ├── entry_edit.html # Edit single entry
    ├── projects.html   # Project list with add form
    ├── project_edit.html # Edit single project
    └── reports.html    # Reporting with period selection and charts
```

## Commands

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run dev server
python app.py
```

App runs on port 5050.

## Key Patterns

- `models.py` handles all database access; `app.py` never touches SQLite directly
- Database auto-initializes on first request via `@app.before_request`
- Only one timer can be active at a time (old timer is replaced on new start)
- Timer stop auto-creates an entry for today with calculated hours
- Projects can be archived (soft delete) — archived projects still appear in filters and reports
- CSS uses custom properties in `:root` for theming
- No JS frameworks — vanilla JS used only for the live timer countdown
