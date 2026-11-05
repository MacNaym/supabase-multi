param(
    [string]$RepoPath = ".",
    [ValidateSet("default","production")]
    [string]$Mode = "default"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = (Resolve-Path $RepoPath).Path
$configPath = Join-Path $repo ".supabase-target.json"

if (-not (Test-Path $configPath)) {
    throw "Manca .supabase-target.json in $repo"
}

$config = Get-Content $configPath -Raw | ConvertFrom-Json

$target = if ($Mode -eq "production") {
    $config.production_target
} else {
    $config.default_target
}

if ([string]::IsNullOrWhiteSpace($target)) {
    throw "Target non definito per mode=$Mode"
}

$mcp = "sb_$target"

[pscustomobject]@{
    project = $config.project
    mode = $Mode
    target = $target
    mcp = $mcp
    config = $configPath
}
