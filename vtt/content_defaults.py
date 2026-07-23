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
        "page_key": "shared", "content_key": "ribbon.nav_dashboard", "text": "Dashboard",
        "description": "Ribbon nav button label",
    },
    {
        "page_key": "shared", "content_key": "ribbon.nav_campaigns", "text": "Campaigns",
        "description": "Ribbon nav button label",
    },
    {
        "page_key": "shared", "content_key": "ribbon.nav_characters", "text": "Characters",
        "description": "Ribbon nav button label",
    },
    {
        "page_key": "shared", "content_key": "ribbon.play_button", "text": "▶ Play",
        "description": "Ribbon Play button label (opens the quick-launch popup)",
    },
    {
        "page_key": "shared", "content_key": "ribbon.logout_button", "text": "Logout",
        "description": "Ribbon logout button label",
    },

    # ── shared: Play quick-launch popup ────────────────────────────────────
    {
        "page_key": "shared", "content_key": "play_launch.title", "text": "Play",
        "description": "Popup title",
    },
    {
        "page_key": "shared", "content_key": "play_launch.subtitle", "text": "Waehle eine Session oder starte in wenigen Schritten eine neue.",
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
        "page_key": "shared", "content_key": "play_launch.action_next_session", "text": "Naechste Session",
        "description": "Card button: DM creates the next session after one ended",
    },
    {
        "page_key": "shared", "content_key": "play_launch.action_open_campaign", "text": "Kampagne oeffnen",
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
        "page_key": "dashboard", "content_key": "shell.left_eyebrow", "text": "Chapter I",
        "description": "Small kicker above the left-page title",
    },
    {
        "page_key": "dashboard", "content_key": "shell.left_title", "text": "Home",
        "description": "Left-page title",
    },
    {
        "page_key": "dashboard", "content_key": "shell.left_copy", "text": "Willkommen zurueck, {username}. Dieses Kapitel ist jetzt dein soziales Zuhause: Guilds, Chronik-Feed und die klaren Wege weiter in Kampagnen, Charaktere, Session-Prep und den kontrollierten Pfad nach Play.",
        "description": "Left-page intro copy; {username} is substituted",
    },
    {
        "page_key": "dashboard", "content_key": "shell.right_eyebrow", "text": "Chronicle Feed",
        "description": "Small kicker above the right-page title",
    },
    {
        "page_key": "dashboard", "content_key": "shell.right_title", "text": "Was gerade zaehlt",
        "description": "Right-page title",
    },
    {
        "page_key": "dashboard", "content_key": "shell.right_copy", "text": "Der Feed liest sich wie eine laufende Chronik: Social-Hinweise, Guild-Status und die naechsten operativen Schritte bleiben sichtbar getrennt voneinander.",
        "description": "Right-page intro copy",
    },
    {
        "page_key": "dashboard", "content_key": "shell.chip_home", "text": "Home / Social Hub",
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
        "page_key": "dashboard", "content_key": "shell.chip_guild_fallback", "text": "Guild folgt",
        "description": "Meta chip shown when the user has no primary guild yet",
    },
    {
        "page_key": "dashboard", "content_key": "shell.chip_prep_blockers", "text": "{count} Prep-Blocker",
        "description": "Meta chip; {count} is substituted",
    },

    # ── dashboard: hero section ────────────────────────────────────────────
    {
        "page_key": "dashboard", "content_key": "home.hero_kicker", "text": "Home",
        "description": "Hero small kicker",
    },
    {
        "page_key": "dashboard", "content_key": "home.hero_title", "text": "Dein Heimathafen vor dem Tisch",
        "description": "Hero heading",
    },
    {
        "page_key": "dashboard", "content_key": "home.hero_summary_default", "text": "Von hier aus verzweigt sich das Buch in Social, Guilds, Kampagnen, Charaktere, Session-Prep und den kontrollierten Weg nach Play.",
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
        "page_key": "dashboard", "content_key": "home.hero_meta_sessions", "text": "{count} Sessions",
        "description": "Hero meta stat; {count} is substituted",
    },
    {
        "page_key": "dashboard", "content_key": "home.social_scope_label", "text": "Social Scope:",
        "description": "Bold label before the social-scope note",
    },
    {
        "page_key": "dashboard", "content_key": "home.social_scope_default", "text": "Dashboard-Social bleibt vom Session-Chat getrennt.",
        "description": "Social-scope note (default; server may send a live note instead)",
    },

    # ── dashboard: navigation rail ──────────────────────────────────────────
    {"page_key": "dashboard", "content_key": "home.nav_social", "text": "Social", "description": "Home nav-rail link"},
    {"page_key": "dashboard", "content_key": "home.nav_guilds", "text": "Guilds", "description": "Home nav-rail link"},
    {"page_key": "dashboard", "content_key": "home.nav_campaigns", "text": "Campaigns", "description": "Home nav-rail link"},
    {"page_key": "dashboard", "content_key": "home.nav_characters", "text": "Characters", "description": "Home nav-rail link"},
    {"page_key": "dashboard", "content_key": "home.nav_session_prep", "text": "Session Prep", "description": "Home nav-rail link"},
    {"page_key": "dashboard", "content_key": "home.nav_play", "text": "Play", "description": "Home nav-rail link"},

    # ── dashboard: guild panel ───────────────────────────────────────────
    {
        "page_key": "dashboard", "content_key": "home.guild_panel_empty_kicker", "text": "Guilds",
        "description": "Kicker shown when there are no guilds yet",
    },
    {
        "page_key": "dashboard", "content_key": "home.guild_panel_empty_title", "text": "Meta-Banner",
        "description": "Heading shown when there are no guilds yet",
    },
    {
        "page_key": "dashboard", "content_key": "home.guild_panel_empty_copy", "text": "Die Guild-Ebene wird vorbereitet.",
        "description": "Body copy shown when there are no guilds yet",
    },
    {
        "page_key": "dashboard", "content_key": "home.guild_panel_kicker", "text": "Guilds",
        "description": "Guild panel kicker",
    },
    {
        "page_key": "dashboard", "content_key": "home.guild_panel_title", "text": "Dein Banner im Buch",
        "description": "Guild panel heading",
    },
    {
        "page_key": "dashboard", "content_key": "home.guild_panel_copy", "text": "Guilds bleiben reine Meta-Identitaet. Sie veraendern keine Rollen, keine Berechtigungen und keinen Session-Chat.",
        "description": "Guild panel intro copy",
    },
    {
        "page_key": "dashboard", "content_key": "home.guild_primary_label", "text": "Primaere Gilde",
        "description": "Kicker above the user's primary guild card",
    },
    {
        "page_key": "dashboard", "content_key": "home.guild_badge_primary", "text": "Primaer",
        "description": "Badge on the user's primary guild card",
    },
    {
        "page_key": "dashboard", "content_key": "home.guild_badge_member_count", "text": "{count} Mitglieder",
        "description": "Badge on non-primary guild cards; {count} is substituted",
    },
    {
        "page_key": "dashboard", "content_key": "home.guild_button_current", "text": "Aktuelle Gilde",
        "description": "Disabled button on the user's current primary guild card",
    },
    {
        "page_key": "dashboard", "content_key": "home.guild_button_set_primary", "text": "Als Primaergilde setzen",
        "description": "Button to switch primary guild",
    },

    # ── dashboard: chronicle feed ────────────────────────────────────────
    {
        "page_key": "dashboard", "content_key": "home.feed_empty_kicker", "text": "Chronicle",
        "description": "Kicker shown when the feed is empty",
    },
    {
        "page_key": "dashboard", "content_key": "home.feed_empty_title", "text": "Home-Feed wird vorbereitet",
        "description": "Heading shown when the feed is empty",
    },
    {
        "page_key": "dashboard", "content_key": "home.feed_empty_copy", "text": "Noch keine Home-Eintraege sichtbar. Kampagnen und Charaktere bleiben solange die stabilen Einstiege.",
        "description": "Body copy shown when the feed is empty",
    },

    # ── dashboard: context (priorities + quick links) ──────────────────
    {
        "page_key": "dashboard", "content_key": "home.priorities_kicker", "text": "Heute wichtig",
        "description": "Priorities section kicker",
    },
    {
        "page_key": "dashboard", "content_key": "home.priorities_title", "text": "Prioritaeten",
        "description": "Priorities section heading",
    },
    {
        "page_key": "dashboard", "content_key": "home.quicklinks_kicker", "text": "Schnellzugriffe",
        "description": "Quick-links section kicker",
    },
    {
        "page_key": "dashboard", "content_key": "home.quicklinks_title", "text": "Wohin du als naechstes gehst",
        "description": "Quick-links section heading",
    },
    {
        "page_key": "dashboard", "content_key": "home.context_note", "text": "Dashboard bleibt Home und Social Hub. Kampagnen, Session-Prep und Play bleiben die operativen Folgeflaechen.",
        "description": "Closing note under quick links",
    },
]
