const platformBadge=s=>{
  const v=(s||"UNKNOWN").toUpperCase();
  if(v==="ACTIVE") return '<span class="platform active">ACTIVE</span>';
  if(v==="PAUSED") return '<span class="platform paused">PAUSED</span>';
  if(v==="RESTORING"||v==="STARTING") return '<span class="platform pending">'+v+'</span>';
  if(v==="ERROR") return '<span class="platform error">ERROR</span>';
  return '<span class="platform unknown">'+v+'</span>';
};
const loginLabel=m=>({classic:'Email/password',github:'GitHub',google:'Google/Gmail',unknown:'—'}[m]||'—');

let currentLang=localStorage.getItem("supabaseMultiLang")||"en";
const I18N={
  en:{
    history_select_hint:"Choose a full backup and click Select for restore.",tab_create:"Backup",tab_validate:"Validation",tab_restore:"Restore",import_hint:"Choose an existing backup folder. Files remain in place.",import_backup:"Import backup",test_restore:"Test restore",technical_details:"Technical details",restore_hint:"Test a trusted full backup in a disposable local Docker database. No remote writes.",restore_source:"Selected backup",choose_backup:"Choose backup",restore_image:"Local Supabase PostgreSQL image",detect_images:"Detect local images",advanced_settings:"Advanced settings",image_digest:"Pinned image digest",restore_trust:"I trust this backup and authorize local SQL execution.",remote_disabled:"Remote restore is not yet available.",no_backup_selected:"No validated backup selected.",choose_image:"Select a local image",no_images:"No eligible local images found. Install a compatible Supabase image first.",date:"Date",files:"Files",path:"Path",integrity:"Integrity",structure:"SQL structure (preliminary)",restore_not_tested:"Restore not tested",passed:"Passed",failed:"Failed",source_external:"External backup — verify source",complete_backup:"Full backup",partial_backup:"Partial backup",
    nav_dashboard:"Dashboard",nav_account:"Connect account",nav_project:"Connect database",nav_auth:"Authentication",nav_scan:"Scan account",nav_backup:"Backup & Restore",nav_status:"Status",nav_guide:"Guide",language:"Language",diagnostics_title:"Diagnostics / Logs",diagnostics_note:"Technical output for troubleshooting.",orphan_title:"Orphaned secrets",orphan_note:"Supabase PAT environment variables no longer referenced by any account or project. Secret values are never shown.",clean_all_orphans:"Clean all",no_orphans:"No orphaned Supabase secret variables found.",secret_variable:"Environment variable",confirm_delete_orphan:"Delete orphaned secret variable",confirm_clean_all_orphans:"Delete all orphaned Supabase secret variables?",
    dashboard_title:"Dashboard",dashboard_note:"Operational overview of your Supabase accounts and databases.",last_check:"Last check:",db_total:"Databases",db_active:"Active",db_paused:"Paused",db_attention:"Need attention",accounts_total:"Accounts",cli_connected:"CLI connected",project_pats:"Project PATs",orphan_secrets_count:"Orphaned secrets",needs_attention:"Needs attention",needs_attention_note:"Only items that may require action are shown here.",all_good:"Nothing needs attention.",database_overview:"Database overview",issue_paused:"Database paused",issue_status_unknown:"Remote status unknown",issue_pat_missing:"Project PAT missing",issue_account_missing:"Account missing",issue_cli_missing:"Account CLI disconnected",issue_identity_incomplete:"Account identity incomplete",issue_orphans:"Orphaned secrets present",account_title:"Account",project_title:"Project / manual database",auth_title:"Authentication",scan_title:"Scan Supabase account",status_title:"Current status",backup_title:"Backup & Restore",backup_note:"Create and verify local logical backups using the configured project ref and PAT.",backup_mode:"Backup type",backup_full:"Full — roles + schema + data",backup_schema:"Schema only",backup_data:"Data only",backup_destination:"Destination",choose_folder:"Choose folder",create_backup:"Create backup",save_default_destination:"Save as default",backup_credential_hint:"Uses project ref + project PAT. Database password is only a fallback.",backup_history:"Backup history",backup_none:"No backups found.",verify_backup:"Verify",open_folder:"Open folder",guide_title:"Complete guide",
    discovery_model_title:"Discovery PAT model",discovery_model_note:"Use the account-wide PAT only to discover projects. Use a separate scoped PAT for each project's operational access.",
    header_subtitle:"Separate accounts and projects · per-project PAT · CLI fallback · ready for end-to-end tests.",refresh:"Refresh",loading:"Loading…",
    account_identity_note:"Required identity: Supabase email + login method. Existing accounts can remain incomplete until you fill them in.",existing_account:"Existing account",load_account:"Load account",account_alias:"Account alias",account_label:"Account name / label",supabase_email:"Supabase email",login_method:"Login method",not_specified:"Not specified",account_browser:"Account browser",system_default:"System default",select_account:"— Select account —",env_production:"Production",env_development:"Development",env_staging:"Staging",
    discovery_env:"Account-wide Discovery PAT env",optional_discovery:"(optional · discovery only)",discovery_pat:"Account-wide Discovery PAT",optional_replace:"(optional · saves/replaces token)",discovery_pat_note:"Use an account-wide/classic PAT, or an equivalent token with visibility across projects. Do not use a PAT scoped to a single project here.",
    enabled:"Enabled",save_account:"Save account",cancel:"Cancel",pat_guide:"PAT guide",cancel_edit:"Cancel edit",label:"Label",environment:"Environment",scoped_pat_env:"Operational scoped PAT env",scoped_pat:"Operational project-scoped PAT",scoped_pat_note:"(recommended · paste here; not stored in registry)",save_project_pat:"Save project + PAT",
    cli_auth_note:"Starts the official Supabase CLI login in a separate profile. GitHub, Google, and email authentication remain handled by Supabase.",important:"Important:",profile_note:"each account alias uses a separate Supabase CLI profile, so multiple accounts can stay connected at the same time.",connect_supabase:"Connect Supabase",disconnect:"Disconnect",save_replace:"Save / replace",remove_token:"Remove token",
    scan_note:"Use simple CLI login or a manual Discovery PAT.",simple_cli_login:"Simple login (CLI)",scan:"🔍 Scan",import_selected:"Import selected",status_note:"Tokens are never displayed. Supabase status is checked at startup and on every refresh. Last check:",clear:"Clear",open_supabase_project:"Open Supabase project",project:"Project",open_dashboard:"Open Dashboard",
    th_account:"Account",th_login:"Login",th_identity:"Identity",th_browser:"Browser",th_target:"Target",th_configured:"Configured",th_source:"Source",
    complete:"COMPLETE",incomplete:"INCOMPLETE",ready:"READY",new:"NEW",edit:"Edit",delete:"Delete",verify_access:"Verify access",open_project:"Open project",not_verified:"not verified",
    account_in_use:"This account is still used by:",confirm_delete_account:"Delete account",confirm_delete_project:"Delete project",
    modal_error:"Error",modal_message:"Message",oauth_connected:"Status: CLI profile authenticated",oauth_disconnected:"Status: not connected",
    no_account_selected:"Select an account first.",scan_running:"Scanning…",scan_failed:"Scan failed.",projects_found:"Projects found:",imported:"Imported:",project_not_found:"Project not found.",account_not_found:"Account not found.",
    project_loaded:"Project loaded into the form.",project_edit_cancelled:"Project edit cancelled.",account_loaded:"Account loaded into the form.",new_account_mode:"Mode: new account",new_project_mode:"Mode: new project",
    pat_check_running:"Checking access…",open_project_error:"Error opening project:",save_error:"Error saving project/PAT:",ready_log:"Ready.",
    guide_full:`<h3>How it works</h3><p>An account represents the Supabase identity you use to sign in. Projects are separate resources attached to an account.</p><ol><li>Create or load an account and record its email/login method.</li><li>Optionally add an account-wide Discovery PAT with <code>Projects (account-wide): Read</code>, or use a Supabase CLI named profile for discovery.</li><li>Scan the account and import the projects you want to manage.</li><li>For each project, configure a dedicated scoped PAT and its Windows environment-variable name.</li><li>Use <strong>Verify access</strong> to confirm the scoped PAT can reach that project.</li><li>Run <strong>MCP Sync</strong> and <strong>Doctor</strong> after configuration changes.</li></ol><h3>Security model</h3><p>PAT values are never written to the registry JSON. Only environment-variable names are stored. Browser sessions live in isolated local browser profiles.</p>`
  },
  it:{
    history_select_hint:"Scegli un backup completo e premi Seleziona per ripristino.",tab_create:"Backup",tab_validate:"Validazione",tab_restore:"Ripristino",import_hint:"Scegli una cartella di backup esistente. I file restano al loro posto.",import_backup:"Importa backup",test_restore:"Test di ripristino",technical_details:"Dettagli tecnici",restore_hint:"Collauda un backup completo attendibile in un database Docker temporaneo. Nessuna scrittura remota.",restore_source:"Backup selezionato",choose_backup:"Scegli backup",restore_image:"Immagine PostgreSQL Supabase locale",detect_images:"Rileva immagini locali",advanced_settings:"Impostazioni avanzate",image_digest:"Digest immagine fissato",restore_trust:"Considero attendibile il backup e autorizzo l’esecuzione SQL locale.",remote_disabled:"Il ripristino remoto non è ancora disponibile.",no_backup_selected:"Nessun backup validato selezionato.",choose_image:"Seleziona un’immagine locale",no_images:"Nessuna immagine locale idonea. Installa prima un’immagine Supabase compatibile.",date:"Data",files:"File",path:"Percorso",integrity:"Integrità",structure:"Struttura SQL (preliminare)",restore_not_tested:"Ripristino non collaudato",passed:"Superato",failed:"Fallito",source_external:"Backup esterno — verifica la provenienza",complete_backup:"Backup completo",partial_backup:"Backup parziale",
    nav_dashboard:"Dashboard",nav_account:"Connetti account",nav_project:"Connetti database",nav_auth:"Autenticazione",nav_scan:"Scansiona account",nav_backup:"Backup e ripristino",nav_status:"Stato",nav_guide:"Guida",language:"Lingua",diagnostics_title:"Diagnostica / Log",diagnostics_note:"Output tecnico per la risoluzione dei problemi.",orphan_title:"Segreti orfani",orphan_note:"Variabili ambiente PAT Supabase non più referenziate da alcun account o progetto. I valori segreti non vengono mai mostrati.",clean_all_orphans:"Pulisci tutti",no_orphans:"Nessuna variabile segreta Supabase orfana trovata.",secret_variable:"Variabile ambiente",confirm_delete_orphan:"Eliminare la variabile segreta orfana",confirm_clean_all_orphans:"Eliminare tutte le variabili segrete Supabase orfane?",
    dashboard_title:"Dashboard",dashboard_note:"Riepilogo operativo degli account e dei database Supabase.",last_check:"Ultimo controllo:",db_total:"Database",db_active:"Attivi",db_paused:"In pausa",db_attention:"Da controllare",accounts_total:"Account",cli_connected:"CLI connessi",project_pats:"PAT progetto",orphan_secrets_count:"Segreti orfani",needs_attention:"Da controllare",needs_attention_note:"Qui compaiono solo gli elementi che potrebbero richiedere un intervento.",all_good:"Nessun elemento richiede attenzione.",database_overview:"Riepilogo database",issue_paused:"Database in pausa",issue_status_unknown:"Stato remoto sconosciuto",issue_pat_missing:"PAT progetto mancante",issue_account_missing:"Account mancante",issue_cli_missing:"CLI account disconnessa",issue_identity_incomplete:"Identità account incompleta",issue_orphans:"Sono presenti segreti orfani",account_title:"Account",project_title:"Progetto / database manuale",auth_title:"Autenticazione",scan_title:"Scansiona account Supabase",status_title:"Stato corrente",backup_title:"Backup e ripristino",backup_note:"Crea e verifica backup logici locali usando project ref e PAT già configurati.",backup_mode:"Tipo di backup",backup_full:"Completo — ruoli + schema + dati",backup_schema:"Solo schema",backup_data:"Solo dati",backup_destination:"Destinazione",choose_folder:"Scegli cartella",create_backup:"Crea backup",save_default_destination:"Salva come predefinita",backup_credential_hint:"Usa project ref + PAT del progetto. La password DB è solo un fallback.",backup_history:"Cronologia backup",backup_none:"Nessun backup trovato.",verify_backup:"Verifica",open_folder:"Apri cartella",guide_title:"Guida completa",
    discovery_model_title:"Modello Discovery PAT",discovery_model_note:"Usa il PAT account-wide solo per scoprire i progetti. Usa un PAT scoped separato per l'accesso operativo di ogni progetto.",
    header_subtitle:"Account e progetti separati · PAT per progetto · fallback CLI · pronto per i test end-to-end.",refresh:"Aggiorna",loading:"Caricamento…",
    account_identity_note:"Identità obbligatoria: email Supabase + metodo login. Gli account esistenti possono restare incompleti finché non inserisci i dati.",existing_account:"Account esistente",load_account:"Carica account",account_alias:"Alias account",account_label:"Nome account / etichetta",supabase_email:"Email Supabase",login_method:"Metodo login",not_specified:"Non specificato",account_browser:"Browser account",system_default:"Predefinito di sistema",select_account:"— Seleziona account —",env_production:"Produzione",env_development:"Sviluppo",env_staging:"Staging",
    discovery_env:"Discovery PAT account-wide env",optional_discovery:"(opzionale · solo discovery)",discovery_pat:"Discovery PAT account-wide",optional_replace:"(opzionale · salva/sostituisce il token)",discovery_pat_note:"Usa un PAT account-wide/classic, o equivalente con visibilità su più progetti. Non usare qui un PAT scoped limitato a un singolo progetto.",
    enabled:"Abilitato",save_account:"Salva account",cancel:"Annulla",pat_guide:"Guida PAT",cancel_edit:"Annulla modifica",label:"Etichetta",environment:"Ambiente",scoped_pat_env:"PAT operativo scoped env",scoped_pat:"PAT operativo scoped per progetto",scoped_pat_note:"(consigliato · incolla qui; non viene salvato nel registry)",save_project_pat:"Salva progetto + PAT",
    cli_auth_note:"Avvia il login ufficiale della Supabase CLI in un profilo separato. GitHub, Google ed email restano gestiti da Supabase.",important:"Importante:",profile_note:"ogni alias account usa un profilo Supabase CLI separato, così puoi mantenere più account collegati contemporaneamente.",connect_supabase:"Connetti Supabase",disconnect:"Disconnetti",save_replace:"Salva / sostituisci",remove_token:"Rimuovi token",
    scan_note:"Usa Login semplice (CLI) oppure Discovery PAT manuale.",simple_cli_login:"Login semplice (CLI)",scan:"🔍 Scansiona",import_selected:"Importa selezionati",status_note:"I token non vengono mai mostrati. Lo stato Supabase viene verificato all'avvio e ad ogni aggiornamento. Ultimo controllo:",clear:"Pulisci",open_supabase_project:"Apri progetto Supabase",project:"Progetto",open_dashboard:"Apri Dashboard",
    th_account:"Account",th_login:"Login",th_identity:"Identità",th_browser:"Browser",th_target:"Target",th_configured:"Configurato",th_source:"Fonte",
    complete:"COMPLETA",incomplete:"DA COMPLETARE",ready:"PRONTO",new:"NUOVO",edit:"Modifica",delete:"Elimina",verify_access:"Verifica accesso",open_project:"Apri progetto",not_verified:"non verificato",
    account_in_use:"Questo account è ancora usato da:",confirm_delete_account:"Eliminare l'account",confirm_delete_project:"Eliminare il progetto",
    modal_error:"Errore",modal_message:"Messaggio",oauth_connected:"Stato: profilo CLI autenticato",oauth_disconnected:"Stato: non connesso",
    no_account_selected:"Seleziona prima un account.",scan_running:"Scansione in corso…",scan_failed:"Scansione non riuscita.",projects_found:"Progetti trovati:",imported:"Importati:",project_not_found:"Progetto non trovato.",account_not_found:"Account non trovato.",
    project_loaded:"Progetto caricato nel modulo.",project_edit_cancelled:"Modifica progetto annullata.",account_loaded:"Account caricato nel modulo.",new_account_mode:"Modalità: nuovo account",new_project_mode:"Modalità: nuovo progetto",
    pat_check_running:"Verifica accesso in corso…",open_project_error:"Errore apertura progetto:",save_error:"Errore salvataggio progetto/PAT:",ready_log:"Pronto.",
    guide_full:`<h3>Come funziona</h3><p>Un account rappresenta l'identità Supabase usata per accedere. I progetti sono risorse separate collegate a un account.</p><ol><li>Crea o carica un account e registra email/metodo di login.</li><li>Facoltativamente aggiungi un Discovery PAT account-wide con <code>Projects (account-wide): Read</code>, oppure usa un profilo nominato Supabase CLI per la discovery.</li><li>Scansiona l'account e importa i progetti che vuoi gestire.</li><li>Per ogni progetto configura un PAT scoped dedicato e il nome della relativa variabile ambiente Windows.</li><li>Usa <strong>Verifica accesso</strong> per confermare che il PAT scoped raggiunga quel progetto.</li><li>Esegui <strong>MCP Sync</strong> e <strong>Doctor</strong> dopo le modifiche alla configurazione.</li></ol><h3>Modello di sicurezza</h3><p>I valori dei PAT non vengono mai scritti nel registry JSON. Vengono salvati solo i nomi delle variabili ambiente. Le sessioni browser vivono in profili locali isolati.</p>`
  }
};
const t=k=>(I18N[currentLang]&&I18N[currentLang][k])||I18N.en[k]||k;
function applyLanguage(){
  document.documentElement.lang=currentLang;
  document.querySelectorAll("[data-i18n]").forEach(el=>{
    const k=el.dataset.i18n;
    if(t(k))el.textContent=t(k);
  });
  document.querySelectorAll("[data-i18n-html]").forEach(el=>{
    const k=el.dataset.i18nHtml;
    if(t(k))el.innerHTML=t(k);
  });
  const sel=$("#languageSelect");
  if(sel)sel.value=currentLang;
  const af=$("#accountMode"); if(af && !af.textContent.includes("·")) af.textContent=t("new_account_mode");
  const pf=$("#projectMode"); if(pf && !pf.textContent.includes("·")) pf.textContent=t("new_project_mode");
}
function showView(name){
  document.querySelectorAll(".view-panel").forEach(p=>p.classList.toggle("active",p.dataset.viewPanel===name));
  document.querySelectorAll(".nav-btn").forEach(b=>b.classList.toggle("active",b.dataset.view===name));
  window.scrollTo({top:0,behavior:"smooth"});
  if(name==="backup")refreshBackupHistory();
}
function bindNavigation(){
  document.querySelectorAll(".nav-btn").forEach(btn=>btn.onclick=()=>showView(btn.dataset.view));
  const sel=$("#languageSelect");
  if(sel)sel.onchange=async()=>{
    currentLang=sel.value;
    localStorage.setItem("supabaseMultiLang",currentLang);
    applyLanguage();
    await refresh();
  };
  applyLanguage();
}

