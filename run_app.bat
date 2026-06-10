@echo off
setlocal

set "ROOT=%~dp0"
set "UI_DIR=%ROOT%ui"

if not exist "%UI_DIR%\package.json" (
    echo Could not find ui\package.json.
    echo Run this file from the Journal_Recommender project root.
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo npm was not found on PATH. Install Node.js or add npm to PATH.
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo python was not found on PATH. Install Python or add it to PATH.
    pause
    exit /b 1
)

if not exist "%UI_DIR%\node_modules" (
    echo ui\node_modules was not found.
    echo Run this once before starting the app:
    echo.
    echo     cd /d "%UI_DIR%"
    echo     npm install
    echo.
    pause
    exit /b 1
)

echo Checking OpenSearch at http://localhost:9200 ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:9200' -UseBasicParsing -TimeoutSec 5; exit 0 } catch { exit 1 }"
if errorlevel 1 (
    echo.
    echo OpenSearch is not responding at http://localhost:9200.
    echo Start your OpenSearch Docker container first, then run this file again.
    pause
    exit /b 1
)

echo Starting Journal Recommender backend on http://127.0.0.1:8787 ...
start "Journal Recommender API" cmd /k "cd /d ""%UI_DIR%"" && npm run dev:api"

echo Starting Journal Recommender frontend on http://127.0.0.1:5173 ...
start "Journal Recommender UI" cmd /k "cd /d ""%UI_DIR%"" && npm run dev -- --host 127.0.0.1"

echo.
echo App is starting. Open this URL in your browser:
echo.
echo     http://127.0.0.1:5173/
echo.
echo To stop the app, run stop_app.bat.
endlocal
