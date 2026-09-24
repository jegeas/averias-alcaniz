@echo off
title Avisos de Averia - Acceso Remoto Cloudflare
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_with_tunnel.ps1"
pause
