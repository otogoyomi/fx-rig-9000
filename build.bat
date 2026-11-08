@echo off
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py) || (set PY=python)
%PY% -m pip install --upgrade pyinstaller
if errorlevel 1 goto err
%PY% build.py
if errorlevel 1 goto err
pause
exit /b 0
:err
echo failed
pause
exit /b 1
