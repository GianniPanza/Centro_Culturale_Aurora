@echo off
rem Avvia il prototipo del Centro Culturale Aurora con un doppio clic (Windows).
rem Uso avanzato: aggiungere --reset-demo per ricaricare i dati dimostrativi.
chcp 65001 >nul
cd /d "%~dp0"

set "PY=python"
where py >nul 2>nul && set "PY=py -3"
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo ERRORE: Python 3 non e' installato. Scaricalo da https://www.python.org/downloads/
  echo Durante l'installazione seleziona "Add python.exe to PATH", poi riprova.
  pause
  exit /b 1
)

rem L'ambiente virtuale non funziona se la cartella e' stata spostata o copiata: in quel caso si ricrea.
if exist ".venv" (
  ".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
  if errorlevel 1 rmdir /s /q ".venv"
)

if not exist ".venv" (
  echo Prima esecuzione: preparo l'ambiente. Serve la connessione a Internet, circa un minuto...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo ERRORE: non riesco a creare l'ambiente Python.
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -c "import flask" >nul 2>nul
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt
  if errorlevel 1 (
    echo ERRORE: non riesco a installare Flask. Controlla la connessione a Internet.
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" avvia.py %*
pause
