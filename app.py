import csv
import io
import os
import secrets
import sqlite3
from datetime import date, datetime, timedelta

from flask import Flask, Response, flash, redirect, render_template, request, url_for

import models

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

models.init_db()


# --- Helpers ---

def week_bounds(d=None):
    d = d or date.today()
    start = d - timedelta(days=d.weekday())  # Monday
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()


def month_bounds(d=None):
    d = d or date.today()
    start = d.replace(day=1)
    if d.month == 12:
        end = d.replace(year=d.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = d.replace(month=d.month + 1, day=1) - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def csv_safe(value):
    """Neutralize CSV formula injection by prefixing risky leading characters."""
    text = str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def parse_entry_form(form):
    """Validate entry form input. Returns (data, None) or (None, error_message)."""
    try:
        project_id = int(form["project_id"])
        hours = float(form["hours"])
    except (KeyError, ValueError):
        return None, "Project and hours are required and must be numeric."

    entry_date = form.get("date", "").strip()
    if not entry_date:
        return None, "Date is required."

    if hours <= 0:
        return None, "Hours must be greater than zero."

    note = form.get("note", "").strip()
    return {"project_id": project_id, "date": entry_date, "hours": hours, "note": note}, None


# --- Dashboard ---

@app.route("/")
def dashboard():
    today = date.today().isoformat()
    week_start, week_end = week_bounds()
    month_start, month_end = month_bounds()

    today_entries = models.get_entries(start_date=today, end_date=today)
    today_total = sum(e["hours"] for e in today_entries)

    week_summary = models.get_summary(week_start, week_end)
    week_total = sum(r["total_hours"] for r in week_summary)

    month_summary = models.get_summary(month_start, month_end)
    month_total = sum(r["total_hours"] for r in month_summary)

    recent_entries = models.get_entries(limit=10)
    timer = models.get_active_timer()
    projects = models.get_projects()

    return render_template(
        "dashboard.html",
        today_total=today_total,
        today_entries=today_entries,
        week_total=week_total,
        week_summary=week_summary,
        month_total=month_total,
        month_summary=month_summary,
        recent_entries=recent_entries,
        timer=timer,
        projects=projects,
        today=today,
    )


# --- Timer ---

@app.route("/timer/start", methods=["POST"])
def timer_start():
    project_id = request.form.get("project_id")
    if not project_id:
        flash("Select a project to start the timer.", "error")
        return redirect(url_for("dashboard"))
    models.start_timer(int(project_id))
    project = models.get_project(int(project_id))
    flash(f"Timer started for {project['name']}.", "success")
    return redirect(url_for("dashboard"))


@app.route("/timer/stop", methods=["POST"])
def timer_stop():
    hours = models.stop_timer()
    if hours is not None:
        flash(f"Timer stopped. {hours:.2f} hours logged.", "success")
    else:
        flash("No active timer.", "error")
    return redirect(url_for("dashboard"))


@app.route("/timer/cancel", methods=["POST"])
def timer_cancel():
    models.cancel_timer()
    flash("Timer cancelled.", "success")
    return redirect(url_for("dashboard"))


# --- Entries ---

@app.route("/entries")
def entries():
    project_id = request.args.get("project_id", type=int)
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    entry_list = models.get_entries(
        project_id=project_id,
        start_date=start_date or None,
        end_date=end_date or None,
    )
    total_hours = sum(e["hours"] for e in entry_list)
    projects = models.get_projects(active_only=False)

    return render_template(
        "entries.html",
        entries=entry_list,
        projects=projects,
        total_hours=total_hours,
        filter_project_id=project_id,
        filter_start=start_date,
        filter_end=end_date,
        today=date.today().isoformat(),
    )


@app.route("/entries/add", methods=["POST"])
def entry_add():
    data, error = parse_entry_form(request.form)
    if error:
        flash(error, "error")
        return redirect(url_for("entries"))

    models.create_entry(data["project_id"], data["date"], data["hours"], data["note"])
    flash("Entry added.", "success")
    return redirect(url_for("entries"))


@app.route("/entries/<int:entry_id>/edit", methods=["GET", "POST"])
def entry_edit(entry_id):
    entry = models.get_entry(entry_id)
    if not entry:
        flash("Entry not found.", "error")
        return redirect(url_for("entries"))

    if request.method == "POST":
        data, error = parse_entry_form(request.form)
        if error:
            flash(error, "error")
            return redirect(url_for("entry_edit", entry_id=entry_id))

        models.update_entry(
            entry_id, data["project_id"], data["date"], data["hours"], data["note"]
        )
        flash("Entry updated.", "success")
        return redirect(url_for("entries"))

    projects = models.get_projects(active_only=False)
    return render_template("entry_edit.html", entry=entry, projects=projects)


@app.route("/entries/<int:entry_id>/delete", methods=["POST"])
def entry_delete(entry_id):
    models.delete_entry(entry_id)
    flash("Entry deleted.", "success")
    return redirect(url_for("entries"))


# --- Projects ---

@app.route("/projects")
def projects():
    show_all = request.args.get("all", "0") == "1"
    project_list = models.get_projects(active_only=not show_all)
    return render_template("projects.html", projects=project_list, show_all=show_all)


@app.route("/projects/add", methods=["POST"])
def project_add():
    name = request.form["name"].strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Project name is required.", "error")
        return redirect(url_for("projects"))

    try:
        models.create_project(name, description)
        flash(f"Project '{name}' created.", "success")
    except sqlite3.IntegrityError:
        flash(f"Project '{name}' already exists.", "error")

    return redirect(url_for("projects"))


@app.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
def project_edit(project_id):
    project = models.get_project(project_id)
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for("projects"))

    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form.get("description", "").strip()
        active = 1 if request.form.get("active") else 0

        try:
            models.update_project(project_id, name, description, active)
            flash("Project updated.", "success")
        except sqlite3.IntegrityError:
            flash("Project name already exists.", "error")
            return redirect(url_for("project_edit", project_id=project_id))

        return redirect(url_for("projects"))

    return render_template("project_edit.html", project=project)


