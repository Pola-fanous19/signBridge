@echo off
cd /d "C:\Users\Pola\Documents\signbridge\signbridge-v4\backend"
"C:\Users\Pola\Documents\signbridge\signbridge-v4\backend\.venv\Scripts\python.exe" -m flask --app app.main run --host 0.0.0.0 --port 8000
