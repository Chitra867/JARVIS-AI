$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerDir = Join-Path $ProjectRoot "server"
$HudIndex = Join-Path $ProjectRoot "hud\dist\index.html"
$PythonExe = Join-Path $ServerDir ".venv\Scripts\python.exe"

$RuntimeDir = Join-Path $env:TEMP "jarvis-os"
$StateFile = Join-Path $RuntimeDir "runtime.json"

$JarvisUrl = "http://127.0.0.1:8000/"
$HealthUrl = "http://127.0.0.1:8000/health"
$OllamaUrl = "http://127.0.0.1:11434/api/tags"

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

function Test-Url {
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
            $response.StatusCode -ge 200 -and
            $response.StatusCode -lt 500
        )
    }
    catch {
        return $false
    }
}

function Wait-Url {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,

        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        if (Test-Url -Url $Url) {
            return $true
        }

        Start-Sleep -Milliseconds 250
    }

    return $false
}

function Get-JarvisBackendProcesses {
    if (-not (Test-Path -LiteralPath $PythonExe)) {
        return @()
    }

    $expectedPython = [System.IO.Path]::GetFullPath($PythonExe)

    return @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $commandLine = [string]$_.CommandLine

            if (-not $commandLine) {
                return $false
            }

            $containsPython =
                $commandLine.IndexOf(
                    $expectedPython,
                    [System.StringComparison]::OrdinalIgnoreCase
                ) -ge 0

            $containsUvicorn =
                $commandLine.IndexOf(
                    "-m uvicorn",
                    [System.StringComparison]::OrdinalIgnoreCase
                ) -ge 0

            $containsApp =
                $commandLine.IndexOf(
                    "app.main:app",
                    [System.StringComparison]::OrdinalIgnoreCase
                ) -ge 0

            $containsPort =
                $commandLine.IndexOf(
                    "--port 8000",
                    [System.StringComparison]::OrdinalIgnoreCase
                ) -ge 0

            return (
                $containsPython -and
                $containsUvicorn -and
                $containsApp -and
                $containsPort
            )
        }
    )
}

function Get-PreferredBackendPid {
    $processes = @(Get-JarvisBackendProcesses)

    if ($processes.Count -eq 0) {
        return $null
    }

    $expectedPython = [System.IO.Path]::GetFullPath($PythonExe)

    foreach ($process in $processes) {
        if ($process.ExecutablePath) {
            $actualPath = [System.IO.Path]::GetFullPath(
                [string]$process.ExecutablePath
            )

            if ($actualPath -ieq $expectedPython) {
                return [int]$process.ProcessId
            }
        }
    }

    return [int]$processes[0].ProcessId
}

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python virtual environment not found: $PythonExe"
}

if (-not (Test-Path -LiteralPath $HudIndex)) {
    throw "Production HUD not found: $HudIndex"
}

$state = [ordered]@{
    startedAt  = (Get-Date).ToString("o")
    backendPid = $null
    ollamaPid  = $null
}

# Start Ollama only if it is not already running.
if (-not (Test-Url -Url $OllamaUrl)) {
    $ollamaCommand = Get-Command "ollama.exe" -ErrorAction SilentlyContinue

    if (-not $ollamaCommand) {
        throw "Ollama is not running and ollama.exe was not found."
    }

    $ollamaOut = Join-Path $RuntimeDir "ollama.out.log"
    $ollamaErr = Join-Path $RuntimeDir "ollama.err.log"

    Remove-Item $ollamaOut -Force -ErrorAction SilentlyContinue
    Remove-Item $ollamaErr -Force -ErrorAction SilentlyContinue

    $ollamaProcess = Start-Process `
        -FilePath $ollamaCommand.Source `
        -ArgumentList @("serve") `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $ollamaOut `
        -RedirectStandardError $ollamaErr `
        -WindowStyle Hidden `
        -PassThru

    $state.ollamaPid = [int]$ollamaProcess.Id

    if (-not (Wait-Url -Url $OllamaUrl -TimeoutSeconds 15)) {
        throw "Ollama did not become ready."
    }
}

# Reuse the backend only if it belongs to this installed JARVIS copy.
if (Test-Url -Url $HealthUrl) {
    $existingPid = Get-PreferredBackendPid

    if (-not $existingPid) {
        throw "Port 8000 is already in use by another backend."
    }

    $state.backendPid = [int]$existingPid

    Write-Host "JARVIS backend already running (PID $existingPid)." `
        -ForegroundColor DarkGray
}
else {
    $existingProcesses = @(Get-JarvisBackendProcesses)

    if ($existingProcesses.Count -gt 0) {
        throw "A JARVIS backend process exists but is not healthy."
    }

    $backendOut = Join-Path $RuntimeDir "backend.out.log"
    $backendErr = Join-Path $RuntimeDir "backend.err.log"

    Remove-Item $backendOut -Force -ErrorAction SilentlyContinue
    Remove-Item $backendErr -Force -ErrorAction SilentlyContinue

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

    $state.backendPid = [int]$backendProcess.Id

    if (-not (Wait-Url -Url $HealthUrl -TimeoutSeconds 25)) {
        if (Test-Path -LiteralPath $backendErr) {
            Get-Content $backendErr -Tail 30
        }

        throw "JARVIS backend did not become ready."
    }

    $verifiedPid = Get-PreferredBackendPid

    if ($verifiedPid) {
        $state.backendPid = [int]$verifiedPid
    }
}

if (-not (Wait-Url -Url $JarvisUrl -TimeoutSeconds 5)) {
    throw "JARVIS HUD did not become reachable."
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