# --- Reports ---

@app.route("/reports")
def reports():
    project_id = request.args.get("project_id", type=int)
    period = request.args.get("period", "week")

    today = date.today()
    if period == "week":
        start_date, end_date = week_bounds(today)
    elif period == "month":
        start_date, end_date = month_bounds(today)
    elif period == "custom":
        start_date = request.args.get("start_date", today.isoformat())
        end_date = request.args.get("end_date", today.isoformat())
    else:
        start_date, end_date = week_bounds(today)

    summary = models.get_summary(start_date, end_date)
    daily_totals = models.get_daily_totals(start_date, end_date)
    total_hours = sum(r["total_hours"] for r in summary)

    entries = models.get_entries(
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
    )

    projects = models.get_projects(active_only=False)

    return render_template(
        "reports.html",
        summary=summary,
        daily_totals=daily_totals,
        total_hours=total_hours,
        entries=entries,
        projects=projects,
        period=period,
        start_date=start_date,
        end_date=end_date,
        filter_project_id=project_id,
    )


@app.route("/reports/csv")
def reports_csv():
    project_id = request.args.get("project_id", type=int)
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    entries = models.get_entries(
        project_id=project_id,
        start_date=start_date or None,
        end_date=end_date or None,
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Date", "Project", "Hours", "Note"])
    for e in entries:
        writer.writerow([
            csv_safe(e["date"]),
            csv_safe(e["project_name"]),
            e["hours"],
            csv_safe(e["note"] or ""),
        ])

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=time_ledger_{start_date}_{end_date}.csv"},
    )


if __name__ == "__main__":
    # Debug is on by default for local dev but can be disabled via the
    # environment (FLASK_DEBUG=0) so it never ships on by accident.
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, port=5050)
