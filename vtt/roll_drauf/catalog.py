"""
Roll Drauf Light — controlled content catalogs.

Single source of truth for species, factions, classes, and backgrounds.
Structure is backward-compatible with routes._catalog_lookup():
  - top-level dicts keyed by slug
  - each entry carries id / slug / name at minimum
  - species entries carry a nested factions dict keyed by faction slug

M24 additions (beyond M23):
  - species: trait (slug/name/description)
  - factions: tags list
  - classes: description, hit_die, base_hp, base_defense, base_fokus,
             training_bonus, progression (levels 1–5)
  - backgrounds: description, perk (slug/name/description)
"""

# ---------------------------------------------------------------------------
# Species + Factions
# ---------------------------------------------------------------------------

SPECIES = {
    'mensch': {
        'id': 'species_mensch',
        'slug': 'mensch',
        'name': 'Mensch',
        'description': (
            'Vielseitig und anpassungsfähig. '
            'Menschen Turtonias besiedeln die meisten Ebenen und'
            ' sind in Handel, Politik und Militär gleichermaßen vertreten.'
        ),
        'trait': {
            'slug': 'vielseitig',
            'name': 'Vielseitig',
            'description': (
                'Wähle beim Start einen zusätzlichen Tag aus einem beliebigen Bereich. '
                'Menschen sind in keinem Feld überragend, aber in jedem brauchbar.'
            ),
        },
        'factions': {
            'rote-rose': {
                'id': 'faction_rote_rose',
                'slug': 'rote-rose',
                'name': 'Rote Rose',
                'tags': ['militärisch', 'diszipliniert'],
                'hook': 'Du stehst in den Diensten der Roten Rose — Ordnung und Pflicht sind dein Codex.',
            },
            'freie-staedte': {
                'id': 'faction_freie_staedte',
                'slug': 'freie-staedte',
                'name': 'Freie Städte',
                'tags': ['händlerisch', 'flexibel'],
                'hook': 'Die Freien Städte bieten dir Neutralität und Handelsrouten — Pragmatismus ist Tugend.',
            },
        },
    },

    'zwerg': {
        'id': 'species_zwerg',
        'slug': 'zwerg',
        'name': 'Zwerg',
        'description': (
            'Robust und ausdauernd. '
            'Zwerge Turtonias sind für ihre Belastbarkeit, ihr Handwerk und ihre Tiefenkenntnis bekannt.'
        ),
        'trait': {
            'slug': 'robust',
            'name': 'Robust',
            'description': (
                'Zwerge stecken mehr ein als andere. '
                'Erhöhe deinen Abwehrwert um 1 und erhalte den Tag "Tragkraft".'
            ),
        },
        'factions': {
            'toldonar': {
                'id': 'faction_toldonar',
                'slug': 'toldonar',
                'name': 'Toldonar',
                'tags': ['bergvolk', 'beständig'],
                'hook': 'Toldonar steht für die alten Werte — Stein, Erz und Versprechen, die halten.',
            },
            'ugotah': {
                'id': 'faction_ugotah',
                'slug': 'ugotah',
                'name': 'Ugotah',
                'tags': ['kriegerisch', 'ehrenhaft'],
                'hook': 'Die Ugotah-Zwerge sind Kämpfer zuerst. Ehre im Gefecht ist ihre Währung.',
            },
        },
    },

    'elf': {
        'id': 'species_elf',
        'slug': 'elf',
        'name': 'Elf',
        'description': (
            'Präzise und fokussiert. '
            'Elfen Turtonias denken in langen Bögen, handeln bedächtig und wahrnehmen mehr als andere.'
        ),
        'trait': {
            'slug': 'praezise',
            'name': 'Präzise',
            'description': (
                'Elfen sind auf Details geschult. '
                'Erhalte den Tag "Wahrnehmung" und +1 auf Fertigkeitsproben, die Genauigkeit erfordern.'
            ),
        },
        'factions': {
            'prankeninseln': {
                'id': 'faction_prankeninseln',
                'slug': 'prankeninseln',
                'name': 'Prankeninseln',
                'tags': ['seefahrend', 'abenteuerlustig'],
                'hook': 'Die Prankeninseln kennen keine festen Grenzen — nur Horizonte, die es zu erkunden gilt.',
            },
            'emperium-drohm': {
                'id': 'faction_emperium_drohm',
                'slug': 'emperium-drohm',
                'name': 'Emperium Drohm',
                'tags': ['akademisch', 'kultiviert'],
                'hook': 'Im Emperium Drohm regiert Wissen. Wer liest, der herrscht — wenn auch still.',
            },
        },
    },

    'turtonen': {
        'id': 'species_turtonen',
        'slug': 'turtonen',
        'name': 'Turtonen',
        'description': (
            'Widerstandsfähig und ausdauernd. '
            'Turtonen tragen ihr Schutzpanzer-Erbe in Haltung und Wesen — sie weichen nicht.'
        ),
        'trait': {
            'slug': 'widerstandsfaehig',
            'name': 'Widerstandsfähig',
            'description': (
                'Turtonen halten mehr stand als andere. '
                'Starte mit 1 zusätzlichen Trefferpunkt und erhalte den Tag "Belastbar".'
            ),
        },
        'factions': {
            'panzerbund-von-talkaruum': {
                'id': 'faction_panzerbund_von_talkaruum',
                'slug': 'panzerbund-von-talkaruum',
                'name': 'Panzerbund von Talkaruum',
                'tags': ['defensiv', 'solidarisch'],
                'hook': 'Der Panzerbund schützt seinen eigenen. Niemand steht allein, solange die Formation hält.',
            },
            'die-schwarze-hand': {
                'id': 'faction_die_schwarze_hand',
                'slug': 'die-schwarze-hand',
                'name': 'Die Schwarze Hand',
                'tags': ['listig', 'opportunistisch'],
                'hook': 'Die Schwarze Hand operiert im Schatten. Nützlichkeit ist Loyalität, nicht Sentiment.',
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Classes — with level 1–5 progression scaffold
# ---------------------------------------------------------------------------
# Progression keys are integers 1–5 (Python dicts).
# Each level entry carries:
#   auto_features: list of features granted automatically at this level
#   choices_available: list of choice descriptors (choice_type, options, …)
# ---------------------------------------------------------------------------

CLASSES = {
    'kaempfer': {
        'id': 'class_kaempfer',
        'slug': 'kaempfer',
        'name': 'Kämpfer',
        'description': 'Verlässlicher Frontliner. Stabile Waffen- und Abwehridentität, einfach zu greifen, hart im Nehmen.',
        'hit_die': 10,
        'base_hp': 10,
        'base_defense': 12,
        'base_fokus': 0,
        'training_bonus': 2,
        'progression': {
            1: {
                'auto_features': [
                    {
                        'slug': 'waffenvertrautheit',
                        'name': 'Waffenvertrautheit',
                        'description': 'Du bist mit allen einfachen und kriegerischen Waffen vertraut und kannst sie ohne Einschränkung einsetzen.',
                        'source': 'class',
                    },
                    {
                        'slug': 'sturmangriff',
                        'name': 'Sturmangriff',
                        'description': 'Einmal pro Rast kannst du einen Sturmangriff ankündigen. Du erhältst +2 auf deinen nächsten Angriffswurf.',
                        'source': 'class',
                    },
                ],
                'choices_available': [],
            },
            2: {
                'auto_features': [
                    {
                        'slug': 'zweiter_atem',
                        'name': 'Zweiter Atem',
                        'description': 'Einmal pro Rast kannst du als schnelle Aktion 1W6 + Trainingsbonus TP wiedergewinnen.',
                        'source': 'class',
                    },
                ],
                'choices_available': [],
            },
            3: {
                'auto_features': [],
                'choices_available': [
                    {
                        'slug': 'kaempfer_signature',
                        'choice_type': 'signature',
                        'prompt': 'Wähle deinen Kampfstil — er prägt dich ab jetzt.',
                        'options': [
                            {
                                'slug': 'defensiver_stil',
                                'name': 'Defensiver Stil',
                                'description': 'Du fokussierst dich auf Deckung und Ausdauer. Dein Abwehrwert erhöht sich dauerhaft um 1.',
                                'source': 'class',
                            },
                            {
                                'slug': 'offensiver_stil',
                                'name': 'Offensiver Stil',
                                'description': 'Du setzt auf Druck und Durchbruch. Füge deinen Waffenangriffen dauerhaft +1 Schaden hinzu.',
                                'source': 'class',
                            },
                        ],
                    },
                ],
            },
            4: {
                'auto_features': [],
                'choices_available': [
                    {
                        'slug': 'attributwahl',
                        'choice_type': 'attribute',
                        'prompt': 'Erhöhe ein Attribut deiner Wahl um 1.',
                        'options': ['str', 'dex', 'con', 'int', 'wis', 'cha'],
                    },
                ],
            },
            5: {
                'auto_features': [
                    {
                        'slug': 'kampfmeister',
                        'name': 'Kampfmeister',
                        'description': 'Dein Trainingsbonus steigt auf 3. Zusätzlich erhältst du +1 auf alle Waffenangriffe — deine Erfahrung wird zur Waffe.',
                        'source': 'class',
                    },
                ],
                'choices_available': [],
            },
        },
    },

    'magier': {
        'id': 'class_magier',
        'slug': 'magier',
        'name': 'Magier',
        'description': 'Fokus-getrieben. Kleine, kontrollierte arkane Techniken — Präzision statt roher Gewalt.',
        'hit_die': 6,
        'base_hp': 6,
        'base_defense': 10,
        'base_fokus': 2,
        'training_bonus': 2,
        'progression': {
            1: {
                'auto_features': [
                    {
                        'slug': 'fokuspuls',
                        'name': 'Fokuspuls',
                        'description': 'Du kannst einen arkanen Fokuspuls einsetzen: ein kleiner, kontrollierter Energiestoss. Verbraucht 1 Fokusslot.',
                        'source': 'class',
                    },
                    {
                        'slug': 'schriftkundig',
                        'name': 'Schriftkundig',
                        'description': 'Du kannst arkane Schriften lesen und verstehen. Du erhältst den Tag "Arkane Schriftkunde".',
                        'source': 'class',
                    },
                ],
                'choices_available': [],
            },
            2: {
                'auto_features': [
                    {
                        'slug': 'erweiterter_fokus',
                        'name': 'Erweiterter Fokus',
                        'description': 'Du erhältst einen zusätzlichen Fokusslot. Deine Kapazität steigt mit deiner Erfahrung.',
                        'source': 'class',
                    },
                ],
                'choices_available': [],
            },
            3: {
                'auto_features': [],
                'choices_available': [
                    {
                        'slug': 'magier_signature',
                        'choice_type': 'signature',
                        'prompt': 'Wähle deine arkane Signatur — sie bestimmt deinen Weg.',
                        'options': [
                            {
                                'slug': 'arkane_ruestung',
                                'name': 'Arkane Rüstung',
                                'description': 'Du leitest Fokusenergie in eine schützende Hülle. Dein Abwehrwert erhöht sich um 1, solange du noch Fokusslots hast.',
                                'source': 'class',
                            },
                            {
                                'slug': 'doppelpuls',
                                'name': 'Doppelpuls',
                                'description': 'Du hast gelernt, zwei Pulse gleichzeitig zu entladen. Einmal pro Runde kannst du zwei Fokuspulse für den Preis von 1 Slot abfeuern.',
                                'source': 'class',
                            },
                        ],
                    },
                ],
            },
            4: {
                'auto_features': [],
                'choices_available': [
                    {
                        'slug': 'attributwahl',
                        'choice_type': 'attribute',
                        'prompt': 'Erhöhe ein Attribut deiner Wahl um 1.',
                        'options': ['str', 'dex', 'con', 'int', 'wis', 'cha'],
                    },
                ],
            },
            5: {
                'auto_features': [
                    {
                        'slug': 'magiemeister',
                        'name': 'Magiemeister',
                        'description': 'Dein Trainingsbonus steigt auf 3. Du erhältst einen weiteren Fokusslot und deine Pulsstärke nimmt messbar zu.',
                        'source': 'class',
                    },
                ],
                'choices_available': [],
            },
        },
    },

    'schurke': {
        'id': 'class_schurke',
        'slug': 'schurke',
        'name': 'Schurke',
        'description': 'Präzise und beweglich. Opportunismus, Mobilität und Tricks — der Schurke gewinnt durch Position, nicht durch Ausdauer.',
        'hit_die': 8,
        'base_hp': 8,
        'base_defense': 11,
        'base_fokus': 0,
        'training_bonus': 2,
        'progression': {
            1: {
                'auto_features': [
                    {
                        'slug': 'hinterhaeltiger_stich',
                        'name': 'Hinterhältiger Stich',
                        'description': 'Wenn du Vorteil auf einen Angriff hast oder ein Verbündeter neben dem Ziel steht, fügst du +1W6 Bonusschaden hinzu.',
                        'source': 'class',
                    },
                    {
                        'slug': 'akrobatik',
                        'name': 'Akrobatik',
                        'description': 'Du bist in Bewegung schwer zu greifen. Du erhältst den Tag "Akrobatik" und kannst dich nach Angriffen 1 Feld weit zurückziehen.',
                        'source': 'class',
                    },
                ],
                'choices_available': [],
            },
            2: {
                'auto_features': [
                    {
                        'slug': 'ausweichen',
                        'name': 'Ausweichen',
                        'description': 'Wenn dir ein Angriff droht, kannst du einmal pro Runde als Reaktion deinen Abwehrwert für diesen Angriff um 2 erhöhen.',
                        'source': 'class',
                    },
                ],
                'choices_available': [],
            },
            3: {
                'auto_features': [],
                'choices_available': [
                    {
                        'slug': 'schurke_signature',
                        'choice_type': 'signature',
                        'prompt': 'Wähle deinen Schurken-Pfad — er bestimmt deine Spezialisierung.',
                        'options': [
                            {
                                'slug': 'meuchler',
                                'name': 'Meuchler',
                                'description': 'Du bist auf lautlosen Schaden spezialisiert. Dein Hinterhältiger Stich richtet +1W6 mehr an, wenn das Ziel ahnungslos ist.',
                                'source': 'class',
                            },
                            {
                                'slug': 'fluchtexperte',
                                'name': 'Fluchtexperte',
                                'description': 'Du bist auf Entkommen und Repositionierung spezialisiert. Du kannst dich nach jedem Angriff bis zu 2 Felder weit bewegen, ohne Gelegenheitsangriffe auszulösen.',
                                'source': 'class',
                            },
                        ],
                    },
                ],
            },
            4: {
                'auto_features': [],
                'choices_available': [
                    {
                        'slug': 'attributwahl',
                        'choice_type': 'attribute',
                        'prompt': 'Erhöhe ein Attribut deiner Wahl um 1.',
                        'options': ['str', 'dex', 'con', 'int', 'wis', 'cha'],
                    },
                ],
            },
            5: {
                'auto_features': [
                    {
                        'slug': 'schattenmeister',
                        'name': 'Schattenmeister',
                        'description': 'Dein Trainingsbonus steigt auf 3. Im Schatten bist du fast unsichtbar: Angreifer haben Nachteil auf dich, wenn du dich in Deckung befindest.',
                        'source': 'class',
                    },
                ],
                'choices_available': [],
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Backgrounds
# ---------------------------------------------------------------------------

BACKGROUNDS = {
    'soldat': {
        'id': 'background_soldat',
        'slug': 'soldat',
        'name': 'Soldat',
        'description': 'Du hast in einer organisierten Streitmacht gedient. Befehlsketten, Disziplin und Waffen sind dir vertraut.',
        'perk': {
            'slug': 'kampferfahren',
            'name': 'Kampferfahren',
            'description': 'Du erhältst den Tag "Kampferfahren" und +1 auf Angriffswürfe mit Waffen, für die du ausgebildet bist.',
        },
    },
    'gelehrte': {
        'id': 'background_gelehrte',
        'slug': 'gelehrte',
        'name': 'Gelehrte',
        'description': 'Du hast deine prägenden Jahre in Bibliotheken, Schulen oder Forschungsstätten verbracht. Wissen ist dein Werkzeug.',
        'perk': {
            'slug': 'buchkundig',
            'name': 'Buchkundig',
            'description': 'Du erhältst den Tag "Buchkundig" und +1 auf Wissensproben und das Verstehen von Texten, Karten oder arkanen Symbolen.',
        },
    },
    'gassenkind': {
        'id': 'background_gassenkind',
        'slug': 'gassenkind',
        'name': 'Gassenkind',
        'description': 'Du bist in den Randbereichen der Stadt aufgewachsen. Überleben, Tricks und das Lesen von Situationen sind deine Stärken.',
        'perk': {
            'slug': 'stadtkundig',
            'name': 'Stadtkundig',
            'description': 'Du erhältst den Tag "Stadtkundig" und +1 auf Täuschungs- und Trickproben in städtischen Umgebungen.',
        },
    },
    'handwerker': {
        'id': 'background_handwerker',
        'slug': 'handwerker',
        'name': 'Handwerker',
        'description': 'Du hast ein Handwerk gelernt und betrieben. Materialien, Werkzeuge und praktische Lösungen sind dein Metier.',
        'perk': {
            'slug': 'werkzeugkundig',
            'name': 'Werkzeugkundig',
            'description': 'Du erhältst den Tag "Werkzeugkundig". Du kannst improvisierte Werkzeuge nutzen, ohne Abzüge zu erhalten, und Geräte und Mechanismen einschätzen.',
        },
    },
    'bote': {
        'id': 'background_bote',
        'slug': 'bote',
        'name': 'Bote',
        'description': 'Du hast Nachrichten, Güter oder Geheimnisse über weite Strecken transportiert. Wege, Menschen und Gefahren kennst du aus der Praxis.',
        'perk': {
            'slug': 'weitgereist',
            'name': 'Weitgereist',
            'description': 'Du erhältst den Tag "Weitgereist". Du kennst Routen, Rastplätze und Wegmarken. +1 auf Orientierungs- und Reiseproben.',
        },
    },
    'novize': {
        'id': 'background_novize',
        'slug': 'novize',
        'name': 'Novize',
        'description': 'Du hast deine frühen Jahre in einem Orden, Tempel oder einer arkanen Institution verbracht. Rituale und Überzeugungen prägen dich.',
        'perk': {
            'slug': 'ritualkenntnis',
            'name': 'Ritualkenntnis',
            'description': 'Du erhältst den Tag "Ritualkenntnis" und +1 auf Proben rund um Zeremonien, religiöse Praktiken oder einfache Rituale.',
        },
    },
}


# ---------------------------------------------------------------------------
# Level-1 stat baselines — kept in sync with progression above.
# These drive the actual Character model fields at creation time.
# ---------------------------------------------------------------------------

LEVEL_ONE_BASELINES = {
    'kaempfer': {'hp_max': 10, 'ac': 12, 'mana_max': 0},
    'magier':   {'hp_max': 6,  'ac': 10, 'mana_max': 2},
    'schurke':  {'hp_max': 8,  'ac': 11, 'mana_max': 0},
}