const HELP_TEXTS={
  en:{
    restore_image:{title:"What is a local database image?",body:"<p>A Docker image contains the PostgreSQL engine and Supabase extensions, not your backup data. Multiple installed versions are normal.</p><p>Choose the version matching the original database where possible. The backup CLI version is not the PostgreSQL version. If unknown, check your source database version before selecting. The test creates a temporary offline container and does not modify the cloud database.</p><p>The short identifier distinguishes images; the full pinned digest is in Advanced settings. No image is downloaded automatically.</p>"},
    restore_source:{title:"Choose a backup",body:"<p>Open History, choose the account and project, then click Select for restore next to the desired full backup. The software validates it and returns to Restore. External backups can be imported in Validation. Verify alone does not prove restorability.</p>"},
    pat:{title:"PAT guide — create and connect tokens",body:`<h3>1. Open Access Tokens</h3><p>Sign in to the correct Supabase account and open <strong>Account → Access Tokens</strong>.</p><h3>2. Choose the right token</h3><p><strong>Account-wide Discovery PAT:</strong> used only to list projects. Minimum permission: <code>Projects (account-wide): Read</code>.</p><p><strong>Project-scoped operational PAT:</strong> recommended for Codex/MCP and automation.</p><h3>3. Recommended operational permissions</h3><ul><li>Project Settings — Read</li><li>Advisors — Read</li><li>Logs — Read</li><li>API Keys — Read</li><li>Database — Read-write</li><li>Migrations — Read-write</li><li>Edge Functions — Read-write</li></ul><h3>4. Store it</h3><p>Paste the project PAT in <strong>Connect database</strong>. The secret is stored in a Windows user environment variable; the registry keeps only the variable name.</p>`},
    account:{title:"Connect account",body:`<h3>Account ≠ project</h3><p>An account is the Supabase identity you sign in with. It can see one or many projects.</p><h3>Email and login method</h3><p>These are saved only as operational hints so you know which identity to use when opening the Dashboard.</p><h3>Discovery PAT</h3><p>Optional. Use it only for account-wide project discovery. The minimum permission is <code>Projects (account-wide): Read</code>.</p>`},
    auth:{title:"Authentication",body:`<h3>CLI login</h3><p>Connect Supabase starts the official CLI login flow using a named profile for the selected account.</p><h3>Browser sessions</h3><p>Dashboard sessions are separate from CLI/PAT authentication and are stored in isolated browser profiles.</p>`},
    scan:{title:"Scan account",body:`<h3>Procedure</h3><ol><li>Select the account.</li><li>Choose CLI or Discovery PAT.</li><li>Run the scan.</li><li>Import only the projects you want to manage.</li><li>If a ref already exists under another account, reassign it instead of duplicating it.</li></ol>`},
    project:{title:"Connect database",body:`<h3>Operational project credentials</h3><p>Each project has a <code>project_ref</code>, environment, MCP configuration, and PAT environment variable.</p><h3>Scoped PAT</h3><p>Prefer a token limited to this project. The secret itself is never stored in the registry JSON.</p>`},
    status:{title:"Status",body:`<h3>Accounts</h3><p>Shows identity, CLI status, browser-profile status, and Discovery PAT availability.</p><h3>Projects</h3><p>Shows remote Supabase status, verification source, scoped PAT availability, project ref, and MCP target.</p>`},
    output:{title:"Diagnostics / Logs",body:`<p>Shows MCP Sync and Doctor output. Tokens are never printed.</p>`}
  },
  it:{
    restore_image:{title:"Che cos’è un’immagine locale?",body:"<p>Un’immagine Docker contiene il motore PostgreSQL e le estensioni Supabase, non i tuoi backup. È normale avere più versioni installate.</p><p>Scegli, se possibile, la versione corrispondente al database di origine. La versione della CLI non è quella di PostgreSQL. Se non conosci la versione del database sorgente, controllala prima di scegliere. Il test crea un container temporaneo isolato e non modifica il database cloud.</p><p>Il codice breve distingue le immagini; il digest completo è nelle impostazioni avanzate. Nessuna immagine viene scaricata automaticamente.</p>"},
    restore_source:{title:"Come scegliere un backup",body:"<p>Apri Cronologia, scegli account e progetto, quindi premi Seleziona per ripristino accanto al backup completo desiderato. Il software lo valida e torna alla scheda Ripristino. Per backup esterni usa Importa backup in Validazione. La verifica dei file non dimostra da sola la ripristinabilità.</p>"},
    pat:{title:"Guida PAT — crea e collega i token",body:`<h3>1. Apri Access Tokens</h3><p>Accedi all'account Supabase corretto e apri <strong>Account → Access Tokens</strong>.</p><h3>2. Scegli il token corretto</h3><p><strong>Discovery PAT account-wide:</strong> serve solo a elencare i progetti. Permesso minimo: <code>Projects (account-wide): Read</code>.</p><p><strong>PAT operativo scoped per progetto:</strong> consigliato per Codex/MCP e automazioni.</p><h3>3. Permessi operativi consigliati</h3><ul><li>Project Settings — Read</li><li>Advisors — Read</li><li>Logs — Read</li><li>API Keys — Read</li><li>Database — Read-write</li><li>Migrations — Read-write</li><li>Edge Functions — Read-write</li></ul><h3>4. Salvataggio</h3><p>Incolla il PAT del progetto in <strong>Connetti database</strong>. Il segreto viene salvato in una variabile ambiente Windows dell'utente; il registry conserva solo il nome della variabile.</p>`},
    account:{title:"Connetti account",body:`<h3>Account ≠ progetto</h3><p>Un account è l'identità Supabase con cui accedi. Può vedere uno o molti progetti.</p><h3>Email e metodo di login</h3><p>Vengono salvati solo come promemoria operativo per sapere quale identità usare quando apri il Dashboard.</p><h3>Discovery PAT</h3><p>Opzionale. Usalo solo per la discovery account-wide. Il permesso minimo è <code>Projects (account-wide): Read</code>.</p>`},
    auth:{title:"Autenticazione",body:`<h3>Login CLI</h3><p>Connetti Supabase avvia il flusso di login ufficiale della CLI usando un profilo nominato per l'account selezionato.</p><h3>Sessioni browser</h3><p>Le sessioni Dashboard sono separate dall'autenticazione CLI/PAT e vengono salvate in profili browser isolati.</p>`},
    scan:{title:"Scansiona account",body:`<h3>Procedura</h3><ol><li>Seleziona l'account.</li><li>Scegli CLI o Discovery PAT.</li><li>Avvia la scansione.</li><li>Importa solo i progetti che vuoi gestire.</li><li>Se un ref esiste già sotto un altro account, riassegnalo invece di duplicarlo.</li></ol>`},
    project:{title:"Connetti database",body:`<h3>Credenziali operative del progetto</h3><p>Ogni progetto ha <code>project_ref</code>, ambiente, configurazione MCP e variabile ambiente del PAT.</p><h3>PAT scoped</h3><p>Preferisci un token limitato a questo progetto. Il segreto non viene mai salvato nel registry JSON.</p>`},
    status:{title:"Stato",body:`<h3>Account</h3><p>Mostra identità, stato CLI, stato del profilo browser e disponibilità del Discovery PAT.</p><h3>Progetti</h3><p>Mostra stato remoto Supabase, fonte della verifica, disponibilità dello scoped PAT, project ref e target MCP.</p>`},
    output:{title:"Diagnostica / Log",body:`<p>Mostra l'output di MCP Sync e Doctor. I token non vengono mai stampati.</p>`}
  }
};
const helpTexts=new Proxy({},{
  get(_target,key){return (HELP_TEXTS[currentLang]||HELP_TEXTS.en)[key];}
});
const $=s=>document.querySelector(s);let state={accounts:[],projects:[]},discovered=[];const output=$("#output"),notice=$("#notice");
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const slug=s=>String(s||"project").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"")||"project";
const env=s=>"SUPABASE_PAT_"+slug(s).replace(/-/g,"_").toUpperCase();
let noticeTimer=null;
function show(msg,err=false){
  const modal=$("#messageModal");
  const title=$("#messageModalTitle");
  const body=$("#messageModalBody");
  title.textContent=err?t("modal_error"):t("modal_message");
  body.textContent=String(msg||"");
  modal.classList.remove("hidden","error");
  if(err) modal.classList.add("error");
}
function closeMessageModal(){
  $("#messageModal").classList.add("hidden");
}
$("#messageModalClose").onclick=closeMessageModal;
$("#messageModalOk").onclick=closeMessageModal;
$("#messageModal").addEventListener("click",e=>{if(e.target===$("#messageModal"))closeMessageModal()});
document.addEventListener("keydown",e=>{if(e.key==="Escape")closeMessageModal()});
if($("#noticeClose"))$("#noticeClose").onclick=()=>$("#notice").classList.add("hidden");
function log(t){output.textContent=String(t||"")}
async function api(path,body){const r=await fetch(path,{method:body===undefined?"GET":"POST",headers:body===undefined?{}:{"Content-Type":"application/json"},body:body===undefined?undefined:JSON.stringify(body)});const d=await r.json();if(!r.ok||!d.ok)throw new Error(d.error||d.message||t("modal_error"));return d}
function opts(el,arr){const cur=el.value;el.innerHTML=arr.map(a=>`<option value="${esc(a.name)}">${esc(a.name)} — ${esc(a.label)}</option>`).join("");if(arr.some(a=>a.name===cur))el.value=cur}
function badge(v){return v?'<span class="ok">OK</span>':'<span class="bad">NO</span>'}

