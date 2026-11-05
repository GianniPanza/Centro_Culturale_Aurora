# Test funzionali e scenari d'uso

Il prototipo è stato verificato su due piani: test automatici sulle API e scenari d'uso eseguiti nel browser.

## Riepilogo

| Tipo di verifica | Quanti | Esito |
|---|---|---|
| Test automatici sulle API | 18 | 18 superati |
| Scenari d'uso nel browser | 14 | 14 superati |
| Scenari di avvio | 2 | 1 superato su macOS, 1 non eseguito |

Verifica del 1° ottobre 2026 su macOS 26.6 con Python 3.9.6, Flask 3.1.3 e SQLite 3.51. Dopo le modifiche del 5 novembre 2026 (informativa, feedback riservato a chi ha prenotato, blocco dei servizi sospesi in modifica, nome non sovrascritto) sono stati rieseguiti i 18 test automatici e gli scenari S2, S4 e S12, e sono state aggiornate le schermate.

## Test automatici

```bash
python -m unittest discover -s tests -v
```

Ogni test crea un database temporaneo con un servizio, un evento futuro da 3 posti e un evento concluso, esegue richieste alle API e controlla codici di risposta e dati salvati. Il database dimostrativo non viene toccato.

| ID | Test nel file `tests/test_api.py` | Che cosa verifica | Esito |
|---|---|---|---|
| A1 | `test_health_home_services_and_events` | La pagina si carica; le API restituiscono servizi ed eventi | Superato |
| A2 | `test_demo_data_belongs_to_fictional_cultural_centre` | I dati dimostrativi: 5 servizi, 6 eventi, 6 partecipanti con email di fantasia, indicatori attesi | Superato |
| A3 | `test_demo_data_can_be_reset` | Il ripristino riporta i dati allo stato iniziale | Superato |
| A4 | `test_service_validation_crud_and_delete_conflict` | Servizio: dati non validi rifiutati, creazione, modifica, eliminazione; rifiuto se ha eventi | Superato |
| A5 | `test_event_create_update_delete_and_capacity_rule` | Evento: creazione, modifica, eliminazione; capienza non riducibile sotto i posti prenotati | Superato |
| A6 | `test_event_cannot_be_scheduled_for_suspended_service` | Nessun evento per un servizio sospeso | Superato |
| A7 | `test_booking_capacity_duplicate_and_participant_list` | Prenotazione entro capienza; rifiuto di duplicati, posti insufficienti e dati non validi; elenco partecipanti | Superato |
| A8 | `test_booking_is_closed_after_event` | Nessuna prenotazione per un evento concluso | Superato |
| A9 | `test_booking_cancellation_frees_seats` | L'annullamento libera i posti | Superato |
| A10 | `test_feedback_requires_completed_event_and_rejects_duplicate` | Feedback solo dopo l'evento, una volta sola, voto da 1 a 5; evento con feedback non eliminabile | Superato |
| A11 | `test_users_registry_reuses_email_and_counts_activity` | Stessa email, anche con maiuscole diverse, uguale a un solo partecipante; conteggi corretti | Superato |
| A12 | `test_dashboard_aggregates_current_data` | Gli indicatori riflettono i dati inseriti | Superato |
| A13 | `test_invalid_json_and_missing_resources_return_api_errors` | Richieste malformate e risorse inesistenti producono errori JSON | Superato |
| A14 | `test_concurrent_bookings_never_exceed_capacity` | Dieci prenotazioni contemporanee per un evento da 3 posti: ne vengono accettate esattamente 3 | Superato |
| A15 | `test_feedback_is_reserved_to_participants` | Feedback rifiutato a chi non ha prenotato l'evento, accettato dopo la prenotazione | Superato |
| A16 | `test_event_cannot_be_moved_to_suspended_service` | Un evento non può essere spostato su un servizio sospeso; resta modificabile se è il suo servizio a essere sospeso | Superato |
| A17 | `test_booking_requires_privacy_acknowledgement` | Prenotazione rifiutata senza la conferma di lettura dell'informativa | Superato |
| A18 | `test_existing_participant_name_is_not_overwritten` | Una nuova prenotazione con la stessa email non modifica il nome registrato | Superato |

Il test A14 rende certa la sovrapposizione tra le richieste: sostituisce la connessione al database con una che si ferma per 50 millisecondi dopo aver letto i posti occupati. Togliendo `BEGIN IMMEDIATE` dalla prenotazione, lo stesso test accetta 10 prenotazioni su 3 posti e fallisce.

## Scenari d'uso

Gli scenari partono dai dati dimostrativi appena ripristinati.

### Vista Visitatore

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| S1 | Aprire la pagina e scorrere *Servizi culturali* e *Programma degli eventi* | 4 servizi attivi; 4 eventi *In programma* e 2 *Conclusi*; nessuno strumento di gestione visibile | Superato |
| S2 | *Racconti brevi ad alta voce* → **Prenota un posto** → nome ed email, 1 posto → **Conferma** senza spuntare l'informativa; poi spuntarla → **Conferma** | Il primo invio è bloccato dal browser, che chiede di spuntare la casella; poi avviso «Prenotazione registrata» e l'evento mostra «Posti esauriti» e 0 / 8 | Superato |
| S3 | *Visita guidata: storie del quartiere* → prenotare con `giulia.demo@example.com` | Avviso «Esiste già una prenotazione per questa email e questo evento»; posti invariati | Superato |
| S4 | *Dialogo con l'archivista*, concluso → **Condividi un feedback** → voto e commento con un'email che non ha prenotato → **Invia**; poi ripetere con `luca.campione@example.com` → aprire **Feedback ricevuti** | Primo invio rifiutato: «Il feedback è riservato a chi ha prenotato questo evento»; il secondo produce l'avviso «Feedback ricevuto», il commento compare in elenco e i feedback passano da 2 a 3 | Superato |

