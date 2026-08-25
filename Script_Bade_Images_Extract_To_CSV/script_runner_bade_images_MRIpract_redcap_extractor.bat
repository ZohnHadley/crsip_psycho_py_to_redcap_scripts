@echo off
setlocal

echo Checking for Python...
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    set "PY=py"
    echo Found Python Launcher.
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        set "PY=python"
        echo Found Python.
    ) else (
        echo Python was not found.
        pause
        exit /b 1
    )
)

echo.
echo Installing/updating required packages...
echo.

%PY% -m pip install colorama pandas regex

if errorlevel 1 (
    echo.
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Dependencies ready.
echo.
echo Running script...
echo.

%PY% script_source_bade_images_MRI_redcap_extractor.py

echo.
echo Script finished.
pause