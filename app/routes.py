import re
import sqlite3
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from app.db import get_db


api = Blueprint("api", __name__)
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SERVICE_STATUSES = {"Attivo", "Sospeso"}


def error(message, status):
    return jsonify({"error": message}), status


def read_json():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def clean_text(value, label, minimum, maximum):
    if not isinstance(value, str):
        raise ValueError(f"{label}: inserisci un testo valido.")
    value = value.strip()
    if not minimum <= len(value) <= maximum:
        raise ValueError(f"{label}: inserisci da {minimum} a {maximum} caratteri.")
    return value


def integer_field(value, label, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{label}: inserisci un numero tra {minimum} e {maximum}.")
    return value


def service_input(data):
    title = clean_text(data.get("title"), "Titolo", 2, 120)
    category = clean_text(data.get("category"), "Categoria", 2, 60)
    description = clean_text(data.get("description"), "Descrizione", 10, 1000)
    duration = integer_field(data.get("duration_minutes"), "Durata in minuti", 15, 480)
    audience = clean_text(data.get("audience"), "Destinatari", 2, 100)
    status = data.get("status")
    if not isinstance(status, str) or status not in SERVICE_STATUSES:
        raise ValueError("Stato del servizio non valido.")
    return title, category, description, duration, audience, status


def event_input(data):
    service_id = integer_field(data.get("service_id"), "Servizio", 1, 2_147_483_647)
    title = clean_text(data.get("title"), "Titolo", 2, 120)
    description = clean_text(data.get("description"), "Descrizione", 10, 1000)
    starts_at = data.get("starts_at")
    if not isinstance(starts_at, str):
        raise ValueError("Data e ora non valide.")
    try:
        parsed_date = datetime.fromisoformat(starts_at)
    except ValueError as exc:
        raise ValueError("Data e ora non valide.") from exc
    if parsed_date.tzinfo is not None:
        raise ValueError("Usa data e ora locali senza fuso orario.")
    venue = clean_text(data.get("venue"), "Luogo", 2, 160)
    capacity = integer_field(data.get("capacity"), "Capienza", 1, 1000)
    return service_id, title, description, parsed_date.isoformat(timespec="minutes"), venue, capacity


def get_service(service_id):
    return get_db().execute("SELECT * FROM services WHERE id = ?", (service_id,)).fetchone()


def event_rows(event_id=None):
    database = get_db()
    query = """SELECT e.id, e.service_id, s.title AS service_title, e.title, e.description,
                      e.starts_at, e.venue, e.capacity, e.created_at,
                      COALESCE(SUM(b.seats), 0) AS booked_seats,
                      e.capacity - COALESCE(SUM(b.seats), 0) AS available_seats,
                      (SELECT ROUND(AVG(f.rating), 1) FROM feedback f WHERE f.event_id = e.id)
                          AS average_rating,
                      (SELECT COUNT(*) FROM feedback f WHERE f.event_id = e.id) AS feedback_count
               FROM events e
               JOIN services s ON s.id = e.service_id
               LEFT JOIN bookings b ON b.event_id = e.id"""
    if event_id is not None:
        query += " WHERE e.id = ?"
        parameters = (event_id,)
    else:
        parameters = ()
    query += " GROUP BY e.id ORDER BY e.starts_at, e.title"
    return [dict(row) for row in database.execute(query, parameters).fetchall()]


def find_or_create_user(database, name, email):
    existing = database.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        database.execute("UPDATE users SET name = ? WHERE id = ?", (name, existing["id"]))
        return existing["id"]
    return database.execute(
        "INSERT INTO users (name, email) VALUES (?, ?)", (name, email)
    ).lastrowid


def participant_input(data):
    name = clean_text(data.get("name"), "Nome", 2, 100)
    email = clean_text(data.get("email"), "Email", 5, 254).lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Inserisci un indirizzo email valido.")
    return name, email


@api.get("/")
def index():
    return send_from_directory(current_app.static_folder, "index.html")


@api.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@api.get("/api/services")
def list_services():
    rows = get_db().execute(
        """SELECT id, title, category, description, duration_minutes, audience, status, created_at
           FROM services ORDER BY category, title"""
    ).fetchall()
    return jsonify({"data": [dict(row) for row in rows]})


@api.post("/api/services")
def create_service():
    data = read_json()
    if data is None:
        return error("Il corpo della richiesta deve essere un oggetto JSON.", 400)
    try:
        values = service_input(data)
    except ValueError as exc:
        return error(str(exc), 400)
    database = get_db()
    cursor = database.execute(
        """INSERT INTO services
           (title, category, description, duration_minutes, audience, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        values,
    )
    database.commit()
    row = get_service(cursor.lastrowid)
    return jsonify({"data": dict(row)}), 201


@api.get("/api/services/<int:service_id>")
def service_detail(service_id):
    row = get_service(service_id)
    if row is None:
        return error("Servizio culturale non trovato.", 404)
    return jsonify({"data": dict(row)})


@api.put("/api/services/<int:service_id>")
def update_service(service_id):
    data = read_json()
    if data is None:
        return error("Il corpo della richiesta deve essere un oggetto JSON.", 400)
    try:
        values = service_input(data)
    except ValueError as exc:
        return error(str(exc), 400)
    database = get_db()
    cursor = database.execute(
        """UPDATE services SET title = ?, category = ?, description = ?,
           duration_minutes = ?, audience = ?, status = ? WHERE id = ?""",
        (*values, service_id),
    )
    if cursor.rowcount == 0:
        database.rollback()
        return error("Servizio culturale non trovato.", 404)
    database.commit()
    return jsonify({"data": dict(get_service(service_id))})


@api.delete("/api/services/<int:service_id>")
def delete_service(service_id):
    database = get_db()
    try:
        cursor = database.execute("DELETE FROM services WHERE id = ?", (service_id,))
        if cursor.rowcount == 0:
            database.rollback()
            return error("Servizio culturale non trovato.", 404)
        database.commit()
    except sqlite3.IntegrityError:
        database.rollback()
        return error("Il servizio è collegato a uno o più eventi e non può essere eliminato.", 409)
    return "", 204


@api.get("/api/events")
def list_events():
    return jsonify({"data": event_rows()})


@api.post("/api/events")
def create_event():
    data = read_json()
    if data is None:
        return error("Il corpo della richiesta deve essere un oggetto JSON.", 400)
    try:
        values = event_input(data)
    except ValueError as exc:
        return error(str(exc), 400)
    database = get_db()
    service = get_service(values[0])
    if service is None:
        return error("Servizio culturale non trovato.", 404)
    if service["status"] != "Attivo":
        return error("Il servizio è sospeso: non è possibile programmare nuovi eventi.", 409)
    cursor = database.execute(
        """INSERT INTO events (service_id, title, description, starts_at, venue, capacity)
           VALUES (?, ?, ?, ?, ?, ?)""",
        values,
    )
    database.commit()
    return jsonify({"data": event_rows(cursor.lastrowid)[0]}), 201


@api.get("/api/events/<int:event_id>")
def event_detail(event_id):
    rows = event_rows(event_id)
    if not rows:
        return error("Evento non trovato.", 404)
    return jsonify({"data": rows[0]})


@api.put("/api/events/<int:event_id>")
def update_event(event_id):
    data = read_json()
    if data is None:
        return error("Il corpo della richiesta deve essere un oggetto JSON.", 400)
    try:
        values = event_input(data)
    except ValueError as exc:
        return error(str(exc), 400)
    database = get_db()
    if get_service(values[0]) is None:
        return error("Servizio culturale non trovato.", 404)
    current = database.execute("SELECT id FROM events WHERE id = ?", (event_id,)).fetchone()
    if current is None:
        return error("Evento non trovato.", 404)
    reserved = database.execute(
        "SELECT COALESCE(SUM(seats), 0) FROM bookings WHERE event_id = ?", (event_id,)
    ).fetchone()[0]
    if values[5] < reserved:
        return error("La capienza non può essere inferiore ai posti già prenotati.", 409)
    database.execute(
        """UPDATE events SET service_id = ?, title = ?, description = ?, starts_at = ?,
           venue = ?, capacity = ? WHERE id = ?""",
        (*values, event_id),
    )
    database.commit()
    return jsonify({"data": event_rows(event_id)[0]})


@api.delete("/api/events/<int:event_id>")
def delete_event(event_id):
    database = get_db()
    try:
        cursor = database.execute("DELETE FROM events WHERE id = ?", (event_id,))
        if cursor.rowcount == 0:
            database.rollback()
            return error("Evento non trovato.", 404)
        database.commit()
    except sqlite3.IntegrityError:
        database.rollback()
        return error("L'evento ha prenotazioni o feedback e non può essere eliminato.", 409)
    return "", 204


@api.get("/api/events/<int:event_id>/bookings")
def list_bookings(event_id):
    database = get_db()
    if database.execute("SELECT id FROM events WHERE id = ?", (event_id,)).fetchone() is None:
        return error("Evento non trovato.", 404)
    rows = database.execute(
        """SELECT b.id, u.name, u.email, b.seats, b.created_at
           FROM bookings b JOIN users u ON u.id = b.user_id
           WHERE b.event_id = ? ORDER BY b.created_at, b.id""",
        (event_id,),
    ).fetchall()
    return jsonify({"data": [dict(row) for row in rows]})


@api.post("/api/events/<int:event_id>/bookings")
def create_booking(event_id):
    data = read_json()
    if data is None:
        return error("Il corpo della richiesta deve essere un oggetto JSON.", 400)
    try:
        name, email = participant_input(data)
        seats = integer_field(data.get("seats"), "Posti richiesti", 1, 20)
    except ValueError as exc:
        return error(str(exc), 400)

    database = get_db()
    try:
        database.execute("BEGIN IMMEDIATE")
        event = database.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if event is None:
            database.rollback()
            return error("Evento non trovato.", 404)
        if datetime.fromisoformat(event["starts_at"]) <= datetime.now():
            database.rollback()
            return error("La prenotazione non è disponibile dopo la data dell'evento.", 409)
        user_id = find_or_create_user(database, name, email)
        duplicate = database.execute(
            "SELECT id FROM bookings WHERE event_id = ? AND user_id = ?", (event_id, user_id)
        ).fetchone()
        if duplicate:
            database.rollback()
            return error("Esiste già una prenotazione per questa email e questo evento.", 409)
        reserved = database.execute(
            "SELECT COALESCE(SUM(seats), 0) FROM bookings WHERE event_id = ?", (event_id,)
        ).fetchone()[0]
        if reserved + seats > event["capacity"]:
            database.rollback()
            return error("Posti non disponibili in numero sufficiente.", 409)
        cursor = database.execute(
            "INSERT INTO bookings (event_id, user_id, seats) VALUES (?, ?, ?)",
            (event_id, user_id, seats),
        )
        database.commit()
    except Exception:
        database.rollback()
        raise

    return jsonify({"data": {"id": cursor.lastrowid, "event_id": event_id, "seats": seats}}), 201


@api.delete("/api/bookings/<int:booking_id>")
def delete_booking(booking_id):
    database = get_db()
    cursor = database.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    if cursor.rowcount == 0:
        database.rollback()
        return error("Prenotazione non trovata.", 404)
    database.commit()
    return "", 204


@api.get("/api/users")
def list_users():
    rows = get_db().execute(
        """SELECT u.id, u.name, u.email, u.created_at,
                  (SELECT COUNT(*) FROM bookings b WHERE b.user_id = u.id) AS booking_count,
                  (SELECT COALESCE(SUM(b.seats), 0) FROM bookings b WHERE b.user_id = u.id)
                      AS seats_reserved,
                  (SELECT COUNT(*) FROM feedback f WHERE f.user_id = u.id) AS feedback_count
           FROM users u ORDER BY u.name, u.id"""
    ).fetchall()
    return jsonify({"data": [dict(row) for row in rows]})


@api.get("/api/events/<int:event_id>/feedback")
def list_feedback(event_id):
    database = get_db()
    if database.execute("SELECT id FROM events WHERE id = ?", (event_id,)).fetchone() is None:
        return error("Evento non trovato.", 404)
    rows = database.execute(
        """SELECT id, rating, comment, created_at FROM feedback
           WHERE event_id = ? ORDER BY created_at DESC, id DESC""",
        (event_id,),
    ).fetchall()
    return jsonify({"data": [dict(row) for row in rows]})


@api.post("/api/events/<int:event_id>/feedback")
def create_feedback(event_id):
    data = read_json()
    if data is None:
        return error("Il corpo della richiesta deve essere un oggetto JSON.", 400)
    try:
        name, email = participant_input(data)
        rating = integer_field(data.get("rating"), "Valutazione", 1, 5)
        comment = clean_text(data.get("comment"), "Commento", 3, 1000)
    except ValueError as exc:
        return error(str(exc), 400)

    database = get_db()
    try:
        database.execute("BEGIN IMMEDIATE")
        event = database.execute("SELECT starts_at FROM events WHERE id = ?", (event_id,)).fetchone()
        if event is None:
            database.rollback()
            return error("Evento non trovato.", 404)
        if datetime.fromisoformat(event["starts_at"]) > datetime.now():
            database.rollback()
            return error("Il feedback è disponibile dopo la data dell'evento.", 409)
        user_id = find_or_create_user(database, name, email)
        duplicate = database.execute(
            "SELECT id FROM feedback WHERE event_id = ? AND user_id = ?", (event_id, user_id)
        ).fetchone()
        if duplicate:
            database.rollback()
            return error("Hai già inviato un feedback per questo evento.", 409)
        cursor = database.execute(
            "INSERT INTO feedback (event_id, user_id, rating, comment) VALUES (?, ?, ?, ?)",
            (event_id, user_id, rating, comment),
        )
        database.commit()
    except Exception:
        database.rollback()
        raise
    return jsonify({"data": {"id": cursor.lastrowid, "event_id": event_id, "rating": rating}}), 201


@api.get("/api/dashboard")
def dashboard():
    database = get_db()
    totals = database.execute(
        """SELECT
             (SELECT COUNT(*) FROM services) AS service_count,
             (SELECT COUNT(*) FROM events) AS event_count,
             (SELECT COUNT(*) FROM bookings) AS booking_count,
             (SELECT COALESCE(SUM(seats), 0) FROM bookings) AS seats_reserved,
             (SELECT ROUND(AVG(rating), 1) FROM feedback) AS average_rating,
             (SELECT COUNT(*) FROM feedback) AS feedback_count,
             (SELECT COUNT(*) FROM users) AS user_count"""
    ).fetchone()
    events = event_rows()
    now = datetime.now().isoformat(timespec="minutes")
    upcoming_events = [event for event in events if event["starts_at"] > now]
    capacity_total = sum(event["capacity"] for event in upcoming_events)
    seats_total = sum(event["booked_seats"] for event in upcoming_events)
    return jsonify({"data": {
        **dict(totals),
        "upcoming_event_count": len(upcoming_events),
        "occupancy_percent": round(seats_total / capacity_total * 100, 1)
        if capacity_total else 0,
        "events": upcoming_events,
    }})
