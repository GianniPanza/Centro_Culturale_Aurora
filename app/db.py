import sqlite3
from datetime import datetime, timedelta

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def init_db():
    database = get_db()
    with current_app.open_resource("schema.sql") as schema_file:
        database.executescript(schema_file.read().decode("utf-8"))

    if current_app.config["SEED_DEMO"]:
        seed_demo_data(database)


def reset_demo_data():
    """Svuota le tabelle e ricarica i dati dimostrativi con date aggiornate a oggi."""
    database = get_db()
    for table in ("feedback", "bookings", "events", "users", "services"):
        database.execute(f"DELETE FROM {table}")
    database.execute("DELETE FROM sqlite_sequence")
    database.commit()
    seed_demo_data(database)


def demo_date(days, hour, minute=0):
    day = datetime.now() + timedelta(days=days)
    return day.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat(timespec="minutes")


def seed_demo_data(database):
    if database.execute("SELECT COUNT(*) FROM services").fetchone()[0] > 0:
        return

    services = [
        (
            "Visite guidate del Centro",
            "Visite",
            "Percorsi tra gli spazi, le collezioni e le storie del territorio.",
            60,
            "Adulti e famiglie",
            "Attivo",
        ),
        (
            "Laboratorio di lettura condivisa",
            "Laboratori",
            "Un incontro partecipato per esplorare testi, idee e nuove prospettive.",
            90,
            "Ragazzi e adulti",
            "Attivo",
        ),
        (
            "Incontri con autori e ricercatori",
            "Incontri",
            "Conversazioni pubbliche con persone che lavorano nei campi della cultura.",
            75,
            "Pubblico generale",
            "Attivo",
        ),
        (
            "Attività creative per famiglie",
            "Attività per famiglie",
            "Attività pratiche per avvicinare persone di età diverse ai temi culturali.",
            90,
            "Famiglie con bambini",
            "Attivo",
        ),
        (
            "Consultazione dell'archivio fotografico",
            "Archivio",
            "Accesso accompagnato alle fotografie storiche del quartiere, su appuntamento.",
            45,
            "Studenti e ricercatori",
            "Sospeso",
        ),
    ]
    database.executemany(
        """INSERT INTO services
           (title, category, description, duration_minutes, audience, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        services,
    )

    # Le date sono calcolate rispetto al giorno di caricamento: quattro eventi futuri e due conclusi.
    events = [
        (
            2,
            "Racconti brevi ad alta voce",
            "Una serata di lettura condivisa in piccolo gruppo, con posti limitati.",
            demo_date(3, 17),
            "Biblioteca del Centro",
            8,
        ),
        (
            1,
            "Visita guidata: storie del quartiere",
            "Un percorso accompagnato tra memorie, luoghi e trasformazioni locali.",
            demo_date(6, 17, 30),
            "Sala delle Mappe",
            24,
        ),
        (
            2,
            "Parole in viaggio",
            "Laboratorio di lettura e dialogo aperto alla comunità.",
            demo_date(11, 18),
            "Biblioteca del Centro",
            18,
        ),
        (
            3,
            "La città raccontata",
            "Un incontro pubblico su archivi, narrazioni e identità dei luoghi.",
            demo_date(17, 18, 30),
            "Sala degli Incontri",
            40,
        ),
        (
            4,
            "Laboratorio creativo in famiglia",
            "Un'attività condivisa per osservare e interpretare immagini e oggetti.",
            demo_date(-8, 16),
            "Atelier Aurora",
            20,
        ),
        (
            3,
            "Dialogo con l'archivista",
            "Come nasce un archivio di comunità e come si conservano le memorie locali.",
            demo_date(-15, 18),
            "Sala degli Incontri",
            30,
        ),
    ]
    database.executemany(
        """INSERT INTO events
           (service_id, title, description, starts_at, venue, capacity)
           VALUES (?, ?, ?, ?, ?, ?)""",
        events,
    )

    users = [
        ("Giulia Demo", "giulia.demo@example.com"),
        ("Marco Esempio", "marco.esempio@example.com"),
        ("Sara Prova", "sara.prova@example.com"),
        ("Luca Campione", "luca.campione@example.com"),
        ("Elena Modello", "elena.modello@example.com"),
        ("Paolo Fittizio", "paolo.fittizio@example.com"),
    ]
    database.executemany("INSERT INTO users (name, email) VALUES (?, ?)", users)

    # (evento, utente, posti)
    bookings = [
        (1, 3, 3), (1, 4, 4),
        (2, 1, 2), (2, 2, 4), (2, 3, 3),
        (3, 4, 2), (3, 5, 5),
        (4, 1, 2), (4, 6, 6), (4, 2, 2),
        (5, 1, 3), (5, 5, 4), (5, 6, 2),
        (6, 2, 2), (6, 3, 2),
    ]
    database.executemany(
        "INSERT INTO bookings (event_id, user_id, seats) VALUES (?, ?, ?)", bookings
    )

    # (evento, utente, valutazione, commento)
    feedback = [
        (5, 1, 5, "Attività accogliente e ben organizzata."),
        (5, 5, 4, "Bambini coinvolti dall'inizio alla fine; gli spazi erano un po' stretti."),
        (5, 6, 5, "Materiali curati e operatori molto disponibili."),
        (6, 2, 4, "Incontro chiaro e ricco di esempi concreti."),
        (6, 3, 3, "Tema interessante, ma l'incontro è iniziato in ritardo."),
    ]
    database.executemany(
        "INSERT INTO feedback (event_id, user_id, rating, comment) VALUES (?, ?, ?, ?)",
        feedback,
    )
    database.commit()
