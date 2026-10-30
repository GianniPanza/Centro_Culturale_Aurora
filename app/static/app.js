const notice = document.querySelector("#notice");
let noticeTimer;
const state = { role: "visitatore", services: [], events: [], loaded: false };

function showNotice(message, isError = false) {
  notice.textContent = message;
  notice.classList.toggle("error", isError);
  notice.classList.add("show");
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => notice.classList.remove("show"), 4200);
}

// Se il programma di avvio viene chiuso, la pagina resta aperta ma il back-end non risponde più:
// lo si segnala e si riprova finché non torna disponibile.
const offlineBanner = document.querySelector("#offline-banner");
let reconnectTimer = null;

function setOffline(isOffline) {
  offlineBanner.hidden = !isOffline;
  if (!isOffline) {
    clearInterval(reconnectTimer);
    reconnectTimer = null;
  } else if (!reconnectTimer) {
    reconnectTimer = setInterval(async () => {
      try {
        if (!(await fetch("/api/health")).ok) return;
      } catch (error) {
        return;
      }
      setOffline(false);
      await refreshAll();
      showNotice("Il prototipo è di nuovo in esecuzione.");
    }, 3000);
  }
}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
  } catch (error) {
    setOffline(true);
    throw new Error("Il prototipo è spento: fai doppio clic su «Avvia Aurora» e riprova.");
  }
  setOffline(false);
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || "Si è verificato un errore.");
  return body.data;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function formatDate(value) {
  return new Intl.DateTimeFormat("it-IT", {
    weekday: "short", day: "2-digit", month: "long", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  }).format(new Date(value));
}

// Le date di registrazione sono salvate da SQLite in UTC, quelle degli eventi in ora locale.
function formatRegistration(value) {
  return new Intl.DateTimeFormat("it-IT", { day: "2-digit", month: "long", year: "numeric" })
    .format(new Date(`${String(value).replace(" ", "T")}Z`));
}

function formatSeats(count) {
  return `${count} ${Number(count) === 1 ? "posto" : "posti"}`;
}

function isPast(value) {
  return new Date(value) <= new Date();
}

// La vista scelta cambia solo ciò che la pagina mostra: non è un controllo di accesso.
function setRole(role) {
  state.role = role === "operatore" ? "operatore" : "visitatore";
  document.body.dataset.role = state.role;
  document.querySelectorAll("[data-role-choice]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.roleChoice === state.role));
  });
  try {
    localStorage.setItem("aurora-vista", state.role);
  } catch (error) {
    // La preferenza non viene ricordata se il browser blocca la memoria locale.
  }
  if (state.loaded) renderServices();
}

function storedRole() {
  try {
    return localStorage.getItem("aurora-vista");
  } catch (error) {
    return null;
  }
}

function renderServices() {
  const container = document.querySelector("#services-list");
  const visible = state.role === "operatore"
    ? state.services
    : state.services.filter((service) => service.status === "Attivo");
  container.setAttribute("aria-busy", "false");
  container.innerHTML = visible.map((service) => `
    <article class="service-card">
      <div class="service-topline"><span class="service-category">${escapeHtml(service.category)}</span>
        <span class="status-pill ${service.status === "Attivo" ? "is-active" : "is-paused"}">${escapeHtml(service.status)}</span></div>
      <h3>${escapeHtml(service.title)}</h3>
      <p>${escapeHtml(service.description)}</p>
      <div class="service-meta"><span>${escapeHtml(service.duration_minutes)} min</span><span>${escapeHtml(service.audience)}</span></div>
      <div class="card-actions operator-only">
        <button class="text-button" type="button" data-edit-service="${service.id}">Modifica</button>
        <button class="text-button" type="button" data-delete-service="${service.id}">Rimuovi</button>
      </div>
    </article>`).join("") || '<p class="empty-state">Il catalogo è vuoto. Aggiungi un servizio culturale dalla vista operatore.</p>';
}

function renderServiceOptions(alwaysEnabledId) {
  const selector = document.querySelector("#event-service");
  selector.innerHTML = state.services.map((service) => {
    const selectable = service.status === "Attivo" || service.id === alwaysEnabledId;
    return `<option value="${service.id}" ${selectable ? "" : "disabled"}>${escapeHtml(service.title)}${service.status === "Attivo" ? "" : " (sospeso)"}</option>`;
  }).join("");
  const hasActive = state.services.some((service) => service.status === "Attivo");
  selector.disabled = state.services.length === 0;
  document.querySelector("#event-form button[type=submit]").disabled = !hasActive && !alwaysEnabledId;
}

async function loadServices() {
  state.services = await api("/api/services");
  state.loaded = true;
  renderServices();
  renderServiceOptions();
}