function renderDashboard(data){
  const projects=data.projects||[];
  const accounts=data.accounts||[];
  const orphans=data.orphan_secrets||[];

  const active=projects.filter(p=>(p.platform_status||"").toUpperCase()==="ACTIVE").length;
  const paused=projects.filter(p=>(p.platform_status||"").toUpperCase()==="PAUSED").length;
  const projectPats=projects.filter(p=>p.token_ok).length;
  const cliConnected=accounts.filter(a=>a.oauth_connected).length;

  const attention=[];
  projects.forEach(p=>{
    const st=(p.platform_status||"UNKNOWN").toUpperCase();
    if(st==="PAUSED") attention.push({type:t("issue_paused"),name:p.name,detail:p.account||"—"});
    else if(!p.platform_seen || ["UNKNOWN","ERROR"].includes(st)) attention.push({type:t("issue_status_unknown"),name:p.name,detail:p.pat_status_error_kind||p.status_source||"—"});
    if(!p.token_ok) attention.push({type:t("issue_pat_missing"),name:p.name,detail:p.token_env||"—"});
    if(!p.account) attention.push({type:t("issue_account_missing"),name:p.name,detail:"—"});
  });
  accounts.forEach(a=>{
    if(!a.oauth_connected) attention.push({type:t("issue_cli_missing"),name:a.name,detail:a.email||"—"});
    if(!a.identity_complete) attention.push({type:t("issue_identity_incomplete"),name:a.name,detail:a.email||"—"});
  });
  if(orphans.length) attention.push({type:t("issue_orphans"),name:String(orphans.length),detail:orphans.join(", ")});

  $("#kpiDbTotal").textContent=projects.length;
  $("#kpiDbActive").textContent=active;
  $("#kpiDbPaused").textContent=paused;
  $("#kpiDbAttention").textContent=attention.length;
  $("#kpiAccounts").textContent=accounts.length;
  $("#kpiCli").textContent=cliConnected+"/"+accounts.length;
  $("#kpiProjectPat").textContent=projectPats+"/"+projects.length;
  $("#kpiOrphans").textContent=orphans.length;
  $("#dashboardCheckedAt").textContent=data.platform_checked_at||"—";

  const ae=$("#attentionEmpty"), aw=$("#attentionWrap");
  if(attention.length){
    ae.classList.add("hidden");aw.classList.remove("hidden");
    $("#attentionTable").innerHTML=`<thead><tr><th>${t("needs_attention")}</th><th>${t("th_target")}</th><th>Detail</th></tr></thead><tbody>`+
      attention.map(x=>`<tr><td><span class="warn">${esc(x.type)}</span></td><td>${esc(x.name)}</td><td>${esc(x.detail)}</td></tr>`).join("")+`</tbody>`;
  }else{
    ae.classList.remove("hidden");aw.classList.add("hidden");$("#attentionTable").innerHTML="";
  }

  $("#dashboardProjectsTable").innerHTML=`<thead><tr><th>${t("th_target")}</th><th>${t("th_account")}</th><th>Supabase</th><th>${t("th_source")}</th><th>PAT</th><th>MCP</th></tr></thead><tbody>`+
    projects.map(p=>`<tr><td><strong>${esc(p.name)}</strong></td><td>${esc(p.account||"—")}</td><td>${platformBadge(p.platform_status)}</td><td>${esc(p.status_source||"—")}</td><td>${badge(p.token_ok)}</td><td>${esc(p.mcp||"—")}</td></tr>`).join("")+
    `</tbody>`;
}

