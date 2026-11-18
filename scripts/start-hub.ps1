param([switch]$ConnectOBS,[switch]$SaveOBSConnection,[switch]$UseExistingOBS)
$ErrorActionPreference = 'Stop'
$studioRoot = Split-Path -Parent $PSScriptRoot
$studioPython = Join-Path (Split-Path -Parent $studioRoot) '.venv\Scripts\python.exe'
if (-not (Test-Path $studioPython)) { $studioPython = (Get-Command python -ErrorAction Stop).Source }
Set-Location $studioRoot
if ((@($ConnectOBS,$SaveOBSConnection,$UseExistingOBS) | Where-Object {$_}).Count -gt 1) { throw 'Choose only one OBS connection setup mode.' }
if ($SaveOBSConnection -or $UseExistingOBS) {
    if ($UseExistingOBS) { & $studioPython -m tools.connect_obs --from-obs }
    else { & $studioPython -m tools.connect_obs --prompt }
    if ($LASTEXITCODE -ne 0) { throw 'OBS connection was not saved. Review the local setup message; no OBS settings were changed.' }
    & $studioPython -m tools.open_hub
} elseif ($ConnectOBS) {
    $existingStudio = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
    if ($existingStudio) { throw 'Close the running studio server before starting with OBS control.' }
    $studioSecret = Read-Host 'OBS WebSocket password (stays on this computer)' -AsSecureString
    $studioCredential = New-Object System.Management.Automation.PSCredential('studio', $studioSecret)
    $env:EMBERBANTER_OBS_PASSWORD = $studioCredential.GetNetworkCredential().Password
    try { & $studioPython -m hub.server --open }
    finally { Remove-Item Env:EMBERBANTER_OBS_PASSWORD -ErrorAction SilentlyContinue; $studioSecret.Dispose() }
} else {
    & $studioPython -m tools.open_hub
}
