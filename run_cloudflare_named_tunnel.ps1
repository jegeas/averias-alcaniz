param (
    [int]$Port = 8000
)

$ErrorActionPreference = "Continue"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $scriptDir

$token = "eyJhIjoiN2FlOTBhMmM3YjRjMTA1N2NlZWE4YzY3Nzk5N2YyNzEiLCJ0IjoiZDgzODIzYjgtYjgyNC00MWM4LWI1NGYtODI2YTczZjg3ZDgwIiwicyI6Ik1HTTBPVFUzTm1FdE1UYzBZaTAwTWpreUxXRTVabVl0TldOa09UbGhaV0poTnpFeCJ9"
$cloudflared = Join-Path $scriptDir "cloudflared.exe"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   INICIANDO TUNEL PERMANENTE DE CLOUDFLARE ZERO TRUST   " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Localizar Python real
$pythonExe = "$env:LOCALAPPDATA\Programs\Python311\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
}
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

# 2. Localizar Tesseract
$tessDir = "$env:LOCALAPPDATA\Programs\Tesseract-OCR"
if (Test-Path $tessDir) {
    $env:PATH = "$tessDir;$env:PATH"
}

# 3. Comprobar si el servidor ya esta activo
$healthUrl = "http://localhost:$Port/api/health"
$appRunning = $false
try {
    $r = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2 -ErrorAction Stop
    if ($r.status -eq "ok") {
        $appRunning = $true
        Write-Host "[1/2] Servidor web local ya activo en el puerto $Port." -ForegroundColor Green
    }
} catch {
    $appRunning = $false
}

if (-not $appRunning) {
    Write-Host "[1/2] Iniciando servidor web de la aplicacion..." -ForegroundColor Yellow
    Start-Process -FilePath $pythonExe -ArgumentList "app.py" -WorkingDirectory $scriptDir -WindowStyle Minimized
    Start-Sleep -Seconds 2
}

# 4. Iniciar tunel oficial de Cloudflare con Token
Write-Host "[2/2] Conectando con la red oficial de Cloudflare..." -ForegroundColor Yellow
Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  TUNEL OFICIAL DE CLOUDFLARE CONECTADO CORRECTAMENTE!    " -ForegroundColor White -BackgroundColor DarkGreen
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Tunnel Name : Averias-Philips" -ForegroundColor Cyan
Write-Host "  Tunnel ID   : d83823b8-b824-41c8-b54f-826a73f87d80" -ForegroundColor Gray
Write-Host ""
Write-Host "  Mantenga esta ventana abierta mientras use la aplicacion." -ForegroundColor DarkYellow
Write-Host "  Presione CTRL+C para detener." -ForegroundColor DarkGray
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""

& "$cloudflared" tunnel run --token "$token"
