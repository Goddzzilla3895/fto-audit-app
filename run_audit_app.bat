@echo off
title Marigold Aviation - FTO Audit System
color 1F

echo =====================================================================
echo                MARIGOLD AVIATION - FTO AUDIT SYSTEM
echo =====================================================================
echo.
echo Starting the central audit server...
echo.

cd /d "C:\Users\sunny\.gemini\antigravity\scratch\fto_audit_app"

start "" http://localhost:8000

python server.py

pause
