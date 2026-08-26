$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerDir = Join-Path $ProjectRoot "server"
$HudDistDir = Join-Path $ProjectRoot "hud\dist"
$HudIndex = Join-Path $HudDistDir "index.html"
$PythonExe = Join-Path $ServerDir ".venv\Scripts\python.exe"
$RuntimeDir = Join-Path $env:TEMP "jarvis-os"
$StateFile = Join-Path $RuntimeDir "runtime.json"

$BackendHealthUrl = "http://127.0.0.1:8000/health"
$JarvisUrl = "http://127.0.0.1:8000/"
$OllamaUrl = "http://127.0.0.1:11434/api/tags"

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

function Test-HttpEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest `
            -Uri $Url `
            -UseBasicParsing `
            -TimeoutSec 2

        return (
            $response.StatusCode -ge 200 `
            -and $response.StatusCode -lt 500
        )
    }
    catch {
        return $false
    }
}

function Wait-HttpEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,

        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    do {
        if (Test-HttpEndpoint -Url $Url) {
            return $true
        }

        Start-Sleep -Milliseconds 250
    }
    while ((Get-Date) -lt $deadline)

    return $false
}

function Show-LogTail {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (Test-Path $Path) {
        Write-Host ""
        Write-Host "---- $Path ----" -ForegroundColor DarkGray
        Get-Content $Path -Tail 20
    }
}

if (-not (Test-Path $PythonExe)) {
    throw (
        "Python virtual environment was not found at: $PythonExe"
    )
}

if (-not (Test-Path $HudIndex)) {
    throw (
        "Production HUD was not found at: $HudIndex`n" +
        "Build it first with: cd `"$ProjectRoot\hud`"; npm run build"
    )
}

$state = [ordered]@{
    startedAt = (Get-Date).ToString("o")
    backendPid = $null
    ollamaPid = $null
}

# ------------------------------------------------------------
# OLLAMA
# ------------------------------------------------------------

if (-not (Test-HttpEndpoint -Url $OllamaUrl)) {
    $OllamaCommand = Get-Command "ollama.exe" -ErrorAction SilentlyContinue

    if (-not $OllamaCommand) {
        throw (
            "Ollama is not running and ollama.exe was not found in PATH."
        )
    }

    $ollamaOut = Join-Path $RuntimeDir "ollama.out.log"
    $ollamaErr = Join-Path $RuntimeDir "ollama.err.log"

    Remove-Item $ollamaOut, $ollamaErr -Force -ErrorAction SilentlyContinue

    $ollamaProcess = Start-Process `
        -FilePath $OllamaCommand.Source `
        -ArgumentList @("serve") `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $ollamaOut `
        -RedirectStandardError $ollamaErr `
        -WindowStyle Hidden `
        -PassThru

    $state.ollamaPid = $ollamaProcess.Id

    if (-not (Wait-HttpEndpoint -Url $OllamaUrl -TimeoutSeconds 15)) {
        Show-LogTail -Path $ollamaErr
        throw "Ollama did not become ready."
    }
}

try {
    $tags = Invoke-RestMethod -Uri $OllamaUrl -TimeoutSec 3
    $modelNames = @(
        $tags.models |
        ForEach-Object {
            $_.name
        }
    )

    if (
        $modelNames.Count -gt 0 `
        -and -not (
            $modelNames |
            Where-Object {
                $_ -eq "llama3.2:3b"
            }
        )
    ) {
        Write-Warning (
            "Ollama is running, but llama3.2:3b was not found. " +
            "Run: ollama pull llama3.2:3b"
        )
    }
}
catch {
    Write-Warning "Could not verify the installed Ollama models."
}

# ------------------------------------------------------------
# JARVIS BACKEND + PRODUCTION HUD
# ------------------------------------------------------------

if (-not (Test-HttpEndpoint -Url $BackendHealthUrl)) {
    $backendOut = Join-Path $RuntimeDir "backend.out.log"
    $backendErr = Join-Path $RuntimeDir "backend.err.log"

    Remove-Item $backendOut, $backendErr -Force -ErrorAction SilentlyContinue

    $backendProcess = Start-Process `
        -FilePath $PythonExe `
        -ArgumentList @(
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000"
        ) `
        -WorkingDirectory $ServerDir `
        -RedirectStandardOutput $backendOut `
        -RedirectStandardError $backendErr `
        -WindowStyle Hidden `
        -PassThru

    $state.backendPid = $backendProcess.Id

    if (-not (Wait-HttpEndpoint -Url $BackendHealthUrl -TimeoutSeconds 25)) {
        Show-LogTail -Path $backendOut
        Show-LogTail -Path $backendErr
        throw "JARVIS backend did not become ready."
    }
}
else {
    Write-Host "Backend already running." -ForegroundColor DarkGray
}

if (-not (Wait-HttpEndpoint -Url $JarvisUrl -TimeoutSeconds 5)) {
    throw "JARVIS HUD did not become reachable through FastAPI."
}

$state |
    ConvertTo-Json |
    Set-Content `
        -Path $StateFile `
        -Encoding UTF8

Write-Host ""
Write-Host "JARVIS OS is ready." -ForegroundColor Green
Write-Host "JARVIS:  $JarvisUrl" -ForegroundColor Cyan
Write-Host "API:     http://127.0.0.1:8000/api" -ForegroundColor Cyan
Write-Host "Logs:    $RuntimeDir" -ForegroundColor DarkGray
Write-Host ""

Start-Process $JarvisUrl
