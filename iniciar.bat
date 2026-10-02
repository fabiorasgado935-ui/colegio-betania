@echo off
cd /d "%~dp0"
where python >nul 2>nul && (set PY=python) || (set PY=py)
if not exist venv (%PY% -m venv venv)
call venv\Scripts\activate
pip install -r requirements.txt
if not exist betania.db %PY% database.py
echo.
echo Abra no navegador: http://127.0.0.1:5000
python app.py
pause
