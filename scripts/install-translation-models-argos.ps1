param(
    [switch]$Enable,
    [switch]$All
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "No .venv found. Run .\setup-windows.cmd first."
    exit 1
}

& $VenvPython (Join-Path $ProjectRoot "scripts\report-install-progress.py") 2 "dependencies" "Preparing Base translation package dependencies."
& $VenvPython -m pip install --upgrade "pip==26.1.2" "setuptools<82" wheel
& $VenvPython -m pip install -r requirements-translation.txt
& $VenvPython (Join-Path $ProjectRoot "scripts\report-install-progress.py") 10 "package-index" "Loading the Argos language package index."

Write-Host ""
Write-Host "Argos Translate is installed in the local .venv."
Write-Host ""
Write-Host "The next step attempts to download/install English -> target-language packages."
Write-Host "Default scope: common church languages. Use -All for every language reachable from the speaker language (CAPTION_SOURCE_LANGUAGE, default pt)."
Write-Host "This requires internet access now, but live translation itself runs locally afterwards."
Write-Host ""

$scope = if ($All) { "all" } else { "common" }
$pythonScript = @"
from app.resource_installer import install_argos
install_argos(all_languages=("$scope" == "all"))
"@
$pythonScript | & $VenvPython -

& $VenvPython (Join-Path $ProjectRoot "scripts\report-install-progress.py") 96 "configuration" "Saving Base translation package settings."

$enableValue = if ($Enable) { "true" } else { "false" }
$configScript = @"
from pathlib import Path
import json
import os

env_path = Path('.env')
if not env_path.exists():
    template = Path('.env.example') if Path('.env.example').exists() else Path('env.example')
    env_path.write_text(template.read_text(encoding='utf-8'), encoding='utf-8')

values = {
    'TRANSLATION_ENABLED': '$enableValue',
    'TRANSLATION_PROVIDER': 'argos',
    'TRANSLATION_ALLOWED_LANGUAGES': '',
    'TRANSLATION_MAX_ACTIVE_LANGUAGES': '1',
}

lines = env_path.read_text(encoding='utf-8').splitlines()
seen = set()
new_lines = []
for line in lines:
    if '=' in line and not line.lstrip().startswith('#'):
        key = line.split('=', 1)[0].strip()
        if key in values:
            new_lines.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)
for key, value in values.items():
    if key not in seen:
        new_lines.append(f"{key}={value}")
env_path.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')

appdata = os.environ.get('APPDATA') or str(Path.home() / 'AppData' / 'Roaming')
data_dir = Path(appdata) / 'Church Cap' / 'data'
data_dir.mkdir(parents=True, exist_ok=True)
runtime_path = data_dir / 'runtime_config.json'
if runtime_path.exists():
    try:
        runtime = json.loads(runtime_path.read_text(encoding='utf-8'))
    except Exception:
        runtime = {}
else:
    runtime = {}
runtime.update({
    'translation_enabled': True if '$enableValue' == 'true' else False,
    'translation_allowed_languages': ['en'],
    'translation_max_active_languages': 20,
})
runtime_path.write_text(json.dumps(runtime, indent=2), encoding='utf-8')
"@
$configScript | & $VenvPython -
& $VenvPython (Join-Path $ProjectRoot "scripts\report-install-progress.py") 100 "complete" "Base translation packages are ready."

if ($Enable) {
    Write-Host ""
    Write-Host "Argos has been configured and enabled in .env and the Windows app data folder."
    Write-Host "Translation remains experimental; keep maximum active languages low for Sunday use."
} else {
    Write-Host ""
    Write-Host "Argos has been configured in .env and the Windows app data folder, but live translation is OFF."
    Write-Host "Enable it in the operator Languages panel when ready, or rerun with -Enable."
}
