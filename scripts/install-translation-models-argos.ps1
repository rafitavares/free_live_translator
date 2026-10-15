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
Write-Host "Default scope: common church languages. Use -All to install every English -> target package in the Argos index."
Write-Host "This requires internet access now, but live translation itself runs locally afterwards."
Write-Host ""

$scope = if ($All) { "all" } else { "common" }
$pythonScript = @"
from argostranslate import package
from app.translation_packages import validate_argos_package_archive
from app.install_progress import write_install_progress
SCOPE = "$scope"
COMMON_TARGETS = ["es", "fr", "pt", "pl", "uk", "ar", "fa", "zh", "zt"]
print("Updating Argos package index...")
package.update_package_index()
available = package.get_available_packages()
if SCOPE == "all":
    targets = sorted({p.to_code for p in available if p.from_code == "en" and p.to_code != "en"})
else:
    targets = COMMON_TARGETS
LABELS = {"es": "Spanish", "fr": "French", "pt": "Portuguese", "pl": "Polish", "uk": "Ukrainian", "ar": "Arabic", "fa": "Farsi", "zh": "Chinese — Simplified", "zt": "Chinese — Traditional"}
progress_items = [{"id": target, "label": LABELS.get(target, target.upper()), "state": "pending", "percent": 0} for target in targets]
write_install_progress(14, "package-index", f"Found {len(targets)} Base language packages to check.", item_count=len(targets), items=progress_items)
installed = []
missing = []
for index, target in enumerate(targets, start=1):
    start_percent = 14 + round(80 * ((index - 1) / max(1, len(targets))))
    progress_items[index - 1].update(state="downloading", percent=20)
    write_install_progress(start_percent, "downloading-package", f"Downloading and installing English to {LABELS.get(target, target.upper())}.", item_index=index, item_count=len(targets), items=progress_items, indeterminate=True)
    candidates = [p for p in available if p.from_code == "en" and p.to_code == target]
    if not candidates:
        missing.append(target)
        progress_items[index - 1].update(state="error", percent=100)
        write_install_progress(start_percent, "package-missing", f"No English to {LABELS.get(target, target.upper())} package was available.", item_index=index, item_count=len(targets), items=progress_items)
        print(f"No en->{target} package found in the Argos index.")
        continue
    pkg = candidates[0]
    print(f"Downloading/installing en->{target}: {pkg.package_version}...")
    path = pkg.download()
    validate_argos_package_archive(path)
    package.install_from_path(path)
    installed.append(target)
    progress_items[index - 1].update(state="complete", percent=100)
    write_install_progress(14 + round(80 * (index / max(1, len(targets)))), "package-complete", f"English to {LABELS.get(target, target.upper())} is installed.", item_index=index, item_count=len(targets), items=progress_items)
print("\nInstalled target languages:", ", ".join(installed) or "none")
if missing:
    print("Missing packages:", ", ".join(missing))
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
    'TRANSLATION_ALLOWED_LANGUAGES': 'en',
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
