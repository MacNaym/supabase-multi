# Migrazione automatica registry v0.1 -> v0.2 PAT

Se esiste un `registry.json` creato dalla prima versione OAuth, la v0.2.3 lo riconosce.

Al primo comando:

```powershell
.\scripts\supabase-manager.ps1 doctor
```

lo script:

1. crea un backup in `backups/registry.pre-v2.<timestamp>.json`;
2. aggiunge `token_env` a ogni account;
3. aggiunge i campi PAT-era mancanti ai progetti;
4. salva il registry aggiornato;
5. NON inventa né salva nessun PAT.

Esempio:

`business` -> `SUPABASE_PAT_BUSINESS`

Dopo la migrazione devi ancora eseguire:

```powershell
.\scripts\supabase-manager.ps1 account-token-set -Name business
```

per inserire il PAT reale.
