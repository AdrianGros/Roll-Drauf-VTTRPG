/**
 * Beyond20 -> Roll Drauf bridge (M-Beyond20, 2026-08-24).
 *
 * The Beyond20 browser extension relays rolls made on dndbeyond.com into
 * VTT pages as DOM CustomEvents (see https://beyond20.here-for-more.info/api).
 * For this page to receive them, the player adds this site's domain to
 * Beyond20's custom domain list (extension advanced options) -- or the
 * site gets added to Beyond20's built-in known-sites list upstream.
 *
 * This file is deliberately ONLY an adapter: it normalizes Beyond20's
 * `Beyond20_RenderedRoll` payload into the table's source-agnostic
 * external-roll envelope and hands it to window.RollDraufTable (exposed
 * by play-ui.js). Multisystem support later means writing more adapters
 * like this one -- the table and server contracts stay untouched.
 *
 * Beyond20 event payloads arrive in `event.detail` as an array of
 * arguments; the roll request is the first element. Documented request
 * fields used here: title, character{name}, attack_rolls[] (each
 * {formula, parts, total, "critical-success", "critical-failure", type}),
 * damage_rolls[] (entries commonly [label, roll, flags]), total_damages,
 * roll_info, whisper, source.
 */
(function () {
    "use strict";

    var queue = [];
    var announced = false;

    function tableReady() {
        return Boolean(window.RollDraufTable && typeof window.RollDraufTable.sendExternalRoll === "function");
    }

    function dispatchToTable(action) {
        if (action.type === "roll") {
            window.RollDraufTable.sendExternalRoll(action.payload);
        } else if (action.type === "hp" && typeof window.RollDraufTable.updateCharacterHp === "function") {
            window.RollDraufTable.updateCharacterHp(action.payload);
        } else if (action.type === "conditions" && typeof window.RollDraufTable.updateCharacterConditions === "function") {
            window.RollDraufTable.updateCharacterConditions(action.payload);
        } else if (action.type === "combat" && typeof window.RollDraufTable.updateCombatTracker === "function") {
            window.RollDraufTable.updateCombatTracker(action.payload);
        }
    }

    function detailPayload(event) {
        var detail = event && event.detail;
        if (Array.isArray(detail)) {
            return detail[0] || null;
        }
        return detail || null;
    }

    function asRollEntry(roll, fallbackLabel) {
        if (!roll || typeof roll !== "object") {
            return null;
        }
        var entry = {
            formula: String(roll.formula || fallbackLabel || ""),
            total: (typeof roll.total === "number") ? roll.total : null,
        };
        // parts is a mixed array of dice groups/operators/numbers; dice
        // groups carry {rolls: [{roll: n}, ...]}. Best effort only.
        if (Array.isArray(roll.parts)) {
            var dice = [];
            roll.parts.forEach(function (part) {
                if (part && typeof part === "object" && Array.isArray(part.rolls)) {
                    part.rolls.forEach(function (die) {
                        if (die && typeof die.roll === "number") {
                            dice.push(die.roll);
                        }
                    });
                }
            });
            if (dice.length) {
                entry.dice = dice;
            }
        }
        return entry;
    }

    function normalizeRenderedRoll(request) {
        if (!request || typeof request !== "object") {
            return null;
        }

        var rolls = [];
        var attackRolls = Array.isArray(request.attack_rolls) ? request.attack_rolls : [];
        attackRolls.forEach(function (roll) {
            var entry = asRollEntry(roll);
            if (entry) {
                entry.kind = "attack";
                entry.label = String((roll && roll.type) || "Wurf");
                rolls.push(entry);
            }
        });

        // damage_rolls entries are [damageType, Roll, flags] tuples per the
        // Beyond20 API docs; tolerate a plain roll object too.
        var damageRolls = Array.isArray(request.damage_rolls) ? request.damage_rolls : [];
        damageRolls.forEach(function (item) {
            var label = Array.isArray(item) ? String(item[0] || "") : "";
            var roll = Array.isArray(item) ? item[1] : item;
            var entry = asRollEntry(roll, label);
            if (entry) {
                entry.kind = "damage";
                entry.label = label || "Schaden";
                if (label && !entry.formula) entry.formula = label;
                rolls.push(entry);
            }
        });

        // roll_info is an array of [name, value] string tuples (save DCs
        // and similar context).
        var info = [];
        if (Array.isArray(request.roll_info)) {
            request.roll_info.forEach(function (tuple) {
                if (Array.isArray(tuple) && tuple.length >= 2) {
                    info.push(String(tuple[0]) + ": " + String(tuple[1]));
                }
            });
        }

        var primary = attackRolls[0] || null;
        var anyCrit = attackRolls.some(function (roll) {
            return roll && roll["critical-success"];
        });
        var anyFumble = attackRolls.some(function (roll) {
            return roll && roll["critical-failure"];
        });

        var total = null;
        if (primary && typeof primary.total === "number") {
            total = primary.total;
        } else if (rolls.length && typeof rolls[0].total === "number") {
            total = rolls[0].total;
        }

        var rollType = "custom";
        if (attackRolls.length && damageRolls.length) {
            rollType = "attack";
        } else if (primary && primary.type) {
            rollType = String(primary.type);
        } else if (damageRolls.length) {
            rollType = "damage";
        }

        var title = String(request.title || "").trim();
        // whisper enum: 0 = none, 1 = whisper, 2 = query, 3 = hide info.
        if (request.whisper === 1 || request.whisper === 3) {
            title = (title ? title + " " : "") + "(gefluestert)";
        }

        return {
            source: "beyond20",
            system: "dnd5e",
            character: String((request.character && request.character.name) || ""),
            title: title,
            roll_type: rollType,
            formula: String((primary && primary.formula) || (rolls[0] && rolls[0].formula) || ""),
            total: total,
            rolls: rolls,
            advantage: anyCrit ? "crit" : (anyFumble ? "fumble" : "normal"),
            info: info,
        };
    }

    function deliver(type, payload) {
        if (!payload) {
            return;
        }
        var action = { type: type, payload: payload };
        if (tableReady()) {
            dispatchToTable(action);
        } else {
            // Table socket not up yet -- keep a short queue so events that
            // arrive during page load are not lost.
            queue.push(action);
            if (queue.length > 10) {
                queue.shift();
            }
        }
    }

    window.addEventListener("rolldrauf:table-ready", function () {
        while (queue.length && tableReady()) {
            dispatchToTable(queue.shift());
        }
    });

    document.addEventListener("Beyond20_Loaded", function () {
        if (!announced) {
            announced = true;
            console.info("[beyond20-bridge] Beyond20 erkannt - D&D-Beyond-Wuerfe " +
                "werden an den Spieltisch weitergeleitet.");
        }
    });

    document.addEventListener("Beyond20_RenderedRoll", function (event) {
        try {
            deliver("roll", normalizeRenderedRoll(detailPayload(event)));
        } catch (error) {
            console.warn("[beyond20-bridge] roll konnte nicht verarbeitet werden:", error);
        }
    });

    // conditions-update messages: {action, character} where
    // character.conditions is an Array<string> and character.exhaustion a
    // separate number (exact shape per the Beyond20 API docs).
    document.addEventListener("Beyond20_UpdateConditions", function (event) {
        try {
            var request = detailPayload(event) || {};
            var character = request.character || request;
            var name = String((character && character.name) || "").trim();
            if (!name) {
                return;
            }
            var conditions = Array.isArray(character.conditions)
                ? character.conditions.map(function (entry) { return String(entry); })
                : [];
            var exhaustion = Number(character.exhaustion);
            if (isFinite(exhaustion) && exhaustion >= 1) {
                conditions = conditions.concat(["Erschoepfung " + Math.min(6, Math.round(exhaustion))]);
            }
            deliver("conditions", { name: name, conditions: conditions });
        } catch (error) {
            console.warn("[beyond20-bridge] conditions-update konnte nicht verarbeitet werden:", error);
        }
    });

    // update-combat messages: {action, combat: [{name, initiative, turn,
    // tags}]} -- the full turn order from D&D Beyond's encounter tracker.
    document.addEventListener("Beyond20_UpdateCombat", function (event) {
        try {
            var request = detailPayload(event) || {};
            var combat = Array.isArray(request.combat) ? request.combat : [];
            var combatants = [];
            combat.forEach(function (entry) {
                if (!entry || typeof entry !== "object") {
                    return;
                }
                var name = String(entry.name || "").trim();
                if (!name) {
                    return;
                }
                var initiative = Number(entry.initiative);
                combatants.push({
                    name: name,
                    initiative: isFinite(initiative) ? initiative : null,
                    turn: Boolean(entry.turn),
                });
            });
            if (combatants.length) {
                deliver("combat", combatants);
            }
        } catch (error) {
            console.warn("[beyond20-bridge] update-combat konnte nicht verarbeitet werden:", error);
        }
    });

    // hp-update messages: {action, character} with character carrying
    // name, hp, "max-hp", "temp-hp" (exact keys per the Beyond20 API
    // docs). Also fired once when a sheet is opened, seeding start HP.
    document.addEventListener("Beyond20_UpdateHP", function (event) {
        try {
            var request = detailPayload(event) || {};
            var character = request.character || request;
            var name = String((character && character.name) || "").trim();
            if (!name) {
                return;
            }
            var hp = Number(character.hp);
            var maxHp = Number(character["max-hp"]);
            deliver("hp", {
                name: name,
                hp: isFinite(hp) ? hp : null,
                maxHp: isFinite(maxHp) ? maxHp : null,
            });
        } catch (error) {
            console.warn("[beyond20-bridge] hp-update konnte nicht verarbeitet werden:", error);
        }
    });
})();