function bookingForm(event) {
  if (event.available_seats < 1) {
    return '<p class="sold-out">Posti esauriti</p>';
  }
  const optionCount = Math.min(20, event.available_seats);
  return `<details class="inline-panel"><summary>Prenota un posto</summary>
    <form class="booking-form" data-book-event="${event.id}">
      <label>Nome<input name="name" required minlength="2" maxlength="100" autocomplete="name"></label>
      <label>Email<input name="email" type="email" required maxlength="254" autocomplete="email"></label>
      <label>Posti<select name="seats">${Array.from({ length: optionCount }, (_, index) =>
        `<option value="${index + 1}">${index + 1}</option>`).join("")}</select></label>
      <button class="button button-dark" type="submit">Conferma prenotazione</button>
    </form></details>`;
}

function feedbackForm(event) {
  return `<details class="inline-panel"><summary>Condividi un feedback</summary>
    <form class="feedback-form" data-feedback-event="${event.id}">
      <label>Nome<input name="name" required minlength="2" maxlength="100" autocomplete="name"></label>
      <label>Email<input name="email" type="email" required maxlength="254" autocomplete="email"></label>
      <label>Valutazione<select name="rating"><option value="5">5 — Molto positivo</option><option value="4">4 — Positivo</option><option value="3">3 — Nella media</option><option value="2">2 — Da migliorare</option><option value="1">1 — Non soddisfacente</option></select></label>
      <label class="span-all">Commento<textarea name="comment" required minlength="3" maxlength="1000" rows="3"></textarea></label>
      <button class="button button-dark" type="submit">Invia feedback</button>
    </form></details>`;
}

function eventCard(event) {
  const past = isPast(event.starts_at);
  const booked = Number(event.booked_seats);
  const fill = event.capacity ? Math.min(100, booked / event.capacity * 100) : 0;
  const seatsLabel = past ? "Posti prenotati" : "Posti disponibili";
  const seatsValue = past ? booked : event.available_seats;
  return `<article class="event-card ${past ? "event-past" : ""}">
    <div class="event-date"><span>${escapeHtml(formatDate(event.starts_at))}</span><span class="event-state">${past ? "Concluso" : "In programma"}</span></div>
    <p class="event-service">${escapeHtml(event.service_title)}</p>
    <h3>${escapeHtml(event.title)}</h3>
    <p class="event-description">${escapeHtml(event.description)}</p>
    <div class="event-venue"><span aria-hidden="true">⌖</span> ${escapeHtml(event.venue)}</div>
    <div class="event-availability"><div class="availability-copy"><span>${seatsLabel}</span><strong>${escapeHtml(seatsValue)} <small>/ ${escapeHtml(event.capacity)}</small></strong></div>
      <div class="mini-track" aria-label="${escapeHtml(booked)} prenotati su ${escapeHtml(event.capacity)} posti"><span style="width:${fill}%"></span></div>
      ${past ? "" : bookingForm(event)}
    </div>
    ${past ? `${feedbackForm(event)}
    <details class="inline-panel feedback-panel" data-panel-key="feedback-${event.id}" data-feedback-panel="${event.id}">
      <summary>Feedback ricevuti (${escapeHtml(event.feedback_count)}${event.average_rating ? ` · media ${escapeHtml(event.average_rating)}/5` : ""})</summary>
      <div class="feedback-list"><p class="muted-copy">Apri per caricare i commenti.</p></div>
    </details>` : ""}
    <details class="inline-panel roster-panel operator-only" data-panel-key="bookings-${event.id}" data-bookings-panel="${event.id}">
      <summary>Partecipanti (${escapeHtml(formatSeats(event.booked_seats))})</summary>
      <div class="attendee-list"><p class="muted-copy">Apri per consultare le prenotazioni.</p></div>
    </details>
    <div class="card-actions operator-only">
      <button class="text-button" type="button" data-edit-event="${event.id}">Modifica evento</button>
      <button class="text-button" type="button" data-delete-event="${event.id}">Rimuovi evento</button>
    </div>
  </article>`;
}

function eventGroup(title, events, emptyMessage) {
  if (!events.length && !emptyMessage) return "";
  return `<h3 class="group-title">${title} <span>${events.length}</span></h3>
    <div class="events-grid">${events.map(eventCard).join("") || `<p class="empty-state">${emptyMessage}</p>`}</div>`;
}

function renderEvents() {
  const container = document.querySelector("#events-list");
  const openPanels = [...container.querySelectorAll("details[open][data-panel-key]")]
    .map((panel) => panel.dataset.panelKey);
  const upcoming = state.events.filter((event) => !isPast(event.starts_at));
  const past = state.events.filter((event) => isPast(event.starts_at)).reverse();
  container.setAttribute("aria-busy", "false");
  container.innerHTML = eventGroup("In programma", upcoming, "Non ci sono eventi in programma.")
    + eventGroup("Conclusi", past, "");
  openPanels.forEach((key) => {
    const panel = container.querySelector(`[data-panel-key="${key}"]`);
    if (panel) panel.open = true;
  });
}

