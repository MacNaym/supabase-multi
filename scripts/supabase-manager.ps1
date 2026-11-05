param(
    [Parameter(Position=0)]
    [ValidateSet('help','account-list','account-add','account-remove','account-token-set','account-token-clear','project-list','project-add','project-remove','project-show','target-init','mcp-sync','mcp-status','doctor')]
    [string]$Command = 'help',
    [string]$Name,
    [string]$RepoPath = '.'
)
. "$PSScriptRoot\_common.ps1"

function Show-Help {
@"
SUPABASE MULTI v0.2 PAT

 account-list
 account-add
 account-remove -Name <alias>
 account-token-set -Name <alias>
 account-token-clear -Name <alias>
 project-list
 project-add
 project-remove -Name <alias>
 project-show -Name <alias>
 target-init -Name <target> -RepoPath <repo>
 mcp-sync
 mcp-status
 doctor
"@
}

$r = Read-SbRegistry
switch ($Command) {
'help' { Show-Help }
'account-list' {
    Write-Host "`nACCOUNT"
    foreach ($a in Get-SbPropertyNames $r.accounts) {
        $x = $r.accounts.$a; $ok = Test-SbEnvPresent ([string]$x.token_env)
        Write-Host ("  {0,-20} env={1,-30} {2}" -f $a,$x.token_env,$(if($ok){'PAT OK'}else{'PAT MANCANTE'}))
    }
}
'account-add' {
    $alias = ConvertTo-SbSlug (Read-Host 'Alias account (es. business)')
    if (-not $alias) { throw 'Alias vuoto.' }
    $label = Read-Host 'Etichetta leggibile [invio = alias]'; if (-not $label) { $label = $alias }
    $defaultEnv = 'SUPABASE_PAT_' + ($alias.ToUpperInvariant() -replace '[^A-Z0-9]','_')
    $tokenEnv = Read-Host "Nome variabile PAT [invio = $defaultEnv]"; if (-not $tokenEnv) { $tokenEnv = $defaultEnv }
    $r.accounts | Add-Member -NotePropertyName $alias -NotePropertyValue ([PSCustomObject]@{label=$label;token_env=$tokenEnv;enabled=$true}) -Force
    Write-SbRegistry $r
    Write-Host "Account '$alias' aggiunto. Ora: .\scripts\supabase-manager.ps1 account-token-set -Name $alias"
}
'account-remove' {
    if (-not $Name) { $Name = Read-Host 'Alias account da rimuovere' }
    $used = @(); foreach ($p in Get-SbPropertyNames $r.projects) { if ([string]$r.projects.$p.account -eq $Name) { $used += $p } }
    if ($used.Count) { throw "Account ancora usato da: $($used -join ', ')" }
    $r.accounts.PSObject.Properties.Remove($Name); Write-SbRegistry $r
}
'account-token-set' {
    if (-not $Name) { $Name = Read-Host 'Alias account' }
    if ((Get-SbPropertyNames $r.accounts) -notcontains $Name) { throw "Account '$Name' non trovato." }
    $envName = [string]$r.accounts.$Name.token_env
    $secure = Read-Host "Incolla il PAT per '$Name' (non viene mostrato)" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
        if (-not $plain) { throw 'PAT vuoto.' }
        [Environment]::SetEnvironmentVariable($envName,$plain,'User')
        [Environment]::SetEnvironmentVariable($envName,$plain,'Process')
    } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
    Write-Host "PAT salvato nella variabile utente '$envName'. Apri un nuovo terminale per i nuovi processi."
}
'account-token-clear' {
    if (-not $Name) { $Name = Read-Host 'Alias account' }
    $envName = [string]$r.accounts.$Name.token_env
    [Environment]::SetEnvironmentVariable($envName,$null,'User'); [Environment]::SetEnvironmentVariable($envName,$null,'Process')
    Write-Host "Variabile '$envName' rimossa."
}
'project-list' {
    Write-Host "`nPROGETTI/TARGET"
    foreach ($p in Get-SbPropertyNames $r.projects) {
        $x=$r.projects.$p; $e=Get-SbEffectiveTokenEnv $r $p
        Write-Host ("  {0,-24} {1,-4} {2,-3} account={3,-12} ref={4,-22} token={5}" -f $p,$(if($x.enabled){'ON'}else{'OFF'}),$(if($x.read_only){'RO'}else{'RW'}),$x.account,$x.project_ref,$(if(Test-SbEnvPresent $e){'OK'}else{'MANCANTE'}))
    }
}
'project-add' {
    $alias = ConvertTo-SbSlug (Read-Host 'Alias target (es. example-prod)'); if (-not $alias) { throw 'Alias vuoto.' }
    $accounts=Get-SbPropertyNames $r.accounts; if (-not $accounts.Count) { throw 'Aggiungi prima un account.' }
    Write-Host "Account: $($accounts -join ', ')"; $account=Read-Host 'Account'; if ($accounts -notcontains $account) { throw 'Account non valido.' }
    $label=Read-Host "Etichetta [invio = $alias]"; if (-not $label) { $label=$alias }
    $ref=Read-Host 'Supabase project_ref'; if (-not $ref) { throw 'project_ref obbligatorio.' }
    $env=Read-Host 'Ambiente [production/development/staging] (default production)'; if (-not $env) { $env='production' }
    $defaultRo=($env -eq 'production'); $ans=Read-Host $(if($defaultRo){'Read-only? [Y/n]'}else{'Read-only? [y/N]'})
    $ro = if($defaultRo){-not ($ans -match '^(n|no)$')}else{$ans -match '^(y|yes|s|si)$'}
    $override=Read-Host 'PAT dedicato? Nome env var oppure INVIO per PAT account'; if (-not $override) { $override=$null }
    $obj=[PSCustomObject]@{label=$label;account=$account;project_ref=$ref;environment=$env;read_only=$ro;features=@('database','debugging','development','functions','docs');token_env=$override;enabled=$true}
    $r.projects | Add-Member -NotePropertyName $alias -NotePropertyValue $obj -Force; Write-SbRegistry $r
    Write-Host "Target '$alias' aggiunto. MCP: $(Get-SbMcpName $r $alias)"
}
'project-remove' {
    if (-not $Name) { $Name=Read-Host 'Alias target da rimuovere' }
    $r.projects.PSObject.Properties.Remove($Name); Write-SbRegistry $r; Write-Host 'Esegui mcp-sync.'
}
'project-show' {
    if (-not $Name) { $Name=Read-Host 'Alias target' }
    $x=$r.projects.$Name; if ($null -eq $x) { throw 'Target non trovato.' }
    [PSCustomObject]@{alias=$Name;mcp=(Get-SbMcpName $r $Name);account=$x.account;project_ref=$x.project_ref;environment=$x.environment;read_only=$x.read_only;token_env=(Get-SbEffectiveTokenEnv $r $Name);url=(Get-SbMcpUrl $x)} | Format-List
}
'target-init' {
    if (-not $Name) { $Name=Read-Host 'Target predefinito' }
    if ((Get-SbPropertyNames $r.projects) -notcontains $Name) { throw 'Target non trovato.' }
    $resolved=(Resolve-Path $RepoPath).Path; $base=$Name -replace '-(prod|production|dev|development|staging|stage)$',''
    $obj=[ordered]@{project=$base;default_target=$Name}; if ([string]$r.projects.$Name.environment -eq 'production') { $obj.production_target=$Name }
    $file=Join-Path $resolved '.supabase-target.json'; $obj | ConvertTo-Json | Set-Content $file -Encoding UTF8; Write-Host "Creato $file"
}
'mcp-sync' {
    Assert-CodexAvailable
    $backup=Backup-CodexConfig; if($backup){Write-Host "Backup Codex: $backup"}
    $statePath=Join-Path (Get-SbRoot) 'state\generated-mcps.json'; $old=@()
    if(Test-Path $statePath){try{$old=@((Get-Content $statePath -Raw|ConvertFrom-Json).names)}catch{}}
    $desired=@(); foreach($p in Get-SbPropertyNames $r.projects){if($r.projects.$p.enabled){$desired+=Get-SbMcpName $r $p}}
    foreach($n in $old){if($desired -notcontains $n){& codex mcp remove $n 2>$null | Out-Null}}
    foreach($p in Get-SbPropertyNames $r.projects){
        $x=$r.projects.$p; if(-not $x.enabled){continue}
        $n=Get-SbMcpName $r $p; $token=Get-SbEffectiveTokenEnv $r $p; $url=Get-SbMcpUrl $x
        if(-not(Test-SbEnvPresent $token)){Write-Warning "${p}: PAT '$token' mancante."}
        & codex mcp remove $n 2>$null | Out-Null
        & codex mcp add $n --url $url --bearer-token-env-var $token
        if($LASTEXITCODE -ne 0){throw "Errore configurando $n"}
    }
    [PSCustomObject]@{generated_at=(Get-Date).ToString('o');names=$desired}|ConvertTo-Json|Set-Content $statePath -Encoding UTF8
    & codex mcp list
}
'mcp-status' { Assert-CodexAvailable; & codex mcp list }
'doctor' {
    Write-Host "`n=== SUPABASE MULTI DOCTOR ==="
    $c=Get-Command codex -ErrorAction SilentlyContinue; Write-Host "Codex: $(if($c){'OK'}else{'MANCANTE'})"
    foreach($a in Get-SbPropertyNames $r.accounts){$e=[string]$r.accounts.$a.token_env;Write-Host "Account $a -> $e -> $(if(Test-SbEnvPresent $e){'OK'}else{'PAT MANCANTE'})"}
    foreach($p in Get-SbPropertyNames $r.projects){$x=$r.projects.$p;$refOk=([string]$x.project_ref -and [string]$x.project_ref -notmatch 'INCOLLA_QUI');$e=Get-SbEffectiveTokenEnv $r $p;Write-Host "Project $p -> ref=$(if($refOk){'OK'}else{'DA COMPILARE'}) token=$(if(Test-SbEnvPresent $e){'OK'}else{'MANCANTE'}) enabled=$($x.enabled)"}
    if($c){& codex mcp list}
}
}

