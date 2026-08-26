$ErrorActionPreference = "Stop"

$RuntimeDir = Join-Path $env:TEMP "jarvis-os"
$StateFile = Join-Path $RuntimeDir "runtime.json"

if (-not (Test-Path $StateFile)) {
    Write-Host "No JARVIS runtime state was found." -ForegroundColor Yellow
    exit 0
}

$state = Get-Content $StateFile -Raw | ConvertFrom-Json

function Stop-ProcessTree {
    param(
        [Nullable[int]]$ProcessId,
        [string]$Name
    )

    if (-not $ProcessId) {
        return
    }

    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue

    if (-not $process) {
        return
    }

    Write-Host "Stopping $Name (PID $ProcessId)..." -ForegroundColor DarkGray

    & taskkill.exe /PID $ProcessId /T /F | Out-Null
}

Stop-ProcessTree -ProcessId $state.hudPid -Name "JARVIS HUD"
Stop-ProcessTree -ProcessId $state.backendPid -Name "JARVIS backend"

# Stop Ollama only if this launcher started it.
Stop-ProcessTree -ProcessId $state.ollamaPid -Name "Ollama"

Remove-Item $StateFile -Force -ErrorAction SilentlyContinue

Write-Host "JARVIS OS stopped." -ForegroundColor Green