async function refresh(){try{applyLanguage();
try { const {runtime}=await api("/api/runtime"); const version=runtime.app_version||"unknown"; $("#appVersionHeader").textContent="LOCAL CONTROL PANEL · V"+version; $("#appVersionFooter").textContent="Supabase Multi "+version+" · Backup "+(runtime.backup_module_version||"unknown")+" · "+(runtime.git_commit||"").slice(0,7); } catch(e) { $("#appVersionHeader").textContent="LOCAL CONTROL PANEL · VERSION UNKNOWN"; }
const{data}=await api("/api/state");state=data;$("#rootPath").textContent=data.root;renderDashboard(data);renderBackupProjectSelector(data);
["authAccount","discoverAccount","projectAccount"].forEach(function(id){
  const el=$("#"+id);
  const previous=el.value;
  opts(el,data.accounts);
  if(previous && Array.from(el.options).some(function(o){return o.value===previous;})){
    el.value=previous;
  }
});
const accountLoad=$("#accountLoadSelect");
if(accountLoad){
  const previousLoad=accountLoad.value;
  accountLoad.innerHTML='<option value="">— Seleziona account —</option>'+
    data.accounts.map(a=>`<option value="${esc(a.name)}">${esc(a.name)}${a.email?' — '+esc(a.email):''}</option>`).join("");
  if(previousLoad && Array.from(accountLoad.options).some(o=>o.value===previousLoad)){
    accountLoad.value=previousLoad;
  }
}
$("#accountsTable").innerHTML=`<thead><tr><th>${t("th_account")}</th><th>Email</th><th>${t("th_login")}</th><th>${t("th_identity")}</th><th>CLI</th><th>${t("th_browser")}</th><th>Discovery PAT</th><th></th></tr></thead><tbody>`+
data.accounts.map(a=>`<tr><td><strong>${esc(a.name)}</strong><br>${esc(a.label)}</td><td>${esc(a.email||"—")}</td><td>${esc(loginLabel(a.login_method))}</td><td>${a.identity_complete?'<span class="ok">'+t("complete")+'</span>':'<span class="warn">'+t("incomplete")+'</span>'}</td><td>${badge(a.oauth_connected)}</td><td>${a.browser_profile_ready?'<span class="ok">'+t("ready")+'</span>':'<span class="muted">'+t("new")+'</span>'}<br><span class="muted">${esc(a.browser)}</span></td><td>${a.discovery_token_env?badge(a.discovery_token_ok):"—"}</td><td><button class="edit-account-btn secondary" data-account="${esc(a.name)}">${t("edit")}</button> <button class="delete-account-btn danger" data-account="${esc(a.name)}">${t("delete")}</button></td></tr>`).join("")+`</tbody>`;
$("#projectsTable").innerHTML=`<thead><tr><th>${t("th_target")}</th><th>${t("th_account")}</th><th>${t("th_configured")}</th><th>Supabase</th><th>${t("th_source")}</th><th>ref</th><th>PAT</th><th>MCP</th><th></th></tr></thead><tbody>`+
data.projects.map(p=>`<tr><td>${esc(p.name)}</td><td>${esc(p.account)}</td><td>${p.enabled?'<span class="ok">ENABLED</span>':'<span class="bad">DISABLED</span>'}</td><td>${platformBadge(p.platform_status)}${p.platform_seen?'':'<br><span class="muted">'+t("not_verified")+'</span>'}${(!p.platform_seen && p.pat_status_error_kind)?'<br><span class="muted">'+esc(p.pat_status_error_kind)+'</span>':''}</td><td>${esc(p.status_source||"—")}</td><td>${esc(p.project_ref)}</td><td>${badge(p.token_ok)}</td><td>${esc(p.mcp)}</td><td><button class="edit-project-btn secondary" data-project="${esc(p.name)}">${t("edit")}</button> <button class="pat-check-btn secondary" data-project="${esc(p.name)}">${t("verify_access")}</button> <button class="open-project-btn" data-project="${esc(p.name)}">${t("open_project")}</button> <button class="delete-project-btn danger" data-project="${esc(p.name)}">${t("delete")}</button></td></tr>`).join("")+`</tbody>`;

const orphans=data.orphan_secrets||[];
const orphanEmpty=$("#orphanSecretsEmpty"), orphanWrap=$("#orphanSecretsWrap"), cleanAll=$("#cleanAllOrphansBtn");
if(orphans.length){
  orphanEmpty.classList.add("hidden");
  orphanWrap.classList.remove("hidden");
  cleanAll.classList.remove("hidden");
  $("#orphanSecretsTable").innerHTML=`<thead><tr><th>${t("secret_variable")}</th><th></th></tr></thead><tbody>`+
    orphans.map(name=>`<tr><td><code>${esc(name)}</code></td><td><button class="delete-orphan-btn danger" data-env="${esc(name)}">${t("delete")}</button></td></tr>`).join("")+
    `</tbody>`;
}else{
  orphanEmpty.classList.remove("hidden");
  orphanWrap.classList.add("hidden");
  cleanAll.classList.add("hidden");
  $("#orphanSecretsTable").innerHTML="";
}

bindOpenProjectButtons();bindPatCheckButtons();bindDeleteButtons();bindOrphanSecretButtons();bindEditAccountButtons();bindEditProjectButtons();
if($("#platformCheckedAt")) $("#platformCheckedAt").textContent=data.platform_checked_at||"—";
updateOauthStatus()
}catch(e){show(e.message,true)}}
function updateOauthStatus(){const a=state.accounts.find(x=>x.name===$("#authAccount").value);$("#oauthStatus").innerHTML=a?.oauth_connected?'<span class="ok">'+t("oauth_connected")+'</span>':'<span class="bad">'+t("oauth_disconnected")+'</span>'}
$("#authAccount").onchange=updateOauthStatus;
$("#tabSimple").onclick=()=>{$("#simpleAuth").classList.remove("hidden");$("#manualAuth").classList.add("hidden");$("#tabSimple").classList.add("active");$("#tabManual").classList.remove("active")}
$("#tabManual").onclick=()=>{$("#manualAuth").classList.remove("hidden");$("#simpleAuth").classList.add("hidden");$("#tabManual").classList.add("active");$("#tabSimple").classList.remove("active")}
$("#accountForm").onsubmit=async e=>{
  e.preventDefault();
  const f=e.target;
  const o=Object.fromEntries(new FormData(f));
  const discoveryToken=(o.discovery_token_value||"").trim();
  delete o.discovery_token_value;
  o.enabled=f.enabled.checked;
  try{
    const r=await api("/api/account",o);
    let message=r.message;
    if(discoveryToken){
      const tr=await api("/api/token",{account:o.name,kind:"discovery",token:discoveryToken});
      message+=" "+tr.message;
    }else{
      message+=" Discovery PAT non modificato.";
    }
    f.discovery_token_value.value="";
    show(message);
    f.reset();
    f.enabled.checked=true;
    f.browser.value="default";
    f.login_method.value="unknown";
    if($("#accountMode"))$("#accountMode").textContent="Modalità: nuovo account";
    if($("#accountLoadSelect"))$("#accountLoadSelect").value="";
    await refresh();
  }catch(x){
    if(f.discovery_token_value)f.discovery_token_value.value="";
    show(x.message,true);
  }
}
$("#connectBtn").onclick=async()=>{
  const account=$("#authAccount").value;
  if(!account)return;
  try{
    const r=await api("/api/oauth-start",{account});
    show(r.message+" Completa il login nella finestra/nel browser aperto da Supabase, poi torna qui e premi Aggiorna.");
  }catch(e){
    show(e.message,true);
  }
}
$("#disconnectBtn").onclick=async()=>{const account=$("#authAccount").value;if(!confirm("Rimuovere la sessione OAuth locale?"))return;try{const r=await api("/api/oauth-disconnect",{account});show(r.message);await refresh()}catch(e){show(e.message,true)}}
$("#tokenForm").onsubmit=async e=>{e.preventDefault();const o=Object.fromEntries(new FormData(e.target));o.account=$("#authAccount").value;try{const r=await api("/api/token",o);show(r.message);e.target.token.value="";await refresh()}catch(x){show(x.message,true)}}
$("#clearTokenBtn").onclick=async()=>{try{const r=await api("/api/token-clear",{account:$("#authAccount").value,kind:"discovery"});show(r.message);await refresh()}catch(e){show(e.message,true)}}
$("#discoverBtn").onclick=async()=>{
  const account=$("#discoverAccount").value;
  const mode=$("#discoverMode").value;
  if(!account){
    show(t("no_account_selected"),true);
    return;
  }
  $("#discoveryEmpty").classList.remove("hidden");
  $("#discoveryEmpty").textContent=t("scan_running");
  $("#discoveryResults").classList.add("hidden");

  try{
    const r=await api("/api/discover",{account:account,mode:mode});
    discovered=Array.isArray(r.projects)?r.projects:[];
    renderDiscovery(account);
    show(t("projects_found")+" "+discovered.length);
  }catch(e){
    discovered=[];
    $("#discoveryResults").classList.add("hidden");
    $("#discoveryEmpty").classList.remove("hidden");
    $("#discoveryEmpty").textContent=t("scan_failed");
    show("Errore scansione: "+(e && e.message ? e.message : String(e)),true);
  }
}

