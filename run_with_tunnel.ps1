param (
    [int]$Port = 8000
)

$ErrorActionPreference = "Continue"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $scriptDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   INICIANDO AVISOS DE AVERIA CON ACCESO REMOTO MOVIL    " -ForegroundColor Yellow
Write-Host "         (Cloudflare Tunnel - 100% Gratuito y Seguro)    " -ForegroundColor Cyan
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

# 3. Localizar Cloudflared
$cloudflared = Join-Path $scriptDir "cloudflared.exe"
if (-not (Test-Path $cloudflared)) {
    Write-Host "[1/3] Descargando motor de tunel seguro Cloudflare..." -ForegroundColor Yellow
    $url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $url -OutFile $cloudflared -UseBasicParsing
}

# 4. Comprobar si el servidor ya esta activo
$healthUrl = "http://localhost:$Port/api/health"
$appRunning = $false
try {
    $r = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2 -ErrorAction Stop
    if ($r.status -eq "ok") {
        $appRunning = $true
        Write-Host "[1/2] El servidor web ya esta activo en el puerto $Port." -ForegroundColor Green
    }
} catch {
    $appRunning = $false
}

if (-not $appRunning) {
    Write-Host "[1/2] Iniciando servidor web de la aplicacion..." -ForegroundColor Yellow
    Start-Process -FilePath $pythonExe -ArgumentList "app.py" -WorkingDirectory $scriptDir -WindowStyle Minimized
    Start-Sleep -Seconds 3
}

# 5. Iniciar Cloudflare Tunnel
Write-Host "[2/2] Generando enlace seguro HTTPS para moviles..." -ForegroundColor Yellow
$logFile = Join-Path $env:TEMP "cf_tunnel_session.log"
if (Test-Path $logFile) { Remove-Item $logFile -Force }

$proc = Start-Process -FilePath $cloudflared -ArgumentList "tunnel", "--url", "http://localhost:$Port", "--logfile", "$logFile" -PassThru -WindowStyle Hidden

Write-Host "Esperando conexion con la red de Cloudflare..." -ForegroundColor Gray
$tunnelUrl = $null
$attempts = 0
while ($attempts -lt 25 -and -not $tunnelUrl) {
    Start-Sleep -Seconds 1
    $attempts++
    if (Test-Path $logFile) {
        $content = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
        if ($content -match '(https://[a-zA-Z0-9\-]+\.trycloudflare\.com)') {
            $tunnelUrl = $matches[1]
        }
    }
}

if ($tunnelUrl) {
    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "  TU APLICACION YA ESTA ACCESIBLE DESDE CUALQUIER MOVIL! " -ForegroundColor White -BackgroundColor DarkGreen
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Direccion HTTPS para tu Movil Android / Tablet:" -ForegroundColor Yellow
    Write-Host "  >> $tunnelUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  (Puedes abrirla desde 4G, 5G o cualquier Wi-Fi)" -ForegroundColor Gray
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host ""

    # Open local browser
    Start-Process "http://localhost:$Port"
    
    Write-Host "Mantenga esta ventana abierta mientras use la app en el movil." -ForegroundColor DarkYellow
    Write-Host "Presione CTRL+C o cierre la ventana para apagar el tunel." -ForegroundColor DarkGray
    $proc.WaitForExit()
} else {
    Write-Host "No se pudo conectar con el tunel automaticamente." -ForegroundColor Red
    Write-Host "Iniciando tunel en modo directo..." -ForegroundColor Yellow
    & "$cloudflared" tunnel --url "http://localhost:$Port"
}