Scenario S1, prima della prenotazione: l'evento ha un posto disponibile su otto.

![Vista visitatore: programma degli eventi](screenshot/programma_visitatore.png)

Scenario S2, dopo la prenotazione: avviso di conferma e posti esauriti.

![Prenotazione registrata e posti esauriti](screenshot/prenotazione_confermata.png)

### Vista Operatore

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| S5 | Selezionare **Operatore** in alto a destra | Compare la fascia «Vista operatore»; il catalogo mostra anche il servizio *Sospeso*; compaiono i comandi di gestione e le sezioni *Partecipanti* e *Indicatori* | Superato |
| S6 | **Gestione del catalogo** → compilare tutti i campi → **Aggiungi al catalogo** | Avviso «Servizio aggiunto al catalogo»; la nuova scheda compare | Superato |
| S7 | Su un servizio: **Modifica** → cambiare i destinatari → **Salva modifiche** | Il modulo si riempie con i dati attuali; dopo il salvataggio la scheda mostra il nuovo valore | Superato |
| S8 | **Gestione del programma** → scegliere il servizio, compilare → **Pubblica evento** | Il servizio sospeso non è selezionabile; avviso «Evento pubblicato nel programma»; il nuovo evento compare tra quelli in programma | Superato |
| S9 | *Parole in viaggio* → **Modifica evento** → capienza 3 → **Salva**; poi capienza 20 → **Salva** | Primo tentativo rifiutato: «La capienza non può essere inferiore ai posti già prenotati»; secondo accettato | Superato |
| S10 | *Racconti brevi ad alta voce* → **Partecipanti** → **Annulla** su una prenotazione | Elenco con nome, email e posti; dopo l'annullamento i posti tornano disponibili | Superato |
| S11 | **Rimuovi** su un servizio con eventi; **Rimuovi evento** su un evento con prenotazioni; poi rimuovere l'evento e il servizio creati in S6 e S8 | I primi due rifiutati con messaggio; gli ultimi due accettati | Superato |
| S12 | Scorrere *Anagrafica dei partecipanti* e *Attività in sintesi* | Una riga per persona con prenotazioni, posti e feedback; 8 indicatori e barre di occupazione coerenti con i dati | Superato |

Scenario S10: l'elenco dei partecipanti comprende la prenotazione dello scenario S2.

![Vista operatore: partecipanti di un evento](screenshot/partecipanti_operatore.png)

Scenario S12: gli indicatori tengono conto della prenotazione dello scenario S2, con 17 prenotazioni, 49 posti e un'occupazione degli eventi futuri del 37,8%, cioè 34 posti su 90.

![Vista operatore: indicatori di attività](screenshot/indicatori_operatore.png)

### Adattamento allo schermo e collegamento

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| S13 | Restringere la finestra del browser fino alla larghezza di un telefono | Menu e contenuti si dispongono su una colonna; nessuno scorrimento orizzontale | Superato a 375 pixel |
| S14 | Con la pagina aperta, chiudere il programma di avvio e premere un pulsante; poi riavviare | Compare la fascia rossa «Il prototipo è spento» con le istruzioni; al riavvio la fascia sparisce entro pochi secondi e i pulsanti tornano a funzionare | Superato, simulando l'interruzione del collegamento |

### Avvio

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| S15 | Doppio clic su `Avvia Aurora` | Si apre la finestra di testo e poi il browser sulla pagina del prototipo | Superato su macOS. Non provato su Windows |
| S16 | Doppio clic su `Ripristina dati demo`, risposta `s` | I dati tornano a 5 servizi, 6 eventi, 16 prenotazioni, 5 feedback | Non eseguito con il doppio clic |

Il ripristino dello scenario S16 è comunque coperto dal test automatico A3 e dall'avvio con l'opzione `--reset-demo`.

## Valori di riferimento dei dati dimostrativi

Dopo il ripristino, la sezione *Attività in sintesi* mostra:

| Indicatore | Valore |
|---|---|
| Servizi a catalogo | 5 |
| Eventi futuri | 4 |
| Partecipanti registrati | 6 |
| Prenotazioni | 16 |
| Posti prenotati | 48 |
| Feedback ricevuti | 5 |
| Valutazione media | 4,2 / 5 |
| Occupazione eventi futuri | 36,7% |

L'occupazione si verifica così: gli eventi futuri hanno capienza 8 + 24 + 18 + 40 = 90 e posti prenotati 7 + 9 + 7 + 10 = 33; 33 ÷ 90 = 36,7%.

## Casi non coperti

- Browser diversi: la verifica manuale è avvenuta su un solo browser.
- Carico: nessuna prova con molti utenti.
- Accessibilità: nessuna verifica con lettori di schermo.