function renderDiscovery(scannedAccount){
  const account=scannedAccount || $("#discoverAccount").value;

  if(!Array.isArray(discovered) || discovered.length===0){
    $("#discoveryResults").classList.add("hidden");
    $("#discoveryEmpty").classList.remove("hidden");
    $("#discoveryEmpty").textContent="Nessun progetto trovato.";
    return;
  }

  $("#discoveryEmpty").classList.add("hidden");
  $("#discoveryResults").classList.remove("hidden");

  const projects=(state && Array.isArray(state.projects)) ? state.projects : [];
  const existingByRef={};
  projects.forEach(function(p){
    if(p && p.project_ref) existingByRef[p.project_ref]=p;
  });

  let accountInfo=null;
  if(state && Array.isArray(state.accounts)){
    accountInfo=state.accounts.find(function(a){return a.name===account;}) || null;
  }
  const accountEmail=(accountInfo && accountInfo.email) ? accountInfo.email : "email non configurata";
  const accountLogin=accountInfo ? loginLabel(accountInfo.login_method) : "—";

  let rows="";
  discovered.forEach(function(p,i){
    const ref=(p && p.ref) ? p.ref : "";
    const existing=existingByRef[ref] || null;
    const existingAccount=(existing && existing.account) ? existing.account : "";
    const same=!!existing && existingAccount===account;
    const mismatch=!!existing && existingAccount!==account;
    const targetValue=(existing && existing.name) ? existing.name : slug((p && p.name) ? p.name : "project")+"-prod";
    const envValue=(existing && existing.token_env) ? existing.token_env : env((p && p.name) ? p.name : "project");

    let statusBadge="";
    if(same) statusBadge=' <span class="ok">già importato</span>';
    else if(mismatch) statusBadge=' <span class="warn">già importato sotto '+esc(existingAccount)+'</span>';

    let reassign="";
    if(mismatch){
      reassign='<button class="reassign-btn" data-project="'+esc(existing.name)+'" data-account="'+esc(account)+'">Riassegna a questo account</button>';
    }

    rows +=
      '<tr>'+
      '<td><input type="checkbox" data-check="'+i+'" '+(same||mismatch?'disabled':'')+'></td>'+
      '<td>'+esc((p && p.name) ? p.name : "—")+statusBadge+'</td>'+
      '<td>'+esc(ref)+'</td>'+
      '<td><span class="status-'+esc((p && p.status_group) ? p.status_group : "")+'">'+esc((p && p.status) ? p.status : "—")+'</span></td>'+
      '<td>'+esc((p && p.region) ? p.region : "—")+'</td>'+
      '<td>'+esc(existingAccount || "—")+'</td>'+
      '<td><input data-target="'+i+'" value="'+esc(targetValue)+'" '+(same||mismatch?'disabled':'')+'></td>'+
      '<td><input data-env="'+i+'" value="'+esc(envValue)+'" '+(same||mismatch?'disabled':'')+'></td>'+
      '<td>'+reassign+'</td>'+
      '<td><button class="open-project-btn" data-account="'+esc(account)+'" data-ref="'+esc(ref)+'">Apri progetto</button></td>'+
      '</tr>';
  });

  $("#discoveryTable").innerHTML=
    '<caption class="scan-account-banner"><strong>Account scansionato:</strong> '+esc(account)+' · '+esc(accountEmail)+' · '+esc(accountLogin)+'</caption>'+
    '<thead><tr><th></th><th>Progetto</th><th>Ref</th><th>Stato</th><th>Regione</th><th>Account attuale</th><th>Target</th><th>token_env</th><th></th><th></th></tr></thead>'+
    '<tbody>'+rows+'</tbody>';

  bindOpenProjectButtons();
  bindReassignButtons();
}

$("#importSelectedBtn").onclick=async()=>{
  const account=$("#discoverAccount").value;
  const items=[];
  document.querySelectorAll("[data-check]:checked").forEach(function(c){
    const i=Number(c.dataset.check);
    const p=discovered[i];
    if(!p)return;
    const targetEl=document.querySelector('[data-target="'+i+'"]');
    const envEl=document.querySelector('[data-env="'+i+'"]');
    items.push({
      ref:p.ref,
      label:p.name,
      target:targetEl ? targetEl.value : slug(p.name)+"-prod",
      token_env:envEl ? envEl.value : env(p.name)
    });
  });

  if(!items.length){
    show("Seleziona almeno un progetto nuovo.",true);
    return;
  }

  try{
    const r=await api("/api/import-projects",{account:account,projects:items});
    show(r.message);
    log(t("imported")+" "+((r.imported||[]).join(", ")));
    await refresh();
    renderDiscovery(account);
  }catch(e){
    show(e.message,true);
  }
}



function bindPatCheckButtons(){
  document.querySelectorAll(".pat-check-btn").forEach(btn=>{
    btn.onclick=async()=>{
      const project=btn.dataset.project;
      try{
        show("Verifica accesso in corso per "+project+"…");
        const r=await api("/api/project-pat-check",{project});
        const msg=r.message+" Fonte: "+(r.source||"—")+(r.fallback_used?" (fallback dal PAT).":"")+(r.token_env?" Env: "+r.token_env+".":"");
        show(msg);
        log(msg);
        await refresh();
      }catch(e){
        const msg="Accesso "+project+": "+(e && e.message ? e.message : String(e));
        show(msg,true);
        log(msg);
      }
    };
  });
}

async function openProject(payload){
  try{
    const r=await api("/api/open-project",payload);
    show(r.message+" Se è la prima apertura con questo account, completa il login Supabase nel browser dedicato.");
    await refresh();
  }catch(e){
    show("Errore apertura progetto: "+(e && e.message ? e.message : String(e)),true);
  }
}

let pendingDashboardProject=null;

function closeLoginInfoModal(){
  $("#loginInfoModal").classList.add("hidden");
  pendingDashboardProject=null;
}

function showLoginInfo(projectName){
  const p=(state.projects||[]).find(x=>x.name===projectName);
  if(!p){show(t("project_not_found"),true);return}
  const a=(state.accounts||[]).find(x=>x.name===p.account)||{};
  pendingDashboardProject=projectName;

  $("#loginProjectName").textContent=p.name||"—";
  $("#loginAccountName").textContent=p.account||"—";
  $("#loginEmail").textContent=a.email||"NON CONFIGURATA";
  $("#loginMethod").textContent=loginLabel(a.login_method||"unknown");
  $("#loginBrowser").textContent=a.browser||"default";

  const complete=!!a.email && (a.login_method||"unknown")!=="unknown";
  $("#loginWarning").textContent=complete
    ? "Se Supabase richiede il login, usa queste credenziali. Il browser verrà aperto con il profilo dedicato a questo account."
    : "Attenzione: email o metodo di login non sono completi. Puoi comunque aprire il Dashboard, ma conviene prima completare l'account nel pannello.";

  $("#loginInfoModal").classList.remove("hidden");
}

$("#loginInfoClose").onclick=closeLoginInfoModal;
$("#loginInfoCancel").onclick=closeLoginInfoModal;
$("#loginInfoModal").addEventListener("click",e=>{if(e.target===$("#loginInfoModal"))closeLoginInfoModal()});

$("#loginInfoOpen").onclick=async()=>{
  const name=pendingDashboardProject;
  if(!name)return;
  try{
    const r=await api("/api/open-project",{project:name});
    closeLoginInfoModal();
    show(r.message);
  }catch(e){
    show(e.message,true);
  }
};

function bindOpenProjectButtons(){
  document.querySelectorAll(".open-project-btn").forEach(btn=>{
    btn.onclick=()=>showLoginInfo(btn.dataset.project);
  });
}



function resetProjectForm(){
  const f=$("#projectForm");
  f.reset();
  f.original_name.value="";
  f.enabled.checked=true;
  f.read_only.checked=false;
  if(f.token_value)f.token_value.value="";
  if($("#projectMode"))$("#projectMode").textContent=t("new_project_mode");
  $("#cancelProjectEdit").classList.add("hidden");
}

