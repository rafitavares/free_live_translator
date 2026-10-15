[CmdletBinding()]
param([string]$EngineDir)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not $EngineDir) { $EngineDir = Join-Path $ProjectRoot 'dist\engine-windows-x64\church-cap-engine' }
$EngineDir = (Resolve-Path -LiteralPath $EngineDir).Path
$Engine = Join-Path $EngineDir 'church-cap-engine.exe'
$Required = @('_internal\LICENSE','_internal\app\templates\operator.html','_internal\app\static\styles.css','_internal\app\locales\client_ui.json','_internal\app\static\flags\LICENSE.flag-icons','_internal\docs\legal\THIRD_PARTY_NOTICES.md','_internal\docs\legal\SPOKEN_LANGUAGE_MODELS.md','_internal\scripts\install-tts-voices.py','_internal\_sounddevice_data\portaudio-binaries\libportaudio64bit.dll')
foreach ($Relative in $Required) { $Path = Join-Path $EngineDir $Relative; if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Required packaged resource is missing: $Path" } }
function Get-PeMachine([string]$Path) {
    $Stream = [System.IO.File]::OpenRead($Path)
    try { $Reader = [System.IO.BinaryReader]::new($Stream); if ($Reader.ReadUInt16() -ne 0x5A4D) { return $null }; $Stream.Position = 0x3C; $Offset = $Reader.ReadUInt32(); if ($Offset -gt $Stream.Length - 6) { return $null }; $Stream.Position = $Offset; if ($Reader.ReadUInt32() -ne 0x00004550) { return $null }; return $Reader.ReadUInt16() } finally { $Stream.Dispose() }
}
$PeFiles = Get-ChildItem -LiteralPath $EngineDir -Recurse -File | Where-Object { $_.Extension -in '.exe', '.dll', '.pyd' }
if (-not $PeFiles) { throw 'No Windows PE files were found in the frozen engine.' }
$Invalid = @($PeFiles | Where-Object { (Get-PeMachine $_.FullName) -ne 0x8664 })
if ($Invalid) { throw "Non-x64 or invalid PE files were found: $($Invalid.FullName -join ', ')" }
$env:CHURCH_CAP_RUNTIME_MODE = 'packaged'; $env:CHURCH_CAP_RESOURCE_INSTALL = 'validate'; & $Engine
if ($LASTEXITCODE -ne 0) { throw "The frozen resource preflight failed with exit code $LASTEXITCODE." }
Write-Host "Windows engine bundle verified: $($PeFiles.Count) x64 PE files and all required shared resources are present."
