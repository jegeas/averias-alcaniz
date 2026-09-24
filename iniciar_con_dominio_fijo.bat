@echo off
title Avisos de Averia - Dominio Fijo Permanente
cd /d "%~dp0"

:: 1. Localizar Python real
set "PY_EXE="
if exist "%LOCALAPPDATA%\Programs\Python311\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python311\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else (
    set "PY_EXE=python"
)

:: 2. Agregar Tesseract al PATH si existe
if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR" (
    set "PATH=%LOCALAPPDATA%\Programs\Tesseract-OCR;%PATH%"
)

:: 3. Iniciar aplicacion y tunel con dominio fijo
"%PY_EXE%" run_permanent_tunnel.py

pause