function loadProjectIntoForm(projectName){
  const p=(state.projects||[]).find(x=>x.name===projectName);
  if(!p){show(t("project_not_found"),true);return}
  const f=$("#projectForm");
  f.original_name.value=p.name||"";
  f.name.value=p.name||"";
  f.label.value=p.label||"";
  f.account.value=p.account||"";
  f.project_ref.value=p.project_ref||"";
  f.environment.value=p.environment||"production";
  f.token_env.value=p.token_env||"";
  if(f.token_value)f.token_value.value="";
  f.read_only.checked=!!p.read_only;
  f.enabled.checked=!!p.enabled;
  if($("#projectMode"))$("#projectMode").textContent=(currentLang==="it"?"Modalità: modifica · ":"Mode: edit · ")+p.name;
  $("#cancelProjectEdit").classList.remove("hidden");
  const d=f.closest(".view-panel");
  if(d){showView(d.dataset.viewPanel||"account");}
  f.scrollIntoView({behavior:"smooth",block:"start"});
}

function bindEditProjectButtons(){
  document.querySelectorAll(".edit-project-btn").forEach(btn=>{
    btn.onclick=()=>{
      loadProjectIntoForm(btn.dataset.project);
      show(t("project_loaded")+" "+btn.dataset.project);
    };
  });
}

$("#cancelProjectEdit").onclick=()=>{
  resetProjectForm();
  show(t("project_edit_cancelled"));
};

$("#projectForm").onsubmit=async e=>{
  e.preventDefault();
  const f=e.target;
  const o=Object.fromEntries(new FormData(f));
  const token=(o.token_value||"").trim();
  delete o.token_value;
  o.read_only=f.read_only.checked;
  o.enabled=f.enabled.checked;

  if(!o.token_env || !o.token_env.trim()){
    show("PAT progetto env è obbligatoria.",true);
    return;
  }

  try{
    const saved=await api("/api/project",o);
    let message=saved.message;

    if(token){
      const tr=await api("/api/project-token",{project:o.name,token:token});
      message+=" "+tr.message;
    }else{
      message+=" Nessun nuovo PAT inserito: l'eventuale token già presente nella env non è stato modificato.";
    }

    f.token_value.value="";
    show(message);
    log(message);
    resetProjectForm();
    await refresh();
  }catch(x){
    f.token_value.value="";
    show(x.message,true);
    log(t("save_error")+" "+x.message);
  }
};


let lastBackupProject="";
let backupBusy=false;
let backupHistoryGeneration=0;

function clearBackupHistory(){
  backupHistoryGeneration++;
  $("#backupRootHint").textContent="—";
  $("#backupEmpty").classList.remove("hidden");
  $("#backupHistoryWrap").classList.add("hidden");
  $("#backupHistoryTable").innerHTML="";
}

function backupSelection(){
  const account=$("#backupAccount").value;
  const project=$("#backupProject").value;
  const p=(state.projects||[]).find(x=>x.name===project && x.account===account && x.enabled!==false);
  return p ? {account,project,p} : null;
}

function updateBackupControls(){
  const selected=backupSelection();
  $("#backupProjectRef").textContent=selected ? "Ref: "+selected.p.project_ref : "—";
  $("#backupAccount").disabled=backupBusy;
  $("#backupProject").disabled=backupBusy||!$("#backupAccount").value;
  ["backupCreateBtn","backupSaveDestinationBtn","backupChooseFolderBtn","backupDestination","backupMode","backupRefreshBtn"].forEach(id=>$("#"+id).disabled=backupBusy||!selected);
}

function backupOptions(el,items,placeholder,previous){
  el.innerHTML='<option value="">'+esc(placeholder)+'</option>'+items.map(x=>'<option value="'+esc(x.name)+'">'+esc(x.label||x.name)+' ('+esc(x.name)+')</option>').join("");
  el.value=items.some(x=>x.name===previous)?previous:"";
}

function renderBackupProjectSelector(data){
  const account=$("#backupAccount"), project=$("#backupProject");
  if(!account||!project)return;
  const previousAccount=account.value, previousProject=project.value;
  backupOptions(account,data.accounts||[],currentLang==="it"?"Seleziona account":"Select account",previousAccount);
  backupOptions(project,(data.projects||[]).filter(p=>account.value && p.account===account.value && p.enabled!==false),currentLang==="it"?"Seleziona progetto":"Select project",previousProject);
  if(project.value!==lastBackupProject){
    clearBackupHistory();
    const selected=backupSelection();
    $("#backupDestination").value=selected?selected.p.backup_dir||"":"";
  }
  lastBackupProject=project.value;
  updateBackupControls();
}

async function refreshBackupHistory(){
  const selected=backupSelection();
  clearBackupHistory();
  if(!selected)return;
  const generation=backupHistoryGeneration;
  const {account,project}=selected;
  try{
    const destination=($("#backupDestination") ? $("#backupDestination").value : "").trim();
    const r=await api("/api/backup-list",{account,project,destination:destination||null});
    if(generation!==backupHistoryGeneration)return;
    const result=r.result||{};
    const backups=result.backups||[];
    $("#backupRootHint").textContent=result.root||"—";
    if(!backups.length){
      $("#backupEmpty").classList.remove("hidden");
      $("#backupHistoryWrap").classList.add("hidden");
      $("#backupHistoryTable").innerHTML="";
      return;
    }
    $("#backupEmpty").classList.add("hidden");
    $("#backupHistoryWrap").classList.remove("hidden");
    let rows="";
    backups.forEach(function(b){
      rows += "<tr>"+
        "<td>"+esc(b.created_at&&!Number.isNaN(Date.parse(b.created_at))?new Date(b.created_at).toLocaleString(currentLang==="it"?"it-IT":"en-GB"):b.created_at||"—")+"</td>"+
        "<td>"+esc(["full","schema","data"].includes(b.mode)?t("backup_"+b.mode):b.mode||"—")+"</td>"+
        "<td>"+esc(b.files||0)+"</td>"+
        "<td><code>"+esc(b.backup_dir||"")+"</code></td>"+
        "<td class=\"actions\">"+
          "<button class=\"secondary backup-verify-btn\" data-path=\""+esc(b.backup_dir||"")+"\">"+t("verify_backup")+"</button>"+
          "<button class=\"secondary backup-select-restore-btn\" data-path=\""+esc(b.backup_dir||"")+"\">"+(currentLang==="it"?"Seleziona per ripristino":"Select for restore")+"</button>"+
          "<button class=\"secondary backup-open-btn\" data-path=\""+esc(b.backup_dir||"")+"\">"+t("open_folder")+"</button>"+
        "</td>"+
      "</tr>";
    });
    $("#backupHistoryTable").innerHTML=
      "<thead><tr><th>"+t("date")+"</th><th>"+t("backup_mode")+"</th><th>"+t("files")+"</th><th>"+t("path")+"</th><th></th></tr></thead><tbody>"+
      rows+
      "</tbody>";
    bindBackupHistoryButtons();
  }catch(e){
    show(e.message,true);
  }
}

let validatedBackupPath="";
let activeBackupTab="create";
function showBackupTab(tab){
  activeBackupTab=tab;
  document.querySelectorAll("[data-backup-panel]").forEach(el=>el.classList.toggle("hidden",el.dataset.backupPanel!==tab));
  document.querySelectorAll("[data-backup-tab]").forEach(el=>el.setAttribute("aria-pressed",String(el.dataset.backupTab===tab)));
  if(tab==="history")refreshBackupHistory();
  if(tab==="restore"&&!$("#restoreImageSelect").dataset.loaded)detectRestoreImages();
}
document.querySelectorAll("[data-backup-tab]").forEach(el=>el.onclick=()=>showBackupTab(el.dataset.backupTab));
$("#backupHistoryImport").onclick=()=>{showBackupTab("validate");$("#backupImportBtn").click();};
$("#restoreChooseSource").onclick=()=>{showBackupTab("history");$("#backupHistorySelectHint").classList.remove("hidden");};
$("#backupGoRestore").onclick=()=>showBackupTab("restore");
let validatedFullBackup=false;
let validatedBackupFingerprint="";
let restoreSourceVersion=null;
let localRestoreImages=[];
let restoreImageRequest=0;
let restoreBusy=false;
let restoreStarting=false;
let validationBusy=false;
async function validateBackupPath(path){
  if(validationBusy)return;
  validationBusy=true;
  validatedBackupPath="";
  validatedFullBackup=false;
  validatedBackupFingerprint="";
  restoreSourceVersion=null;
  restoreImageRequest++;
  $("#restoreImage").value="";
  $("#restoreImageSelect").value="";
  $("#restoreAutoStatus").textContent="";
  $("#restoreTrusted").checked=false;
  updateRestoreControls();
  const panel=$("#backupValidationReport");
  panel.classList.remove("hidden");
  $("#backupValidationStatus").textContent=currentLang==="it"?"Verifica in corso…":"Validating…";
  $("#backupValidationDetails").textContent="";
  $("#backupValidationSummary").textContent="";
  $("#restoreSourceLabel").textContent=t("no_backup_selected");
  try{
    const {result:r}=await api("/api/backup-import",{path});
    const it=currentLang==="it";
    $("#backupValidationStatus").textContent=r.ok?(it?"Controlli superati — ripristino non collaudato":"Checks passed — restore not tested"):(it?"Validazione non superata":"Validation failed");
    const lines=[
      (it?"Percorso: ":"Path: ")+(r.backup_dir||path),
      (it?"Progetto: ":"Project: ")+(r.project||"—")+" / "+(r.project_ref||"—"),
      "Account: "+(r.account||"—"), "Mode: "+(r.mode||"—"),
      "Date: "+(r.created_at||"—"), "CLI: "+(r.supabase_cli_version||"—"),
      "Bytes: "+(r.total_bytes??"—"),
      "SHA-256: "+(r.integrity_ok?"PASS":"FAIL"),
      (it?"Struttura SQL (euristica): ":"SQL structure (heuristic): ")+(r.structure_ok?"PASS":"FAIL"),
      ...(r.files||[]).map(f=>f.name+" · "+(f.ok?"SHA-256 OK":"SHA-256 FAIL")+" · "+(f.bytes??"—")+" B · "+(f.structure_note||f.error||"")),
      ...(r.error?[r.error]:[]), ...(r.limitations||[])
    ];
    $("#backupValidationDetails").textContent=lines.join("\n");
    const summary=$("#backupValidationSummary");
    [r.project||t("source_external"),r.full_backup?t("complete_backup"):t("partial_backup"),t("integrity")+": "+t(r.integrity_ok?"passed":"failed"),t("structure")+": "+t(r.structure_ok?"passed":"failed"),t("restore_not_tested")].forEach(value=>{const el=document.createElement("p");el.textContent=value;summary.appendChild(el);});
    if(r.ok){restoreSourceVersion=r.postgres_source_version||null;validatedBackupPath=r.backup_dir;validatedFullBackup=r.full_backup===true;validatedBackupFingerprint=r.integrity_fingerprint||"";$("#restoreSourceLabel").textContent=(r.project||t("source_external"))+" · "+(r.created_at||"")+" · "+r.backup_dir;}
    if(r.ok&&validatedFullBackup)await detectRestoreImages();
    updateRestoreControls();
    show(r.ok?(it?"Backup verificato; ripristino da collaudare.":"Backup verified; restore not tested."):(it?"Backup non valido.":"Backup validation failed."),!r.ok);
  }catch(e){
    $("#backupValidationStatus").textContent="Validation failed";
    $("#backupValidationDetails").textContent=e.message;
    show(e.message,true);
  }finally{validationBusy=false;updateRestoreControls();}
}
$("#backupImportBtn").onclick=async function(){
  if(validationBusy)return;
  this.disabled=true;
  try{
    const r=await api("/api/backup-pick-folder",{initial_dir:validatedBackupPath||""});
    if(r.selected)await validateBackupPath(r.selected);
  }catch(e){show(e.message,true)}
  finally{this.disabled=false;}
};

