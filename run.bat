@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -B -m src.server %*
) else (
    py -B -m src.server %*
)
