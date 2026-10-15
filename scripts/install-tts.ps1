param(
    [string]$Packages = "",
    [string]$Languages = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Church Cap's local environment was not found. Run setup first."
}

Push-Location $Root
try {
    & $Python (Join-Path $Root "scripts\report-install-progress.py") 2 "dependencies" "Preparing the local speech runtime."
    & $Python -m pip install -r (Join-Path $Root "requirements-tts.txt")
    if ($LASTEXITCODE -ne 0) { throw "Translated-audio runtime installation failed with exit code $LASTEXITCODE." }
    & $Python (Join-Path $Root "scripts\report-install-progress.py") 8 "voices" "Speech runtime ready; preparing selected voice packs."
    $Arguments = @((Join-Path $Root "scripts\install-tts-voices.py"))
    if ($Packages) { $Arguments += @("--packages", $Packages) }
    if ($Languages) { $Arguments += @("--languages", $Languages) }
    if ($Force) { $Arguments += "--force" }
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Translated-audio voice installation failed with exit code $LASTEXITCODE." }
}
finally {
    Pop-Location
}