async function loadEvents() {
  state.events = await api("/api/events");
  renderEvents();
}

async function loadUsers() {
  const users = await api("/api/users");
  const container = document.querySelector("#users-list");
  container.setAttribute("aria-busy", "false");
  container.innerHTML = users.length ? `<table class="data-table">
    <thead><tr><th>Nome</th><th>Email</th><th class="number">Prenotazioni</th><th class="number">Posti</th><th class="number">Feedback</th><th>Registrato il</th></tr></thead>
    <tbody>${users.map((user) => `<tr><td><strong>${escapeHtml(user.name)}</strong></td><td>${escapeHtml(user.email)}</td>
      <td class="number">${escapeHtml(user.booking_count)}</td><td class="number">${escapeHtml(user.seats_reserved)}</td>
      <td class="number">${escapeHtml(user.feedback_count)}</td><td>${escapeHtml(formatRegistration(user.created_at))}</td></tr>`).join("")}</tbody>
  </table>` : '<p class="empty-state">Nessun partecipante registrato: l’anagrafica si popola con la prima prenotazione.</p>';
}

async function loadDashboard() {
  const data = await api("/api/dashboard");
  const average = data.average_rating === null ? "—" : `${Number(data.average_rating).toFixed(1)}<small> / 5</small>`;
  const stats = [
    ["Servizi a catalogo", data.service_count],
    ["Eventi futuri", data.upcoming_event_count],
    ["Partecipanti registrati", data.user_count],
    ["Prenotazioni", data.booking_count],
    ["Posti prenotati", data.seats_reserved],
    ["Feedback ricevuti", data.feedback_count],
    ["Valutazione media", average],
    ["Occupazione eventi futuri", `${Number(data.occupancy_percent).toFixed(1)}%`],
  ];
  const statContainer = document.querySelector("#dashboard-stats");
  statContainer.setAttribute("aria-busy", "false");
  statContainer.innerHTML = stats.map(([label, value], index) => `
    <article class="stat-card stat-${index + 1}"><span>${escapeHtml(label)}</span><strong>${value}</strong></article>`).join("");

  const occupancy = document.querySelector("#occupancy-list");
  occupancy.innerHTML = data.events.map((event) => {
    const percent = event.capacity ? Math.round(event.booked_seats / event.capacity * 100) : 0;
    return `<div class="occupancy-row"><div class="occupancy-title"><strong>${escapeHtml(event.title)}</strong><span>${escapeHtml(formatDate(event.starts_at))}</span></div>
      <div class="occupancy-track" role="progressbar" aria-label="Occupazione ${escapeHtml(event.title)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}"><span style="width:${percent}%"></span></div>
      <span class="occupancy-count">${escapeHtml(event.booked_seats)} / ${escapeHtml(event.capacity)} · ${percent}%</span></div>`;
  }).join("") || '<p class="muted-copy">Nessun evento futuro da mostrare.</p>';
}

async function refreshAll() {
  await loadServices();
  await Promise.all([loadEvents(), loadUsers(), loadDashboard()]);
}

function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function startEdit(form, values, id) {
  Object.entries(values).forEach(([name, value]) => {
    const field = form.elements.namedItem(name);
    if (field) field.value = value;
  });
  form.dataset.editId = id;
  form.querySelector("button[type=submit]").textContent = "Salva modifiche";
  form.querySelector("[data-cancel-edit]").hidden = false;
  form.closest("details").open = true;
  form.scrollIntoView({ behavior: "smooth", block: "center" });
}

function stopEdit(form) {
  form.reset();
  delete form.dataset.editId;
  form.querySelector("button[type=submit]").textContent = form.dataset.createLabel;
  form.querySelector("[data-cancel-edit]").hidden = true;
  if (form.id === "event-form") renderServiceOptions();
}

