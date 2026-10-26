@echo off
setlocal
set "DEST=%USERPROFILE%\guardian"
echo Installing Guardian to %DEST% ...
where py >nul 2>nul || where python >nul 2>nul || (echo Python not found. Install from https://python.org and tick "Add to PATH". & exit /b 1)
if /I not "%~dp0"=="%DEST%\" (
  xcopy /E /I /Y "%~dp0" "%DEST%" >nul
)
powershell -NoProfile -Command "$p=[Environment]::GetEnvironmentVariable('Path','User'); if(($p -split ';') -notcontains '%DEST%'){[Environment]::SetEnvironmentVariable('Path',($p.TrimEnd(';')+';%DEST%'),'User')}"
echo.
echo Done. Close this window, open a NEW terminal, then run:
echo     guardian run %DEST%\demo.grd
endlocal
