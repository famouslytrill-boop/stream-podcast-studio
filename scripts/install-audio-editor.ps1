param([switch]$Launch)
$ErrorActionPreference = 'Stop'
$studioApps = Join-Path $env:LOCALAPPDATA 'EmberBanter\apps'
$installRoot = Join-Path $studioApps 'audacity-4.0.2'
$editor = Join-Path $installRoot 'application\bin\Audacity4.exe'
$expectedHash = '6f375602254672b4f0db959e8b1e6fd46a97462aeab85b7ff21e1e9d9a54c5b3'
if (-not (Test-Path -LiteralPath $editor)) {
    New-Item -ItemType Directory -Force $studioApps | Out-Null
    $package = Join-Path $studioApps 'audacity-win-4.0.2-x86_64.7z'
    Invoke-WebRequest -Uri 'https://github.com/audacity/audacity/releases/download/Audacity-4.0.2/audacity-win-4.0.2-x86_64.7z' -OutFile $package
    if ((Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
        throw 'Official Audacity portable package checksum did not match.'
    }
    New-Item -ItemType Directory -Force $installRoot | Out-Null
    tar -xf $package -C $installRoot
    if ($LASTEXITCODE -ne 0) { throw 'Portable archive extraction failed.' }
    $extracted = Get-ChildItem -LiteralPath $installRoot -Directory | Where-Object { $_.Name -like 'Audacity-*' } | Select-Object -First 1
    if (-not $extracted) { throw 'Expected application directory was not found.' }
    Move-Item -LiteralPath $extracted.FullName -Destination (Join-Path $installRoot 'application')
}
if (-not (Test-Path -LiteralPath $editor)) { throw 'Audacity executable was not found.' }
$signature = Get-AuthenticodeSignature -FilePath $editor
if ($signature.Status -ne 'Valid') { throw 'Audacity executable signature was not valid.' }
if ($Launch) { Start-Process -FilePath $editor -WorkingDirectory (Split-Path $editor) | Out-Null }
[PSCustomObject]@{ Installed=$true; Version='4.0.2'; Portable=$true; Signature='Valid'; LaunchRequested=[bool]$Launch }
