@echo off
chcp 65001 > nul
title Configurar Inicio Automatico con Windows
cd /d "%~dp0"

echo ========================================================
echo   CONFIGURAR INICIO AUTOMATICO CON WINDOWS
echo ========================================================
echo.

set "TARGET_BAT=%~dp0iniciar_con_dominio_fijo.bat"
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Avisos_Averias.lnk"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%TARGET_BAT%'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.WindowStyle = 7; $Shortcut.Save(); Write-Host 'Acceso directo de inicio automatico creado con exito!' -ForegroundColor Green"

echo.
echo ========================================================
echo   La aplicacion se iniciara automaticamente en segundo
echo   plano cada vez que inicies sesion en tu ordenador.
echo ========================================================
echo.
pause
