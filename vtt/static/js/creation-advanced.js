/* Advanced studio: complete documents, atomic saves and private executable tests. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const en = {
    title:'Advanced studio',eyebrow:'HOMEBREW / ADVANCED',intro:'Your rules, in full. Edit a definition, save a revision, then put it to the test.',
    skip:'Skip to document',dashboard:'Dashboard',creator:'Creation Engine',language:'Language',author:'01 / Author',test:'02 / Test bench',
    draft:'Draft',newType:'New definition',create:'Create draft',reload:'Reload',empty:'Choose a definition type and create a draft. No rules are preselected.',
    document:'Definition',format:'Format',import:'Import JSON',download:'Download',discard:'Discard edits',shortcuts:'Ctrl/⌘ S saves · Ctrl/⌘ Enter validates · Tab moves to the next control.',
    validate:'Validate',save:'Save draft',validation:'Validation',changes:'Changes since last save',reference:'Field reference',findField:'Find a field',fullSchema:'Full document schema',
    revision:'Save a revision',revisionHelp:'A revision is a fixed snapshot. Existing tests keep their original revisions.',quality:'Intended use',lore:'Description',sheet:'Sheet ready',runtime:'Executable',commit:'Save revision',history:'Draft history',restoreVersion:'Restore version',restore:'Restore as new version',
    testHelp:'Private test characters only. Choose saved class, race and spell revisions; the test uses those exact rules.',newSandbox:'New test',edition:'Edition',choose:'Choose…',pinRevisions:'Revisions to include',createSandbox:'Create private test',openSandbox:'Open test',refreshTest:'Refresh tests',testAction:'Test action',operation:'Action',class:'Class revision',race:'Race revision',character:'Character / caster',target:'Target',spell:'Known spell',prepare:'Prepare action',actionDocument:'Action values',actionSchema:'Action schema',execute:'Run action',characters:'Characters & resources',outcome:'Last outcome',state:'Complete test state',testHistory:'Recorded actions & dice',moreHistory:'Load more history',clearAction:'Discard action edits',
    accessTitle:'Access paused',recheck:'Check access',pendingHelp:'The last request has an unknown outcome. Retry the exact request to recover its original result.',retry:'Retry exact request',conflictTitle:'The saved draft changed',conflictHelp:'Your document is preserved. Compare the latest saved content before choosing what to save.',compare:'Load latest for comparison',acceptBase:'Keep my document against this version',
    saved:'Saved',unsaved:'Unsaved edits',loading:'Loading…',working:'Working…',valid:'Document is valid. Review its intended-use requirements.',ready:'Ready for this use',validateFirst:'Save the draft before creating a revision.',noChanges:'No changes.',before:'Before',after:'After',version:'Version',untitled:'Untitled',noDrafts:'No drafts yet',missing:'Missing',required:'Required',optional:'Optional',jump:'Find in document',
    jsonError:'Invalid JSON',duplicate:'Duplicate property',number:'Number is not finite or safely representable',large:'The document exceeds 256 KiB.',blocked:'Save or discard your edits first.',offline:'Connection could not be checked. Input is preserved; editing is paused until access is checked.',denied:'Access is unavailable or the account changed. Protected content has been cleared. Sign in and check access again.',failed:'The request failed. Your input is preserved.',savedRefresh:'The write succeeded, but refreshing failed. Reload to see the saved result.',imported:'Imported into the editor. Review, validate and save to keep it.',noRevisions:'No executable revisions for this edition. Save class, race and spell revisions as Executable first.',needRevisions:'Select at least one class, executable race and spell of the same edition.',newScope:'Private test created.',chooseScope:'Choose a private test first.',actionHelp:'Fill every missing value. Base values exclude class/race bonuses. Review all choices and attestations before running.',actionReady:'Action prepared. Review and fill its values before running.',scopeChanged:'The test changed. Refresh it, review your retained action and run again explicitly.',concentration:'Concentration needs an explicit decision before another action can run.',revisionSaved:'Revision saved',typeClass:'D&D class',typeRace:'D&D race · executable',typeSpell:'D&D spell',typeItem:'Magic item',typeManualRace:'D&D race · sheet',typeConditional:'Conditional card · manual',typeChoice:'Choice card · manual',typeLore:'Lore',
    BuildCharacter:'Build character',RebuildCharacter:'Rebuild / change level',CastSpell:'Cast spell',AdvanceRounds:'Advance rounds',RecoverResources:'Recover resources',EndConcentration:'End concentration',ResolveConcentration:'Resolve concentration',
    DRAFT_VERSION_CONFLICT:'The saved draft changed.',SCOPE_VERSION_CONFLICT:'The test changed. Refresh and review your action.',RESOURCE_BOUND_EXCEEDED:'Insufficient resources or a value outside its allowed bounds.',CHOICE_REQUIRED:'Complete the required feature choices.',CHOICE_INVALID:'Check the selected feature choices.',SPELL_NOT_KNOWN:'This character does not know that spell.',SPELL_TARGET_INVALID:'Check the target and distance.',SCOPE_BUSY:'Resolve the pending concentration decision first.',QUALITY_CLAIM_UNMET:'This revision does not meet the chosen readiness level.',SCHEMA_INVALID:'A value does not match the required format.',CLASS_LEVEL_UNSUPPORTED:'This class does not define the requested level.',SPELL_NOT_IN_LOCK:'A granted spell is missing from this test’s revisions.',CHARACTER_SYSTEM_MISMATCH:'The content editions must match.',SPELL_KEY_AMBIGUOUS:'Select only one revision per spell key.',CASTER_INCAPACITATED:'The caster has no hit points.',SPELL_LEVEL_INVALID:'This casting level is unsupported.',DECISION_STALE:'This decision is no longer current.',IDEMPOTENCY_KEY_REUSE:'This request key belongs to different content.',
  };
  const words = {en,de:{...en,title:'Erweiterte Werkstatt',eyebrow:'HOMEBREW / ERWEITERT',intro:'Deine Regeln vollständig bearbeiten, als Revision speichern und direkt testen.',skip:'Zum Dokument',dashboard:'Übersicht',creator:'Creation Engine',language:'Sprache',author:'01 / Erstellen',test:'02 / Testbereich',draft:'Entwurf',newType:'Neuer Inhalt',create:'Entwurf erstellen',reload:'Neu laden',empty:'Wähle einen Inhaltstyp und erstelle einen Entwurf. Keine Regeln sind vorausgewählt.',document:'Definition',format:'Formatieren',import:'JSON importieren',download:'Herunterladen',discard:'Änderungen verwerfen',shortcuts:'Strg/⌘ S speichert · Strg/⌘ Eingabe prüft · Tab wechselt zum nächsten Bedienelement.',validate:'Prüfen',save:'Entwurf speichern',validation:'Prüfung',changes:'Änderungen seit dem Speichern',reference:'Feldreferenz',findField:'Feld suchen',fullSchema:'Vollständiges Dokumentschema',revision:'Revision speichern',revisionHelp:'Revisionen sind unveränderliche Stände. Bestehende Tests behalten ihre ursprünglichen Revisionen.',quality:'Verwendung',lore:'Beschreibung',sheet:'Datenblatt',runtime:'Ausführbar',commit:'Revision speichern',history:'Entwurfsverlauf',restoreVersion:'Version wiederherstellen',restore:'Als neue Version wiederherstellen',testHelp:'Nur private Testcharaktere. Wähle gespeicherte Klassen-, Volks- und Zauberrevisionen; der Test verwendet genau diese Regeln.',newSandbox:'Neuer Test',edition:'Ausgabe',choose:'Auswählen…',pinRevisions:'Enthaltene Revisionen',createSandbox:'Privaten Test erstellen',openSandbox:'Test öffnen',refreshTest:'Tests aktualisieren',testAction:'Testaktion',operation:'Aktion',class:'Klassenrevision',race:'Volksrevision',character:'Charakter / Zaubernder',target:'Ziel',spell:'Bekannter Zauber',prepare:'Aktion vorbereiten',actionDocument:'Aktionswerte',actionSchema:'Aktionsschema',execute:'Aktion ausführen',characters:'Charaktere und Ressourcen',outcome:'Letztes Ergebnis',state:'Vollständiger Testzustand',testHistory:'Gespeicherte Aktionen und Würfel',moreHistory:'Weiteren Verlauf laden',clearAction:'Aktionseingabe verwerfen',accessTitle:'Zugriff pausiert',recheck:'Zugriff prüfen',pendingHelp:'Das Ergebnis der letzten Anfrage ist unbekannt. Wiederhole genau diese Anfrage, um das ursprüngliche Ergebnis abzurufen.',retry:'Genau diese Anfrage wiederholen',conflictTitle:'Der gespeicherte Entwurf wurde geändert',conflictHelp:'Dein Dokument bleibt erhalten. Vergleiche den aktuellen Stand vor dem nächsten Speichern.',compare:'Aktuellen Stand zum Vergleich laden',acceptBase:'Mein Dokument auf dieser Version weiterbearbeiten',saved:'Gespeichert',unsaved:'Ungespeicherte Änderungen',loading:'Laden…',working:'Wird verarbeitet…',valid:'Dokument gültig. Prüfe die Anforderungen für die gewünschte Verwendung.',ready:'Für diese Verwendung bereit',validateFirst:'Speichere den Entwurf vor dem Erstellen einer Revision.',noChanges:'Keine Änderungen.',before:'Vorher',after:'Nachher',version:'Version',untitled:'Unbenannt',noDrafts:'Noch keine Entwürfe',missing:'Fehlt',required:'Erforderlich',optional:'Optional',jump:'Im Dokument finden',jsonError:'Ungültiges JSON',duplicate:'Doppelte Eigenschaft',number:'Zahl ist nicht endlich oder nicht exakt darstellbar',large:'Das Dokument überschreitet 256 KiB.',blocked:'Änderungen zuerst speichern oder verwerfen.',offline:'Verbindung nicht prüfbar. Eingaben bleiben erhalten; Bearbeitung bis zur Zugriffsprüfung pausiert.',denied:'Zugriff nicht verfügbar oder Konto gewechselt. Geschützte Inhalte wurden entfernt. Melde dich an und prüfe den Zugriff erneut.',failed:'Anfrage fehlgeschlagen. Deine Eingabe bleibt erhalten.',savedRefresh:'Gespeichert, aber Aktualisierung fehlgeschlagen. Lade den gespeicherten Stand neu.',imported:'In den Editor importiert. Prüfen und speichern, um den Inhalt zu behalten.',noRevisions:'Keine ausführbaren Revisionen für diese Ausgabe. Speichere zuerst Klasse, Volk und Zauber als ausführbar.',needRevisions:'Wähle mindestens eine Klasse, ein ausführbares Volk und einen Zauber derselben Ausgabe.',newScope:'Privater Test erstellt.',chooseScope:'Wähle zuerst einen privaten Test.',actionHelp:'Ergänze alle fehlenden Werte. Basiswerte enthalten keine Klassen-/Volksboni. Prüfe Auswahl und Bestätigungen vor der Ausführung.',actionReady:'Aktion vorbereitet. Werte vor dem Ausführen prüfen und ergänzen.',scopeChanged:'Der Test wurde geändert. Aktualisiere ihn und prüfe deine erhaltene Aktion vor erneutem Ausführen.',concentration:'Die Konzentrationsentscheidung muss vor der nächsten Aktion aufgelöst werden.',revisionSaved:'Revision gespeichert',typeClass:'D&D-Klasse',typeRace:'D&D-Volk · ausführbar',typeSpell:'D&D-Zauber',typeItem:'Magischer Gegenstand',typeManualRace:'D&D-Volk · Datenblatt',typeConditional:'Bedingungskarte · manuell',typeChoice:'Auswahlkarte · manuell',typeLore:'Hintergrundtext',BuildCharacter:'Charakter erstellen',RebuildCharacter:'Charakter / Stufe ändern',CastSpell:'Zauber wirken',AdvanceRounds:'Runden weiterschalten',RecoverResources:'Ressourcen erholen',EndConcentration:'Konzentration beenden',ResolveConcentration:'Konzentration auflösen'},
  fr:{...en,title:'Atelier avancé',eyebrow:'HOMEBREW / AVANCÉ',intro:'Vos règles en entier. Modifiez une définition, enregistrez une révision, puis testez-la.',skip:'Aller au document',dashboard:'Tableau de bord',language:'Langue',author:'01 / Créer',test:'02 / Banc de test',draft:'Brouillon',newType:'Nouvelle définition',create:'Créer un brouillon',reload:'Recharger',empty:'Choisissez un type de contenu et créez un brouillon. Aucune règle n’est présélectionnée.',document:'Définition',format:'Formater',import:'Importer JSON',download:'Télécharger',discard:'Annuler les modifications',shortcuts:'Ctrl/⌘ S enregistre · Ctrl/⌘ Entrée valide · Tab passe au contrôle suivant.',validate:'Valider',save:'Enregistrer le brouillon',validation:'Validation',changes:'Modifications depuis l’enregistrement',reference:'Référence des champs',findField:'Rechercher un champ',fullSchema:'Schéma du document',revision:'Enregistrer une révision',revisionHelp:'Une révision est un instantané fixe. Les tests existants conservent leurs révisions.',quality:'Utilisation prévue',lore:'Description',sheet:'Fiche prête',runtime:'Exécutable',commit:'Enregistrer la révision',history:'Historique du brouillon',restoreVersion:'Version à restaurer',restore:'Restaurer comme nouvelle version',testHelp:'Personnages de test privés uniquement. Sélectionnez les révisions de classe, peuple et sorts à tester.',newSandbox:'Nouveau test',edition:'Édition',choose:'Choisir…',pinRevisions:'Révisions à inclure',createSandbox:'Créer un test privé',openSandbox:'Ouvrir un test',refreshTest:'Actualiser les tests',testAction:'Action de test',operation:'Action',class:'Révision de classe',race:'Révision de peuple',character:'Personnage / lanceur',target:'Cible',spell:'Sort connu',prepare:'Préparer l’action',actionDocument:'Valeurs de l’action',actionSchema:'Schéma de l’action',execute:'Exécuter l’action',characters:'Personnages et ressources',outcome:'Dernier résultat',state:'État complet du test',testHistory:'Actions et dés enregistrés',moreHistory:'Charger la suite',clearAction:'Annuler la saisie de l’action',accessTitle:'Accès suspendu',recheck:'Vérifier l’accès',pendingHelp:'Le résultat de la dernière requête est inconnu. Réessayez exactement cette requête pour retrouver son résultat.',retry:'Réessayer la requête exacte',conflictTitle:'Le brouillon enregistré a changé',conflictHelp:'Votre document est conservé. Comparez le contenu actuel avant de choisir quoi enregistrer.',compare:'Charger pour comparer',acceptBase:'Conserver mon document sur cette version',saved:'Enregistré',unsaved:'Modifications non enregistrées',loading:'Chargement…',working:'Traitement…',valid:'Document valide. Vérifiez les conditions de l’utilisation prévue.',ready:'Prêt pour cette utilisation',validateFirst:'Enregistrez le brouillon avant de créer une révision.',noChanges:'Aucune modification.',before:'Avant',after:'Après',version:'Version',untitled:'Sans titre',noDrafts:'Aucun brouillon',missing:'Manquant',required:'Obligatoire',optional:'Facultatif',jump:'Trouver dans le document',jsonError:'JSON invalide',duplicate:'Propriété en double',number:'Nombre non fini ou non représentable exactement',large:'Le document dépasse 256 Kio.',blocked:'Enregistrez ou annulez d’abord vos modifications.',offline:'Connexion invérifiable. La saisie est conservée ; vérifiez l’accès pour reprendre.',denied:'Accès indisponible ou compte modifié. Le contenu protégé a été effacé. Connectez-vous puis vérifiez l’accès.',failed:'La requête a échoué. Votre saisie est conservée.',savedRefresh:'Enregistrement réussi, mais actualisation impossible. Rechargez le résultat.',imported:'Importé dans l’éditeur. Vérifiez et enregistrez pour conserver le contenu.',noRevisions:'Aucune révision exécutable pour cette édition. Enregistrez d’abord classe, peuple et sorts comme exécutables.',needRevisions:'Choisissez une classe, un peuple exécutable et un sort de la même édition.',newScope:'Test privé créé.',chooseScope:'Choisissez d’abord un test privé.',actionHelp:'Complétez les valeurs manquantes. Les bases excluent les bonus de classe/peuple. Vérifiez les choix et attestations.',actionReady:'Action préparée. Vérifiez et complétez avant de lancer.',scopeChanged:'Le test a changé. Actualisez-le et vérifiez votre action conservée.',concentration:'Résolvez la concentration avant toute autre action.',revisionSaved:'Révision enregistrée',typeClass:'Classe D&D',typeRace:'Peuple D&D · exécutable',typeSpell:'Sort D&D',typeItem:'Objet magique',typeManualRace:'Peuple D&D · fiche',typeConditional:'Condition · manuelle',typeChoice:'Choix · manuel',typeLore:'Récit',BuildCharacter:'Créer un personnage',RebuildCharacter:'Modifier le personnage / niveau',CastSpell:'Lancer un sort',AdvanceRounds:'Avancer les rounds',RecoverResources:'Récupérer les ressources',EndConcentration:'Terminer la concentration',ResolveConcentration:'Résoudre la concentration'}};
  const typeKeys = {'dnd5e.authored-class':'typeClass','dnd5e.runtime-race':'typeRace','dnd5e.authored-spell':'typeSpell','g1.authored-magic-item':'typeItem','dnd5e.authored-race':'typeManualRace','g1.authored-manual-conditional':'typeConditional','g1.authored-manual-choice':'typeChoice','g1.authored-lore':'typeLore'};
  let workspace, draft, baseText='', pending=null, conflict=null, busy=false, denied=false, paused=false, epoch=0, checking=false;
  let catalog, scope, actionBase='', scopeConflict=false, historyAfter=0, currentTab='author', validation=null;
  const controllers = new Set();
  const t = key => (words[$('language').value] || en)[key] || key;
  const pretty = value => JSON.stringify(value,null,2);
  const dirty = () => !!draft && $('source').value !== baseText;
  const actionDirty = () => $('action-source').value !== actionBase;
  const root = () => `/api/ce/authoring/workspaces/${encodeURIComponent(workspace.workspaceId)}`;
  const draftRoot = () => `${root()}/drafts/${encodeURIComponent(draft.draftId)}`;
  const hbRoot = () => `${root()}/homebrew`;
  const status = message => { $('status').textContent=message; };
  function node(tag,text,parent) { const n=document.createElement(tag); if(text!==undefined)n.textContent=text; if(parent)parent.append(n); return n; }
  function translate() { document.documentElement.lang=$('language').value; document.title=`${t('title')} · Roll Drauf`; document.querySelectorAll('[data-text]').forEach(n=>n.textContent=t(n.dataset.text)); }
  function options(element, rows, selected, placeholder=true) { element.replaceChildren(); if(placeholder){const o=node('option',t('choose'),element);o.value='';} rows.forEach(([id,label])=>{const o=node('option',label,element);o.value=id;}); if(rows.some(([id])=>id===selected))element.value=selected; }
  function lock() {
    const held=busy||denied||paused||!!pending;
    document.querySelectorAll('button,input,textarea,select').forEach(n=>{ n.disabled=held; });
    $('recheck').disabled=busy||checking;
    $('retry').disabled=busy||denied||paused;
    $('pending').hidden=!pending;
    if(!held){
      ['create','new-type','drafts','reload','language','author-tab','test-tab'].forEach(id=>$(id).disabled=dirty()||actionDirty()||!!conflict);
      ['format','import','download','validate','save','quality'].forEach(id=>$(id).disabled=!draft||!!conflict);
      $('source').disabled=!draft||!!conflict;
      $('save').disabled=!dirty()||!!conflict;
      $('discard').disabled=!dirty()&&!conflict;
      $('commit').disabled=!draft||dirty()||!!conflict||(draft?.qualityGates[$('quality').value]?.length??1)>0;
      $('restore').disabled=!draft||dirty()||!!conflict||!$('restore-version').value;
      ['sandboxes','edition','create-sandbox','operation','build-class','build-race','actor','target','spell','prepare'].forEach(id=>$(id).disabled=actionDirty());
      $('create-sandbox').disabled=actionDirty()||!catalog;
      $('execute').disabled=!scope||!$('action-source').value||scopeConflict;
      $('refresh-test').disabled=actionDirty()&&!scopeConflict;
    }
    $('save-state').textContent=dirty()?t('unsaved'):t('saved');
    document.querySelectorAll('[data-nav]').forEach(a=>a.setAttribute('aria-disabled',String(held||dirty()||actionDirty()||!!conflict)));
  }
  class Obsolete extends Error {}
  function clearAccess(){
    epoch++;controllers.forEach(c=>c.abort()); denied=true;paused=false;busy=false;
    workspace=draft=catalog=scope=pending=conflict=null;baseText=actionBase='';validation=null;
    for(const id of ['source','action-source','field-filter'])$(id).value='';
    for(const id of ['drafts','new-type','document-title','document-version','line-numbers','issues','diff','fields','schema','history','restore-version','revision-result','gates','remote-content','revision-list','sandboxes','build-class','build-race','actor','target','spell','actors','outcome','test-state','test-history','scope-version','action-schema','concentration'])$(id).replaceChildren();
    $('editing').hidden=$('test-controls').hidden=$('conflict').hidden=$('concentration').hidden=true;
    $('access').hidden=false;$('access-message').textContent=t('denied');status(t('denied'));lock();$('recheck').focus();
  }
  async function api(url,method='GET',body){
    const generation=epoch,controller=new AbortController();controllers.add(controller);
    const timeout=setTimeout(()=>controller.abort(),20000);
    try{
      const response=await fetch(url,{method,credentials:'include',cache:'no-store',signal:controller.signal,headers:Auth.buildHeaders(method,body!==undefined),...(body===undefined?{}:{body:JSON.stringify(body)})});
      if(generation!==epoch)throw new Obsolete();
      if([401,403,404].includes(response.status)){clearAccess();throw new Obsolete();}
      const data=await response.json();if(generation!==epoch)throw new Obsolete();
      if(!response.ok){const e=new Error(data.error?.code||'failed');e.status=response.status;e.issues=data.error?.issues;e.gates=data.error?.gates;throw e;}
      if(workspace&&data.workspaceId&&data.workspaceId!==workspace.workspaceId){clearAccess();throw new Obsolete();}
      return data;
    }finally{clearTimeout(timeout);controllers.delete(controller);}
  }
  async function run(fn,{recovery=false}={}){
    if(busy||(!recovery&&(denied||paused)))return;
    const generation=epoch;busy=true;lock();
    try{await fn();}catch(e){if(!(e instanceof Obsolete)){status(t(e.message)||t('failed'));if(e.issues)showIssues(e.issues);}}
    finally{if(generation===epoch){busy=false;lock();}}
  }
  // Parse once for JSON syntax, then index tokens to reject duplicate names and
  // imprecise numbers before JSON.stringify could silently alter the document.
  function parse(text){
    if(new TextEncoder().encode(text).length>262144)throw new Error('large');
    let value;try{value=JSON.parse(text);}catch(e){throw new Error(t('jsonError')+': '+e.message);}
    const tokens=[...text.matchAll(/"(?:\\.|[^"\\])*"|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null|[{}\[\]:,]/g)];
    let i=0;const positions=new Map();
    const escape=key=>String(key).replace(/~/g,'~0').replace(/\//g,'~1');
    function walk(path){const token=tokens[i++];positions.set(path,token.index);
      if(token[0]==='{'){const seen=new Set();if(tokens[i][0]==='}'){i++;return;}while(true){const key=JSON.parse(tokens[i++][0]);if(seen.has(key))throw new Error(t('duplicate')+': '+key);seen.add(key);i++;walk(path+'/'+escape(key));if(tokens[i++][0]==='}')break;}}
      else if(token[0]==='['){let n=0;if(tokens[i][0]===']'){i++;return;}while(true){walk(path+'/'+n++);if(tokens[i++][0]===']')break;}}
      else if(/^-?\d/.test(token[0])){const number=Number(token[0]);if(!Number.isFinite(number)||Number.isInteger(number)&&!Number.isSafeInteger(number))throw new Error('number');}
    }
    walk('');return {value,positions};
  }
  function jump(path){try{const {positions}=parse($('source').value);let p=path;while(!positions.has(p)&&p)p=p.slice(0,p.lastIndexOf('/'));const at=positions.get(p)||0;$('source').focus();$('source').setSelectionRange(at,at+1);$('source').scrollTop=Math.max(0,($('source').value.slice(0,at).split('\n').length-4)*23);}catch(_){$('source').focus();}}
  function lineNumbers(){$('line-numbers').textContent=Array.from({length:$('source').value.split('\n').length},(_,i)=>i+1).join('\n');$('line-numbers').scrollTop=$('source').scrollTop;}
  function showIssues(issues){$('issues').replaceChildren();if(!issues.length){node('li',t('valid'),$('issues'));return;}issues.forEach(issue=>{const li=node('li',undefined,$('issues'));const b=node('button',`${issue.path||'/'} · ${t(issue.code)}${issue.message?' — '+issue.message:''}`,li);b.onclick=()=>jump(issue.path||'');});}
  function diff(){
    $('diff').replaceChildren();let before,after;try{before=JSON.parse(baseText);after=parse($('source').value).value;}catch(_){node('p',t('jsonError'),$('diff'));return;}
    let count=0;function walk(a,b,path){if(JSON.stringify(a)===JSON.stringify(b))return;if(count>=100)return;
      if(a&&b&&typeof a==='object'&&typeof b==='object'&&!Array.isArray(a)&&!Array.isArray(b)){new Set([...Object.keys(a),...Object.keys(b)]).forEach(k=>walk(a[k],b[k],path+'/'+k));return;}
      count++;const row=node('div',undefined,$('diff'));row.className='diff-entry';node('strong',path||'/',row);node('pre',t('before')+': '+(a===undefined?t('missing'):pretty(a)),row).className='removed';node('pre',t('after')+': '+(b===undefined?t('missing'):pretty(b)),row).className='added';}
    walk(before,after,'');if(!count)node('p',t('noChanges'),$('diff'));
  }
  function fields(){if(!draft)return;$('fields').replaceChildren();const query=$('field-filter').value.toLowerCase();draft.questions.filter(q=>(q.path.join('.')+' '+q.label).toLowerCase().includes(query)).forEach(q=>{
    const d=node('details',undefined,$('fields'));d.className='field-entry';node('summary',q.path.join('.'),d);node('p',q.label+' · '+t(q.required?'required':'optional'),d);node('p',q.help,d);node('pre',pretty(q.schema),d);const b=node('button',t('jump'),d);b.onclick=()=>jump('/'+q.path.join('/'));});$('schema').textContent=pretty(draft.contentSchema);
  }
  function gates(){const use=$('quality').value;const values=(validation?.text===$('source').value?validation.gates:draft?.qualityGates)?.[use]||[];$('gates').replaceChildren();if(dirty())node('li',t('validateFirst'),$('gates'));values.forEach(g=>node('li',`/${g.path.join('/')} · ${t(g.code)}`,$('gates')));if(!values.length)node('li',t('ready'),$('gates'));lock();}
  async function loadDraft(id){
    const data=await api(`${root()}/drafts/${encodeURIComponent(id)}/document?locale=${$('language').value}`);
    const history=await api(`${root()}/drafts/${encodeURIComponent(id)}/history`);
    draft=data;baseText=pretty(data.content);$('source').value=baseText;$('source').scrollTop=0;validation=null;$('drafts').value=id;
    $('editing').hidden=false;$('empty').hidden=true;$('document-title').textContent=data.content.name||t('untitled');$('document-version').textContent=t('version')+' '+data.draftVersion;
    $('quality').value=typeKeys[data.schemaType.typeId]&&data.schemaType.typeId.startsWith('dnd5e.')&&data.schemaType.typeId!=='dnd5e.authored-race'?'runtime_ready':'sheet_ready';
    $('revision-result').textContent='';$('issues').replaceChildren();lineNumbers();fields();diff();gates();
    $('history').replaceChildren();history.slice().reverse().forEach(h=>node('li',`${t('version')} ${h.draftVersion} · ${h.operation}`, $('history')));
    options($('restore-version'),Array.from({length:data.draftVersion-1},(_,i)=>[String(i+1),t('version')+' '+(i+1)]),'');
  }
  async function loadWorkspace(preferred){
    workspace=await api('/api/ce/authoring/advanced/workspace');
    const types=workspace.schemaTypes.filter(x=>typeKeys[x.typeId]);types.sort((a,b)=>Object.keys(typeKeys).indexOf(a.typeId)-Object.keys(typeKeys).indexOf(b.typeId));
    options($('new-type'),types.map(x=>[x.typeId,t(typeKeys[x.typeId])]),$('new-type').value);
    options($('drafts'),workspace.drafts.map(x=>[x.draftId,`${x.name||t('untitled')} · ${t(typeKeys[x.schemaType.typeId]||x.schemaType.typeId)} · v${x.version}`]),preferred);
    const selected=preferred||workspace.drafts.at(-1)?.draftId;
    if(selected)await loadDraft(selected);else{$('editing').hidden=true;$('empty').hidden=false;}
  }
  function documentBody(save){return {contractVersion:'advanced-document:1',expectedDraftVersion:draft.draftVersion,promptLocale:$('language').value,content:parse($('source').value).value,...(save?{idempotencyKey:crypto.randomUUID()}:{})};}
  async function validate(){const text=$('source').value;const result=await api(draftRoot()+'/document/validate','POST',documentBody(false));validation={text,gates:result.qualityGates};showIssues([]);gates();status(t('valid'));}
  function a1(operation,payload){const body={contractVersion:'1.1.3',commandId:crypto.randomUUID(),idempotencyKey:crypto.randomUUID(),workspaceId:workspace.workspaceId,authorityEpoch:1,operation,payload};if(operation!=='CreateDraft')Object.assign(body,{draftId:draft.draftId,expectedDraftVersion:draft.draftVersion});return body;}
  async function write(kind,url,body){pending={kind,url,body,source:$('source').value};await sendPending();}
  async function sendPending(){
    const request=pending;status(t('working'));
    try{
      let result=await api(request.url,'POST',request.body);
      if(request.kind==='a1'){
        const base=request.body.operation==='CreateDraft'?root():`${root()}/drafts/${encodeURIComponent(request.body.draftId)}`;
        result=await api(`${base}/commands/${encodeURIComponent(request.body.idempotencyKey)}`);
      }
      pending=null;
      if(request.kind==='homebrew'){$('action-source').value=actionBase='';scopeConflict=false;}
      else if(request.kind==='document'){baseText=request.source;draft.draftVersion=result.draftVersion;}
      try{
        if(request.kind==='homebrew'){await loadCatalog(result.sandboxId);$('outcome').textContent=pretty(result);}
        else{await loadWorkspace(result.draftId);if(result.revision)$('revision-result').textContent=t('revisionSaved')+': '+result.revision.id;}
        status(t('saved'));
      }catch(e){if(e instanceof Obsolete)throw e;status(t('savedRefresh'));}
    }catch(e){
      if(e instanceof Obsolete)throw e;
      if(e.status&&e.status<500&&e.status!==429)pending=null;
      if(e.message==='DRAFT_VERSION_CONFLICT'){conflict={latest:null};$('conflict').hidden=false;$('accept-base').hidden=true;$('remote-content').textContent='';$('conflict-heading').focus();}
      if(e.message==='SCOPE_VERSION_CONFLICT'||e.message==='SCOPE_BUSY'){scopeConflict=true;status(t('scopeChanged'));}
      if(pending)status(t('pendingHelp'));else throw e;
    }
  }
  async function loadCatalog(preferred){
    catalog=await api(hbRoot());const selected=preferred||scope?.sandboxId;
    options($('sandboxes'),catalog.sandboxes.map(x=>[x.sandboxId,`${x.sandboxId} · v${x.version}`]),selected);revisionList();
    if(selected)await loadScope(selected);
  }
  function revisionList(){
    const retained=new Set([...$('revision-list').querySelectorAll('input:checked')].map(n=>n.value));$('revision-list').replaceChildren();
    const rows=(catalog?.revisions||[]).filter(r=>Object.values(r.content).some(v=>v&&typeof v==='object'&&v.edition===$('edition').value));
    if(!rows.length)node('p',t('noRevisions'),$('revision-list'));
    rows.forEach(r=>{const label=node('label',undefined,$('revision-list'));const input=node('input',undefined,label);input.type='checkbox';input.value=r.revision.id;input.checked=retained.has(input.value);node('span',`${r.content.name} · ${t(typeKeys[r.schemaType.typeId])} · ${r.revision.id.slice(-8)}`,label);});
  }
  async function loadScope(id){
    scope=await api(`${hbRoot()}/sandboxes/${encodeURIComponent(id)}`);$('sandboxes').value=id;$('test-controls').hidden=false;$('scope-version').textContent=`${t('version')} ${scope.version} · ${scope.sandboxId}`;
    const docs=Object.entries(scope.executionLock.documents);for(const kind of ['class','race'])options($('build-'+kind),docs.filter(([,d])=>d.kind===kind).map(([id,d])=>[id,d.content.name+' · '+id.slice(-8)]),$('build-'+kind).value);
    const actors=Object.entries(scope.state.characters).map(([id,a])=>[id,a.name+' · '+id.slice(-8)]);
    options($('actor'),actors,$('actor').value);options($('target'),actors,$('target').value);
    options($('operation'),Object.keys(catalog.commands).filter(x=>x!=='CreateSandbox').map(x=>[x,t(x)]),$('operation').value||'BuildCharacter',false);
    $('actors').replaceChildren();Object.entries(scope.state.characters).forEach(([id,a])=>{const card=node('section',undefined,$('actors'));card.className='actor-card';node('h3',a.name,card);node('p',`${a.className} ${a.level} · ${a.raceName} · ${id.slice(-8)}`,card);node('p',`HP ${a.hp}/${a.stats.hpMax} · AC ${a.effectiveStats.ac} · ${a.effectiveStats.speed} ft`,card);Object.entries(a.resources).forEach(([key,v])=>node('p',`${key}: ${v.current}/${v.maximum}`,card));});
    $('test-state').textContent=pretty(scope.state);$('concentration').hidden=!scope.state.pendingConcentration;$('concentration').textContent=t('concentration')+' '+pretty(scope.state.pendingConcentration);
    if(scope.state.pendingConcentration&&!actionDirty())$('operation').value='ResolveConcentration';operationView();historyAfter=0;$('test-history').replaceChildren();await moreHistory();
  }
  async function moreHistory(){const records=await api(`${hbRoot()}/sandboxes/${encodeURIComponent(scope.sandboxId)}/history?after=${historyAfter}`);records.forEach(e=>{const item=node('li',undefined,$('test-history'));const d=node('details',undefined,item);node('summary',`v${e.result.version} · ${t(e.result.operation)} · ${e.createdAt}`,d);node('pre',pretty(e.result),d);historyAfter=e.result.version;});$('more-history').hidden=records.length<100;}
  function operationView(){
    const op=$('operation').value;$('build-selectors').hidden=op!=='BuildCharacter';$('actor-selectors').hidden=['BuildCharacter','AdvanceRounds'].includes(op);$('target-label').hidden=$('spell-label').hidden=op!=='CastSpell';
    const actor=scope?.state.characters[$('actor').value];const spells=Object.values(scope?.executionLock.documents||{}).filter(d=>d.kind==='spell'&&actor?.spells[d.content.spell.key]);options($('spell'),spells.map(d=>[d.content.spell.key,d.content.name]),$('spell').value);
    $('action-help').textContent=t('actionHelp');$('action-schema').textContent=pretty(catalog?.commands[op]?.properties.payload||{});
  }
  function prepare(){if(!scope)throw new Error('chooseScope');const op=$('operation').value,id=$('actor').value;let payload;
    if(op==='BuildCharacter')payload={name:'',classRevision:$('build-class').value,raceRevision:$('build-race').value,level:null,baseScores:{str:null,dex:null,con:null,int:null,wis:null,cha:null},baseAc:null,baseHp:null,choices:{}};
    if(op==='RebuildCharacter'){if(!scope.state.characters[id])throw new Error('choose');payload={characterId:id,build:scope.state.characters[id].build};}
    if(op==='CastSpell'){const spell=Object.values(scope.executionLock.documents).find(d=>d.kind==='spell'&&d.content.spell.key===$('spell').value);payload={casterId:id,targetId:$('target').value,spellKey:$('spell').value,castLevel:spell?.content.spell.level??null,distanceFeet:id&&id===$('target').value?0:null,adjudication:{timingSatisfied:false,componentsSatisfied:false}};}
    if(op==='AdvanceRounds')payload={rounds:null};
    if(op==='RecoverResources')payload={characterId:id,event:null,reason:''};
    if(op==='EndConcentration')payload={characterId:id,reason:''};
    if(op==='ResolveConcentration')payload={characterId:scope.state.pendingConcentration?.characterId||id,maintained:null,reason:''};
    $('action-source').value=pretty(payload);actionBase='';status(t('actionReady'));$('action-source').focus();lock();
  }
  async function tab(name){if(dirty()||actionDirty()||conflict)throw new Error('blocked');currentTab=name;for(const x of ['author','test']){$(x+'-panel').hidden=x!==name;$(x+'-tab').setAttribute('aria-selected',String(x===name));$(x+'-tab').tabIndex=x===name?0:-1;}if(name==='test')await loadCatalog();}
  async function checkAccess(){if(checking||busy||document.hidden)return;checking=true;lock();try{
    const found=await api('/api/ce/authoring/advanced/workspace');if(workspace&&workspace.workspaceId!==found.workspaceId){clearAccess();return;}
    const wasDenied=denied,wasPaused=paused;denied=paused=false;$('access').hidden=true;
    if(wasDenied||!workspace){workspace=found;await loadWorkspace();}else if(wasPaused&&!pending)status('');
  }catch(e){if(!(e instanceof Obsolete)){paused=true;$('access').hidden=false;$('access-message').textContent=t('offline');status(t('offline'));}}
  finally{checking=false;lock();}}
  $('source').oninput=()=>{validation=null;lineNumbers();diff();gates();$('issues').replaceChildren();lock();};$('source').onscroll=()=>$('line-numbers').scrollTop=$('source').scrollTop;
  $('field-filter').oninput=fields;
  $('validate').onclick=()=>run(validate);
  $('save').onclick=()=>run(()=>write('document',draftRoot()+'/document',documentBody(true)));
  $('format').onclick=()=>run(async()=>{$('source').value=pretty(parse($('source').value).value);lineNumbers();diff();gates();});
  $('discard').onclick=()=>run(async()=>{conflict=null;$('conflict').hidden=true;await loadDraft(draft.draftId);status(t('saved'));});
  $('create').onclick=()=>run(async()=>{const schemaType=workspace.schemaTypes.find(x=>x.typeId===$('new-type').value);if(!schemaType)throw new Error('choose');await write('a1','/api/ce/commands',a1('CreateDraft',{schemaType,authoringLocale:$('language').value}));});
  $('drafts').onchange=()=>run(()=>loadDraft($('drafts').value));$('reload').onclick=()=>run(()=>loadWorkspace(draft?.draftId));
  $('language').onchange=()=>run(async()=>{translate();await loadWorkspace(draft?.draftId);if(currentTab==='test')await loadCatalog();});
  $('quality').onchange=gates;$('restore-version').onchange=lock;
  $('commit').onclick=()=>run(()=>write('a1','/api/ce/commands',a1('CommitDraftRevision',{declaredQuality:$('quality').value,definition:draft.definitionId?{kind:'definition',id:draft.definitionId}:{kind:'new'}})));
  $('restore').onclick=()=>run(()=>write('a1','/api/ce/commands',a1('RevertDraft',{toDraftVersion:Number($('restore-version').value)})));
  $('import').onclick=()=>$('file').click();$('file').onchange=()=>run(async()=>{const file=$('file').files[0];$('file').value='';if(!file)return;if(file.size>262144)throw new Error('large');const generation=epoch;const text=await file.text();if(generation!==epoch)throw new Obsolete();parse(text);$('source').value=text;validation=null;lineNumbers();diff();gates();status(t('imported'));});
  $('download').onclick=()=>run(async()=>{parse($('source').value);const blob=new Blob([$('source').value+'\n'],{type:'application/json'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=(draft.content.name||'homebrew').replace(/[^a-z0-9_-]/gi,'_').slice(0,80)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  $('compare').onclick=()=>run(async()=>{conflict.latest=await api(draftRoot()+'/document?locale='+$('language').value);$('remote-content').textContent=`${t('version')} ${conflict.latest.draftVersion}\n${pretty(conflict.latest.content)}`;$('accept-base').hidden=false;});
  $('accept-base').onclick=()=>{const local=$('source').value;draft=conflict.latest;baseText=pretty(draft.content);conflict=null;$('conflict').hidden=true;$('source').value=local;$('document-version').textContent=t('version')+' '+draft.draftVersion;validation=null;fields();diff();gates();status(t('unsaved'));lock();$('source').focus();};
  $('retry').onclick=()=>run(sendPending);$('recheck').onclick=()=>checkAccess();
  $('author-tab').onclick=()=>run(()=>tab('author'));$('test-tab').onclick=()=>run(()=>tab('test'));
  document.querySelector('.studio-tabs').onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const next=e.key==='Home'?'author':e.key==='End'?'test':currentTab==='author'?'test':'author';run(async()=>{await tab(next);$(next+'-tab').focus();});}};
  $('edition').onchange=revisionList;
  $('create-sandbox').onclick=()=>run(async()=>{const ids=new Set([...$('revision-list').querySelectorAll('input:checked')].map(n=>n.value));const rows=catalog.revisions.filter(r=>ids.has(r.revision.id));if(!['dnd5e.authored-class','dnd5e.runtime-race','dnd5e.authored-spell'].every(t=>rows.some(r=>r.schemaType.typeId===t)))throw new Error('needRevisions');await write('homebrew',hbRoot()+'/commands',{contractVersion:catalog.contractVersion,idempotencyKey:crypto.randomUUID(),operation:'CreateSandbox',payload:{edition:$('edition').value,revisions:rows.map(r=>r.revision)}});});
  $('sandboxes').onchange=()=>run(async()=>{if($('sandboxes').value)await loadScope($('sandboxes').value);});
  $('refresh-test').onclick=()=>run(async()=>{await loadCatalog();scopeConflict=false;status(t('scopeChanged'));});
  $('operation').onchange=operationView;$('actor').onchange=operationView;$('prepare').onclick=()=>run(async()=>prepare());
  $('action-source').oninput=lock;
  const clear=node('button',t('clearAction'),$('execute').parentElement);clear.id='clear-action';clear.dataset.text='clearAction';clear.onclick=()=>{$('action-source').value='';actionBase='';lock();};
  $('execute').onclick=()=>run(()=>write('homebrew',hbRoot()+'/commands',{contractVersion:catalog.contractVersion,idempotencyKey:crypto.randomUUID(),sandboxId:scope.sandboxId,expectedVersion:scope.version,operation:$('operation').value,payload:parse($('action-source').value).value}));
  $('more-history').onclick=()=>run(moreHistory);
  document.querySelectorAll('[data-nav]').forEach(a=>a.onclick=e=>{if(!e.ctrlKey&&!e.metaKey&&!e.shiftKey&&(busy||pending||dirty()||actionDirty()||conflict)){e.preventDefault();status(t('blocked'));$('status').focus();}});
  document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&currentTab==='author'&&(e.key.toLowerCase()==='s'||e.key==='Enter')){e.preventDefault();const button=e.key==='Enter'?$('validate'):$('save');if(!button.disabled)button.click();}});
  window.addEventListener('beforeunload',e=>{if(dirty()||actionDirty()||pending||busy){e.preventDefault();e.returnValue='';}});
  window.addEventListener('pagehide',()=>{epoch++;controllers.forEach(c=>c.abort());busy=false;paused=true;lock();});
  window.addEventListener('pageshow',e=>{if(e.persisted)checkAccess();});window.addEventListener('focus',checkAccess);document.addEventListener('visibilitychange',()=>{if(!document.hidden)checkAccess();});setInterval(checkAccess,15000);
  translate();run(()=>loadWorkspace());
})();
