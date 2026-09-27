/* All modes use the same typed RecordDraftDecision command. No prose compiler. */
(() => {
  'use strict';
  const words = {
    de: {
      overview: 'Übersicht', campaigns: 'Kampagnen', characters: 'Charaktere', navigation: 'Buchnavigation',
      location: 'Inhalte · Gegenstand', title: 'Gegenstand erschaffen', toolbar: 'Entwurf und Ansicht', skipToEditor: 'Zum Inhalt', untitled: 'Unbenannter Gegenstand',
      home: 'Zur Übersicht', intro: 'Erschaffe einen magischen Gegenstand. Jede Regel ist deine Entscheidung.',
      language: 'Sprache', mode: 'Ansicht', guided: 'Geführt', structured: 'Strukturiert', advanced: 'Erweitert', drafts: 'Entwürfe',
      newItem: 'Neuer Gegenstand', reload: 'Neu laden', retry: 'Gleiche Anfrage erneut senden', discard: 'Ungespeicherte Eingabe verwerfen',
      decisions: 'Deine Entscheidungen', preview: 'Vorschau', quality: 'Verwendbarkeit', claim: 'Revision speichern als',
      lore_only: 'Beschreibung', sheet_ready: 'Datenblatt', runtime_ready: 'Ausführbar', automation_complete: 'Vollständig automatisiert',
      commit: 'Unveränderliche Revision speichern', presets: 'Vorlagen prüfen', presetHelp: 'Die Vorschau zeigt alle vorgegebenen Antworten. Erst beim Anwenden werden sie übernommen.',
      visualPreset: 'Harmlose Flammen ansehen', damagePreset: 'Zusatzschaden ansehen', applyPreset: 'Diese Antworten übernehmen',
      history: 'Verlauf', restoreVersion: 'Version wiederherstellen', revert: 'Als neue Version wiederherstellen',
      save: 'Antwort speichern', skip: 'Überspringen', retract: 'Antwort zurückziehen', choose: 'Bitte ausdrücklich wählen',
      saved: 'Gespeichert.', loading: 'Wird geladen …', empty: 'Erstelle einen Gegenstand oder öffne einen Entwurf.',
      complete: 'Alle erforderlichen Antworten sind gespeichert. In der strukturierten Ansicht kannst du sie bearbeiten oder eine Beschreibung ergänzen.',
      stale: 'Frühere Antworten sind veraltet und wirken nicht mehr: ', unsaved: 'Speichere oder verwerfe diese Eingabe, bevor du weiterwechselst.',
      version: 'Version', ready: 'Erfüllt', blocked: 'Offen', revision: 'Revision gespeichert: ',
      visual: 'Nur sichtbare Flammen', damage: 'Zusatzschaden', burst: 'Flammenstoß (manuell)', transformation: 'Verwandlung (manuell)', manual: 'Manuelle Wirkung',
      activation: 'Bei Aktivierung', after_hit: 'Nach bestätigtem Treffer', long_rest: 'Bestätigte lange Rast', campaign_dawn: 'Bestätigte Morgendämmerung der Kampagne', manual_event: 'Manuell bestätigtes Ereignis',
      fire: 'Feuer', committed_hit_target: 'Ziel des bestätigten Treffers', count: 'Anzahl der Würfel', sides: 'Seiten pro Würfel',
      activationWindow: 'Nur diese Aktivierung', hitWindow: 'Nur dieser bestätigte Treffer', custom: 'Andere Dauer (JSON; gegebenenfalls manuell)',
      invalid: 'Bitte prüfe die Eingabe. Es wurde nichts gespeichert.', network: 'Die Antwort ist unklar. Sende dieselbe Anfrage erneut, um den gespeicherten Stand sicher abzurufen.',
      conflict: 'Der Entwurf wurde geändert. Prüfe deine Eingabe und lade den aktuellen Stand neu.', forbidden: 'Kein Zugriff. Prüfe deine Anmeldung.',
      QUESTION_REQUIRED: 'Eine erforderliche Frage kann nicht übersprungen werden.', QUESTION_NOT_READY: 'Beantworte zuerst die vorausgehenden Fragen.',
      AUTHORING_REGISTRY_MISMATCH: 'Diese Version benötigt eine geprüfte Migration. Gespeicherte Antworten bleiben erhalten.',
      GUIDE_DEAD_END: 'Keine nächste Frage verfügbar. Wechsle zur strukturierten Ansicht.', PRESET_PREVIEW_STALE: 'Die Vorlage wurde geändert. Öffne die Vorschau erneut.',
      ANSWER_REQUIRED: 'Antwort fehlt', MANUAL_BEHAVIOR: 'Diese Wirkung wird manuell aufgelöst', UNSUPPORTED_TIMING: 'Auslöser wird noch nicht ausgeführt',
      MANUAL_DURATION: 'Dauer wird manuell verfolgt', RESOURCE_BOUND_EXCEEDED: 'Wert übersteigt die Ladungskapazität',
      HUMAN_EVENT_ATTESTATION_REQUIRED: 'Ein Mensch muss das Ereignis bestätigen', RUNTIME_REGISTRATION_PENDING: 'Sandbox-Ausführung ist noch nicht angebunden',
      QUALITY_CLAIM_UNMET: 'Die gewählte Verwendbarkeit ist noch nicht erreicht. Prüfe die offenen Punkte.',
      RecordDraftDecision: 'Antwort gespeichert', SkipDraftQuestion: 'Frage übersprungen', RetractDraftDecision: 'Antwort zurückgezogen',
      ApplyDraftPreset: 'Vorlage übernommen', RevertDraft: 'Frühere Version wiederhergestellt', CommitDraftRevision: 'Revision gespeichert'
    },
    en: {
      overview: 'Overview', campaigns: 'Campaigns', characters: 'Characters', navigation: 'Book navigation',
      location: 'Content · Item', title: 'Create an item', toolbar: 'Draft and view', skipToEditor: 'Skip to content', untitled: 'Untitled item',
      home: 'Back to dashboard', intro: 'Create a magic item. Every rule is your decision.', language: 'Language', mode: 'View', guided: 'Guided', structured: 'Structured', advanced: 'Advanced', drafts: 'Drafts',
      newItem: 'New item', reload: 'Reload', retry: 'Retry the same request', discard: 'Discard unsaved input', decisions: 'Your decisions', preview: 'Preview', quality: 'Readiness', claim: 'Save revision as',
      lore_only: 'Description', sheet_ready: 'Sheet ready', runtime_ready: 'Runtime ready', automation_complete: 'Fully automated', commit: 'Save immutable revision',
      presets: 'Review presets', presetHelp: 'The preview shows every supplied answer. Nothing is applied until you choose to apply it.',
      visualPreset: 'Preview harmless flames', damagePreset: 'Preview additional damage', applyPreset: 'Apply these answers', history: 'History', restoreVersion: 'Version to restore', revert: 'Restore as a new version',
      save: 'Save answer', skip: 'Skip', retract: 'Retract answer', choose: 'Choose explicitly', saved: 'Saved.', loading: 'Loading …', empty: 'Create an item or open a draft.',
      complete: 'All required answers are saved. Use Structured view to edit them or add a description.', stale: 'Earlier answers are stale and no longer active: ',
      unsaved: 'Save or discard this input before switching.', version: 'Version', ready: 'Met', blocked: 'Open', revision: 'Revision saved: ',
      visual: 'Visible flames only', damage: 'Additional damage', burst: 'Flame burst (manual)', transformation: 'Transformation (manual)', manual: 'Manual effect',
      activation: 'On activation', after_hit: 'After a committed hit', long_rest: 'Confirmed long rest', campaign_dawn: 'Confirmed campaign dawn', manual_event: 'Manually confirmed event',
      fire: 'Fire', committed_hit_target: 'The committed hit’s target', count: 'Number of dice', sides: 'Sides per die', activationWindow: 'Only this activation', hitWindow: 'Only this committed hit', custom: 'Other duration (JSON; may be manual)',
      invalid: 'Check the input. Nothing was saved.', network: 'The response is uncertain. Retry the same request to recover the saved result safely.',
      conflict: 'The draft changed. Check your input and reload the current version.', forbidden: 'Access denied. Check your sign-in.',
      QUESTION_REQUIRED: 'A required question cannot be skipped.', QUESTION_NOT_READY: 'Answer the preceding questions first.',
      AUTHORING_REGISTRY_MISMATCH: 'This version needs a reviewed migration. Saved answers are retained.', GUIDE_DEAD_END: 'No next question is available. Switch to Structured view.',
      PRESET_PREVIEW_STALE: 'The preset changed. Open its preview again.', ANSWER_REQUIRED: 'Answer needed', MANUAL_BEHAVIOR: 'This behavior is resolved manually',
      UNSUPPORTED_TIMING: 'This timing cannot execute yet', MANUAL_DURATION: 'Duration is tracked manually', RESOURCE_BOUND_EXCEEDED: 'Value exceeds charge capacity',
      HUMAN_EVENT_ATTESTATION_REQUIRED: 'A person must confirm the event', RUNTIME_REGISTRATION_PENDING: 'Sandbox execution is not connected yet',
      QUALITY_CLAIM_UNMET: 'The selected readiness is not met. Review the open gates.', RecordDraftDecision: 'Answer saved', SkipDraftQuestion: 'Question skipped',
      RetractDraftDecision: 'Answer retracted', ApplyDraftPreset: 'Preset applied', RevertDraft: 'Earlier version restored', CommitDraftRevision: 'Revision saved'
    },
    fr: {
      overview: 'Vue d’ensemble', campaigns: 'Campagnes', characters: 'Personnages', navigation: 'Navigation du livre',
      location: 'Contenu · Objet', title: 'Créer un objet', toolbar: 'Brouillon et vue', skipToEditor: 'Aller au contenu', untitled: 'Objet sans titre',
      home: 'Retour au tableau de bord', intro: 'Créez un objet magique. Chaque règle est votre décision.', language: 'Langue', mode: 'Vue', guided: 'Guidée', structured: 'Structurée', advanced: 'Avancée', drafts: 'Brouillons',
      newItem: 'Nouvel objet', reload: 'Recharger', retry: 'Renvoyer la même demande', discard: 'Abandonner la saisie non enregistrée', decisions: 'Vos décisions', preview: 'Aperçu', quality: 'Utilisabilité', claim: 'Enregistrer la révision comme',
      lore_only: 'Description', sheet_ready: 'Fiche prête', runtime_ready: 'Exécutable', automation_complete: 'Entièrement automatisé', commit: 'Enregistrer une révision immuable',
      presets: 'Examiner les modèles', presetHelp: 'L’aperçu montre toutes les réponses proposées. Elles ne sont reprises qu’après votre choix de les appliquer.',
      visualPreset: 'Voir les flammes inoffensives', damagePreset: 'Voir les dégâts supplémentaires', applyPreset: 'Appliquer ces réponses', history: 'Historique', restoreVersion: 'Version à restaurer', revert: 'Restaurer comme nouvelle version',
      save: 'Enregistrer la réponse', skip: 'Passer', retract: 'Retirer la réponse', choose: 'Choisissez explicitement', saved: 'Enregistré.', loading: 'Chargement …', empty: 'Créez un objet ou ouvrez un brouillon.',
      complete: 'Toutes les réponses requises sont enregistrées. Utilisez la vue structurée pour les modifier ou ajouter une description.', stale: 'Ces anciennes réponses sont obsolètes et ne sont plus actives : ',
      unsaved: 'Enregistrez ou abandonnez cette saisie avant de changer de vue.', version: 'Version', ready: 'Satisfait', blocked: 'À résoudre', revision: 'Révision enregistrée : ',
      visual: 'Flammes visibles uniquement', damage: 'Dégâts supplémentaires', burst: 'Explosion de flammes (manuelle)', transformation: 'Transformation (manuelle)', manual: 'Effet manuel',
      activation: 'À l’activation', after_hit: 'Après une touche confirmée', long_rest: 'Repos long confirmé', campaign_dawn: 'Aube de campagne confirmée', manual_event: 'Événement confirmé manuellement',
      fire: 'Feu', committed_hit_target: 'Cible de la touche confirmée', count: 'Nombre de dés', sides: 'Faces par dé', activationWindow: 'Cette activation uniquement', hitWindow: 'Cette touche confirmée uniquement', custom: 'Autre durée (JSON ; éventuellement manuelle)',
      invalid: 'Vérifiez la saisie. Rien n’a été enregistré.', network: 'La réponse est incertaine. Renvoyez la même demande pour retrouver le résultat enregistré.',
      conflict: 'Le brouillon a changé. Vérifiez votre saisie et rechargez la version actuelle.', forbidden: 'Accès refusé. Vérifiez votre connexion.',
      QUESTION_REQUIRED: 'Une question requise ne peut pas être ignorée.', QUESTION_NOT_READY: 'Répondez d’abord aux questions précédentes.',
      AUTHORING_REGISTRY_MISMATCH: 'Cette version nécessite une migration examinée. Les réponses sont conservées.', GUIDE_DEAD_END: 'Aucune question suivante disponible. Passez à la vue structurée.',
      PRESET_PREVIEW_STALE: 'Le modèle a changé. Ouvrez à nouveau son aperçu.', ANSWER_REQUIRED: 'Réponse requise', MANUAL_BEHAVIOR: 'Ce comportement est résolu manuellement',
      UNSUPPORTED_TIMING: 'Ce déclenchement ne peut pas encore être exécuté', MANUAL_DURATION: 'La durée est suivie manuellement', RESOURCE_BOUND_EXCEEDED: 'La valeur dépasse la capacité de charges',
      HUMAN_EVENT_ATTESTATION_REQUIRED: 'Une personne doit confirmer l’événement', RUNTIME_REGISTRATION_PENDING: 'L’exécution dans le bac à sable n’est pas encore connectée',
      QUALITY_CLAIM_UNMET: 'L’utilisabilité choisie n’est pas atteinte. Vérifiez les points ouverts.', RecordDraftDecision: 'Réponse enregistrée', SkipDraftQuestion: 'Question passée',
      RetractDraftDecision: 'Réponse retirée', ApplyDraftPreset: 'Modèle appliqué', RevertDraft: 'Ancienne version restaurée', CommitDraftRevision: 'Révision enregistrée'
    }
  };
  Object.assign(words.de, {
    sandboxTitle: 'Privater Sandbox-Test', sandboxHelp: 'Wähle die gespeicherten Revisionen für diesen Test. Jede Kopie hat eigene Ressourcen. Ein Treffer und ein Erholungsereignis werden ausdrücklich bestätigt.',
    sandboxDisabled: 'Sandbox-Ausführung ist in dieser Umgebung nicht verfügbar.', sandboxRevisions: 'Revisionen für eine neue Sandbox', sandboxCreate: 'Sandbox mit dieser Auswahl erstellen',
    sandboxChoose: 'Vorhandene Sandbox', sandboxCopy: 'Neue Kopie', sandboxRevision: 'Gesperrte Revision', sandboxHolder: 'Träger (nur für Gegenstände)', sandboxReason: 'Grund', sandboxInstantiate: 'Diese Kopie erstellen',
    sandboxUse: 'Gegenstand testen', sandboxItem: 'Gegenstandskopie', sandboxEquip: 'Ausrüstungszustand wechseln', sandboxActivate: 'Harmlose Flammen aktivieren', sandboxTarget: 'Ziel eines bestätigten Treffers',
    sandboxHit: 'Treffer bestätigen und Flammen anbieten', sandboxActorHelp: 'Für Schaden werden importierte Charakterrevisionen als Träger und Ziel benötigt. Die Sandbox erfindet keine Charakterwerte.',
    sandboxRecover: 'Angegebenes Erholungsereignis bestätigen', sandboxManual: 'Unterbrochenen Ablauf manuell abschließen', sandboxOutcome: 'Festgehaltenes Ergebnis', sandboxResolve: 'Ohne weitere Ressourcenänderung abschließen',
    sandboxNone: 'Kein Träger', sandboxCharges: 'Ladungen', sandboxHP: 'Lebenspunkte', sandboxIdle: 'Bereit', sandboxBusy: 'Ablauf aktiv', sandboxSuspended: 'Manuelle Entscheidung erforderlich',
    sandboxDecision: 'Flammen für diesen bestätigten Treffer einsetzen?', sandboxYes: 'Ja, Ladungen ausgeben', sandboxNo: 'Nein, Treffer beibehalten', sandboxDeadline: 'Antwortfrist', sandboxConflict: 'Der Ablauf wurde geändert. Lade die Sandbox neu.'
  });
  Object.assign(words.en, {
    sandboxTitle: 'Private sandbox test', sandboxHelp: 'Choose saved revisions for this test. Each copy has its own resources. A hit and a recovery event must be explicitly confirmed.',
    sandboxDisabled: 'Sandbox execution is unavailable in this environment.', sandboxRevisions: 'Revisions for a new sandbox', sandboxCreate: 'Create sandbox with this selection',
    sandboxChoose: 'Existing sandbox', sandboxCopy: 'New copy', sandboxRevision: 'Locked revision', sandboxHolder: 'Holder (items only)', sandboxReason: 'Reason', sandboxInstantiate: 'Create this copy',
    sandboxUse: 'Test an item', sandboxItem: 'Item copy', sandboxEquip: 'Toggle equipped state', sandboxActivate: 'Activate harmless flames', sandboxTarget: 'Target of a confirmed hit',
    sandboxHit: 'Confirm hit and offer flames', sandboxActorHelp: 'Damage needs imported character revisions for the holder and target. The sandbox does not invent character statistics.',
    sandboxRecover: 'Confirm the specified recovery event', sandboxManual: 'Finish a suspended action manually', sandboxOutcome: 'Recorded outcome', sandboxResolve: 'Finish without further resource changes',
    sandboxNone: 'No holder', sandboxCharges: 'Charges', sandboxHP: 'Hit points', sandboxIdle: 'Ready', sandboxBusy: 'Action active', sandboxSuspended: 'Manual decision required',
    sandboxDecision: 'Use flames for this confirmed hit?', sandboxYes: 'Yes, spend charges', sandboxNo: 'No, keep the hit', sandboxDeadline: 'Response deadline', sandboxConflict: 'The action changed. Reload the sandbox.'
  });
  Object.assign(words.fr, {
    sandboxTitle: 'Test dans un bac à sable privé', sandboxHelp: 'Choisissez les révisions enregistrées pour ce test. Chaque exemplaire possède ses ressources. Une touche et un événement de récupération doivent être confirmés explicitement.',
    sandboxDisabled: 'L’exécution dans le bac à sable est indisponible dans cet environnement.', sandboxRevisions: 'Révisions pour un nouveau bac à sable', sandboxCreate: 'Créer avec cette sélection',
    sandboxChoose: 'Bac à sable existant', sandboxCopy: 'Nouvel exemplaire', sandboxRevision: 'Révision verrouillée', sandboxHolder: 'Porteur (objets uniquement)', sandboxReason: 'Raison', sandboxInstantiate: 'Créer cet exemplaire',
    sandboxUse: 'Tester un objet', sandboxItem: 'Exemplaire de l’objet', sandboxEquip: 'Changer l’état d’équipement', sandboxActivate: 'Activer les flammes inoffensives', sandboxTarget: 'Cible d’une touche confirmée',
    sandboxHit: 'Confirmer la touche et proposer les flammes', sandboxActorHelp: 'Les dégâts nécessitent des révisions de personnages importés pour le porteur et la cible. Aucune statistique de personnage n’est inventée.',
    sandboxRecover: 'Confirmer l’événement de récupération indiqué', sandboxManual: 'Terminer manuellement une action suspendue', sandboxOutcome: 'Résultat consigné', sandboxResolve: 'Terminer sans autre modification des ressources',
    sandboxNone: 'Sans porteur', sandboxCharges: 'Charges', sandboxHP: 'Points de vie', sandboxIdle: 'Prêt', sandboxBusy: 'Action en cours', sandboxSuspended: 'Décision manuelle requise',
    sandboxDecision: 'Utiliser les flammes pour cette touche confirmée ?', sandboxYes: 'Oui, dépenser les charges', sandboxNo: 'Non, conserver la touche', sandboxDeadline: 'Délai de réponse', sandboxConflict: 'L’action a changé. Rechargez le bac à sable.'
  });
  Object.assign(words.de, {
    conflictTitle: 'Geänderter Entwurf', conflictHelp: 'Deine Eingabe bleibt hier erhalten. Lade den aktuellen Stand und vergleiche ihn vor einem neuen Speichern.',
    retainedAnswer: 'Deine aufbewahrte Eingabe', currentAnswer: 'Aktuell gespeicherter Stand', refreshConflict: 'Aktuellen Stand zum Vergleichen laden',
    editRetained: 'Aufbewahrte Antwort bearbeiten', discardRetained: 'Aufbewahrte Eingabe verwerfen', notLoaded: 'Noch nicht geladen.', noAnswer: 'Keine aktive Antwort gespeichert.',
    reviewRetained: 'Vergleiche beide Antworten. Bearbeiten öffnet deine Eingabe in der strukturierten Ansicht oder behält die JSON-Ansicht. Erst erneutes Speichern übernimmt sie.',
    cannotRestore: 'Diese Frage ist jetzt nicht verfügbar oder wurde geändert. Deine Eingabe bleibt zum Kopieren erhalten; beantworte danach die aktuellen Fragen.',
    reviewAction: 'Prüfe den aktuellen Entwurf. Verwirf diesen Hinweis und wähle die gewünschte Aktion erneut.',
    restoredInput: 'Deine Eingabe ist wieder im Formular. Prüfe sie und speichere ausdrücklich erneut.', tabMemory: 'Ungespeicherte Eingaben bleiben nur in diesem geöffneten Tab erhalten.',
    invalidJSON: 'Gib gültiges JSON ein. Deine Eingabe wurde nicht gespeichert.', loadFailed: 'Der aktuelle Stand konnte nicht geladen werden. Versuche das Laden erneut.', saving: 'Wird gespeichert …', completeTitle: 'Erforderliche Antworten gespeichert', copyIdentity: 'Kopie'
  });
  Object.assign(words.en, {
    conflictTitle: 'Draft changed', conflictHelp: 'Your input is retained here. Load the current draft and compare it before saving again.',
    retainedAnswer: 'Your retained input', currentAnswer: 'Currently saved state', refreshConflict: 'Load current draft to compare',
    editRetained: 'Edit retained answer', discardRetained: 'Discard retained input', notLoaded: 'Not loaded yet.', noAnswer: 'No active answer saved.',
    reviewRetained: 'Compare both answers. Editing opens your input in Structured view or keeps JSON view. Only an explicit new save applies it.',
    cannotRestore: 'This question is now unavailable or has changed. Your input remains available to copy; then answer the current questions.',
    reviewAction: 'Review the current draft. Dismiss this notice and choose the intended action again.',
    restoredInput: 'Your input is back in the form. Review it and explicitly save again.', tabMemory: 'Unsaved input is retained only in this open tab.',
    invalidJSON: 'Enter valid JSON. Your input was not saved.', loadFailed: 'The current state could not be loaded. Try loading again.', saving: 'Saving …', completeTitle: 'Required answers saved', copyIdentity: 'Copy'
  });
  Object.assign(words.fr, {
    conflictTitle: 'Brouillon modifié', conflictHelp: 'Votre saisie est conservée ici. Chargez le brouillon actuel et comparez-le avant un nouvel enregistrement.',
    retainedAnswer: 'Votre saisie conservée', currentAnswer: 'État actuellement enregistré', refreshConflict: 'Charger le brouillon actuel pour comparer',
    editRetained: 'Modifier la réponse conservée', discardRetained: 'Abandonner la saisie conservée', notLoaded: 'Pas encore chargé.', noAnswer: 'Aucune réponse active enregistrée.',
    reviewRetained: 'Comparez les deux réponses. La modification ouvre votre saisie en vue structurée ou conserve la vue JSON. Seul un nouvel enregistrement explicite l’applique.',
    cannotRestore: 'Cette question est indisponible ou a changé. Votre saisie reste disponible à copier ; répondez ensuite aux questions actuelles.',
    reviewAction: 'Examinez le brouillon actuel. Fermez cet avis et choisissez de nouveau l’action souhaitée.',
    restoredInput: 'Votre saisie est de nouveau dans le formulaire. Vérifiez-la et enregistrez-la explicitement.', tabMemory: 'La saisie non enregistrée est conservée uniquement dans cet onglet ouvert.',
    invalidJSON: 'Saisissez du JSON valide. Votre saisie n’a pas été enregistrée.', loadFailed: 'Impossible de charger l’état actuel. Réessayez le chargement.', saving: 'Enregistrement …', completeTitle: 'Réponses requises enregistrées', copyIdentity: 'Exemplaire'
  });
  Object.assign(words.de, {
    accessUnavailable: 'Inhalt nicht verfügbar', accessCleared: 'Der Inhalt dieses Tabs wurde entfernt. Prüfe deine Anmeldung und lade den aktuellen Stand erneut.',
    accessOutcome: 'Eine laufende Anfrage kann abgeschlossen worden sein. Prüfe den gespeicherten Stand, bevor du sie erneut ausführst.',
    accessPaused: 'Zugriff konnte nicht geprüft werden. Bearbeiten ist pausiert; deine ungespeicherte Eingabe bleibt in diesem Tab erhalten.',
    accessCheckFailed: 'Zugriffsprüfung fehlgeschlagen', checkAccess: 'Zugriff erneut prüfen', signIn: 'Anmelden', sandboxUpdated: 'Sandbox aktualisiert. Prüfe deine Auswahl.'
  });
  Object.assign(words.en, {
    accessUnavailable: 'Content unavailable', accessCleared: 'This tab’s content has been cleared. Check your sign-in and load the current state again.',
    accessOutcome: 'An in-flight request may have completed. Check the saved state before repeating it.',
    accessPaused: 'Access could not be checked. Editing is paused; your unsaved input remains in this tab.',
    accessCheckFailed: 'Access check failed', checkAccess: 'Check access again', signIn: 'Sign in', sandboxUpdated: 'Sandbox updated. Review your selection.'
  });
  Object.assign(words.fr, {
    accessUnavailable: 'Contenu indisponible', accessCleared: 'Le contenu de cet onglet a été effacé. Vérifiez votre connexion et rechargez l’état actuel.',
    accessOutcome: 'Une demande en cours peut avoir abouti. Vérifiez l’état enregistré avant de la répéter.',
    accessPaused: 'Impossible de vérifier l’accès. La modification est en pause ; votre saisie non enregistrée reste dans cet onglet.',
    accessCheckFailed: 'Échec de la vérification d’accès', checkAccess: 'Vérifier de nouveau l’accès', signIn: 'Se connecter', sandboxUpdated: 'Bac à sable actualisé. Vérifiez votre sélection.'
  });
  Object.assign(words.de, {
    newType: 'Neuer Inhalt', newContent: 'Neuen Inhalt anlegen', contentTitle: 'Inhalt erschaffen', contentLocation: 'Inhalte',
    contentIntro: 'Wähle die Art deines Inhalts. Jede Regel ist deine Entscheidung.',
    magicItem: 'Magischer Gegenstand', conditionalCard: 'Bedingte Wirkung (manuell)', choiceCard: 'Auswahl (manuell)', loreCard: 'Hintergrundtext',
    manualNotice: 'Manuelle Anleitung: Bedingungen, Auswahl und Änderungen werden von Menschen aufgelöst. Speichere vollständige Angaben als Datenblatt. Dieser Inhalt wird nicht in der Sandbox ausgeführt.',
    loreNotice: 'Dieser Inhalt ist ausschließlich beschreibend. Es werden keine Spielregeln daraus abgeleitet.',
    MANUAL_PROFILE_ONLY: 'Dieser Inhalt wird ausschließlich manuell aufgelöst', DESCRIPTIVE_ONLY: 'Dieser Inhalt ist ausschließlich beschreibend',
    CHOICE_COUNT_EXCEEDED: 'Die Auswahlzahl übersteigt die Anzahl der Alternativen', CHOICE_LABEL_DUPLICATE: 'Jede Alternative benötigt einen eindeutigen Namen'
  });
  Object.assign(words.en, {
    newType: 'New content type', newContent: 'Create content', contentTitle: 'Create content', contentLocation: 'Content',
    contentIntro: 'Choose your content type. Every rule is your decision.',
    magicItem: 'Magic item', conditionalCard: 'Conditional effect (manual)', choiceCard: 'Choice (manual)', loreCard: 'Lore',
    manualNotice: 'Manual instructions: people resolve conditions, choices and changes. Save complete instructions as Sheet ready. This content does not execute in the sandbox.',
    loreNotice: 'This content is descriptive only. No game rules are inferred from it.',
    MANUAL_PROFILE_ONLY: 'This content is resolved manually only', DESCRIPTIVE_ONLY: 'This content is descriptive only',
    CHOICE_COUNT_EXCEEDED: 'The selection count exceeds the number of alternatives', CHOICE_LABEL_DUPLICATE: 'Each alternative needs a distinct name'
  });
  Object.assign(words.fr, {
    newType: 'Nouveau type de contenu', newContent: 'Créer du contenu', contentTitle: 'Créer du contenu', contentLocation: 'Contenu',
    contentIntro: 'Choisissez le type de contenu. Chaque règle est votre décision.',
    magicItem: 'Objet magique', conditionalCard: 'Effet conditionnel (manuel)', choiceCard: 'Choix (manuel)', loreCard: 'Récit',
    manualNotice: 'Instructions manuelles : les personnes résolvent les conditions, les choix et les modifications. Enregistrez les instructions complètes comme Fiche prête. Ce contenu ne s’exécute pas dans le bac à sable.',
    loreNotice: 'Ce contenu est uniquement descriptif. Aucune règle de jeu n’en est déduite.',
    MANUAL_PROFILE_ONLY: 'Ce contenu est résolu uniquement manuellement', DESCRIPTIVE_ONLY: 'Ce contenu est uniquement descriptif',
    CHOICE_COUNT_EXCEEDED: 'Le nombre de sélections dépasse le nombre d’alternatives', CHOICE_LABEL_DUPLICATE: 'Chaque alternative nécessite un nom distinct'
  });
  const profileLabels = {'g1.authored-magic-item': 'magicItem', 'g1.authored-manual-conditional': 'conditionalCard',
    'g1.authored-manual-choice': 'choiceCard', 'g1.authored-lore': 'loreCard'};
  const $ = id => document.getElementById(id);
  let workspace, draft, preview, pending, dirtyForm, conflict, runtimeCatalog, sandboxState, busy = false, focusTarget;
  let accessEpoch = 0, accessDenied = false, accessPaused = false, checkingAccess = false, sandboxRead = 0, catalogRead = 0;
  const requests = new Set();
  class ObsoleteResponse extends Error {}
  const t = key => words[$('locale').value][key];
  const root = () => `/api/ce/authoring/workspaces/${encodeURIComponent(workspace.workspaceId)}`;
  const draftPath = () => `${root()}/drafts/${encodeURIComponent(draft.draftId)}`;
  const status = text => { if (!accessDenied) $('status').textContent = text; };
  function node(tag, text, parent) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (parent) parent.append(n); return n; }
  function translate() {
    document.documentElement.lang = $('locale').value;
    document.title = `${t('title')} · Roll Drauf`;
    document.querySelectorAll('[data-i18n]').forEach(n => { n.textContent = t(n.dataset.i18n); });
    document.querySelectorAll('[data-i18n-label]').forEach(n => { n.setAttribute('aria-label', t(n.dataset.i18nLabel)); });
    [...$('new-type').options].forEach(option => { option.textContent = t(profileLabels[option.value]); });
    updateCreateLabel();
    if (draft && draft.schemaType.typeId !== 'g1.authored-magic-item') {
      document.title = `${t('contentTitle')} · Roll Drauf`;
      for (const [key, replacement] of [['title', 'contentTitle'], ['location', 'contentLocation'], ['intro', 'contentIntro']]) {
        document.querySelector(`[data-i18n="${key}"]`).textContent = t(replacement);
      }
    }
  }
  function updateCreateLabel() {
    $('new').textContent = t($('new-type').value === 'g1.authored-magic-item' ? 'newItem' : 'newContent');
  }
  function lock() {
    document.querySelectorAll('button, input, select, textarea').forEach(n => {
      if (n.id === 'check-access') n.disabled = busy || checkingAccess;
      else if (accessDenied) n.disabled = true;
      else if (n.id === 'discard') n.disabled = busy || Boolean(pending);
      else if (accessPaused) n.disabled = true;
      else if (n.id === 'retry') n.disabled = busy;
      else if (n.closest('#conflict')) n.disabled = busy || Boolean(pending) || n.dataset.unavailable === 'true';
      else n.disabled = busy || Boolean(pending || conflict) || Boolean(dirtyForm && !dirtyForm.contains(n)) || n.dataset.unavailable === 'true';
    });
    $('retry').hidden = !pending; $('discard').hidden = !dirtyForm || Boolean(conflict);
    document.querySelectorAll('[data-ce-nav]').forEach(n => {
      if (busy || pending || dirtyForm || conflict) n.setAttribute('aria-disabled', 'true');
      else n.removeAttribute('aria-disabled');
    });
  }
  function clearSandboxView() {
    sandboxState = null; sandboxRead++;
    for (const id of ['sb-instances', 'sb-revision', 'sb-holder', 'sb-target', 'sb-item', 'sb-decisions', 'sb-state', 'sb-recovery']) $(id).replaceChildren();
    for (const id of ['sb-reason', 'sb-outcome', 'sb-manual-reason']) $(id).value = '';
    $('sb-scope').hidden = $('sb-manual').hidden = true;
  }
  function clearSandbox() {
    runtimeCatalog = null; catalogRead++;
    $('sb-revisions').replaceChildren(); $('sb-select').replaceChildren();
    clearSandboxView(); $('sandbox').hidden = true;
  }
  function clearProtected() {
    workspace = draft = preview = pending = dirtyForm = conflict = null; focusTarget = null;
    for (const id of ['drafts', 'new-type', 'draft-info', 'profile-notice', 'stale', 'questions', 'content', 'quality', 'revision', 'preset-values', 'versions', 'history', 'conflict-local', 'conflict-current', 'conflict-note']) $(id).replaceChildren();
    $('claim').value = 'lore_only';
    $('editor').querySelectorAll('[data-unavailable]').forEach(control => { control.dataset.unavailable = 'true'; });
    $('editor').hidden = $('conflict').hidden = $('preset').hidden = true;
    clearSandbox();
  }
  function denyAccess() {
    if (accessDenied) return;
    const unknownOutcome = Boolean(pending);
    accessDenied = true; accessPaused = false; accessEpoch++; busy = checkingAccess = false;
    requests.forEach(controller => controller.abort());
    clearProtected();
    $('access-heading').dataset.i18n = 'accessUnavailable';
    $('access-explanation').dataset.i18n = 'accessCleared';
    $('access-outcome').hidden = !unknownOutcome; $('access-notice').hidden = false;
    translate(); $('status').textContent = t('accessUnavailable'); lock(); $('access-heading').focus();
  }
  async function api(url, method = 'GET', body, {optionalNotFound = false, timeout = 0} = {}) {
    const epoch = accessEpoch, controller = new AbortController();
    requests.add(controller);
    const timer = timeout ? setTimeout(() => controller.abort(), timeout) : null;
    try {
      const response = await fetch(url, {method, credentials: 'include', cache: 'no-store', signal: controller.signal,
        headers: Auth.buildHeaders(method, body !== undefined), ...(body === undefined ? {} : {body: JSON.stringify(body)})});
      if (epoch !== accessEpoch) throw new ObsoleteResponse();
      if ([401, 403, 404].includes(response.status) && !(optionalNotFound && response.status === 404)) {
        denyAccess(); throw new ObsoleteResponse();
      }
      const data = await response.json();
      if (epoch !== accessEpoch) throw new ObsoleteResponse();
      if (['NOT_FOUND', 'OPERATION_FORBIDDEN'].includes(data.errorCode) || workspace && data.workspaceId && data.workspaceId !== workspace.workspaceId) {
        denyAccess(); throw new ObsoleteResponse();
      }
      if (!response.ok && !data.operationId) { const error = new Error(data.error?.code || 'ENGINE_UNAVAILABLE'); error.status = response.status; throw error; }
      return data;
    } catch (error) {
      if (epoch !== accessEpoch) throw new ObsoleteResponse();
      throw error;
    } finally {
      requests.delete(controller); if (timer !== null) clearTimeout(timer);
    }
  }
  function errorText(error) {
    if (words[$('locale').value][error.message]) return t(error.message);
    if (error.message === 'DRAFT_VERSION_CONFLICT') return t('conflict');
    if (['SCOPE_VERSION_CONFLICT', 'DECISION_STALE', 'SCOPE_BUSY'].includes(error.message)) return t('sandboxConflict');
    if ([401, 403, 404].includes(error.status)) return t('forbidden');
    return error.status && error.status < 500 ? t('invalid') : t(pending ? 'network' : 'loadFailed');
  }
  async function run(action, recovery = false) {
    if (busy || !recovery && (accessDenied || accessPaused)) return;
    const origin = document.activeElement, epoch = accessEpoch;
    busy = true; lock();
    try { await action(); } catch (error) { if (!(error instanceof ObsoleteResponse)) status(errorText(error)); }
    finally {
      if (epoch === accessEpoch) {
        busy = false; lock();
        const target = focusTarget ? focusTarget() : origin;
        focusTarget = null;
        if (target && target !== document.body && target.isConnected && !target.disabled && target.getClientRects().length) target.focus();
        else if (origin !== document.body) $('status').focus();
      }
    }
  }
  function questionForm(id) { return [...$('questions').querySelectorAll('form')].find(form => form.dataset.question === id); }
  function firstField(form) { return form?.querySelector('input:not(:disabled), textarea:not(:disabled), select:not(:disabled)'); }
  function focusEditor() { return firstField(questionForm(draft?.nextQuestionId)) || $('questions-complete') || $('decisions-heading'); }
  function clearFieldError(form) {
    form.querySelectorAll('[aria-invalid]').forEach(field => field.removeAttribute('aria-invalid'));
    const error = form.querySelector('.field-error'); error.hidden = true; error.textContent = '';
  }
  function fieldError(form, message, field = form.querySelector('input, textarea, select')) {
    const error = form.querySelector('.field-error'); error.textContent = message; error.hidden = false;
    field?.setAttribute('aria-invalid', 'true');
    if (busy) focusTarget = () => field; else field?.focus();
  }
  function displayValue(question, value) {
    if (question?.schema.enum) return t(value);
    if (question?.questionId === 'flame.damage') return `${value.count}d${value.sides}`;
    if (question?.questionId === 'flame.duration' && value.kind === 'window') {
      if (value.windowId === 'g1.flame.activation') return t('activationWindow');
      if (value.windowId === 'g1.flame.hit') return t('hitWindow');
    }
    return typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value);
  }
  function controls(question, form) {
    const value = question.answer?.value;
    function input(label, type, initial) {
      const l = node('label', undefined, form); node('span', label, l);
      const el = node(type === 'textarea' ? 'textarea' : 'input', undefined, l);
      if (type !== 'textarea') el.type = type;
      if (initial !== undefined) el.value = initial;
      el.required = true; return el;
    }
    function choice(options, initial) {
      const l = node('label', undefined, form); node('span', question.label, l);
      const el = node('select', undefined, l); el.required = true;
      const placeholder = node('option', t('choose'), el); placeholder.value = '';
      options.forEach(([key, label]) => { const option = node('option', label, el); option.value = key; });
      el.value = initial ?? ''; return el;
    }
    if ($('mode').value === 'advanced') {
      node('code', question.path.join('.'), form);
      const el = input(question.label + ' (JSON)', 'textarea', value === undefined ? '' : JSON.stringify(value, null, 2));
      return () => JSON.parse(el.value);
    }
    if (question.schema.enum) { const el = choice(question.schema.enum.map(k => [k, t(k)]), value); return () => el.value; }
    if (question.questionId === 'flame.duration') {
      const activation = 'g1.flame.activation', hit = 'g1.flame.hit';
      const current = value === undefined ? '' : value.kind === 'window' && [activation, hit].includes(value.windowId) ? value.windowId : 'custom';
      const el = choice([[activation, t('activationWindow')], [hit, t('hitWindow')], ['custom', t('custom')]], current);
      const custom = input(t('custom'), 'textarea', current === 'custom' ? JSON.stringify(value, null, 2) : '');
      const toggle = () => { custom.parentElement.hidden = el.value !== 'custom'; custom.required = el.value === 'custom'; };
      el.addEventListener('change', toggle); toggle();
      return () => el.value === 'custom' ? JSON.parse(custom.value) : {kind: 'window', windowId: el.value};
    }
    if (question.questionId === 'flame.damage') {
      const count = input(t('count'), 'number', value?.count), sides = input(t('sides'), 'number', value?.sides);
      count.min = '1'; count.max = '100'; sides.min = '2'; sides.max = '1000'; count.step = sides.step = '1';
      return () => ({count: Number(count.value), sides: Number(sides.value)});
    }
    const el = input(question.label, question.schema.type === 'integer' ? 'number' : 'textarea', value);
    if (question.schema.type === 'integer') { el.min = question.schema.minimum; el.max = question.schema.maximum; el.step = '1'; }
    if (question.schema.maxLength) el.maxLength = question.schema.maxLength;
    if (!question.required) el.required = false;
    return () => question.schema.type === 'integer' ? Number(el.value) : el.value;
  }
  function render() {
    if (accessDenied) return;
    translate(); $('editor').hidden = !draft;
    if (!draft) { status(t('empty')); return; }
    const flameProfile = draft.schemaType.typeId === 'g1.authored-magic-item';
    $('presets-section').hidden = !flameProfile;
    ['visual-preset', 'damage-preset', 'apply-preset'].forEach(id => { $(id).dataset.unavailable = String(!flameProfile); });
    $('profile-notice').hidden = flameProfile;
    $('profile-notice').textContent = flameProfile ? '' : t(draft.schemaType.typeId === 'g1.authored-lore' ? 'loreNotice' : 'manualNotice');
    $('draft-info').textContent = `${draft.content.name || t('untitled')} · ${t('version')} ${draft.draftVersion}`;
    const selectedDraft = [...$('drafts').options].find(option => option.value === draft.draftId);
    if (selectedDraft) selectedDraft.textContent = $('draft-info').textContent;
    $('content').replaceChildren();
    if ($('mode').value === 'advanced') node('pre', JSON.stringify(draft.content, null, 2), $('content'));
    else {
      const list = node('dl', undefined, $('content'));
      draft.questions.filter(q => q.answer && q.visible).forEach(q => {
        node('dt', q.label, list); node('dd', displayValue(q, q.answer.value), list);
      });
    }
    const stale = draft.questions.filter(q => q.stale).map(q => q.label);
    $('stale').hidden = stale.length === 0; $('stale').textContent = t('stale') + stale.join(' · ');
    $('questions').replaceChildren();
    const visible = draft.questions.filter(q => q.visible && ($('mode').value !== 'guided' || q.questionId === draft.nextQuestionId));
    if (!draft.nextQuestionId) {
      const heading = node('h3', t('completeTitle'), $('questions')); heading.id = 'questions-complete'; heading.tabIndex = -1;
      node('p', t('complete'), $('questions'));
    }
    visible.forEach(question => {
      const form = node('form', undefined, $('questions')); form.dataset.question = question.questionId;
      form.noValidate = true;
      const field = node('fieldset', undefined, form); node('legend', question.label, field);
      const help = node('p', question.help, field); help.className = 'help'; help.id = `help-${question.questionId}`;
      const getValue = controls(question, field);
      const error = node('p', undefined, field); error.className = 'field-error'; error.id = `error-${question.questionId}`; error.hidden = true;
      form.querySelectorAll('input, textarea, select').forEach((control, index) => {
        control.id = `answer-${question.questionId}-${index}`;
        control.setAttribute('aria-describedby', `${help.id} ${error.id}`);
      });
      const ref = {questionId: question.questionId, questionVersion: question.questionVersion};
      const save = node('button', t('save'), field); save.type = 'submit';
      if (!question.ready) form.querySelectorAll('input, textarea, select, button').forEach(n => { n.dataset.unavailable = 'true'; });
      form.addEventListener('input', () => { clearFieldError(form); dirtyForm = form; status(t('unsaved')); lock(); });
      form.addEventListener('submit', event => {
        event.preventDefault();
        const invalid = [...form.querySelectorAll('input, textarea, select')].find(control => !control.checkValidity());
        if (invalid) { fieldError(form, invalid.validationMessage, invalid); status(t('invalid')); return; }
        let value;
        try { value = getValue(); } catch {
          fieldError(form, t('invalidJSON'), [...form.querySelectorAll('textarea')].find(control => control.getClientRects().length));
          status(t('invalidJSON')); return;
        }
        const answer = {kind: question.answerKind, value};
        if (question.answerType) answer.schemaType = question.answerType;
        run(() => mutate('RecordDraftDecision', {question: ref, answer, promptLocale: $('locale').value}));
      });
      if (!question.required) {
        const skip = node('button', t('skip'), field); skip.type = 'button'; skip.dataset.unavailable = String(!question.ready);
        skip.onclick = () => run(() => mutate('SkipDraftQuestion', {question: ref}));
      }
      if (question.answer || question.stale || question.skipped) {
        const retract = node('button', t('retract'), field); retract.type = 'button';
        retract.onclick = () => run(() => mutate('RetractDraftDecision', {question: ref}));
      }
    });
    $('quality').replaceChildren();
    ['lore_only', 'sheet_ready', 'runtime_ready', 'automation_complete'].forEach(quality => {
      const gates = draft.qualityGates[quality];
      if (!gates.length) { node('p', `${t(quality)} — ${t('ready')}`, $('quality')).className = 'ready'; return; }
      const detail = node('details', undefined, $('quality')); detail.dataset.quality = quality;
      detail.open = $('claim').value === quality;
      node('summary', `${t(quality)} — ${t('blocked')} (${gates.length})`, detail);
      const list = node('ul', undefined, detail);
      gates.forEach(g => { const q = draft.questions.find(q => q.questionId === g.questionId || q.path.join('.') === g.path.join('.')); node('li', `${q ? q.label + ': ' : ''}${t(g.code)}`, list); });
    });
    $('commit').dataset.unavailable = String(draft.qualityGates[$('claim').value].length > 0);
    if (draft.guideError) status(t(draft.guideError));
    lock();
  }
  async function loadDraft(id) {
    const base = `${root()}/drafts/${encodeURIComponent(id)}`;
    const current = await api(`${base}?locale=${$('locale').value}&mode=${$('mode').value}`);
    const history = await api(base + '/history');
    draft = current;
    $('history').replaceChildren(); $('versions').replaceChildren();
    for (let version = 1; version < draft.draftVersion; version++) { const option = node('option', `${t('version')} ${version}`, $('versions')); option.value = version; }
    $('revert').dataset.unavailable = String(draft.draftVersion <= 1);
    history.forEach(entry => node('li', `${t('version')} ${entry.draftVersion}: ${t(entry.operation)}`, $('history')));
    $('revision').textContent = '';
    $('drafts').value = id; preview = null; $('preset').hidden = true; dirtyForm = null; render();
  }
  async function loadWorkspace(preferred) {
    workspace = await api('/api/ce/authoring/workspace'); $('drafts').replaceChildren();
    const chosenType = $('new-type').value;
    $('new-type').replaceChildren();
    workspace.schemaTypes.filter(type => profileLabels[type.typeId]).forEach(type => {
      const option = node('option', t(profileLabels[type.typeId]), $('new-type')); option.value = type.typeId;
    });
    if ([...$('new-type').options].some(option => option.value === chosenType)) $('new-type').value = chosenType;
    workspace.drafts.forEach((d, index) => { const option = node('option', `${index + 1} · ${t('version')} ${d.version}`, $('drafts')); option.value = d.draftId; });
    const id = preferred || workspace.drafts.at(-1)?.draftId;
    if (id) await loadDraft(id); else { draft = null; render(); }
    await loadRuntimeCatalog();
  }
  async function mutate(operation, payload) {
    const creation = operation === 'CreateDraft';
    pending = {contractVersion: '1.1.3', commandId: crypto.randomUUID(), idempotencyKey: crypto.randomUUID(),
      workspaceId: workspace.workspaceId, authorityEpoch: 1, operation, payload};
    if (!creation) Object.assign(pending, {draftId: draft.draftId, expectedDraftVersion: draft.draftVersion});
    await sendPending();
  }
  async function sendPending() {
    const command = pending;
    status(t('saving'));
    try {
      const receipt = await api('/api/ce/commands', 'POST', command);
      if (command.scopeId || command.operation === 'CreateSandboxScope') {
        pending = null;
        await loadRuntimeCatalog(command.scopeId || receipt.scopeId);
        focusTarget = () => $('sb-decisions').querySelector('button:not(:disabled)') || $('sb-state');
        status(receipt.status === 'committed' ? t('saved') : t(receipt.errorCode) || t('sandboxSuspended'));
        return;
      }
      const resultPath = command.operation === 'CreateDraft' ? root() : `${root()}/drafts/${encodeURIComponent(command.draftId)}`;
      const result = await api(`${resultPath}/commands/${encodeURIComponent(command.idempotencyKey)}`);
      pending = null; dirtyForm = null;
      await loadWorkspace(result.draftId);
      focusTarget = focusEditor;
      status(t('saved'));
      if (result.revision) $('revision').textContent = t('revision') + result.revision.id;
    } catch (error) {
      if (error instanceof ObsoleteResponse) throw error;
      if (error.status && error.status < 500 && error.status !== 429) pending = null;
      if (error.message === 'DRAFT_VERSION_CONFLICT') retainConflict(command);
      else if (pending) focusTarget = () => $('retry');
      else if (command.operation === 'RecordDraftDecision') {
        const form = questionForm(command.payload.question.questionId);
        if (form) fieldError(form, errorText(error));
      }
      throw error;
    }
  }
  function retainConflict(command) {
    const form = dirtyForm || questionForm(command.payload.question?.questionId);
    const inputs = form ? [...form.querySelectorAll('input, textarea, select')].map(control => control.value) : [];
    conflict = {command, inputs, mode: $('mode').value, refreshed: false};
    const actionLabel = {ApplyDraftPreset: 'applyPreset', CommitDraftRevision: 'commit', RevertDraft: 'revert'};
    $('conflict-local').textContent = form ? inputs.join('\n') : t(actionLabel[command.operation] || 'save');
    $('conflict-current').textContent = t('notLoaded');
    $('conflict-note').textContent = '';
    $('conflict-edit').hidden = true;
    $('conflict').hidden = false;
    focusTarget = () => $('conflict-heading');
  }
  function retainedQuestion() {
    if (!conflict?.refreshed || conflict.command.operation !== 'RecordDraftDecision') return;
    const ref = conflict.command.payload.question;
    return draft.questions.find(q => q.questionId === ref.questionId && q.questionVersion === ref.questionVersion && q.ready && q.visible);
  }
  async function refreshConflict() {
    // Reads only: a rejected command is never replayed against a newer version.
    await loadDraft(conflict.command.draftId);
    conflict.refreshed = true;
    const question = draft.questions.find(q => q.questionId === conflict.command.payload.question?.questionId);
    $('conflict-current').textContent = `${t('version')} ${draft.draftVersion}\n` +
      (question ? question.answer ? displayValue(question, question.answer.value) : t('noAnswer') : draft.content.name || t('untitled'));
    const canEdit = Boolean(retainedQuestion());
    $('conflict-edit').hidden = !canEdit;
    $('conflict-note').textContent = t(canEdit ? 'reviewRetained' : conflict.command.operation === 'RecordDraftDecision' ? 'cannotRestore' : 'reviewAction');
    status(t('conflictTitle'));
    focusTarget = () => $('conflict-current');
  }
  function editRetained() {
    const question = retainedQuestion();
    if (!question) return;
    const retained = conflict;
    $('mode').value = retained.mode === 'advanced' ? 'advanced' : 'structured';
    conflict = null; $('conflict').hidden = true; render();
    const form = questionForm(question.questionId);
    form.querySelectorAll('input, textarea, select').forEach((control, index) => {
      control.value = retained.inputs[index];
      if (control.tagName === 'SELECT') control.dispatchEvent(new Event('change'));
    });
    dirtyForm = form; status(t('restoredInput')); lock(); firstField(form)?.focus();
  }
  async function showPreset(id) {
    preview = await api(`${root()}/presets/${id}?locale=${$('locale').value}`);
    $('preset-values').replaceChildren();
    preview.decisions.forEach(d => { node('p', preview.labels[d.question.questionId].label, $('preset-values'));
      node('pre', displayValue(draft.questions.find(q => q.questionId === d.question.questionId), d.answer.value), $('preset-values')); });
    $('preset').hidden = false; focusTarget = () => $('apply-preset');
  }
  $('new-type').onchange = updateCreateLabel;
  $('new').onclick = () => run(() => mutate('CreateDraft', {
    schemaType: workspace.schemaTypes.find(type => type.typeId === $('new-type').value), authoringLocale: $('locale').value}));
  $('reload').onclick = () => run(() => loadWorkspace(draft?.draftId));
  $('drafts').onchange = () => run(() => loadDraft($('drafts').value));
  for (const id of ['mode', 'locale']) $(id).onchange = () => run(async () => {
    status(''); translate(); if (draft) await loadDraft(draft.draftId); else render(); await loadRuntimeCatalog();
    focusTarget = () => $(id);
  });
  $('discard').onclick = () => { const id = dirtyForm?.dataset.question; dirtyForm = null; render(); status(''); (firstField(questionForm(id)) || focusEditor()).focus(); };
  $('conflict-refresh').onclick = () => run(refreshConflict);
  $('conflict-edit').onclick = editRetained;
  $('conflict-discard').onclick = () => run(async () => {
    // Do not leave the user editing the stale version if they discard before refreshing.
    if (!conflict.refreshed) await loadDraft(conflict.command.draftId);
    conflict = null; dirtyForm = null; $('conflict').hidden = true; render(); status(''); focusTarget = focusEditor;
  });
  document.querySelectorAll('[data-ce-nav]').forEach(link => link.addEventListener('click', event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    if (!busy && !pending && !dirtyForm && !conflict) return;
    event.preventDefault();
    status(t(pending ? 'network' : busy ? 'loading' : conflict ? 'conflict' : 'unsaved'));
    $('status').focus();
  }));
  $('retry').onclick = () => run(sendPending);
  $('claim').onchange = () => {
    $('commit').dataset.unavailable = String(draft.qualityGates[$('claim').value].length > 0);
    $('quality').querySelectorAll('details').forEach(d => { d.open = d.dataset.quality === $('claim').value; }); lock();
  };
  $('commit').onclick = () => run(() => mutate('CommitDraftRevision', {declaredQuality: $('claim').value,
    definition: draft.definitionId ? {kind: 'definition', id: draft.definitionId} : {kind: 'new'}}));
  $('visual-preset').onclick = () => run(() => showPreset('g1.harmless-flames'));
  $('damage-preset').onclick = () => run(() => showPreset('g1.post-hit-flames'));
  $('apply-preset').onclick = () => run(() => mutate('ApplyDraftPreset', {preset: {presetId: preview.presetId, version: preview.version}, previewDigest: preview.previewDigest}));
  $('revert').onclick = () => run(() => mutate('RevertDraft', {toDraftVersion: Number($('versions').value)}));
  function selectOptions(id, values, placeholder = 'choose') {
    const select = $(id), before = select.value;
    select.replaceChildren(); const empty = node('option', t(placeholder), select); empty.value = '';
    values.forEach(([value, label]) => { const option = node('option', label, select); option.value = value; });
    select.value = values.some(([value]) => value === before) ? before : '';
  }
  async function loadRuntimeCatalog(scopeId = sandboxState?.scopeId, {background = false} = {}) {
    const serial = ++catalogRead;
    let current;
    try { current = await api('/api/ce/authoring/sandboxes', 'GET', undefined, {optionalNotFound: true, timeout: background ? 10000 : 0}); }
    catch (error) {
      if (error instanceof ObsoleteResponse) throw error;
      if (serial !== catalogRead) return;
      if (error.status !== 404) throw error;
      clearSandbox(); sandboxControls();
      // A host without native authoring also returns 404. Confirm authoring access
      // before treating the unavailable optional surface as a capability gap.
      await api('/api/ce/authoring/workspace', 'GET', undefined, {timeout: background ? 10000 : 0}); return;
    }
    if (serial !== catalogRead) return;
    if (background) scopeId = $('sb-select').value || undefined;
    if (scopeId && !current.sandboxes.some(scope => scope.scopeId === scopeId)) { denyAccess(); throw new ObsoleteResponse(); }
    const changed = JSON.stringify(current) !== JSON.stringify(runtimeCatalog);
    runtimeCatalog = current;
    $('sandbox').hidden = false; $('sb-disabled').hidden = runtimeCatalog.runtimeEnabled;
    if (!background || changed) {
      const checked = new Set([...$('sb-revisions').querySelectorAll('input:checked')].map(input => input.value));
      const focusedRevision = document.activeElement.closest('#sb-revisions') ? document.activeElement.value : null;
      $('sb-revisions').replaceChildren();
      runtimeCatalog.revisions.forEach((revision, index) => {
        const label = node('label', undefined, $('sb-revisions')), check = node('input', undefined, label);
        check.type = 'checkbox'; check.value = revision.revision.id; check.dataset.unavailable = String(!runtimeCatalog.runtimeEnabled);
        check.checked = background && checked.has(check.value);
        label.append(document.createTextNode(` ${revision.name} · ${index + 1}`));
        check.onchange = sandboxControls;
      });
      selectOptions('sb-select', runtimeCatalog.sandboxes.map((s, index) => [s.scopeId, `Sandbox ${index + 1}`]));
      sandboxControls();
      if (background && focusedRevision) {
        const replacement = [...$('sb-revisions').querySelectorAll('input')].find(input => input.value === focusedRevision && !input.disabled);
        (replacement || $('status')).focus();
      }
    }
    if (scopeId) { $('sb-select').value = scopeId; await loadSandbox(scopeId, {background}); }
    else { clearSandboxView(); sandboxControls(); }
  }
  async function loadSandbox(scopeId, {background = false} = {}) {
    if (sandboxState && sandboxState.scopeId !== scopeId) clearSandboxView();
    const serial = ++sandboxRead;
    const current = await api(`/api/ce/authoring/sandboxes/${encodeURIComponent(scopeId)}`, 'GET', undefined, {timeout: background ? 10000 : 0});
    if (serial !== sandboxRead || scopeId !== $('sb-select').value) return;
    if (background && JSON.stringify(current) === JSON.stringify(sandboxState)) return;
    const previousFocus = document.activeElement.closest('#sb-scope') ? document.activeElement.id : null;
    sandboxState = current;
    $('sb-scope').hidden = false; $('sb-instances').replaceChildren();
    const instances = sandboxState.instances, actors = instances.filter(i => Object.hasOwn(i.fields, 'hp_current'));
    // Authorized instance IDs identify copies independently of names or resource changes.
    // Expand colliding abbreviations to the complete ID rather than showing ambiguous labels.
    const identity = instance => instances.some(other => other.id !== instance.id && other.id.slice(-12) === instance.id.slice(-12)) ? instance.id : instance.id.slice(-12);
    const copyLabel = instance => `${t('copyIdentity')} ${identity(instance)} · ${instance.fields.name}`;
    instances.forEach(i => { const f = i.fields; let label = copyLabel(i);
      if (Object.hasOwn(f, 'charges')) label += ` · ${t('sandboxCharges')}: ${f.charges}/${f.maximumCharges}`;
      if (Object.hasOwn(f, 'hp_current')) label += ` · ${t('sandboxHP')}: ${f.hp_current}/${f.hp_max}`;
      const row = node('li', label, $('sb-instances')); row.dataset.instance = i.id;
    });
    selectOptions('sb-revision', sandboxState.revisions.map((r, index) => [r.id, `${runtimeCatalog.revisions.find(x => x.revision.id === r.id)?.name || t('sandboxRevision')} · ${index + 1}`]));
    selectOptions('sb-holder', actors.map(i => [i.id, copyLabel(i)]), 'sandboxNone');
    selectOptions('sb-target', actors.map(i => [i.id, copyLabel(i)]));
    selectOptions('sb-item', instances.filter(i => i.fields.revision).map(i => [i.id, copyLabel(i)]));
    $('sb-state').textContent = t(sandboxState.activeAction ? sandboxState.activeAction.state === 'SUSPENDED' ? 'sandboxSuspended' : 'sandboxBusy' : 'sandboxIdle');
    $('sb-manual').hidden = sandboxState.activeAction?.state !== 'SUSPENDED';
    $('sb-decisions').replaceChildren();
    sandboxState.decisions.forEach(decision => {
      const field = node('fieldset', undefined, $('sb-decisions')); node('legend', t('sandboxDecision'), field);
      node('p', `${t('sandboxDeadline')}: ${new Date(decision.deadline).toLocaleString($('locale').value)}`, field);
      for (const value of [true, false]) {
        const button = node('button', t(value ? 'sandboxYes' : 'sandboxNo'), field);
        button.id = `sb-decision-${decision.decisionId}-${value}`;
        button.dataset.unavailable = String(!runtimeCatalog.runtimeEnabled);
        button.onclick = () => run(() => runtimeMutation('ResolveDecision', {actionId: decision.actionId, decisionId: decision.decisionId,
          expectedDecisionVersion: decision.decisionVersion, contextToken: decision.contextToken, answer: {kind: 'boolean', value}}));
      }
    });
    sandboxControls();
    if (background) {
      $('sb-state').textContent += ` · ${t('sandboxUpdated')}`;
      if (previousFocus) ($(previousFocus) || $('sb-state')).focus();
    }
  }
  async function checkAccess(manual = false) {
    if (accessDenied || checkingAccess || !workspace || document.hidden && !manual) return;
    const epoch = accessEpoch, currentDraft = draft?.draftId;
    checkingAccess = true; lock();
    try {
      const current = await api('/api/ce/authoring/workspace', 'GET', undefined, {timeout: 10000});
      if (currentDraft && draft?.draftId === currentDraft && !current.drafts.some(entry => entry.draftId === currentDraft)) {
        denyAccess(); return;
      }
      await loadRuntimeCatalog(sandboxState?.scopeId, {background: true});
      accessPaused = false; $('access-notice').hidden = true;
      if (manual) {
        lock(); (pending ? $('retry') : firstField(dirtyForm) || focusEditor()).focus();
      }
    } catch (error) {
      if (epoch === accessEpoch && !(error instanceof ObsoleteResponse)) {
        accessPaused = true; $('access-explanation').dataset.i18n = 'accessPaused';
        $('access-heading').dataset.i18n = 'accessCheckFailed';
        $('access-outcome').hidden = true; $('access-notice').hidden = false; translate();
        status(t('accessPaused'));
        if (manual) $('access-heading').focus();
      }
    } finally {
      if (epoch === accessEpoch) { checkingAccess = false; lock(); }
    }
  }
  $('check-access').onclick = () => {
    if (busy || checkingAccess) return;
    if (!accessDenied && workspace) { checkAccess(true); return; }
    // Recovery starts from fresh authorized reads. No old command survives or replays.
    accessEpoch++; clearProtected(); accessDenied = false; accessPaused = true;
    run(async () => {
      status(t('loading')); await loadWorkspace();
      accessPaused = false; $('access-notice').hidden = true; status(''); focusTarget = focusEditor;
    }, true);
  };
  function sandboxItem() { return sandboxState?.instances.find(i => i.id === $('sb-item').value); }
  function sandboxControls() {
    const enabled = runtimeCatalog?.runtimeEnabled, idle = enabled && sandboxState && !sandboxState.activeAction;
    const item = sandboxItem()?.fields;
    $('sb-create').dataset.unavailable = String(!enabled || !$('sb-revisions').querySelector('input:checked'));
    $('sb-refresh').dataset.unavailable = String(!sandboxState);
    $('sb-instantiate').dataset.unavailable = String(!idle || !$('sb-revision').value || !$('sb-reason').value.trim());
    $('sb-equip').dataset.unavailable = String(!idle || !item?.holderId);
    $('sb-activate').dataset.unavailable = String(!idle || item?.behavior !== 'visual' || item.holderId && !item.is_equipped);
    $('sb-hit').dataset.unavailable = String(!idle || item?.behavior !== 'damage' || !item.holderId || !item.is_equipped || !$('sb-target').value);
    $('sb-recover').dataset.unavailable = String(!idle || !item);
    $('sb-recovery').textContent = item ? t(item.recovery) : '';
    $('sb-resolve').dataset.unavailable = String(!enabled || !$('sb-outcome').value.trim() || !$('sb-manual-reason').value.trim());
    lock();
  }
  function instanceRef(id) { return {kind: 'instance', id, scopeId: sandboxState.scopeId}; }
  async function runtimeMutation(operation, payload) {
    pending = {contractVersion: '1.1.3', commandId: crypto.randomUUID(), idempotencyKey: crypto.randomUUID(), operation, payload,
      scopeId: sandboxState.scopeId, expectedScopeVersion: sandboxState.stateVersion, authorityEpoch: sandboxState.authorityEpoch, executionLockDigest: sandboxState.executionLockDigest};
    await sendPending();
  }
  function invokeNative(activityId, targets = []) {
    const item = sandboxItem();
    return runtimeMutation('InvokeActivity', {actorInstance: instanceRef(item.fields.holderId || item.id), sourceInstance: instanceRef(item.id),
      activityRevisionRef: item.fields.revision, activityId, targets});
  }
  $('sb-create').onclick = () => run(async () => {
    const ids = [...$('sb-revisions').querySelectorAll('input:checked')].map(i => i.value);
    pending = {contractVersion: '1.1.3', commandId: crypto.randomUUID(), idempotencyKey: crypto.randomUUID(), authorityEpoch: 1,
      workspaceId: workspace.workspaceId, operation: 'CreateSandboxScope', payload: {ruleset: runtimeCatalog.ruleset,
        revisions: runtimeCatalog.revisions.filter(r => ids.includes(r.revision.id)).map(r => r.revision)}};
    await sendPending();
  });
  $('sb-select').onchange = () => run(async () => { if ($('sb-select').value) await loadSandbox($('sb-select').value); else { clearSandboxView(); sandboxControls(); } });
  $('sb-refresh').onclick = () => run(() => loadSandbox(sandboxState.scopeId));
  for (const id of ['sb-revision', 'sb-item', 'sb-target', 'sb-holder', 'sb-reason', 'sb-outcome', 'sb-manual-reason']) $(id).addEventListener('input', sandboxControls);
  $('sb-instantiate').onclick = () => run(() => runtimeMutation('InstantiateRevision', {revision: sandboxState.revisions.find(r => r.id === $('sb-revision').value),
    holder: $('sb-holder').value ? instanceRef($('sb-holder').value) : null, reason: $('sb-reason').value}));
  $('sb-equip').onclick = () => run(() => runtimeMutation('SetItemEquipped', {item: instanceRef(sandboxItem().id), equipped: !sandboxItem().fields.is_equipped}));
  $('sb-activate').onclick = () => run(() => invokeNative('g1.flame.activate'));
  $('sb-hit').onclick = () => run(() => invokeNative('g1.flame.confirmed-hit', [instanceRef($('sb-target').value)]));
  $('sb-recover').onclick = () => run(() => invokeNative('g1.flame.recover.' + sandboxItem().fields.recovery));
  $('sb-resolve').onclick = () => run(() => runtimeMutation('ResolveActionManually', {actionId: sandboxState.activeAction.actionId,
    expectedActionVersion: sandboxState.activeAction.version, adjustments: [], outcomeNote: $('sb-outcome').value, reason: $('sb-manual-reason').value}));
  window.addEventListener('beforeunload', event => { if (dirtyForm || pending || conflict) { event.preventDefault(); event.returnValue = ''; } });
  window.addEventListener('focus', () => checkAccess());
  document.addEventListener('visibilitychange', () => { if (!document.hidden) checkAccess(); });
  window.addEventListener('pageshow', event => { if (event.persisted) denyAccess(); });
  window.addEventListener('storage', event => { if (event.key === Auth.LOGOUT_REDIRECT_KEY && event.newValue) denyAccess(); });
  setInterval(() => checkAccess(), 15000);
  translate(); run(() => loadWorkspace());
})();
