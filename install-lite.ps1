#Requires -Version 5.1
<#
  Lodestar - native lite installer for low-end Windows hardware.

  One command to: create a virtualenv, install dependencies (skipping the
  heavy ChromaDB/ONNX vector-search stack), run first-time setup (prints an
  admin password on first run), and start the server with LODESTAR_LITE=true.
  Safe to re-run - it skips whatever already exists.

  Usage:
    powershell -ExecutionPolicy Bypass -File .\install-lite.ps1
    powershell -ExecutionPolicy Bypass -File .\install-lite.ps1 -Port 7000 -BindHost 127.0.0.1

  Lite mode (see src/constants.py LODESTAR_LITE):
    - no ChromaDB-backed RAG / vector memory (keyword search instead)
    - no Playwright/browser MCP auto-start
    - smaller SQLite cache_size/mmap_size
    - single uvicorn worker

  For a GPU workstation or to use Personal Docs RAG / semantic memory, use
  launch-windows.ps1 instead.
#>
param(
    [int]$Port = 7000,
    [string]$BindHost = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Write-Step($msg) { Write-Host ""; Write-Host ("==> " + $msg) -ForegroundColor Cyan }
function Fail($msg) {
    Write-Host ""
    Write-Host ("ERROR: " + $msg) -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# 1. Locate a Python interpreter (3.11+ required)
Write-Step "Checking for Python"
function Get-PythonVersionText($launcher, $launcherArgs) {
    try {
        return (& $launcher @launcherArgs -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null).Trim()
    } catch {
        return $null
    }
}

$pyExe = $null
$pyArgs = @()
$pyVersion = $null

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    foreach ($v in @("-3.13", "-3.12", "-3.11")) {
        $ver = Get-PythonVersionText $pyLauncher.Source @($v)
        if ($ver) {
            $pyExe = $pyLauncher.Source
            $pyArgs = @($v)
            $pyVersion = $ver
            break
        }
    }
}

if (-not $pyExe) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $ver = Get-PythonVersionText $pythonCmd.Source @()
        if ($ver) {
            $versionParts = $ver.Split('.')
            $major = [int]$versionParts[0]
            $minor = [int]$versionParts[1]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11)) {
                $pyExe = $pythonCmd.Source
                $pyVersion = $ver
            }
        }
    }
}

if (-not $pyExe) {
    Fail "Couldn't find Python 3.11+ for Windows setup. Install Python 3.11+ (or open the Python launcher with 'py -3.11') from https://www.python.org/downloads/, then re-run this script."
}
$pythonLabel = ("Using Python {0}: {1} {2}" -f $pyVersion, $pyExe, ($pyArgs -join ' ')).TrimEnd()
Write-Host $pythonLabel

# 2. Create the virtualenv if missing
$venvPy = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Step "Creating virtual environment (venv)"
    & $pyExe @pyArgs -m venv venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPy)) { Fail "Failed to create the virtual environment." }
} else {
    Write-Host "venv already exists - skipping creation."
}

# 3. Install / update dependencies, excluding the heavy ChromaDB/ONNX
#    vector-search stack. LODESTAR_LITE=true skips the code paths that would
#    use them (see src/constants.py LODESTAR_LITE), so the app degrades to
#    keyword search instead of failing.
Write-Step "Installing dependencies (first run can take a few minutes)"
& $venvPy -m pip install --upgrade pip --quiet

$liteReqFile = Join-Path $PSScriptRoot "venv\requirements-lite.txt"
Get-Content (Join-Path $PSScriptRoot "requirements.txt") |
    Where-Object { $_ -notmatch '^(chromadb-client|fastembed|onnxruntime)([><=! ].*)?$' } |
    Set-Content -Path $liteReqFile

& $venvPy -m pip install -r $liteReqFile
if ($LASTEXITCODE -ne 0) { Fail "Dependency install failed. Scroll up for the pip error." }

# 4. First-time setup (creates data dirs, DB, .env, admin user)
Write-Step "Running first-time setup"
& $venvPy setup.py
if ($LASTEXITCODE -ne 0) { Fail "setup.py failed." }

# 5. Start the server in lite mode (use `python -m uvicorn` - bare `uvicorn`
#    may not be on PATH). Single worker is the uvicorn default but is made
#    explicit here since lite mode targets memory-constrained machines.
Write-Step ("Starting Lodestar (lite mode) at http://{0}:{1}" -f $BindHost, $Port)
Write-Host "Press Ctrl+C to stop."
Write-Host ""
$env:LODESTAR_LITE = "true"
& $venvPy -m uvicorn app:app --host $BindHost --port $Port --workers 1
