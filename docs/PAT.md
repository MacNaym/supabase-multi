# Come creare il PAT Supabase

Per ogni account Supabase:
1. Accedi a Supabase con quell'account.
2. Vai in Account Settings -> Access Tokens.
3. Crea un PAT, per esempio `Codex Business`.
4. Se disponibili, preferisci Scoped PAT con i permessi minimi necessari.
5. Copia il PAT e salvalo con `account-token-set`.

Strategia semplice: un PAT per account (`SUPABASE_PAT_BUSINESS`, `SUPABASE_PAT_PERSONAL`).
Strategia più sicura: PAT scoped dedicato per progetto; nel registry il `token_env` del progetto sovrascrive quello dell'account.

Non mettere mai il PAT in registry.json, .supabase-target.json, Git, README o screenshot/log.