function autoSelectRestoreImage(){
  const it=currentLang==="it";
  const status=$("#restoreAutoStatus");
  const select=$("#restoreImageSelect");
  const version=restoreSourceVersion;
  if(!validatedFullBackup){status.textContent=it?"Seleziona prima un backup completo.":"Select a full backup first.";return;}
  if(!version){status.textContent=it?"Versione PostgreSQL non presente nel dump. Verifica la versione di origine prima di usare le impostazioni avanzate.":"Source PostgreSQL version unavailable. Verify it before using advanced settings.";return;}
  const parts=version.split(".").map(Number);
  const candidates=[];
  for(const image of localRestoreImages){
    if(typeof image==="string")continue;
    for(const tag of image.tags||[]){
      const m=tag.match(/:(\d+)\.(\d+)\.(\d+)\.(\d+)$/);
      if(!m)continue;
      const v=m.slice(1).map(Number);
      if(v[0]===parts[0]&&v[1]===parts[1])candidates.push({digest:image.digest,tag,v});
    }
  }
  candidates.sort((a,b)=>b.v[2]-a.v[2]||b.v[3]-a.v[3]||a.digest.localeCompare(b.digest));
  if(!candidates.length){status.textContent=(it?"Nessuna immagine locale con la stessa versione PostgreSQL ":"No local image matching PostgreSQL ")+version+(it?". Installa una versione compatibile o consulta le impostazioni avanzate.":". Install a compatible image or review advanced settings.");return;}
  const chosen=candidates[0];
  select.value=chosen.digest;
  $("#restoreImage").value=chosen.digest;
  status.textContent=(it?"Selezione automatica per PostgreSQL ":"Automatic selection for PostgreSQL ")+version+" · "+chosen.tag+(it?" (compatibilità da collaudare)":" (compatibility not yet tested)");
}
async function detectRestoreImages(){
  const select=$("#restoreImageSelect"), request=++restoreImageRequest;
  try{
    const {images}=await api("/api/restore-images");
    if(request!==restoreImageRequest)return;
    localRestoreImages=images;
    select.replaceChildren(new Option(t("choose_image"),""));
    for(const image of images){
      const digest=typeof image==="string"?image:image.digest;
      const tags=typeof image==="string"?[]:image.tags||[];
      select.add(new Option((tags.length?tags.join(", "):digest.split("@")[0])+" · "+digest.split("sha256:").pop().slice(0,12),digest));
    }
    select.dataset.loaded="1";
    $("#restoreImage").value="";
    autoSelectRestoreImage();
    if(!images.length)$("#restoreAutoStatus").textContent=t("no_images");
  }catch(e){if(request===restoreImageRequest)$("#restoreAutoStatus").textContent=e.message;}
  updateRestoreControls();
}
$("#restoreDetectImages").onclick=detectRestoreImages;
$("#restoreImageSelect").onchange=function(){$("#restoreImage").value=this.value;$("#restoreAutoStatus").textContent=currentLang==="it"?"Immagine scelta manualmente — verifica compatibilità.":"Manual image selection — verify compatibility.";updateRestoreControls();};
function updateRestoreControls(){
  $("#backupGoRestore").disabled=!validatedFullBackup||validationBusy;
  $("#restoreTestBtn").disabled=restoreBusy||restoreStarting||backupBusy||!validatedFullBackup||!$("#restoreTrusted").checked||!$("#restoreImage").value.trim();
}
$("#restoreTrusted").onchange=updateRestoreControls;
$("#restoreImage").oninput=updateRestoreControls;
let restorePolling=false;
async function pollRestoreJob(){
  if(restorePolling)return;
  restorePolling=true;
  try{
    const {job}=await api("/api/restore-job");
    if(restoreStarting)return;
    restoreBusy=!!job&&["queued","running"].includes(job.status);
    if(job){
      const phases=["validation","container","readiness","copy","restore_roles","restore_schema","restore_data","postcheck"];
      $("#restoreProgress").max=phases.length;
      $("#restoreProgress").value=job.status==="completed"?phases.length:Math.max(0,phases.indexOf(job.phase));
      $("#restoreStatus").textContent=(currentLang==="it"?({queued:"In coda",running:"In corso",completed:"Completato",failed:"Fallito"}[job.status]||job.status):job.status)+" · "+job.phase+" · "+job.elapsed_seconds+" s";
      $("#restoreReport").textContent=job.status+" · "+job.phase+" · "+job.elapsed_seconds+" s"+(job.report?"\n"+JSON.stringify(job.report,null,2):job.error?"\n"+job.error:"");
    }
  }catch(e){if(restoreBusy)$("#restoreReport").textContent="Connection lost; restore status unknown.";}
  finally{restorePolling=false;updateRestoreControls();}
}
$("#restoreTestBtn").onclick=async function(){
  if(this.disabled)return;
  restoreStarting=true;
  updateRestoreControls();
  try{
    await api("/api/restore-test-start",{path:validatedBackupPath,image:$("#restoreImage").value.trim(),trusted:$("#restoreTrusted").checked,approved_fingerprint:validatedBackupFingerprint});
    restoreBusy=true;
  }catch(e){show(e.message,true);}
  finally{restoreStarting=false;updateRestoreControls();await pollRestoreJob();}
};
setInterval(pollRestoreJob,1500);

async function recoverImportedBackupState(){
  try{
    const {result}=await api("/api/backup-imports");
    const latest=(result.backups||[]).find(item=>item.ok&&item.full_backup);
    if(latest)await validateBackupPath(latest.backup_dir);
  }catch(e){/* Imported folders may be unavailable after a restart. */}
}
// Do not silently select the latest external backup on startup.

function bindBackupHistoryButtons(){
  document.querySelectorAll(".backup-select-restore-btn").forEach(btn=>{btn.onclick=async()=>{if(validationBusy)return;await validateBackupPath(btn.dataset.path);if(validatedFullBackup&&validatedBackupFingerprint){showBackupTab("restore");}else{showBackupTab("validate");if(validatedBackupPath&&!validatedFullBackup)show(currentLang==="it"?"Per il test di ripristino serve un backup completo.":"Restore testing requires a full backup.",true);}};});
  document.querySelectorAll(".backup-verify-btn").forEach(function(btn){
    btn.onclick=async function(){
      try{
        showBackupTab("validate");
        await validateBackupPath(btn.dataset.path);
      }catch(e){show(e.message,true)}
    };
  });
  document.querySelectorAll(".backup-open-btn").forEach(function(btn){
    btn.onclick=async function(){
      try{await api("/api/backup-open",{path:btn.dataset.path})}
      catch(e){show(e.message,true)}
    };
  });
}

if($("#backupAccount"))$("#backupAccount").onchange=function(){
  $("#backupProject").value="";
  lastBackupProject="";
  $("#backupDestination").value="";
  clearBackupHistory();
  renderBackupProjectSelector(state);
};
if($("#backupProject"))$("#backupProject").onchange=async function(){
  lastBackupProject=$("#backupProject").value;
  const selected=backupSelection();
  $("#backupDestination").value=selected?selected.p.backup_dir||"":"";
  updateBackupControls();
  await refreshBackupHistory();
};

if($("#backupChooseFolderBtn"))$("#backupChooseFolderBtn").onclick=async function(){
  try{
    const selected=backupSelection(); if(!selected)return;
    const r=await api("/api/backup-pick-folder",{initial_dir:($("#backupDestination").value||"").trim()});
    const current=backupSelection();
    if(r.selected&&current&&current.account===selected.account&&current.project===selected.project)$("#backupDestination").value=r.selected;
  }catch(e){show(e.message,true)}
};

if($("#backupSaveDestinationBtn"))$("#backupSaveDestinationBtn").onclick=async function(){
  const selected=backupSelection();
  if(!selected){show(t("project_not_found"),true);return}
  const {account,project}=selected;
  try{
    const r=await api("/api/backup-settings",{account,project,backup_dir:($("#backupDestination").value||"").trim()});
    show(r.message);
    await refresh();
    await refreshBackupHistory();
  }catch(e){show(e.message,true)}
};

