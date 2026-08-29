@echo off
title QueryDesk - Enterprise AI Customer Support
echo ========================================================
echo   Starting QueryDesk Customer Support Platform...
echo ========================================================
echo.
echo   Customer Chat UI: http://127.0.0.1:5000
echo   Admin Console:    http://127.0.0.1:5000/admin
echo   API Docs:         http://127.0.0.1:5000/docs
echo.
echo Press Ctrl+C to stop the server.
echo.

python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 5000
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Python not found on standard PATH, trying py launcher...
    py -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 5000
)
pause
