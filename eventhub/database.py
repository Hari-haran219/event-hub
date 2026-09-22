"""
Database Design & Integration (SQLite)
---------------------------------------
Handles connection management and schema creation for:
- users
- events
- registrations (junction table between users and events)
"""

import sqlite3
from flask import current_app, g
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta


def get_db():
    """Open a new database connection if one doesn't exist for this request."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'participant',   -- 'participant' or 'admin'
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    location TEXT NOT NULL,
    event_date TEXT NOT NULL,
    capacity INTEGER NOT NULL,
    organizer_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organizer_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    registered_at TEXT NOT NULL,
    UNIQUE(event_id, user_id),
    FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
"""


# --------------------------------------------------------------------------
# Demo seed data — used only the first time the app runs (empty database)
# --------------------------------------------------------------------------

# (full_name, email, phone, password, role)
DEMO_USERS = [
    ("Admin User",   "admin@example.com",  "9999999999", "admin123",  "admin"),
    ("Priya Sharma", "priya@example.com",  "9876543210", "priya123",  "participant"),
    ("Arjun Mehta",  "arjun@example.com",  "9876500011", "arjun123",  "participant"),
    ("Kavya Nair",   "kavya@example.com",  "9876500022", "kavya123",  "participant"),
    ("Rohan Verma",  "rohan@example.com",  "9876500033", "rohan123",  "participant"),
    ("Sneha Iyer",   "sneha@example.com",  "9876500044", "sneha123",  "participant"),
    ("Vikram Rao",   "vikram@example.com", "9876500055", "vikram123", "participant"),
    ("Divya Menon",  "divya@example.com",  "9876500066", "divya123",  "participant"),
]

# (title, description, category, location, day_offset_from_today, capacity, organizer_email)
DEMO_EVENTS = [
    # Technology — organized by Arjun
    ("Tech Innovators Summit",
     "A summit exploring AI, cloud, and the future of software, with talks from engineers across the industry.",
     "Technology", "Coimbatore Convention Center", 15, 100, "arjun@example.com"),
    ("Cloud & DevOps Bootcamp",
     "A hands-on weekend bootcamp covering containers, CI/CD pipelines, and cloud infrastructure basics.",
     "Technology", "Bengaluru", 40, 60, "arjun@example.com"),
    ("AI for Everyone: A Beginner's Workshop",
     "A friendly introduction to machine learning concepts for people with no coding background.",
     "Technology", "Chennai", 22, 80, "arjun@example.com"),
    ("Cybersecurity Conclave",
     "Security researchers and practitioners share the latest on threat detection and safe system design.",
     "Technology", "Hyderabad", 55, 120, "arjun@example.com"),

    # Health — organized by Kavya
    ("Community Health Camp",
     "Free health checkups, eye screenings, and wellness workshops for the community.",
     "Health", "City Community Hall, Coimbatore", 7, 50, "kavya@example.com"),
    ("Mental Wellness & Mindfulness Retreat",
     "A two-day retreat with guided meditation, journaling, and talks on managing everyday stress.",
     "Health", "Kodaikanal", 35, 40, "kavya@example.com"),
    ("Yoga & Nutrition Workshop",
     "Morning yoga sessions paired with practical nutrition guidance from registered dietitians.",
     "Health", "Kochi", 18, 45, "kavya@example.com"),
    ("Blood Donation & Health Screening Drive",
     "A single-day drive combining blood donation with basic health screenings, run with local hospitals.",
     "Health", "Coimbatore", -3, 150, "kavya@example.com"),

    # Business — organized by Rohan
    ("Startup Pitch Night",
     "Local startups pitch their ideas to a panel of investors and get feedback in front of a live audience.",
     "Business", "Innovation Hub, Peelamedu, Coimbatore", 30, 8, "rohan@example.com"),
    ("Founders' Fireside: Scaling from Zero to One",
     "An evening conversation with founders who've taken their companies from idea to first revenue.",
     "Business", "Mumbai", 50, 70, "rohan@example.com"),
    ("Women in Business Leadership Meet",
     "A networking evening and panel discussion for women leading and building businesses.",
     "Business", "Chennai", 28, 90, "rohan@example.com"),
    ("Freelancer & Consultant Networking Mixer",
     "An informal mixer for freelancers and independent consultants to meet and trade notes.",
     "Business", "Pune", 12, 55, "rohan@example.com"),

    # Education — organized by Sneha
    ("Career Guidance & Higher Studies Fair",
     "Counsellors and alumni answer questions on higher studies, scholarships, and career paths.",
     "Education", "Coimbatore", 20, 200, "sneha@example.com"),
    ("Public Speaking Masterclass",
     "A practical, exercise-driven session on structuring talks and speaking with confidence.",
     "Education", "Bengaluru", 33, 45, "sneha@example.com"),
    ("Financial Literacy for Young Adults",
     "A plain-language session on budgeting, saving, and understanding credit for first-time earners.",
     "Education", "Delhi", 45, 60, "sneha@example.com"),
    ("Teachers' Training Workshop on Digital Classrooms",
     "A training day for school teachers on using digital tools and tech in the classroom.",
     "Education", "Coimbatore", -1, 40, "sneha@example.com"),

    # Arts & Culture — organized by Divya
    ("Coimbatore Heritage Photowalk",
     "A guided walk through the city's older neighbourhoods, timed for the best early morning light.",
     "Arts & Culture", "Coimbatore", 9, 25, "divya@example.com"),
    ("Classical Music & Dance Evening",
     "An evening of Carnatic vocal music and Bharatanatyam performances by local artists.",
     "Arts & Culture", "Chennai", 26, 150, "divya@example.com"),
    ("Independent Short Film Festival",
     "A weekend screening of short films from independent filmmakers, followed by director Q&As.",
     "Arts & Culture", "Bengaluru", 60, 120, "divya@example.com"),
    ("Pottery & Craft Weekend Workshop",
     "A two-day hands-on workshop covering wheel-throwing and hand-building techniques.",
     "Arts & Culture", "Auroville", 48, 20, "divya@example.com"),

    # Sports — organized by Vikram
    ("City Marathon & Fun Run",
     "A timed 10K and a family-friendly 3K fun run through the city, with routes for all fitness levels.",
     "Sports", "Coimbatore", 42, 300, "vikram@example.com"),
    ("Weekend Badminton League Finals",
     "The finals of the weekend badminton league — open for anyone to come watch or join as a spectator.",
     "Sports", "Coimbatore", 10, 6, "vikram@example.com"),
    ("Amateur Cricket Premier Cup",
     "A weekend cricket tournament for amateur club teams from across the city.",
     "Sports", "Chennai", 37, 160, "vikram@example.com"),
    ("Trail Running & Hiking Meet",
     "A guided trail run and hike through the hills, ending with breakfast at the summit.",
     "Sports", "Ooty", 16, 35, "vikram@example.com"),

    # Other — organized by Admin
    ("Community Board Games Night",
     "A casual evening of board games and card games. Bring one along, or just come play.",
     "Other", "Coimbatore", 5, 30, "admin@example.com"),
    ("Volunteer Clean-Up Drive: Save Our Lakes",
     "A community clean-up drive at the local lake, with gloves, bags, and refreshments provided.",
     "Other", "Coimbatore", -5, 100, "admin@example.com"),
]

