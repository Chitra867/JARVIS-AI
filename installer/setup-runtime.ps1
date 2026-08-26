param(
    [switch]$SkipModelCheck
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ServerDir = Join-Path $ProjectRoot "server"
$RequirementsFile = Join-Path $ServerDir "requirements.txt"
$VenvDir = Join-Path $ServerDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$RuntimeDir = Join-Path $env:LOCALAPPDATA "JARVIS OS\logs"
$SetupLog = Join-Path $RuntimeDir "setup-runtime.log"

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

function Write-SetupLog {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $line = (
        "[{0}] {1}" -f
        (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"),
        $Message
    )

    $line | Tee-Object -FilePath $SetupLog -Append
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string[]]$ArgumentList
    )

    Write-SetupLog (
        "Running: {0} {1}" -f
        $FilePath,
        ($ArgumentList -join " ")
    )

    & $FilePath @ArgumentList

    if ($LASTEXITCODE -ne 0) {
        throw (
            "Command failed with exit code {0}: {1}" -f
            $LASTEXITCODE,
            $FilePath
        )
    }
}

function Find-Python313 {
    $py = Get-Command "py.exe" -ErrorAction SilentlyContinue

    if ($py) {
        & $py.Source -3.13 -c "import sys; print(sys.executable)" *> $null

        if ($LASTEXITCODE -eq 0) {
            return @{
                FilePath = $py.Source
                Prefix = @("-3.13")
            }
        }
    }

    $python = Get-Command "python.exe" -ErrorAction SilentlyContinue

    if ($python) {
        $version = & $python.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"

        if ($LASTEXITCODE -eq 0 -and $version.Trim() -eq "3.13") {
            return @{
                FilePath = $python.Source
                Prefix = @()
            }
        }
    }

    return $null
}

Write-SetupLog "Starting JARVIS runtime setup."

if (-not (Test-Path $RequirementsFile)) {
    throw "requirements.txt was not found at: $RequirementsFile"
}

$python313 = Find-Python313

if (-not $python313) {
    throw (
        "Python 3.13 was not found. Install Python 3.13, " +
        "then run this setup again."
    )
}

if (-not (Test-Path $VenvPython)) {
    Write-SetupLog "Creating Python virtual environment."

    $venvArgs = @()
    $venvArgs += $python313.Prefix
    $venvArgs += @(
        "-m",
        "venv",
        $VenvDir
    )

    Invoke-Checked `
        -FilePath $python313.FilePath `
        -ArgumentList $venvArgs
}
else {
    Write-SetupLog "Existing JARVIS virtual environment found."
}

Invoke-Checked `
    -FilePath $VenvPython `
    -ArgumentList @(
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--upgrade",
        "pip",
        "setuptools",
        "wheel"
    )

Invoke-Checked `
    -FilePath $VenvPython `
    -ArgumentList @(
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "-r",
        $RequirementsFile
    )

Write-SetupLog "Installing openWakeWord pretrained models."

Invoke-Checked `
    -FilePath $VenvPython `
    -ArgumentList @(
        "-c",
        (
            "import openwakeword; " +
            "openwakeword.utils.download_models(" +
            "model_names=['hey_jarvis_v0.1']); " +
            "print('openWakeWord models installed.')"
        )
    )

Write-SetupLog "Verifying critical Python imports."

Invoke-Checked `
    -FilePath $VenvPython `
    -ArgumentList @(
        "-c",
        (
            "import fastapi, uvicorn, pyautogui, pywinauto; " +
            "import faster_whisper, openwakeword; " +
            "print('JARVIS Python runtime verified.')"
        )
    )

if (-not $SkipModelCheck) {
    $ollama = Get-Command "ollama.exe" -ErrorAction SilentlyContinue

    if (-not $ollama) {
        Write-SetupLog (
            "WARNING: Ollama was not found. " +
            "Install Ollama before starting JARVIS."
        )
    }
    else {
        Write-SetupLog "Checking Ollama model availability."

        $modelOutput = & $ollama.Source list 2>&1 | Out-String

        if ($LASTEXITCODE -ne 0) {
            Write-SetupLog (
                "WARNING: Ollama is installed but its model list " +
                "could not be read."
            )
        }
        elseif ($modelOutput -notmatch "(?im)^llama3\.2:3b\s") {
            Write-SetupLog (
                "WARNING: llama3.2:3b is not installed. " +
                "Run: ollama pull llama3.2:3b"
            )
        }
        else {
            Write-SetupLog "Ollama model llama3.2:3b found."
        }
    }
}

Write-SetupLog "JARVIS runtime setup completed successfully."
Write-Host ""
Write-Host "JARVIS runtime is ready." -ForegroundColor Green
Write-Host "Setup log: $SetupLog" -ForegroundColor DarkGray