document.addEventListener("submit", async (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  const bookingEvent = form.dataset.bookEvent;
  const feedbackEvent = form.dataset.feedbackEvent;
  if (form.id !== "service-form" && form.id !== "event-form" && !bookingEvent && !feedbackEvent) return;
  event.preventDefault();
  const values = formValues(form);
  const editId = form.dataset.editId;

  try {
    if (form.id === "service-form") {
      values.duration_minutes = Number(values.duration_minutes);
      await api(editId ? `/api/services/${editId}` : "/api/services",
        { method: editId ? "PUT" : "POST", body: JSON.stringify(values) });
      stopEdit(form);
      showNotice(editId ? "Servizio aggiornato." : "Servizio aggiunto al catalogo.");
      await refreshAll();
    } else if (form.id === "event-form") {
      values.service_id = Number(values.service_id);
      values.capacity = Number(values.capacity);
      await api(editId ? `/api/events/${editId}` : "/api/events",
        { method: editId ? "PUT" : "POST", body: JSON.stringify(values) });
      stopEdit(form);
      showNotice(editId ? "Evento aggiornato." : "Evento pubblicato nel programma.");
      await refreshAll();
    } else if (bookingEvent) {
      values.seats = Number(values.seats);
      await api(`/api/events/${bookingEvent}/bookings`, { method: "POST", body: JSON.stringify(values) });
      showNotice("Prenotazione registrata. Grazie!");
      await refreshAll();
    } else if (feedbackEvent) {
      values.rating = Number(values.rating);
      await api(`/api/events/${feedbackEvent}/feedback`, { method: "POST", body: JSON.stringify(values) });
      showNotice("Feedback ricevuto. Grazie per aver condiviso la tua esperienza.");
      await refreshAll();
    }
  } catch (error) {
    showNotice(error.message, true);
  }
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const data = button.dataset;
  try {
    if (data.roleChoice) {
      setRole(data.roleChoice);
    } else if ("cancelEdit" in data) {
      stopEdit(button.form);
    } else if (data.editService) {
      const service = state.services.find((item) => item.id === Number(data.editService));
      startEdit(document.querySelector("#service-form"), service, service.id);
    } else if (data.editEvent) {
      const item = state.events.find((entry) => entry.id === Number(data.editEvent));
      renderServiceOptions(item.service_id);
      startEdit(document.querySelector("#event-form"), item, item.id);
    } else if (data.deleteService) {
      if (!window.confirm("Rimuovere questo servizio dal catalogo?")) return;
      await api(`/api/services/${data.deleteService}`, { method: "DELETE" });
      showNotice("Servizio rimosso dal catalogo.");
      await refreshAll();
    } else if (data.deleteEvent) {
      if (!window.confirm("Rimuovere questo evento dal programma?")) return;
      await api(`/api/events/${data.deleteEvent}`, { method: "DELETE" });
      showNotice("Evento rimosso dal programma.");
      await refreshAll();
    } else if (data.cancelBooking) {
      if (!window.confirm("Annullare questa prenotazione e liberare i posti?")) return;
      await api(`/api/bookings/${data.cancelBooking}`, { method: "DELETE" });
      showNotice("Prenotazione annullata: i posti sono di nuovo disponibili.");
      await refreshAll();
    }
  } catch (error) {
    showNotice(error.message, true);
  }
});

document.addEventListener("toggle", async (event) => {
  const panel = event.target;
  if (!(panel instanceof HTMLDetailsElement) || !panel.open) return;
  if (panel.dataset.feedbackPanel && panel.dataset.loaded !== "true") {
    const content = panel.querySelector(".feedback-list");
    try {
      const feedback = await api(`/api/events/${panel.dataset.feedbackPanel}/feedback`);
      content.innerHTML = feedback.map((item) => `
        <article class="feedback-entry"><span class="rating-stars" aria-label="Valutazione ${item.rating} su 5">${"★".repeat(item.rating)}${"☆".repeat(5 - item.rating)}</span>
          <p>${escapeHtml(item.comment)}</p><time>${escapeHtml(formatRegistration(item.created_at))}</time></article>`).join("") || '<p class="muted-copy">Non sono ancora presenti feedback.</p>';
      panel.dataset.loaded = "true";
    } catch (error) {
      content.innerHTML = `<p class="error-copy">${escapeHtml(error.message)}</p>`;
    }
  }
  if (panel.dataset.bookingsPanel && panel.dataset.loaded !== "true") {
    const content = panel.querySelector(".attendee-list");
    try {
      const bookings = await api(`/api/events/${panel.dataset.bookingsPanel}/bookings`);
      content.innerHTML = bookings.map((booking) => `
        <div class="attendee-row"><span><strong>${escapeHtml(booking.name)}</strong><small>${escapeHtml(booking.email)}</small></span>
          <span>${escapeHtml(formatSeats(booking.seats))}</span>
          <button class="text-button" type="button" data-cancel-booking="${booking.id}">Annulla</button></div>`).join("") || '<p class="muted-copy">Non risultano prenotazioni per questo evento.</p>';
      panel.dataset.loaded = "true";
    } catch (error) {
      content.innerHTML = `<p class="error-copy">${escapeHtml(error.message)}</p>`;
    }
  }
}, true);

setRole(storedRole());
refreshAll().catch((error) => showNotice(error.message, true));
