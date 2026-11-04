@echo off
setlocal
set "ROOT=%~dp0"
python "%ROOT%tools\ppt.py" install %*
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo Installation was not completed.
pause
exit /b %RESULT%
