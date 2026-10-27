# Run Flutter with DEV_HOST / DEV_API_PORT from repo root .env
param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$FlutterArgs
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $repoRoot '.env'

$devHost = '127.0.0.1'
$devPort = '8001'

if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -match '^\s*#' -or $line -eq '') { return }
    if ($line -match '^\s*DEV_HOST=(.+)$') { $devHost = $matches[1].Trim().Trim('"') }
    if ($line -match '^\s*DEV_API_PORT=(.+)$') { $devPort = $matches[1].Trim().Trim('"') }
  }
} else {
  Write-Warning "No .env at $envFile — using $devHost`:$devPort (copy .env.example to .env)"
}

Write-Host "MedaZone mobile → DEV_HOST=$devHost DEV_API_PORT=$devPort" -ForegroundColor Cyan

Push-Location (Join-Path $repoRoot 'mobile')
try {
  flutter run `
    --dart-define=DEV_HOST=$devHost `
    --dart-define=DEV_API_PORT=$devPort `
    @FlutterArgs
} finally {
  Pop-Location
}
