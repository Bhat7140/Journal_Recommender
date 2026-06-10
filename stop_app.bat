@echo off
setlocal

echo Stopping Journal Recommender backend and frontend...

for %%P in (8787 5173) do (
    for /f "tokens=5" %%I in ('netstat -ano ^| findstr /R /C:":%%P .*LISTENING"') do (
        echo Stopping process %%I on port %%P
        taskkill /F /T /PID %%I >nul 2>nul
    )
)

echo.
echo Done. If any app command windows remain open, you can close them.
endlocal
