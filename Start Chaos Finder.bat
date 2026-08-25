@echo off
cd /d "%~dp0"

rem --- make sure the files were actually extracted (not run from inside the zip) ---
if not exist "chaos_app.py" goto notextracted
if not exist "chaos_tool.html" goto notextracted

rem --- make sure Python is available ---
where python >nul 2>nul && goto run
where py >nul 2>nul && goto run
goto nopython

:run
echo Starting Chaos Finder... your browser will open in a moment.
python chaos_app.py 2>nul || py chaos_app.py
echo.
echo Chaos Finder stopped. You can close this window.
pause
exit /b

:notextracted
echo.
echo   The Chaos Finder files aren't all here.
echo.
echo   Please EXTRACT the whole zip first: right-click the .zip, choose
echo   "Extract All", then open the extracted folder and run this file
echo   from there. (Running it from inside the zip won't work.)
echo.
echo   Or, to just browse builds with nothing to install, double-click
echo   "Chaos Agents Build Finder.html".
echo.
pause
exit /b

:nopython
echo.
echo   Python isn't installed, so the live-refresh version can't start.
echo.
echo   To just browse builds (no install needed), double-click
echo   "Chaos Agents Build Finder.html" instead.
echo.
echo   To use the Refresh button, install Python from
echo   https://www.python.org/downloads/  (tick "Add Python to PATH"
echo   on the first screen), then run this file again.
echo.
pause
exit /b
