# Come creare il PAT Supabase

Per ogni account/progetto Supabase:
1. Accedi a Supabase con quell'account.
2. Vai in Account Settings -> Access Tokens.
3. Crea un PAT con un nome che descriva chiaramente lo scopo.
4. Preferisci uno **Scoped PAT** limitato al singolo progetto.
5. Concedi solo i permessi necessari.
6. Copia il PAT e salvalo nella variabile ambiente configurata da Supabase Multi.

## Profilo consigliato: sola lettura SQL

Se l'agente deve solo leggere il database:

```text
Database: Read
```

Aggiungi solo ciò che serve davvero, per esempio:

```text
Project Settings: Read
Advisors: Read
Logs: Read
API Keys: Read
```

Con `Database: Read`, il tool MCP ufficiale `execute_sql` è disponibile, ma le query che modificano dati o schema vengono eseguite con privilegi di sola lettura e falliscono.

## Profilo consigliato: sviluppo / SQL in scrittura

Se Supabase Multi deve poter eseguire realmente query come `INSERT`, `UPDATE`, `DELETE`, `CREATE TABLE`, `ALTER TABLE` o altre modifiche tramite `execute_sql`, il PAT deve avere:

```text
Database: Read-write
```

Se deve anche applicare migrazioni tramite gli strumenti Supabase dedicati, aggiungi:

```text
Migrations: Read-write
```

Questi sono permessi separati: `Database: Read-write` abilita SQL in scrittura; `Migrations: Read-write` serve per le operazioni di migrazione come `apply_migration`.

Aggiungi altri permessi di scrittura, per esempio `Edge Functions: Read-write`, solo se il workflow li usa davvero.

## Strategia consigliata

La strategia più sicura è un PAT scoped dedicato per progetto. Nel registry, il `token_env` del progetto indica solo il nome della variabile ambiente: il valore del PAT non viene salvato nel registry.

Per produzione, preferisci `Database: Read` quando basta. Usa `Database: Read-write` solo per target che devono davvero consentire scritture, e mantieni `read_only=true` in Supabase Multi per i target che non devono essere modificati.

Non mettere mai il PAT in `registry.json`, `.supabase-target.json`, Git, README, screenshot o log.

Riferimento ufficiale: https://supabase.com/docs/guides/platform/personal-access-tokens
