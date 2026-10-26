@echo off
where py >nul 2>nul && (py -3 "%~dp0guardian.py" %*) || (python "%~dp0guardian.py" %*)
