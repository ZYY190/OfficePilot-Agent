@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
python -m agent.web_app
endlocal
