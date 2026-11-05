Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-SbRoot {
    return Split-Path -Parent $PSScriptRoot
}
function Get-SbRegistryPath { Join-Path (Get-SbRoot) "registry.json" }
function Read-SbRegistry {
    $p = Get-SbRegistryPath
    if (-not (Test-Path $p)) {
        throw "registry.json non trovato: $p. Copia registry.example.json in registry.json oppure esegui install.ps1."
    }

    $registry = Get-Content $p -Raw | ConvertFrom-Json
    $migration = Update-SbRegistrySchema $registry

    if ($migration.Changed) {
        $backupDir = Join-Path (Get-SbRoot) "backups"
        New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $backup = Join-Path $backupDir "registry.pre-v2.$stamp.json"
        Copy-Item $p $backup -Force
        $migration.Registry | ConvertTo-Json -Depth 30 | Set-Content $p -Encoding UTF8
        Write-Host "Registry legacy migrato automaticamente a schema v2."
        Write-Host "Backup: $backup"
    }

    return $migration.Registry
}
function Write-SbRegistry($registry) { $registry | ConvertTo-Json -Depth 30 | Set-Content (Get-SbRegistryPath) -Encoding UTF8 }
function Get-SbPropertyNames($obj) {
    if ($null -eq $obj) {
        return @()
    }

    return @(
        $obj.PSObject.Properties |
        ForEach-Object { $_.Name }
    )
}
function ConvertTo-SbSlug([string]$value) {
    $v = $value.ToLowerInvariant() -replace '[^a-z0-9_-]', '_'
    ($v -replace '_+', '_').Trim('_')
}
function Get-SbEffectiveTokenEnv($registry, [string]$projectName) {
    $project = $registry.projects.$projectName
    if ($null -eq $project) { throw "Progetto '$projectName' non trovato." }
    if (($project.PSObject.Properties.Name -contains 'token_env') -and -not [string]::IsNullOrWhiteSpace([string]$project.token_env)) {
        return [string]$project.token_env
    }
    $account = $registry.accounts.([string]$project.account)
    if ($null -eq $account) { throw "Account '$($project.account)' non trovato." }
    [string]$account.token_env
}
function Get-SbMcpName($registry, [string]$projectName) {
    $prefix = if ($registry.defaults.mcp_prefix) { [string]$registry.defaults.mcp_prefix } else { 'sb_' }
    $prefix + (ConvertTo-SbSlug $projectName)
}
function Get-SbMcpUrl($project) {
    $ref = [string]$project.project_ref
    if ([string]::IsNullOrWhiteSpace($ref) -or $ref -match 'INCOLLA_QUI') { throw "project_ref non configurato." }
    $url = "https://mcp.supabase.com/mcp?project_ref=$([uri]::EscapeDataString($ref))"
    if ($project.read_only -eq $true) { $url += '&read_only=true' }
    if ($project.features -and $project.features.Count -gt 0) {
        $url += "&features=$([uri]::EscapeDataString(($project.features -join ',')))"
    }
    $url
}
function Assert-CodexAvailable {
    if (-not (Get-Command codex -ErrorAction SilentlyContinue)) { throw "Codex CLI non trovato. Prova: codex --version" }
}
function Backup-CodexConfig {
    $config = Join-Path $HOME '.codex\config.toml'
    if (-not (Test-Path $config)) { return $null }
    $backupDir = Join-Path (Get-SbRoot) 'backups'
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    $backup = Join-Path $backupDir ("config.toml.{0}.bak" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
    Copy-Item $config $backup -Force
    $backup
}
function Test-SbEnvPresent([string]$envName) {
    $v = [Environment]::GetEnvironmentVariable($envName, 'Process')
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $true }
    $v = [Environment]::GetEnvironmentVariable($envName, 'User')
    -not [string]::IsNullOrWhiteSpace($v)
}


function Get-SbOptionalProperty($obj, [string]$name, $defaultValue = $null) {
    if ($null -eq $obj) { return $defaultValue }
    if ($obj.PSObject.Properties.Name -contains $name) {
        return $obj.$name
    }
    return $defaultValue
}

function Update-SbRegistrySchema($registry) {
    $changed = $false

    if (-not ($registry.PSObject.Properties.Name -contains "version")) {
        $registry | Add-Member -NotePropertyName version -NotePropertyValue 2
        $changed = $true
    }

    if (-not ($registry.PSObject.Properties.Name -contains "defaults")) {
        $registry | Add-Member -NotePropertyName defaults -NotePropertyValue ([PSCustomObject]@{
            read_only_production = $true
            features = @("database","debugging","development","functions","docs")
            mcp_prefix = "sb_"
        })
        $changed = $true
    }

    foreach ($a in Get-SbPropertyNames $registry.accounts) {
        $acct = $registry.accounts.$a

        if (-not ($acct.PSObject.Properties.Name -contains "token_env") -or
            [string]::IsNullOrWhiteSpace([string](Get-SbOptionalProperty $acct "token_env" ""))) {
            $envName = "SUPABASE_PAT_" + ($a.ToUpperInvariant() -replace '[^A-Z0-9]','_')
            $acct | Add-Member -NotePropertyName token_env -NotePropertyValue $envName -Force
            $changed = $true
        }

        if (-not ($acct.PSObject.Properties.Name -contains "enabled")) {
            $acct | Add-Member -NotePropertyName enabled -NotePropertyValue $true
            $changed = $true
        }
    }

    foreach ($p in Get-SbPropertyNames $registry.projects) {
        $proj = $registry.projects.$p

        if (-not ($proj.PSObject.Properties.Name -contains "environment")) {
            $proj | Add-Member -NotePropertyName environment -NotePropertyValue "production"
            $changed = $true
        }

        if (-not ($proj.PSObject.Properties.Name -contains "read_only")) {
            $proj | Add-Member -NotePropertyName read_only -NotePropertyValue $true
            $changed = $true
        }

        if (-not ($proj.PSObject.Properties.Name -contains "features")) {
            $proj | Add-Member -NotePropertyName features -NotePropertyValue @("database","debugging","development","functions","docs")
            $changed = $true
        }

        if (-not ($proj.PSObject.Properties.Name -contains "token_env")) {
            $proj | Add-Member -NotePropertyName token_env -NotePropertyValue $null
            $changed = $true
        }

        if (-not ($proj.PSObject.Properties.Name -contains "enabled")) {
            $proj | Add-Member -NotePropertyName enabled -NotePropertyValue $true
            $changed = $true
        }
    }

    return [PSCustomObject]@{
        Registry = $registry
        Changed = $changed
    }
}
