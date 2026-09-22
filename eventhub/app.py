"""
Online Event Registration and Management System
-------------------------------------------------
Flask + SQLite backend with server-rendered HTML/CSS/JS frontend.

Modules covered:
- User Registration & Login (with password hashing, sessions)
- User Profile Management
- Event Creation & Management (CRUD)
- Event Listing & Search
- Event Registration Module (participants register for events)
- Participant Management
- Form Validation & Error Handling
- Admin Dashboard & Event Management
"""

import os
import re
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g
)
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db, init_db, close_db

# --------------------------------------------------------------------------
# App configuration
# --------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = "change-this-secret-key-in-production"  # use env var in real deployment
app.config["DATABASE"] = os.path.join(app.root_path, "event_system.db")

app.teardown_appcontext(close_db)


# --------------------------------------------------------------------------
# Helpers / Decorators
# --------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

CATEGORY_SLUGS = {
    "Technology": "tech",
    "Health": "health",
    "Business": "business",
    "Education": "education",
    "Arts & Culture": "arts",
    "Sports": "sports",
    "Other": "other",
}


@app.template_filter("ticket_date")
def ticket_date(value):
    """Turn a 'YYYY-MM-DD' string into a {day, mon, year} dict for the ticket-stub date block."""
    try:
        d = datetime.strptime(value, "%Y-%m-%d").date()
        return {"day": f"{d.day:02d}", "mon": MONTHS[d.month - 1], "year": str(d.year)}
    except (ValueError, TypeError):
        return {"day": "--", "mon": "---", "year": ""}


@app.template_filter("cat_slug")
def cat_slug(value):
    """Map a category name to a short CSS slug used for category colour-coding."""
    return CATEGORY_SLUGS.get(value, "other")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Admin access only.", "error")
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    if "user_id" not in session:
        return None
    db = get_db()
    return db.execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()


@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "current_year": datetime.now().year}


# --------------------------------------------------------------------------
# Home / Event listing & search
# --------------------------------------------------------------------------
@app.route("/")
def index():
    db = get_db()
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    query = """
        SELECT e.*, u.full_name AS organizer_name,
               (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS seats_taken
        FROM events e
        JOIN users u ON u.id = e.organizer_id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (e.title LIKE ? OR e.description LIKE ? OR e.location LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like]

    if category:
        query += " AND e.category = ?"
        params.append(category)

    query += " ORDER BY e.event_date ASC"

    events = db.execute(query, params).fetchall()
    categories = db.execute("SELECT DISTINCT category FROM events ORDER BY category").fetchall()

    return render_template(
        "index.html", events=events, search=search,
        category=category, categories=categories, today=date.today().isoformat()
    )


@app.route("/events/<int:event_id>")
def event_detail(event_id):
    db = get_db()
    event = db.execute(
        """SELECT e.*, u.full_name AS organizer_name, u.email AS organizer_email
           FROM events e JOIN users u ON u.id = e.organizer_id
           WHERE e.id = ?""", (event_id,)
    ).fetchone()

    if event is None:
        flash("Event not found.", "error")
        return redirect(url_for("index"))

    seats_taken = db.execute(
        "SELECT COUNT(*) AS c FROM registrations WHERE event_id = ?", (event_id,)
    ).fetchone()["c"]

    already_registered = False
    if "user_id" in session:
        reg = db.execute(
            "SELECT 1 FROM registrations WHERE event_id = ? AND user_id = ?",
            (event_id, session["user_id"])
        ).fetchone()
        already_registered = reg is not None

    return render_template(
        "event_detail.html", event=event, seats_taken=seats_taken,
        already_registered=already_registered
    )


# --------------------------------------------------------------------------
# Authentication: Registration & Login
# --------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []
        if len(full_name) < 2:
            errors.append("Full name must be at least 2 characters.")
        if not EMAIL_RE.match(email):
            errors.append("Please enter a valid email address.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")

        db = get_db()
        if not errors:
            existing = db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                errors.append("An account with this email already exists.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", form=request.form)

        password_hash = generate_password_hash(password)
        db.execute(
            """INSERT INTO users (full_name, email, phone, password_hash, role, created_at)
               VALUES (?, ?, ?, ?, 'participant', ?)""",
            (full_name, email, phone, password_hash, datetime.now().isoformat())
        )
        db.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html", email=email)

        session["user_id"] = user["id"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]
        flash(f"Welcome back, {user['full_name']}!", "success")

        next_url = request.args.get("next")
        return redirect(next_url or url_for("index"))

    return render_template("login.html", email="")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


# --------------------------------------------------------------------------
# User Profile Management
# --------------------------------------------------------------------------
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    user = current_user()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        new_password = request.form.get("new_password", "")

        errors = []
        if len(full_name) < 2:
            errors.append("Full name must be at least 2 characters.")
        if new_password and len(new_password) < 6:
            errors.append("New password must be at least 6 characters.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("profile.html", user=user)

        if new_password:
            db.execute(
                "UPDATE users SET full_name=?, phone=?, password_hash=? WHERE id=?",
                (full_name, phone, generate_password_hash(new_password), user["id"])
            )
        else:
            db.execute(
                "UPDATE users SET full_name=?, phone=? WHERE id=?",
                (full_name, phone, user["id"])
            )
        db.commit()
        session["full_name"] = full_name
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))

    my_registrations = db.execute(
        """SELECT r.*, e.title, e.event_date, e.location
           FROM registrations r JOIN events e ON e.id = r.event_id
           WHERE r.user_id = ? ORDER BY e.event_date""",
        (user["id"],)
    ).fetchall()

    return render_template("profile.html", user=user, registrations=my_registrations)


# --------------------------------------------------------------------------
# Event Creation & Management (CRUD) — organizers/admins
# --------------------------------------------------------------------------
@app.route("/events/new", methods=["GET", "POST"])
@login_required
def create_event():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        location = request.form.get("location", "").strip()
        event_date = request.form.get("event_date", "").strip()
        capacity = request.form.get("capacity", "").strip()

        errors = []
        if len(title) < 3:
            errors.append("Title must be at least 3 characters.")
        if not category:
            errors.append("Please choose a category.")
        if not location:
            errors.append("Location is required.")
        try:
            event_date_parsed = datetime.strptime(event_date, "%Y-%m-%d").date()
            if event_date_parsed < date.today():
                errors.append("Event date cannot be in the past.")
        except ValueError:
            errors.append("Please provide a valid event date.")
        try:
            capacity_val = int(capacity)
            if capacity_val <= 0:
                errors.append("Capacity must be a positive number.")
        except ValueError:
            errors.append("Capacity must be a number.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("create_event.html", form=request.form, editing=False)

        db = get_db()
        db.execute(
            """INSERT INTO events
               (title, description, category, location, event_date, capacity, organizer_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, description, category, location, event_date, capacity_val,
             session["user_id"], datetime.now().isoformat())
        )
        db.commit()
        flash("Your event is live on the board.", "success")
        return redirect(url_for("index"))

    return render_template("create_event.html", form={}, editing=False)


