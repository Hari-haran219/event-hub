# EventHub — Online Event Registration & Management System

A Flask + SQLite app for browsing, hosting, and registering for events, restyled
around a box-office ticket identity: events are shown as admission tickets with
a perforated stub, a serial number, and colour-coded categories, instead of a
generic rounded-card layout.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000**. The SQLite database (`event_system.db`) is
created and seeded automatically the first time you run the app.

## Demo data

The seed data includes 8 users and **26 events** spread across all 7
categories (Technology, Health, Business, Education, Arts & Culture, Sports,
Other), with a mix of past and future dates, varied capacities, and a
handful of pre-filled registrations — including one sold-out event — so the
app looks lived-in right away.

**Demo logins:**

| Role | Email | Password |
|---|---|---|
| Admin | admin@example.com | admin123 |
| Organizer (Technology) | arjun@example.com | arjun123 |
| Organizer (Health) | kavya@example.com | kavya123 |
| Organizer (Business) | rohan@example.com | rohan123 |
| Organizer (Education) | sneha@example.com | sneha123 |
| Organizer (Arts & Culture) | divya@example.com | divya123 |
| Organizer (Sports) | vikram@example.com | vikram123 |
| Participant | priya@example.com | priya123 |

Any user can create ("host") events — "organizer" just means whoever created
a given event, and can edit it, view its ticket holders, or delete it. Admins
can do this for every event, plus manage user roles from `/admin`.

## What's in this build

- **`app.py`** — routes, auth, validation. Added two small Jinja filters
  (`ticket_date`, `cat_slug`) used by the new templates, and fixed a
  pre-existing bug where opening the *edit event* page crashed (it passed a
  raw `sqlite3.Row` to a template calling `.get()` on it).
- **`database.py`** — schema is unchanged; the seed data was expanded from 3
  events/2 users to 26 events/8 users with sample registrations.
- **`static/css/style.css`** — full visual redesign (see below).
- **`templates/*.html`** — restructured to match, with a few copy changes
  for voice (e.g. "Get my ticket" instead of "Register").

## Design notes

- **Palette:** navy ink (`#161a2c`) + marigold gold (`#e8a23b`) as the brand
  colours, with crimson reserved for "sold out" / destructive states. Each
  event category gets its own colour, used consistently for badges, ticket
  spines, and the filter chips on the homepage.
- **Type:** Bebas Neue (condensed, marquee-style) for headlines, dates, and
  big numbers; Work Sans for body copy and forms. Loaded from Google Fonts —
  an internet connection is needed for the fonts to load, though the app
  works fine without it (browsers fall back to system fonts).
- **Layout:** events are a stacked list of ticket rows (not a card grid),
  each split by a dashed "perforation" into a main section and a stub
  holding the date and seat count. The event detail page is the same ticket,
  enlarged, with a serial number and the registration action in the stub.
  The admin dashboard's stats render as a dark scoreboard strip.
