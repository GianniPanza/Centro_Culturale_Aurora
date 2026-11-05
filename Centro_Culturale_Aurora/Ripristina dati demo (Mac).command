#!/bin/bash
# Ricarica i dati dimostrativi con date aggiornate a oggi e avvia il prototipo (macOS).

cd "$(dirname "$0")" || exit 1

echo "Questa operazione CANCELLA servizi, eventi, prenotazioni e feedback inseriti finora"
echo "e ricarica i dati di esempio, con gli eventi ricalcolati rispetto alla data di oggi."
echo
read -r -p "Vuoi continuare? Scrivi s e premi INVIO: " risposta
if [ "$risposta" != "s" ] && [ "$risposta" != "S" ]; then
  echo "Operazione annullata: i dati non sono stati modificati."
  read -r -p "Premi INVIO per chiudere questa finestra."
  exit 0
fi

"./Avvia Aurora (Mac).command" --reset-demo
