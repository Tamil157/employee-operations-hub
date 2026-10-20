$ErrorActionPreference = "Stop"
# Make pnpm deterministic when this script is started non-interactively.
$env:CI = "true"

$projectRoot = $PSScriptRoot
$environmentFile = Join-Path $projectRoot ".env"

if (-not (Test-Path -LiteralPath $environmentFile)) {
    Copy-Item (Join-Path $projectRoot ".env.example") $environmentFile
    Write-Host "Created .env from .env.example. Add your selected provider configuration, then run this script again." -ForegroundColor Yellow
    exit 1
}

Push-Location (Join-Path $projectRoot "backend")
try {
    uv sync --all-groups
}
finally {
    Pop-Location
}

Push-Location (Join-Path $projectRoot "frontend")
try {
    pnpm install --frozen-lockfile
    pnpm start
}
finally {
    Pop-Location
}