let backupLastStatus="";
let backupPollRunning=false;
let backupStarting=false;
async function pollBackupJob(){
  if(backupPollRunning)return;
  backupPollRunning=true;
  try{
    const {job}=await api("/api/backup-job");
    if(backupStarting)return;
    if(!job){
      if(backupBusy){
        backupBusy=false;
        updateBackupControls();
        $("#backupProgressStatus").textContent="Job not found — server may have restarted.";
      }
      return;
    }
    const active=["queued","running"].includes(job.status);
    const it=currentLang==="it";
    const labels=it?{preflight:"Prerequisiti",connection:"Connessione",pooler:"Connessione IPv4",roles:"Ruoli",schema:"Schema",data:"Dati",manifest:"Manifest",verify:"Verifica integrità",complete:"Completato"}:{preflight:"Preflight",connection:"Connection",pooler:"IPv4 connection",roles:"Roles",schema:"Schema",data:"Data",manifest:"Manifest",verify:"Integrity check",complete:"Complete"};
    $("#backupProgressPanel").classList.remove("hidden");
    $("#backupProgressTitle").textContent=job.account+" / "+job.project+" — "+job.mode.toUpperCase();
    $("#backupProgressBar").max=job.phases.length;
    $("#backupProgressBar").value=job.completed;
    $("#backupProgressPhase").textContent=(labels[job.phase]||job.phase)+" · "+job.completed+"/"+job.phases.length;
    $("#backupProgressStats").textContent=(it?"Tempo: ":"Elapsed: ")+job.elapsed_seconds+" s · "+(it?"File prodotti: ":"Files written: ")+job.bytes_written.toLocaleString()+" B · "+(it?"Fase corrente: ":"Current phase: ")+Math.max(0,Math.floor(job.server_time-job.phase_started_at))+" s · "+(it?"Server raggiungibile":"Server reachable");
    $("#backupProgressStatus").textContent=active?(it?"In corso — la fase attuale può richiedere tempo.":"Running — current phase may take time."):(job.status==="completed"?(it?"Backup completato e verificato.":"Backup completed and verified."):(job.error||"Backup failed"));
    backupBusy=active;
    updateBackupControls();
    const key=job.id+":"+job.status;
    if(key!==backupLastStatus && !active){
      if(job.status==="completed"){show(job.backup_dir);await refreshBackupHistory();}
      else show(job.error||"Backup failed",true);
    }
    backupLastStatus=key;
  }catch(e){
    if(backupBusy)$("#backupProgressStatus").textContent="Server connection lost — backup status unknown; retrying.";
  }finally{backupPollRunning=false;}
}
if($("#backupCreateBtn"))$("#backupCreateBtn").onclick=async function(){
  const selected=backupSelection();
  if(!selected||backupBusy)return;
  backupBusy=true;
  backupStarting=true;
  updateBackupControls();
  try{
    await api("/api/backup-start",{account:selected.account,project:selected.project,mode:$("#backupMode").value,destination:($("#backupDestination").value||"").trim()||null});
    backupStarting=false;
    await pollBackupJob();
  }catch(e){
    backupStarting=false;
    backupBusy=false;
    updateBackupControls();
    show(e.message,true);
    await pollBackupJob();
  }
};
setInterval(pollBackupJob,1500);
pollBackupJob();

if($("#backupRefreshBtn"))$("#backupRefreshBtn").onclick=refreshBackupHistory;

async function action(path){log("Esecuzione...");try{const r=await api(path,{});let t=r.message+"\n\n";if(r.result)t+=(r.result.stdout||"")+(r.result.stderr||"");if(r.sync)t+="--- SYNC ---\n"+(r.sync.stdout||"")+(r.sync.stderr||"")+"\n--- DOCTOR ---\n"+(r.doctor.stdout||"")+(r.doctor.stderr||"");log(t);show(r.message);await refresh()}catch(e){log(e.message);show(e.message,true)}}
if($("#dashboardRefreshBtn"))$("#dashboardRefreshBtn").onclick=refresh;$("#syncBtn").onclick=()=>action("/api/sync");$("#doctorBtn").onclick=()=>action("/api/doctor");$("#allBtn").onclick=()=>action("/api/sync-doctor");$("#refreshBtn").onclick=refresh;$("#clearOutputBtn").onclick=()=>log(t("ready_log"));bindNavigation();refresh();


let helpWindow=null;

function openHelpWindow(sectionKey){
  const h=helpTexts[sectionKey];
  if(!h)return;

  const popupFeatures="width=760,height=850,resizable=yes,scrollbars=yes";
  if(!helpWindow || helpWindow.closed){
    helpWindow=window.open("", "supabaseMultiHelp", popupFeatures);
  }else{
    helpWindow.focus();
  }

  if(!helpWindow){
    show("Il browser ha bloccato la finestra di aiuto. Consenti i popup per 127.0.0.1 e riprova.", true);
    return;
  }

  const doc=helpWindow.document;
  doc.open();
  doc.write(`<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${h.title} — Supabase Multi Help</title>
<style>
  :root{color-scheme:dark;--bg:#0b0d10;--card:#14181d;--line:#283039;--muted:#8e9aa7;--text:#eef2f6;--accent:#69a7ff}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);font:15px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}
  main{max-width:760px;margin:0 auto;padding:28px}
  header{position:sticky;top:0;background:#0b0d10ee;backdrop-filter:blur(8px);padding:0 0 14px;border-bottom:1px solid var(--line);margin-bottom:22px}
  .eyebrow{font-size:11px;letter-spacing:.14em;color:var(--accent);font-weight:700}
  h1{font-size:28px;margin:4px 0 0}
  h3{margin-top:24px;margin-bottom:8px;color:#fff}
  p,li{color:#cbd3dc}
  code{background:#0d1115;border:1px solid var(--line);padding:2px 5px;border-radius:5px}
  .tip{margin-top:28px;border:1px solid var(--line);background:var(--card);border-radius:12px;padding:14px;color:var(--muted)}
</style>
</head>
<body>
<main>
<header>
<div class="eyebrow">SUPABASE MULTI · GUIDA CONTESTUALE</div>
<h1>${h.title}</h1>
</header>
${h.body}
<div class="tip">Puoi lasciare questa finestra aperta, spostarla dove vuoi e tornare al pannello principale mentre segui i passaggi.</div>
</main>
</body>
</html>`);
  doc.close();
  helpWindow.focus();
}

$("#patGuideBtn").onclick=()=>openHelpWindow("pat");

document.querySelectorAll(".help-btn").forEach(btn=>{
  btn.addEventListener("click",()=>openHelpWindow(btn.dataset.help));
});


function bindReassignButtons(){
  document.querySelectorAll(".reassign-btn").forEach(btn=>{
    btn.onclick=async()=>{
      try{
        const r=await api("/api/reassign-project",{project:btn.dataset.project,target_account:btn.dataset.account});
        show(r.message);
        await refresh();
        renderDiscovery();
      }catch(e){show(e.message,true)}
    };
  });
}






function bindOrphanSecretButtons(){
  document.querySelectorAll(".delete-orphan-btn").forEach(btn=>{
    btn.onclick=async()=>{
      const name=btn.dataset.env;
      if(!confirm(t("confirm_delete_orphan")+" "+name+"?"))return;
      try{
        const r=await api("/api/orphan-secret-remove",{name});
        show(r.message);
        await refresh();
      }catch(e){show(e.message,true)}
    };
  });
  const all=$("#cleanAllOrphansBtn");
  if(all){
    all.onclick=async()=>{
      if(!confirm(t("confirm_clean_all_orphans")))return;
      try{
        const r=await api("/api/orphan-secrets-clean",{});
        show(r.message);
        await refresh();
      }catch(e){show(e.message,true)}
    };
  }
}

function bindDeleteButtons(){
  document.querySelectorAll(".delete-account-btn").forEach(btn=>{
    btn.onclick=async()=>{
      const name=btn.dataset.account;
      const a=(state.accounts||[]).find(x=>x.name===name);
      const used=(a&&a.used_by)||[];
      if(used.length){
        show(t("account_in_use")+" "+used.join(", "),true);
        return;
      }
      if(!confirm(t("confirm_delete_account")+" "+name+"?"))return;
      try{
        const r=await api("/api/account-remove",{name:name,clear_tokens:false});
        show(r.message);
        await refresh();
      }catch(e){show(e.message,true)}
    };
  });

  document.querySelectorAll(".delete-project-btn").forEach(btn=>{
    btn.onclick=async()=>{
      const name=btn.dataset.project;
      if(!confirm(t("confirm_delete_project")+" "+name+"?"))return;
      try{
        const r=await api("/api/project-remove",{name:name});
        show(r.message);
        await refresh();
      }catch(e){show(e.message,true)}
    };
  });
}

function loadAccountIntoForm(accountName){
  const a=(state.accounts||[]).find(x=>x.name===accountName);
  if(!a){show(t("account_not_found"),true);return}
  const f=$("#accountForm");
  f.original_name.value=a.name||"";
  f.name.value=a.name||"";
  f.label.value=a.label||"";
  f.email.value=a.email||"";
  if(f.login_method) f.login_method.value=a.login_method||"unknown";
  if(f.browser) f.browser.value=a.browser||"default";
  f.discovery_token_env.value=a.discovery_token_env||"";
  if(f.discovery_token_value) f.discovery_token_value.value="";
  f.enabled.checked=!!a.enabled;
  if($("#accountLoadSelect")) $("#accountLoadSelect").value=a.name;
  if($("#accountMode")) $("#accountMode").textContent=(currentLang==="it"?"Modalità: modifica · ":"Mode: edit · ")+a.name;
  const d=f.closest(".view-panel");
  if(d){showView(d.dataset.viewPanel||"account");}
}

function bindEditAccountButtons(){
  document.querySelectorAll(".edit-account-btn").forEach(btn=>{
    btn.onclick=()=>{
      loadAccountIntoForm(btn.dataset.account);
      $("#accountForm").scrollIntoView({behavior:"smooth",block:"start"});
      show("Account '"+btn.dataset.account+"' caricato nel modulo.");
    };
  });
}

$("#loadAccountBtn").onclick=()=>{
  const name=$("#accountLoadSelect").value;
  if(!name){show("Seleziona un account da caricare.",true);return}
  loadAccountIntoForm(name);
  show(t("account_loaded")+" "+name);
};