@app.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

    if event is None:
        flash("Event not found.", "error")
        return redirect(url_for("index"))

    if event["organizer_id"] != session["user_id"] and session.get("role") != "admin":
        flash("You don't have permission to edit this event.", "error")
        return redirect(url_for("event_detail", event_id=event_id))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        location = request.form.get("location", "").strip()
        event_date = request.form.get("event_date", "").strip()
        capacity = request.form.get("capacity", "").strip()

        errors = []
        if len(title) < 3:
            errors.append("Title must be at least 3 characters.")
        if not category:
            errors.append("Please choose a category.")
        if not location:
            errors.append("Location is required.")
        try:
            datetime.strptime(event_date, "%Y-%m-%d")
        except ValueError:
            errors.append("Please provide a valid event date.")
        try:
            capacity_val = int(capacity)
            if capacity_val <= 0:
                errors.append("Capacity must be a positive number.")
        except ValueError:
            errors.append("Capacity must be a number.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("create_event.html", form=request.form, editing=True, event_id=event_id)

        db.execute(
            """UPDATE events SET title=?, description=?, category=?, location=?,
               event_date=?, capacity=? WHERE id=?""",
            (title, description, category, location, event_date, capacity_val, event_id)
        )
        db.commit()
        flash("Changes saved.", "success")
        return redirect(url_for("event_detail", event_id=event_id))

    return render_template("create_event.html", form=dict(event), editing=True, event_id=event_id)


@app.route("/events/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_event(event_id):
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

    if event is None:
        flash("Event not found.", "error")
        return redirect(url_for("index"))

    if event["organizer_id"] != session["user_id"] and session.get("role") != "admin":
        flash("You don't have permission to delete this event.", "error")
        return redirect(url_for("event_detail", event_id=event_id))

    db.execute("DELETE FROM registrations WHERE event_id = ?", (event_id,))
    db.execute("DELETE FROM events WHERE id = ?", (event_id,))
    db.commit()
    flash("Event removed from the board.", "success")
    return redirect(url_for("index"))


# --------------------------------------------------------------------------
# Event Registration Module (participants register/unregister)
# --------------------------------------------------------------------------
@app.route("/events/<int:event_id>/register", methods=["POST"])
@login_required
def register_for_event(event_id):
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

    if event is None:
        flash("Event not found.", "error")
        return redirect(url_for("index"))

    existing = db.execute(
        "SELECT 1 FROM registrations WHERE event_id=? AND user_id=?",
        (event_id, session["user_id"])
    ).fetchone()
    if existing:
        flash("You already have a ticket for this one.", "error")
        return redirect(url_for("event_detail", event_id=event_id))

    seats_taken = db.execute(
        "SELECT COUNT(*) AS c FROM registrations WHERE event_id=?", (event_id,)
    ).fetchone()["c"]

    if seats_taken >= event["capacity"]:
        flash("This event is sold out.", "error")
        return redirect(url_for("event_detail", event_id=event_id))

    db.execute(
        "INSERT INTO registrations (event_id, user_id, registered_at) VALUES (?, ?, ?)",
        (event_id, session["user_id"], datetime.now().isoformat())
    )
    db.commit()
    flash("Your ticket is confirmed.", "success")
    return redirect(url_for("event_detail", event_id=event_id))


@app.route("/events/<int:event_id>/unregister", methods=["POST"])
@login_required
def unregister_from_event(event_id):
    db = get_db()
    db.execute(
        "DELETE FROM registrations WHERE event_id=? AND user_id=?",
        (event_id, session["user_id"])
    )
    db.commit()
    flash("Ticket cancelled.", "success")
    return redirect(url_for("event_detail", event_id=event_id))


# --------------------------------------------------------------------------
# Participant Management (organizer view of who registered)
# --------------------------------------------------------------------------
@app.route("/events/<int:event_id>/participants")
@login_required
def event_participants(event_id):
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

    if event is None:
        flash("Event not found.", "error")
        return redirect(url_for("index"))

    if event["organizer_id"] != session["user_id"] and session.get("role") != "admin":
        flash("You don't have permission to view participants.", "error")
        return redirect(url_for("event_detail", event_id=event_id))

    participants = db.execute(
        """SELECT u.id, u.full_name, u.email, u.phone, r.registered_at
           FROM registrations r JOIN users u ON u.id = r.user_id
           WHERE r.event_id = ? ORDER BY r.registered_at""",
        (event_id,)
    ).fetchall()

    return render_template("participants.html", event=event, participants=participants)


@app.route("/events/<int:event_id>/participants/<int:user_id>/remove", methods=["POST"])
@login_required
def remove_participant(event_id, user_id):
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

    if event is None:
        flash("Event not found.", "error")
        return redirect(url_for("index"))

    if event["organizer_id"] != session["user_id"] and session.get("role") != "admin":
        flash("You don't have permission to manage participants.", "error")
        return redirect(url_for("event_detail", event_id=event_id))

    db.execute("DELETE FROM registrations WHERE event_id=? AND user_id=?", (event_id, user_id))
    db.commit()
    flash("Ticket holder removed.", "success")
    return redirect(url_for("event_participants", event_id=event_id))


# --------------------------------------------------------------------------
# Admin Dashboard
# --------------------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    stats = {
        "total_users": db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
        "total_events": db.execute("SELECT COUNT(*) c FROM events").fetchone()["c"],
        "total_registrations": db.execute("SELECT COUNT(*) c FROM registrations").fetchone()["c"],
        "upcoming_events": db.execute(
            "SELECT COUNT(*) c FROM events WHERE event_date >= ?", (date.today().isoformat(),)
        ).fetchone()["c"],
    }

    events = db.execute(
        """SELECT e.*, u.full_name AS organizer_name,
                  (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS seats_taken
           FROM events e JOIN users u ON u.id = e.organizer_id
           ORDER BY e.event_date DESC"""
    ).fetchall()

    users = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()

    return render_template("admin_dashboard.html", stats=stats, events=events, users=users)


@app.route("/admin/users/<int:user_id>/toggle-role", methods=["POST"])
@admin_required
def toggle_user_role(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("admin_dashboard"))

    new_role = "admin" if user["role"] != "admin" else "participant"
    db.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
    db.commit()
    flash(f"{user['full_name']} is now {'an admin' if new_role == 'admin' else 'a participant'}.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    if user_id == session["user_id"]:
        flash("You cannot delete your own account while logged in.", "error")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    db.execute("DELETE FROM registrations WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM events WHERE organizer_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    flash("User deleted.", "success")
    return redirect(url_for("admin_dashboard"))


# --------------------------------------------------------------------------
# Error handlers
# --------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        init_db(app)
    app.run(debug=True)
