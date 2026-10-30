@echo off
rem Ricarica i dati dimostrativi con date aggiornate a oggi e avvia il prototipo (Windows).
chcp 65001 >nul
cd /d "%~dp0"

echo Questa operazione CANCELLA servizi, eventi, prenotazioni e feedback inseriti finora
echo e ricarica i dati di esempio, con gli eventi ricalcolati rispetto alla data di oggi.
echo.
set /p risposta="Vuoi continuare? Scrivi s e premi INVIO: "
if /i not "%risposta%"=="s" (
  echo Operazione annullata: i dati non sono stati modificati.
  pause
  exit /b 0
)

call "Avvia Aurora (Windows).bat" --reset-demo
