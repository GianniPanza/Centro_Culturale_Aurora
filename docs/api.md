# Specifica delle API REST

Le API sono il punto di contatto tra l'interfaccia web e il back-end. Sono servite da Flask sullo stesso indirizzo della pagina (`http://127.0.0.1:5050`) e scambiano dati in formato JSON.

## Convenzioni

| Aspetto | Regola |
|---|---|
| Risposta riuscita con dati | `{"data": ...}` |
| Risposta di errore | `{"error": "messaggio leggibile"}` |
| Data e ora degli eventi (`starts_at`) | Ora locale, formato ISO `AAAA-MM-GGTHH:MM` |
| Data di registrazione (`created_at`) | Generata dal database in UTC, formato `AAAA-MM-GG HH:MM:SS` |
| Corpo delle richieste `POST` e `PUT` | Oggetto JSON con intestazione `Content-Type: application/json` |

| Codice | Significato nel prototipo |
|---|---|
| `200` | Richiesta riuscita |
| `201` | Risorsa creata |
| `204` | Risorsa eliminata, nessun contenuto |
| `400` | Dati mancanti o non validi |
| `404` | Risorsa inesistente |
| `409` | Conflitto con una regola applicativa: capienza, duplicati, dati collegati |

## Riepilogo degli endpoint

| Metodo | Percorso | Operazione | Codici |
|---|---|---|---|
| `GET` | `/api/health` | Verifica che il servizio risponda | 200 |
| `GET` | `/api/services` | Elenco dei servizi | 200 |
| `POST` | `/api/services` | Crea un servizio | 201, 400 |
| `GET` | `/api/services/<id>` | Dettaglio di un servizio | 200, 404 |
| `PUT` | `/api/services/<id>` | Aggiorna un servizio | 200, 400, 404 |
| `DELETE` | `/api/services/<id>` | Rimuove un servizio senza eventi | 204, 404, 409 |
| `GET` | `/api/events` | Elenco degli eventi con disponibilità e riepilogo feedback | 200 |
| `POST` | `/api/events` | Programma un evento | 201, 400, 404, 409 |
| `GET` | `/api/events/<id>` | Dettaglio e disponibilità | 200, 404 |
| `PUT` | `/api/events/<id>` | Aggiorna un evento | 200, 400, 404, 409 |
| `DELETE` | `/api/events/<id>` | Rimuove un evento senza prenotazioni o feedback | 204, 404, 409 |
| `GET` | `/api/events/<id>/bookings` | Elenco delle prenotazioni dell'evento | 200, 404 |
| `POST` | `/api/events/<id>/bookings` | Registra una prenotazione | 201, 400, 404, 409 |
| `DELETE` | `/api/bookings/<id>` | Annulla una prenotazione e libera i posti | 204, 404 |
| `GET` | `/api/events/<id>/feedback` | Elenco di valutazioni e commenti | 200, 404 |
| `POST` | `/api/events/<id>/feedback` | Registra un feedback | 201, 400, 404, 409 |
| `GET` | `/api/users` | Anagrafica dei partecipanti con conteggi | 200 |
| `GET` | `/api/dashboard` | Indicatori aggregati | 200 |

## Servizi culturali

Corpo per `POST /api/services` e `PUT /api/services/<id>`:

```json
{
  "title": "Visite guidate del Centro",
  "category": "Visite",
  "description": "Percorsi tra gli spazi e le storie del territorio.",
  "duration_minutes": 60,
  "audience": "Adulti e famiglie",
  "status": "Attivo"
}
```

| Campo | Vincolo |
|---|---|
| `title` | Testo, da 2 a 120 caratteri |
| `category` | Testo, da 2 a 60 caratteri |
| `description` | Testo, da 10 a 1000 caratteri |
| `duration_minutes` | Intero, da 15 a 480 |
| `audience` | Testo, da 2 a 100 caratteri |
| `status` | `Attivo` oppure `Sospeso` |

Un servizio collegato ad almeno un evento non può essere eliminato: la risposta è `409`.

## Eventi

Corpo per `POST /api/events` e `PUT /api/events/<id>`:

```json
{
  "service_id": 1,
  "title": "Visita guidata: storie del quartiere",
  "description": "Un percorso accompagnato tra memorie e luoghi locali.",
  "starts_at": "2026-10-07T17:30",
  "venue": "Sala delle Mappe",
  "capacity": 24
}
```