# (event_title, [registrant_emails]) — a hand-picked subset so seat counts
# vary realistically, including one fully sold-out event.
DEMO_REGISTRATIONS = [
    ("Tech Innovators Summit",
     ["priya@example.com", "kavya@example.com", "rohan@example.com",
      "sneha@example.com", "vikram@example.com", "divya@example.com"]),
    ("Weekend Badminton League Finals",
     ["admin@example.com", "priya@example.com", "arjun@example.com",
      "kavya@example.com", "rohan@example.com", "sneha@example.com"]),
    ("Startup Pitch Night",
     ["admin@example.com", "priya@example.com", "arjun@example.com", "kavya@example.com"]),
    ("Coimbatore Heritage Photowalk",
     ["priya@example.com", "sneha@example.com", "vikram@example.com"]),
    ("City Marathon & Fun Run",
     ["admin@example.com", "priya@example.com", "arjun@example.com", "kavya@example.com",
      "rohan@example.com", "sneha@example.com", "divya@example.com"]),
]


def init_db(app):
    """Create tables and seed demo data if the database is empty."""
    db_path = app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    user_count = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    if user_count == 0:
        now = datetime.now().isoformat()

        for full_name, email, phone, password, role in DEMO_USERS:
            conn.execute(
                """INSERT INTO users (full_name, email, phone, password_hash, role, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (full_name, email, phone, generate_password_hash(password), role, now),
            )
        conn.commit()

        user_id_by_email = {
            row["email"]: row["id"]
            for row in conn.execute("SELECT id, email FROM users").fetchall()
        }

        event_id_by_title = {}
        for title, desc, category, location, day_offset, capacity, organizer_email in DEMO_EVENTS:
            event_date = (datetime.now() + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            cur = conn.execute(
                """INSERT INTO events
                   (title, description, category, location, event_date, capacity, organizer_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, desc, category, location, event_date, capacity,
                 user_id_by_email[organizer_email], now),
            )
            event_id_by_title[title] = cur.lastrowid
        conn.commit()

        for title, registrant_emails in DEMO_REGISTRATIONS:
            event_id = event_id_by_title[title]
            for email in registrant_emails:
                conn.execute(
                    "INSERT INTO registrations (event_id, user_id, registered_at) VALUES (?, ?, ?)",
                    (event_id, user_id_by_email[email], now),
                )
        conn.commit()

    conn.close()
