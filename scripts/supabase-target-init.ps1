param(
    [Parameter(Mandatory=$true)]
    [string]$Name,

    [Parameter(Mandatory=$true)]
    [string]$RepoPath,

    [string]$ProductionTarget = "",

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = (Resolve-Path $RepoPath).Path
$outFile = Join-Path $repo ".supabase-target.json"

if ((Test-Path $outFile) -and -not $Force) {
    throw "Esiste già: $outFile. Usa -Force per sovrascrivere."
}

if ([string]::IsNullOrWhiteSpace($ProductionTarget)) {
    $ProductionTarget = $Name
}

$projectName = $Name
if ($projectName -match "^(.*?)-(prod|dev|staging)$") {
    $projectName = $Matches[1]
}

$data = [ordered]@{
    version = 1
    project = $projectName
    default_target = $Name
    production_target = $ProductionTarget
}

$data | ConvertTo-Json -Depth 5 | Set-Content -Path $outFile -Encoding UTF8

Write-Host "Creato: $outFile"
Write-Host ""
Write-Host "Contenuto:"
Get-Content $outFile
