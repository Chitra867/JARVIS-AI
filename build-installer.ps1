$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$HudDir = Join-Path $ProjectRoot "hud"
$ServerDir = Join-Path $ProjectRoot "server"
$InstallerScript = Join-Path $ProjectRoot "installer\JARVIS.iss"
$ReleaseDir = Join-Path $ProjectRoot "release"

function Find-Iscc {
    $command = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue

    if ($null -ne $command) {
        return $command.Source
    }

    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }

    throw "ISCC.exe was not found. Install Inno Setup 6 first."
}

Write-Host "Running JARVIS release tests..." -ForegroundColor Cyan

$VenvPython = Join-Path $ServerDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "Development virtual environment was not found: $VenvPython"
}

Push-Location $ServerDir

try {
    & $VenvPython -m pytest -q

    if ($LASTEXITCODE -ne 0) {
        throw "Python tests failed."
    }
}
finally {
    Pop-Location
}

Write-Host "Building production HUD..." -ForegroundColor Cyan

$Npm = Get-Command "npm.cmd" -ErrorAction SilentlyContinue

if ($null -eq $Npm) {
    throw "npm.cmd was not found. Install Node.js and reopen PowerShell."
}

Push-Location $HudDir

try {
    & $Npm.Source run build

    if ($LASTEXITCODE -ne 0) {
        throw "HUD build failed."
    }
}
finally {
    Pop-Location
}

$HudIndex = Join-Path $HudDir "dist\index.html"

if (-not (Test-Path -LiteralPath $HudIndex)) {
    throw "Production HUD index.html was not created."
}

if (-not (Test-Path -LiteralPath $InstallerScript)) {
    throw "Inno Setup script was not found: $InstallerScript"
}

$Iscc = Find-Iscc

New-Item `
    -ItemType Directory `
    -Force `
    -Path $ReleaseDir |
    Out-Null

Write-Host "Compiling JARVIS installer..." -ForegroundColor Cyan
Write-Host "Inno Setup: $Iscc" -ForegroundColor DarkGray

& $Iscc $InstallerScript

if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed."
}

$Installer = Join-Path $ReleaseDir "JARVIS-OS-Setup-1.0.0.exe"

if (-not (Test-Path -LiteralPath $Installer)) {
    throw "Installer output was not found: $Installer"
}

$hash = Get-FileHash `
    -Path $Installer `
    -Algorithm SHA256

Write-Host ""
Write-Host "JARVIS installer built successfully." -ForegroundColor Green
Write-Host "Installer: $Installer" -ForegroundColor Cyan
Write-Host "SHA256:    $($hash.Hash)" -ForegroundColor DarkGray
