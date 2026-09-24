@echo off
chcp 65001 > nul
title App Avisos de Averia - Agenor Mantenimientos
cd /d "%~dp0"

echo ========================================================
echo   INICIANDO APLICACION EXTRACTOR DE S/N Y CORREO
echo ========================================================
echo.

:: Localizar Python real evitando el alias de Windows Store
set "PY_EXE="

if exist "%LOCALAPPDATA%\Programs\Python311\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python311\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else if exist "%ProgramFiles%\Python311\python.exe" (
    set "PY_EXE=%ProgramFiles%\Python311\python.exe"
) else (
    py -3.11 --version >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_EXE=py -3.11"
    ) else (
        py --version >nul 2>nul
        if %errorlevel% equ 0 (
            set "PY_EXE=py"
        ) else (
            set "PY_EXE=python"
        )
    )
)

:: Agregar Tesseract al PATH si existe
if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR" (
    set "PATH=%LOCALAPPDATA%\Programs\Tesseract-OCR;%PATH%"
)
if exist "%ProgramFiles%\Tesseract-OCR" (
    set "PATH=%ProgramFiles%\Tesseract-OCR;%PATH%"
)

echo [1/2] Comprobando Python y dependencias...
echo Usando Python en: %PY_EXE%
"%PY_EXE%" -m pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo [AVISO] Continuando con paquetes existentes...
)

echo [2/2] Abriendo aplicacion en el navegador...
start http://127.0.0.1:8000

echo.
echo ========================================================
echo   Servidor en ejecucion en http://127.0.0.1:8000
echo   Para cerrar la aplicacion, cierre esta ventana.
echo ========================================================
echo.

"%PY_EXE%" app.py

pause
