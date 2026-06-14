"""Tests for the Flask routes and request handling in app.py."""

import models


def test_dashboard_ok(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_add_entry(client, project):
    resp = client.post(
        "/entries/add",
        data={"project_id": str(project), "date": "2026-06-14", "hours": "2.5", "note": "work"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    entries = models.get_entries()
    assert len(entries) == 1
    assert entries[0]["hours"] == 2.5


def test_add_entry_rejects_zero_hours(client, project):
    client.post(
        "/entries/add",
        data={"project_id": str(project), "date": "2026-06-14", "hours": "0"},
        follow_redirects=True,
    )
    assert models.get_entries() == []


def test_add_entry_rejects_non_numeric_hours(client, project):
    # Previously raised ValueError -> HTTP 500; now flashed and redirected.
    resp = client.post(
        "/entries/add",
        data={"project_id": str(project), "date": "2026-06-14", "hours": "abc"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert models.get_entries() == []


def test_add_entry_missing_field_is_handled(client, project):
    resp = client.post(
        "/entries/add",
        data={"project_id": str(project), "date": "2026-06-14"},  # no hours
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert models.get_entries() == []


def test_edit_missing_entry_redirects(client):
    resp = client.get("/entries/999/edit")
    assert resp.status_code == 302


def test_duplicate_project_flashes_not_500(client, project):
    resp = client.post(
        "/projects/add",
        data={"name": "Acme"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"already exists" in resp.data
    assert len(models.get_projects()) == 1


def test_csv_export_neutralizes_formula_injection(client, project):
    models.create_entry(project, "2026-06-14", 1.0, '=HYPERLINK("evil")')
    resp = client.get("/reports/csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    body = resp.get_data(as_text=True)
    # The dangerous cell is prefixed with a quote so spreadsheets treat it as text.
    assert "'=HYPERLINK" in body
    assert "\n=HYPERLINK" not in body


def test_csv_export_quotes_commas_and_newlines(client, project):
    models.create_entry(project, "2026-06-14", 1.0, "a, b\nc")
    body = client.get("/reports/csv").get_data(as_text=True)
    # csv module wraps the field in quotes, preserving the comma and newline.
    assert '"a, b\nc"' in body
