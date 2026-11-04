@echo off
setlocal
set "ROOT=%~dp0"
if "%~1"=="" (
  echo Drag a brief file onto start-ppt.cmd, or enter the brief path here.
  set /p "BRIEF=Brief path: "
) else (
  set "BRIEF=%~1"
)
if not exist "%BRIEF%" (
  echo Brief file not found: "%BRIEF%"
  pause
  exit /b 2
)
if not exist "%ROOT%..\ppt-jobs" mkdir "%ROOT%..\ppt-jobs"
set "JOB=%ROOT%..\ppt-jobs\deck-%RANDOM%-%RANDOM%"
python "%ROOT%tools\ppt.py" generate --brief "%BRIEF%" --job "%JOB%"
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo The run needs attention. Your job files were kept at "%JOB%".
echo Press any key to close this window.
pause >nul
exit /b %RESULT%
