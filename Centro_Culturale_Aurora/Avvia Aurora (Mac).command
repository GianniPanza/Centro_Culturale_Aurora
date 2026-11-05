#!/bin/bash
# Avvia il prototipo del Centro Culturale Aurora con un doppio clic (macOS).
# Uso avanzato: aggiungere --reset-demo per ricaricare i dati dimostrativi.

cd "$(dirname "$0")" || exit 1

chiudi_con_errore() {
  echo
  echo "ERRORE: $1"
  echo
  read -r -p "Premi INVIO per chiudere questa finestra."
  exit 1
}

command -v python3 >/dev/null 2>&1 || chiudi_con_errore \
  "Python 3 non è installato. Scaricalo da https://www.python.org/downloads/ e riprova."

# L'ambiente virtuale non funziona se la cartella è stata spostata o copiata: in quel caso si ricrea.
if [ -d ".venv" ] && ! .venv/bin/python -c "import sys" >/dev/null 2>&1; then
  rm -rf .venv
fi

if [ ! -d ".venv" ]; then
  echo "Prima esecuzione: preparo l'ambiente (serve la connessione a Internet, circa un minuto)..."
  python3 -m venv .venv || chiudi_con_errore "Non riesco a creare l'ambiente Python."
fi

if ! .venv/bin/python -c "import flask" >/dev/null 2>&1; then
  .venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt \
    || chiudi_con_errore "Non riesco a installare Flask. Controlla la connessione a Internet."
fi

.venv/bin/python avvia.py "$@"
