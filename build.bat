@echo off
chcp 65001 > nul
echo ========================================================
echo   HandBrake Auto AV1-10bit - EXE Ersteller
echo ========================================================
echo.
python build_exe.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Fehler beim Erstellen der EXE aufgetreten!
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo Fertig! Die fertige EXE liegt im Ordner "dist\HandBrakeAutoAV1.exe"
pause
