@echo off
echo.
echo  Protellect ^| Protein Triage Platform
echo  =======================================
echo.

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt -q

echo.
echo Starting Protellect at http://localhost:8501
echo Press Ctrl+C to stop
echo.

streamlit run app.py
pause
