"""Tests for the data-access layer in models.py."""

import sqlite3
from datetime import date, datetime, timedelta

import pytest

import models


# --- Projects ---

def test_create_and_get_project(db):
    models.create_project("Acme", "desc")
    projects = models.get_projects()
    assert len(projects) == 1
    assert projects[0]["name"] == "Acme"
    assert projects[0]["description"] == "desc"
    assert projects[0]["active"] == 1


def test_duplicate_project_name_raises(project):
    with pytest.raises(sqlite3.IntegrityError):
        models.create_project("Acme")


def test_active_only_filter(project):
    models.update_project(project, "Acme", "", active=0)
    assert models.get_projects(active_only=True) == []
    assert len(models.get_projects(active_only=False)) == 1


# --- Entries ---

def test_create_and_filter_entries(project):
    models.create_entry(project, "2026-06-10", 2.0, "early")
    models.create_entry(project, "2026-06-14", 3.0, "late")

    assert len(models.get_entries()) == 2

    in_range = models.get_entries(start_date="2026-06-12", end_date="2026-06-30")
    assert len(in_range) == 1
    assert in_range[0]["note"] == "late"

    # joined project name is exposed
    assert in_range[0]["project_name"] == "Acme"


def test_entries_limit(project):
    for i in range(5):
        models.create_entry(project, f"2026-06-1{i}", 1.0)
    assert len(models.get_entries(limit=3)) == 3


def test_update_and_delete_entry(project):
    models.create_entry(project, "2026-06-14", 1.0, "orig")
    entry_id = models.get_entries()[0]["id"]

    models.update_entry(entry_id, project, "2026-06-15", 4.5, "changed")
    updated = models.get_entry(entry_id)
    assert updated["hours"] == 4.5
    assert updated["note"] == "changed"

    models.delete_entry(entry_id)
    assert models.get_entry(entry_id) is None


# --- Timers ---

def test_start_replaces_existing_timer(project):
    models.create_project("Beta")
    beta_id = [p["id"] for p in models.get_projects() if p["name"] == "Beta"][0]

    models.start_timer(project)
    models.start_timer(beta_id)

    timer = models.get_active_timer()
    assert timer is not None
    assert timer["project_id"] == beta_id
    # only one timer ever active
    with models.get_db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM timers").fetchone()[0] == 1


def test_stop_timer_creates_entry(project, monkeypatch):
    # Pin start to one hour ago so the logged duration is deterministic.
    started = datetime.now() - timedelta(hours=1)
    models.start_timer(project)
    with models.get_db() as conn:
        conn.execute("UPDATE timers SET started_at = ?", (started.isoformat(),))
        conn.commit()

    hours = models.stop_timer()
    assert hours == pytest.approx(1.0, abs=0.05)
    assert models.get_active_timer() is None

    entries = models.get_entries()
    assert len(entries) == 1
    assert entries[0]["date"] == date.today().isoformat()


def test_stop_timer_with_none_active(db):
    assert models.stop_timer() is None


def test_stop_timer_clamps_negative_hours(project):
    # A future start time (e.g. clock shift) must not log negative hours.
    future = datetime.now() + timedelta(hours=2)
    models.start_timer(project)
    with models.get_db() as conn:
        conn.execute("UPDATE timers SET started_at = ?", (future.isoformat(),))
        conn.commit()

    hours = models.stop_timer()
    assert hours == 0.0
    assert models.get_entries()[0]["hours"] == 0.0


def test_cancel_timer(project):
    models.start_timer(project)
    models.cancel_timer()
    assert models.get_active_timer() is None


# --- Summaries ---

def test_get_summary_groups_by_project(project):
    models.create_project("Beta")
    beta_id = [p["id"] for p in models.get_projects() if p["name"] == "Beta"][0]
    models.create_entry(project, "2026-06-14", 2.0)
    models.create_entry(project, "2026-06-14", 1.0)
    models.create_entry(beta_id, "2026-06-14", 5.0)

    summary = {r["project_name"]: r for r in models.get_summary("2026-06-01", "2026-06-30")}
    assert summary["Acme"]["total_hours"] == 3.0
    assert summary["Acme"]["entry_count"] == 2
    assert summary["Beta"]["total_hours"] == 5.0
    # ordered by total_hours DESC
    assert list(models.get_summary("2026-06-01", "2026-06-30"))[0]["project_name"] == "Beta"


def test_get_daily_totals(project):
    models.create_entry(project, "2026-06-14", 2.0)
    models.create_entry(project, "2026-06-14", 1.5)
    models.create_entry(project, "2026-06-15", 4.0)

    totals = {r["date"]: r["total_hours"] for r in models.get_daily_totals("2026-06-01", "2026-06-30")}
    assert totals == {"2026-06-14": 3.5, "2026-06-15": 4.0}
