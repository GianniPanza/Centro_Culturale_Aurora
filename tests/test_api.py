import os
import tempfile
import unittest
from datetime import datetime, timedelta

from app import create_app
from app.db import get_db, reset_demo_data


class AuroraPlatformTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.sqlite3")
        self.app = create_app({
            "TESTING": True,
            "DATABASE": self.database_path,
            "SEED_DEMO": False,
        })
        self.client = self.app.test_client()
        now = datetime.now().replace(second=0, microsecond=0)
        with self.app.app_context():
            database = get_db()
            database.execute(
                """INSERT INTO services
                   (title, category, description, duration_minutes, audience, status)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("Visite guidate", "Visite", "Percorsi culturali di prova.", 60,
                 "Pubblico generale", "Attivo"),
            )
            database.execute(
                """INSERT INTO events (service_id, title, description, starts_at, venue, capacity)
                   VALUES (1, ?, ?, ?, ?, ?)""",
                ("Evento futuro", "Evento usato per il test funzionale.",
                 (now + timedelta(days=2)).isoformat(timespec="minutes"), "Sala Test", 3),
            )
            database.execute(
                """INSERT INTO events (service_id, title, description, starts_at, venue, capacity)
                   VALUES (1, ?, ?, ?, ?, ?)""",
                ("Evento concluso", "Evento concluso usato per il test funzionale.",
                 (now - timedelta(days=2)).isoformat(timespec="minutes"), "Sala Test", 10),
            )
            database.commit()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_health_home_services_and_events(self):
        self.assertEqual(self.client.get("/api/health").json["status"], "ok")
        landing = self.client.get("/")
        self.assertIn("Centro Culturale Aurora", landing.get_data(as_text=True))
        landing.close()
        self.assertEqual(len(self.client.get("/api/services").json["data"]), 1)
        self.assertEqual(len(self.client.get("/api/events").json["data"]), 2)

    def test_demo_data_belongs_to_fictional_cultural_centre(self):
        demo_app = create_app({
            "TESTING": True,
            "DATABASE": os.path.join(self.temp_dir.name, "demo.sqlite3"),
        })
        demo_client = demo_app.test_client()
        services = demo_client.get("/api/services").json["data"]
        events = demo_client.get("/api/events").json["data"]
        dashboard = demo_client.get("/api/dashboard").json["data"]
        self.assertEqual(len(services), 5)
        self.assertEqual(len(events), 6)
        self.assertEqual(dashboard["upcoming_event_count"], 4)
        self.assertEqual(dashboard["user_count"], 6)
        self.assertEqual(dashboard["seats_reserved"], 46)
        self.assertEqual(dashboard["average_rating"], 4.2)
        self.assertIn("Visite guidate del Centro", [item["title"] for item in services])
        self.assertTrue(all(item["email"].endswith("@example.com")
                            for item in demo_client.get("/api/users").json["data"]))

    def test_demo_data_can_be_reset(self):
        demo_app = create_app({
            "TESTING": True,
            "DATABASE": os.path.join(self.temp_dir.name, "reset.sqlite3"),
        })
        demo_client = demo_app.test_client()
        self.assertEqual(demo_client.delete("/api/bookings/1").status_code, 204)
        with demo_app.app_context():
            reset_demo_data()
        dashboard = demo_client.get("/api/dashboard").json["data"]
        self.assertEqual(dashboard["booking_count"], 15)
        self.assertEqual(dashboard["upcoming_event_count"], 4)

    def test_service_validation_crud_and_delete_conflict(self):
        invalid = self.client.post("/api/services", json={"title": "x"})
        self.assertEqual(invalid.status_code, 400)
        created = self.client.post("/api/services", json={
            "title": "Nuovo laboratorio", "category": "Laboratori",
            "description": "Attività culturale aggiunta durante il test.",
            "duration_minutes": 75, "audience": "Adulti", "status": "Attivo",
        })
        self.assertEqual(created.status_code, 201)
        service_id = created.json["data"]["id"]
        updated = self.client.put(f"/api/services/{service_id}", json={
            "title": "Laboratorio aggiornato", "category": "Laboratori",
            "description": "Descrizione aggiornata per il servizio di prova.",
            "duration_minutes": 90, "audience": "Ragazzi e adulti", "status": "Sospeso",
        })
        self.assertEqual(updated.json["data"]["status"], "Sospeso")
        self.assertEqual(self.client.delete(f"/api/services/{service_id}").status_code, 204)
        self.assertEqual(self.client.delete("/api/services/1").status_code, 409)

    def test_event_create_update_delete_and_capacity_rule(self):
        payload = {
            "service_id": 1, "title": "Nuovo incontro",
            "description": "Un incontro culturale aggiunto dal test.",
            "starts_at": (datetime.now() + timedelta(days=10)).isoformat(timespec="minutes"),
            "venue": "Sala Nuova", "capacity": 25,
        }
        created = self.client.post("/api/events", json=payload)
        self.assertEqual(created.status_code, 201)
        event_id = created.json["data"]["id"]
        payload["venue"] = "Sala Aggiornata"
        self.assertEqual(self.client.put(f"/api/events/{event_id}", json=payload).json["data"]["venue"], "Sala Aggiornata")
        self.assertEqual(self.client.delete(f"/api/events/{event_id}").status_code, 204)
        self.assertEqual(self.client.get(f"/api/events/{event_id}").status_code, 404)

        booking = self.client.post("/api/events/1/bookings", json={
            "name": "Ada Rossi", "email": "ada@example.com", "seats": 2,
        })
        self.assertEqual(booking.status_code, 201)
        capacity_change = self.client.put("/api/events/1", json={
            **payload, "title": "Evento futuro", "capacity": 1,
        })
        self.assertEqual(capacity_change.status_code, 409)

    def test_event_cannot_be_scheduled_for_suspended_service(self):
        suspended = self.client.post("/api/services", json={
            "title": "Servizio in pausa", "category": "Archivio",
            "description": "Servizio sospeso usato per il test funzionale.",
            "duration_minutes": 45, "audience": "Ricercatori", "status": "Sospeso",
        })
        response = self.client.post("/api/events", json={
            "service_id": suspended.json["data"]["id"], "title": "Evento non ammesso",
            "description": "Evento collegato a un servizio sospeso.",
            "starts_at": (datetime.now() + timedelta(days=5)).isoformat(timespec="minutes"),
            "venue": "Sala Test", "capacity": 10,
        })
        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(self.client.get("/api/events").json["data"]), 2)

    def test_booking_cancellation_frees_seats(self):
        booking = self.client.post("/api/events/1/bookings", json={
            "name": "Ada Rossi", "email": "ada@example.com", "seats": 3,
        })
        self.assertEqual(self.client.get("/api/events/1").json["data"]["available_seats"], 0)
        cancelled = self.client.delete(f"/api/bookings/{booking.json['data']['id']}")
        self.assertEqual(cancelled.status_code, 204)
        self.assertEqual(self.client.get("/api/events/1").json["data"]["available_seats"], 3)
        self.assertEqual(self.client.delete("/api/bookings/999").status_code, 404)

    def test_users_registry_reuses_email_and_counts_activity(self):
        self.client.post("/api/events/1/bookings", json={
            "name": "Ada Rossi", "email": "ada@example.com", "seats": 2,
        })
        self.client.post("/api/events/2/feedback", json={
            "name": "Ada Rossi", "email": "ADA@example.com", "rating": 4,
            "comment": "Un incontro piacevole.",
        })
        users = self.client.get("/api/users").json["data"]
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["email"], "ada@example.com")
        self.assertEqual(users[0]["booking_count"], 1)
        self.assertEqual(users[0]["seats_reserved"], 2)
        self.assertEqual(users[0]["feedback_count"], 1)

    def test_booking_capacity_duplicate_and_participant_list(self):
        first = self.client.post("/api/events/1/bookings", json={
            "name": "Ada Rossi", "email": "ada@example.com", "seats": 2,
        })
        self.assertEqual(first.status_code, 201)
        duplicate = self.client.post("/api/events/1/bookings", json={
            "name": "Ada Rossi", "email": "ADA@example.com", "seats": 1,
        })
        self.assertEqual(duplicate.status_code, 409)
        full = self.client.post("/api/events/1/bookings", json={
            "name": "Luca Bianchi", "email": "luca@example.com", "seats": 2,
        })
        self.assertEqual(full.status_code, 409)
        invalid = self.client.post("/api/events/1/bookings", json={
            "name": "Lu", "email": "non-email", "seats": 0,
        })
        self.assertEqual(invalid.status_code, 400)
        event = self.client.get("/api/events/1").json["data"]
        self.assertEqual(event["booked_seats"], 2)
        self.assertEqual(event["available_seats"], 1)
        bookings = self.client.get("/api/events/1/bookings").json["data"]
        self.assertEqual(bookings[0]["email"], "ada@example.com")

    def test_booking_is_closed_after_event(self):
        response = self.client.post("/api/events/2/bookings", json={
            "name": "Ada Rossi", "email": "ada@example.com", "seats": 1,
        })
        self.assertEqual(response.status_code, 409)

    def test_feedback_requires_completed_event_and_rejects_duplicate(self):
        payload = {
            "name": "Ada Rossi", "email": "ada@example.com", "rating": 5,
            "comment": "Un'attività molto interessante.",
        }
        too_early = self.client.post("/api/events/1/feedback", json=payload)
        self.assertEqual(too_early.status_code, 409)
        saved = self.client.post("/api/events/2/feedback", json=payload)
        self.assertEqual(saved.status_code, 201)
        duplicate = self.client.post("/api/events/2/feedback", json=payload)
        self.assertEqual(duplicate.status_code, 409)
        invalid = self.client.post("/api/events/2/feedback", json={**payload, "rating": 8})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(len(self.client.get("/api/events/2/feedback").json["data"]), 1)
        self.assertEqual(self.client.delete("/api/events/2").status_code, 409)

    def test_dashboard_aggregates_current_data(self):
        self.client.post("/api/events/1/bookings", json={
            "name": "Ada Rossi", "email": "ada@example.com", "seats": 2,
        })
        self.client.post("/api/events/2/feedback", json={
            "name": "Ada Rossi", "email": "ada@example.com", "rating": 4,
            "comment": "Un incontro piacevole.",
        })
        data = self.client.get("/api/dashboard").json["data"]
        self.assertEqual(data["service_count"], 1)
        self.assertEqual(data["booking_count"], 1)
        self.assertEqual(data["seats_reserved"], 2)
        self.assertEqual(data["feedback_count"], 1)
        self.assertEqual(data["average_rating"], 4.0)
        self.assertGreater(data["occupancy_percent"], 0)

    def test_invalid_json_and_missing_resources_return_api_errors(self):
        self.assertEqual(self.client.post("/api/services", data="no-json").status_code, 400)
        missing = self.client.get("/api/events/999")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json["error"], "Evento non trovato.")
        unknown_route = self.client.get("/api/unknown")
        self.assertEqual(unknown_route.status_code, 404)
        self.assertIn("error", unknown_route.json)


if __name__ == "__main__":
    unittest.main()