| Campo | Vincolo |
|---|---|
| `service_id` | Identificativo di un servizio esistente, altrimenti `404` |
| `title` | Testo, da 2 a 120 caratteri |
| `description` | Testo, da 10 a 1000 caratteri |
| `starts_at` | Data e ora locali, senza fuso orario |
| `venue` | Testo, da 2 a 160 caratteri |
| `capacity` | Intero, da 1 a 1000 |

Regole applicative:

- un nuovo evento richiede un servizio in stato `Attivo`; per un servizio `Sospeso` la risposta è `409`;
- in modifica la capienza non può scendere sotto i posti già prenotati (`409`);
- un evento con prenotazioni o feedback non può essere eliminato (`409`).

Ogni evento restituito contiene anche i campi calcolati `service_title`, `booked_seats`, `available_seats`, `average_rating` e `feedback_count`.

## Prenotazioni

`POST /api/events/<id>/bookings`

```json
{"name": "Ada Rossi", "email": "ada@example.com", "seats": 2}
```

| Campo | Vincolo |
|---|---|
| `name` | Testo, da 2 a 100 caratteri |
| `email` | Indirizzo email valido, al massimo 254 caratteri; non distingue maiuscole e minuscole |
| `seats` | Intero, da 1 a 20 |

Regole applicative, tutte con risposta `409`:

- l'evento non deve essere già iniziato;
- la stessa email può avere una sola prenotazione per evento;
- i posti richiesti non possono superare quelli disponibili.

Controllo e inserimento avvengono nella stessa transazione SQLite (`BEGIN IMMEDIATE`), così due richieste contemporanee non possono superare la capienza. Se l'email è nuova viene creato il partecipante; se esiste già, viene riutilizzato e il nome aggiornato.

`GET /api/events/<id>/bookings` restituisce per ogni prenotazione `id`, `name`, `email`, `seats`, `created_at`.

`DELETE /api/bookings/<id>` annulla la prenotazione. Il partecipante resta in anagrafica.

Gli endpoint che restituiscono nomi ed email non sono protetti da autenticazione: sono pensati per l'esecuzione locale e non per l'esposizione pubblica.

## Feedback

`POST /api/events/<id>/feedback`

```json
{
  "name": "Ada Rossi",
  "email": "ada@example.com",
  "rating": 5,
  "comment": "Un incontro interessante e ben organizzato."
}
```

| Campo | Vincolo |
|---|---|
| `name`, `email` | Come per le prenotazioni |
| `rating` | Intero, da 1 a 5 |
| `comment` | Testo, da 3 a 1000 caratteri |

Il feedback è accettato solo dopo la data dell'evento e una sola volta per email ed evento; negli altri casi la risposta è `409`.

`GET /api/events/<id>/feedback` restituisce `id`, `rating`, `comment`, `created_at`, senza dati anagrafici.

## Partecipanti

`GET /api/users` restituisce l'anagrafica in ordine alfabetico:

```json
{
  "data": [
    {
      "id": 1,
      "name": "Giulia Demo",
      "email": "giulia.demo@example.com",
      "created_at": "2026-10-01 14:30:00",
      "booking_count": 3,
      "seats_reserved": 7,
      "feedback_count": 1
    }
  ]
}
```

## Dashboard

`GET /api/dashboard` restituisce gli indicatori calcolati al momento della richiesta.

| Campo | Significato |
|---|---|
| `service_count` | Servizi a catalogo |
| `event_count` | Eventi totali |
| `upcoming_event_count` | Eventi futuri |
| `user_count` | Partecipanti registrati |
| `booking_count` | Prenotazioni totali |
| `seats_reserved` | Posti prenotati in totale |
| `feedback_count` | Feedback ricevuti |
| `average_rating` | Media delle valutazioni, con un decimale; `null` se non ci sono feedback |
| `occupancy_percent` | Posti prenotati diviso capienza, sugli eventi futuri, in percentuale |
| `events` | Elenco degli eventi futuri con i rispettivi posti |

## Sicurezza dei dati in ingresso

I campi sono validati lato server anche quando la pagina li ha già controllati. Tutte le query SQL usano parametri. L'interfaccia codifica i testi ricevuti prima di mostrarli, per evitare che un contenuto inserito da un utente venga interpretato come codice.

## Provare le API senza l'interfaccia

A prototipo avviato, da un secondo terminale:

```bash
curl http://127.0.0.1:5050/api/dashboard
```

```bash
curl -X POST http://127.0.0.1:5050/api/events/2/bookings -H "Content-Type: application/json" -d '{"name":"Ada Rossi","email":"ada@example.com","seats":2}'
```
