"""Default page_content rows, seeded idempotently at app startup.

Text here is the *current* copy, extracted verbatim from book-scene.js so
the site looks identical the moment this ships - only where the text lives
changes. `{placeholder}` tokens mark spots where the frontend substitutes a
live value (a count, a username, ...); editors can move a placeholder
around a sentence but must not delete it.

Scope: persistent UI copy - headings, body text, nav/button labels. NOT
included: transient step-by-step progress messages ("Schritt 1/3: ...") and
raw error fallback strings - those are operational feedback tied to code
paths, not editorial content, and change meaning if reworded carelessly.
"""

PAGE_CONTENT_DEFAULTS = [
    # ── shared: ribbon (renders on every book-mode page) ──────────────────
    {
        "page_key": "shared", "content_key": "ribbon.nav_dashboard", "text": "Übersicht",
        "description": "Ribbon nav button label",
    },
    {
        "page_key": "shared", "content_key": "ribbon.nav_campaigns", "text": "Kampagnen",
        "description": "Ribbon nav button label",
    },
    {
        "page_key": "shared", "content_key": "ribbon.nav_characters", "text": "Charaktere",
        "description": "Ribbon nav button label",
    },
    {
        "page_key": "shared", "content_key": "ribbon.play_button", "text": "▶ Spieltisch",
        "description": "Ribbon Play button label (opens the quick-launch popup)",
    },
    {
        "page_key": "shared", "content_key": "ribbon.logout_button", "text": "Abmelden",
        "description": "Ribbon logout button label",
    },

    # ── shared: Play quick-launch popup ────────────────────────────────────
    {
        "page_key": "shared", "content_key": "play_launch.title", "text": "Spieltisch",
        "description": "Popup title",
    },
    {
        "page_key": "shared", "content_key": "play_launch.subtitle", "text": "Wähle eine Session oder starte in wenigen Schritten eine neue.",
        "description": "Popup subtitle",
    },
    {
        "page_key": "shared", "content_key": "play_launch.loading", "text": "Lade Kampagnen...",
        "description": "Shown while campaigns are loading",
    },
    {
        "page_key": "shared", "content_key": "play_launch.empty_title", "text": "Noch keine Kampagne",
        "description": "Heading shown when the user has zero campaigns",
    },
    {
        "page_key": "shared", "content_key": "play_launch.empty_copy", "text": "Leg direkt los: Name eingeben, wir legen Kampagne und erste Session an und du bist am Tisch.",
        "description": "Body copy in the zero-campaigns fast-track panel",
    },
    {
        "page_key": "shared", "content_key": "play_launch.empty_name_placeholder", "text": "Name deiner Kampagne",
        "description": "Input placeholder in the fast-track campaign name field",
    },
    {
        "page_key": "shared", "content_key": "play_launch.empty_create_button", "text": "Kampagne erstellen & zu Play",
        "description": "Fast-track button: creates campaign + session + starts + enters Play",
    },
    {
        "page_key": "shared", "content_key": "play_launch.action_resume", "text": "Fortsetzen",
        "description": "Card button: resume a paused session",
    },
    {
        "page_key": "shared", "content_key": "play_launch.action_to_play", "text": "Zu Play",
        "description": "Card button: jump into a live session",
    },
    {
        "page_key": "shared", "content_key": "play_launch.action_start_session", "text": "Session starten",
        "description": "Card button: DM starts a scheduled/ready session",
    },
    {
        "page_key": "shared", "content_key": "play_launch.action_waiting_for_dm", "text": "Wartet auf DM",
        "description": "Disabled card button: player waiting for DM to start (owner view context)",
    },
    {
        "page_key": "shared", "content_key": "play_launch.action_next_session", "text": "Nächste Session",
        "description": "Card button: DM creates the next session after one ended",
    },
    {
        "page_key": "shared", "content_key": "play_launch.action_open_campaign", "text": "Kampagne öffnen",
        "description": "Card button: non-owner opens the campaign hub after a session ended",
    },
    {
        "page_key": "shared", "content_key": "play_launch.action_create_session", "text": "Session erstellen & zu Play",
        "description": "Card button: DM creates first session for a campaign with none yet",
    },
    {
        "page_key": "shared", "content_key": "play_launch.action_waiting_for_dm_player", "text": "Warte auf DM",
        "description": "Disabled card button: player view, campaign has no session yet",
    },
    {
        "page_key": "shared", "content_key": "play_launch.no_session_yet", "text": "Noch keine Session",
        "description": "Card session line when a campaign has no sessions",
    },
    {
        "page_key": "shared", "content_key": "play_launch.add_campaign_button", "text": "Weitere Kampagne anlegen",
        "description": "Button at the bottom of the campaign grid",
    },
    {
        "page_key": "shared", "content_key": "play_launch.phase_live", "text": "Live",
        "description": "Session status badge",
    },
    {
        "page_key": "shared", "content_key": "play_launch.phase_paused", "text": "Pausiert",
        "description": "Session status badge",
    },
    {
        "page_key": "shared", "content_key": "play_launch.phase_ended", "text": "Beendet",
        "description": "Session status badge",
    },
    {
        "page_key": "shared", "content_key": "play_launch.phase_ready", "text": "Bereit",
        "description": "Session status badge",
    },
    {
        "page_key": "shared", "content_key": "play_launch.phase_scheduled", "text": "Geplant",
        "description": "Session status badge",
    },
    {
        "page_key": "shared", "content_key": "play_launch.role_dm", "text": "DM",
        "description": "Card role label when the user owns the campaign",
    },
    {
        "page_key": "shared", "content_key": "play_launch.role_player", "text": "Spieler",
        "description": "Card role label fallback",
    },
    {
        "page_key": "shared", "content_key": "play_launch.member_count", "text": "{count} Mitglieder",
        "description": "Card meta line; {count} is substituted with the member count",
    },

    # ── dashboard: page shell (title/copy/chips around the Home spread) ───
    {
        "page_key": "dashboard", "content_key": "shell.left_eyebrow", "text": "Kapitel I",
        "description": "Small kicker above the left-page title",
    },
    {
        "page_key": "dashboard", "content_key": "shell.left_title", "text": "Übersicht",
        "description": "Left-page title",
    },
    {
        "page_key": "dashboard", "content_key": "shell.left_copy", "text": "Willkommen zurück, {username}.",
        "description": "Left-page intro copy; {username} is substituted",
    },
    {
        "page_key": "dashboard", "content_key": "shell.right_eyebrow", "text": "Chronik",
        "description": "Small kicker above the right-page title",
    },
    {
        "page_key": "dashboard", "content_key": "shell.right_title", "text": "Was gerade zählt",
        "description": "Right-page title",
    },
    {
        "page_key": "dashboard", "content_key": "shell.right_copy", "text": "VTT-Stand und nächste Vorbereitungsschritte.",
        "description": "Right-page intro copy",
    },
    {
        "page_key": "dashboard", "content_key": "shell.chip_home", "text": "Übersicht",
        "description": "Meta chip on the right page",
    },
    {
        "page_key": "dashboard", "content_key": "shell.chip_campaigns", "text": "{count} Kampagnen",
        "description": "Meta chip; {count} is substituted",
    },
    {
        "page_key": "dashboard", "content_key": "shell.chip_characters", "text": "{count} Charaktere",
        "description": "Meta chip; {count} is substituted",
    },
    {
        "page_key": "dashboard", "content_key": "shell.chip_prep_blockers", "text": "{count} offene Punkte",
        "description": "Meta chip; {count} is substituted",
    },

    # ── dashboard: hero section ────────────────────────────────────────────
    {
        "page_key": "dashboard", "content_key": "home.hero_kicker", "text": "Lesebändchen",
        "description": "Hero small kicker",
    },
    {
        "page_key": "dashboard", "content_key": "home.hero_title", "text": "Weiterlesen",
        "description": "Hero heading",
    },
    {
        "page_key": "dashboard", "content_key": "home.hero_summary_default", "text": "Dein Stand auf einen Blick: Kampagnen, Charaktere, Vorbereitung und Spieltisch.",
        "description": "Hero body copy (default; server may send a live summary instead)",
    },
    {
        "page_key": "dashboard", "content_key": "home.hero_meta_campaigns", "text": "{count} Kampagnen",
        "description": "Hero meta stat; {count} is substituted",
    },
    {
        "page_key": "dashboard", "content_key": "home.hero_meta_characters", "text": "{count} Helden",
        "description": "Hero meta stat; {count} is substituted",
    },
    {
        "page_key": "dashboard", "content_key": "home.hero_meta_sessions", "text": "{count} Sitzungen",
        "description": "Hero meta stat; {count} is substituted",
    },
    {
        "page_key": "dashboard", "content_key": "home.overview_scope_label", "text": "Bereich:",
        "description": "Bold label before the personal VTT overview note",
    },
    {
        "page_key": "dashboard", "content_key": "home.overview_scope_default", "text": "Diese Übersicht zeigt deinen VTT-Stand: Kampagnen, Charaktere, Sitzungen und Vorbereitung.",
        "description": "Personal VTT overview note (default; server may send a live note instead)",
    },

    # ── dashboard: navigation rail ──────────────────────────────────────────
    {"page_key": "dashboard", "content_key": "home.nav_campaigns", "text": "Kampagnen", "description": "Home nav-rail link"},
    {"page_key": "dashboard", "content_key": "home.nav_characters", "text": "Charaktere", "description": "Home nav-rail link"},
    {"page_key": "dashboard", "content_key": "home.nav_session_prep", "text": "Vorbereitung", "description": "Home nav-rail link"},
    {"page_key": "dashboard", "content_key": "home.nav_play", "text": "Spieltisch", "description": "Home nav-rail link"},

    # ── dashboard: chronicle feed ────────────────────────────────────────
    {
        "page_key": "dashboard", "content_key": "home.feed_empty_kicker", "text": "Chronik",
        "description": "Kicker shown when the feed is empty",
    },
    {
        "page_key": "dashboard", "content_key": "home.feed_empty_title", "text": "Neuigkeiten werden vorbereitet",
        "description": "Heading shown when the feed is empty",
    },
    {
        "page_key": "dashboard", "content_key": "home.feed_empty_copy", "text": "Noch keine Neuigkeiten sichtbar. Kampagnen und Charaktere sind deine nächsten Einstiege.",
        "description": "Body copy shown when the feed is empty",
    },

    # ── dashboard: context (priorities + quick links) ──────────────────
    {
        "page_key": "dashboard", "content_key": "home.priorities_kicker", "text": "Heute wichtig",
        "description": "Priorities section kicker",
    },
    {
        "page_key": "dashboard", "content_key": "home.priorities_title", "text": "Prioritäten",
        "description": "Priorities section heading",
    },
    {
        "page_key": "dashboard", "content_key": "home.quicklinks_kicker", "text": "Schnellzugriffe",
        "description": "Quick-links section kicker",
    },
    {
        "page_key": "dashboard", "content_key": "home.quicklinks_title", "text": "Wohin du als nächstes gehst",
        "description": "Quick-links section heading",
    },
    {
        "page_key": "dashboard", "content_key": "home.context_note", "text": "Die Übersicht zeigt deinen Stand. Öffne eine Kapitelzeile oben, um weiterzuarbeiten.",
        "description": "Closing note under quick links",
    },
]


