$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerDir = Join-Path $ProjectRoot "server"
$PythonExe = Join-Path $ServerDir ".venv\Scripts\python.exe"
$RuntimeDir = Join-Path $env:TEMP "jarvis-os"
$StateFile = Join-Path $RuntimeDir "runtime.json"

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

function Stop-ProcessTree {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ProcessId,

        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $process = Get-Process `
        -Id $ProcessId `
        -ErrorAction SilentlyContinue

    if ($null -eq $process) {
        return
    }

    Write-Host "Stopping $Name (PID $ProcessId)..." `
        -ForegroundColor DarkGray

    & taskkill.exe `
        /PID $ProcessId `
        /T `
        /F `
        2>$null |
        Out-Null
}

$state = $null

if (Test-Path -LiteralPath $StateFile) {
    try {
        $state =
            Get-Content $StateFile -Raw |
            ConvertFrom-Json
    }
    catch {
        $state = $null
    }
}

$backendProcesses = @(Get-JarvisBackendProcesses)

if ($backendProcesses.Count -gt 0) {

    $expectedPython =
        [System.IO.Path]::GetFullPath($PythonExe)

    $launcher = $null

    foreach ($process in $backendProcesses) {

        if (-not $process.ExecutablePath) {
            continue
        }

        $actualPath =
            [System.IO.Path]::GetFullPath(
                [string]$process.ExecutablePath
            )

        if ($actualPath -ieq $expectedPython) {
            $launcher = $process
            break
        }
    }

    if ($null -ne $launcher) {

        Stop-ProcessTree `
            -ProcessId ([int]$launcher.ProcessId) `
            -Name "JARVIS backend"

        Start-Sleep -Milliseconds 500
    }

    # Re-check only after killing the launcher.
    $remainingProcesses = @(Get-JarvisBackendProcesses)

    foreach ($process in $remainingProcesses) {

        Stop-ProcessTree `
            -ProcessId ([int]$process.ProcessId) `
            -Name "JARVIS backend"
    }

    Start-Sleep -Milliseconds 300
}

# Stop Ollama only if JARVIS originally started it.
if (
    $null -ne $state -and
    $state.ollamaPid
) {

    $ollamaPid = [int]$state.ollamaPid

    $ollamaProcess =
        Get-Process `
            -Id $ollamaPid `
            -ErrorAction SilentlyContinue

    if (
        $null -ne $ollamaProcess -and
        $ollamaProcess.ProcessName -ieq "ollama"
    ) {

        Stop-ProcessTree `
            -ProcessId $ollamaPid `
            -Name "Ollama"
    }
}

Remove-Item `
    $StateFile `
    -Force `
    -ErrorAction SilentlyContinue

$remainingProcesses = @(Get-JarvisBackendProcesses)

if ($remainingProcesses.Count -gt 0) {

    $remainingPids =
        (
            $remainingProcesses |
            ForEach-Object {
                [string]$_.ProcessId
            }
        ) -join ", "

    throw (
        "JARVIS backend processes are still running after shutdown: " +
        $remainingPids
    )
}

Write-Host "JARVIS OS stopped." `
    -ForegroundColor Green