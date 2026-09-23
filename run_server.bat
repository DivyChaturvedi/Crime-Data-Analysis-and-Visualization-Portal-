@echo off
title CDAVP - Crime Intelligence & Public Safety Portal
echo ================================================================
echo   CDAVP - Crime Detection, Analysis & Visualization Platform
echo ================================================================
echo.
echo [1/3] Checking dependencies...
python -m pip install -r requirements.txt --quiet

echo.
echo [2/3] Applying database migrations...
python manage.py migrate

echo.
echo [3/3] Launching CDAVP Development Server...
echo ================================================================
echo   Portal is running at: http://127.0.0.1:8000/
echo.
echo   Demo Credentials:
echo   - Super Admin: admin / Admin@2026
echo   - Police Officer: officer1 / Officer@2026
echo   - Citizen User: citizen1 / Citizen@2026
echo ================================================================
echo.
python manage.py runserver 0.0.0.0:8000
pause