# B1 language pass (Designbrief 2026-08-24): rows seeded with these OLD
# default texts get retranslated in place at startup -- ONLY if the row
# still exactly matches the old default, so editor changes survive.
PAGE_CONTENT_RETRANSLATIONS = [
    ('dashboard', 'shell.left_copy', 'Willkommen zurück, {username}. Dieses Kapitel ist jetzt dein soziales Zuhause: Guilds, Chronik-Feed und die klaren Wege weiter in Kampagnen, Charaktere, Session-Prep und den kontrollierten Pfad nach Play.', 'Willkommen zurück, {username}. Hier siehst du deinen persönlichen VTT-Stand und den nächsten Weg in Kampagnen, Charaktere, Session-Prep und Play.'),
    ('dashboard', 'home.hero_kicker', 'Übersicht', 'Lesebändchen'),
    ('dashboard', 'home.hero_title', 'Dein Heimathafen vor dem Tisch', 'Weiterlesen'),
    ('shared', 'ribbon.nav_dashboard', 'Dashboard', 'Übersicht'),
    ('shared', 'ribbon.nav_campaigns', 'Campaigns', 'Kampagnen'),
    ('shared', 'ribbon.nav_characters', 'Characters', 'Charaktere'),
    ('shared', 'ribbon.play_button', '▶ Play', '▶ Spieltisch'),
    ('shared', 'ribbon.logout_button', 'Logout', 'Abmelden'),
    ('shared', 'play_launch.title', 'Play', 'Spieltisch'),
    ('dashboard', 'shell.left_eyebrow', 'Chapter I', 'Kapitel I'),
    ('dashboard', 'shell.left_title', 'Home', 'Übersicht'),
    ('dashboard', 'shell.right_eyebrow', 'Chronicle Feed', 'Chronik'),
    ('dashboard', 'shell.chip_home', 'Home / Social Hub', 'Übersicht'),
    ('dashboard', 'home.hero_kicker', 'Home', 'Übersicht'),
    ('dashboard', 'home.overview_scope_label', 'Social Scope:', 'Bereich:'),
    ('dashboard', 'home.overview_scope_default', 'Neuigkeiten und Vorbereitung stehen hier gesammelt.', 'Diese Übersicht zeigt deinen VTT-Stand: Kampagnen, Charaktere, Sitzungen und Vorbereitung.'),
    ('dashboard', 'shell.right_copy', 'Social-Hinweise, Guild-Status und nächste Schritte.', 'VTT-Stand und nächste Vorbereitungsschritte.'),
    ('dashboard', 'home.nav_session_prep', 'Session Prep', 'Vorbereitung'),
    ('dashboard', 'home.nav_campaigns', 'Campaigns', 'Kampagnen'),
    ('dashboard', 'home.nav_characters', 'Characters', 'Charaktere'),
    ('dashboard', 'home.nav_play', 'Play', 'Spieltisch'),
    ('dashboard', 'home.feed_empty_kicker', 'Chronicle', 'Chronik'),
]
