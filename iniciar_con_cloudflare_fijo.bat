@echo off
title Avisos de Averia - Tunel Cloudflare Oficial
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_cloudflare_named_tunnel.ps1"
pause
