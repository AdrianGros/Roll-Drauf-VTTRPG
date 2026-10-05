# DAD-M Apply: Roll20-Inspired Sheet and Action Manifest

Date: 2026-08-31
Status: proposed Apply design
Source analysis: [Roll20 GitHub translation research](ROLL20_GITHUB_VTT_TRANSLATION_RESEARCH_2026-08-31.md)

## Decision

Introduce a declarative, non-executable `SheetActionManifest` contract for system-specific character-sheet surfaces and action-bar metadata.

The manifest is a small external interface for describing:

- the fields a character sheet exposes;
- the logical bindings for persisted and derived values;
- localized content keys;
- references to already-registered server actions; and
- compatibility and data-schema versions.

The manifest does not contain Python, JavaScript, macros, arbitrary formulas, imports, URLs, or permission-granting rules. It cannot create a new executable action by itself. The existing server action registry and `execute_action` route remain authoritative for behavior and authorization.

This translates the useful boundary visible in Roll20’s public sheet and API repositories—declarative sheet metadata, named handlers, computed values, translations, and versioned community modules—without importing a script runtime or copying implementation code/assets.

## Current seams and constraints

The design is deliberately fitted to the current VTT rather than to an assumed Roll20 architecture:

| Existing seam | Fact used by this design | Apply consequence |
| --- | --- | --- |
| Character model | Fixed gameplay fields plus flexible `character_data` JSON | Bind manifest fields through stable logical keys; do not expose database paths. |
| Action catalog | `vtt/play/actions.py` currently defines `attack_basic`, `dash_move`, and `interact_object` | A manifest may reference only registered action codes; it does not define handlers. |
| Action route | `vtt/play/routes.py` checks campaign/session state, role, token existence, ownership, and target requirements | Manifest scopes are descriptive metadata; the route and permission service enforce access. |
| Permissions | Campaign roles and resource ownership are already separate from platform roles/profile tiers | `campaign_operator` maps to the existing campaign operator boundary; a platform role never grants token control by manifest declaration. |
| Localization | `PageContent` and `content_defaults.py` provide the current editable, German-first copy path | Manifests carry message keys and required-key declarations, not a second copy database. |
| Realtime state | Socket events and state snapshots are sequenced and role-scoped | A manifest may describe a surface; it does not publish state or bypass snapshot/event filtering. |

Relevant implementation seams are [character.py](../vtt/models/character.py#L1), [actions.py](../vtt/play/actions.py#L8), [routes.py](../vtt/play/routes.py#L546), [permissions.py](../vtt/permissions.py#L1), and [page_content.py](../vtt/models/page_content.py#L1).

## Module boundary

The planned module is the `Sheet Manifest Module`, with a future home under `vtt/sheets/`. In codebase-design terms, this is a deep module: its public interface is small, while validation, compatibility checks, locale fallback, logical binding resolution, and action-reference checks remain hidden behind it.

Proposed external interface:

```text
resolve(system_id, locale="de") -> ResolvedSheetManifest
```

The returned value is read-only and contains validated declarations plus resolved labels. The module may reject an invalid or incompatible manifest; it must not return a partially valid surface.

The module owns:

- loading repository-managed JSON manifests;
- validating the contract and supported versions;
- checking logical field bindings against the selected system adapter;
- checking action references against the server action registry;
- resolving requested locale to the German-first fallback; and
- returning immutable data to a future sheet renderer or bootstrap adapter.

The module does not own:

- action execution or dice resolution;
- campaign/session authorization;
- token ownership or visibility;
- persistence writes;
- Socket.IO events;
- user-uploaded extensions; or
- arbitrary code execution.

The seam is intentionally one-way: a renderer may consume a resolved manifest, but the manifest cannot call back into the renderer, route layer, database, or socket layer.

## Contract v1

Manifests are JSON because the format is straightforward to validate, matches the useful `sheet.json` convention found in Roll20’s public repository, and avoids adding a parser or executable configuration language.

### Top-level shape

```json
{
  "contract_version": 1,
  "system_id": "roll-drauf-light",
  "module_version": "0.1.0",
  "display": {
    "name_key": "sheet.roll_drauf_light.name",
    "description_key": "sheet.roll_drauf_light.description"
  },
  "i18n": {
    "default_locale": "de",
    "namespace": "sheet.roll_drauf_light",
    "required_keys": []
  },
  "data": {
    "schema_version": 1,
    "namespace": "roll_drauf_light",
    "attributes": [],
    "computed": []
  },
  "actions": [],
  "compatibility": {
    "runtime_capabilities": ["sheet_surface.v1", "action_refs.v1"],
    "migration_ids": []
  }
}
```

Required invariants:

- `contract_version` is the manifest contract version, not the character-data version.
- `system_id` is stable and unique. It is an identifier, not a user-controlled import path.
- `module_version` uses semantic-version syntax and changes when the module’s declarations change.
- `data.schema_version` changes when persisted meaning or binding compatibility changes.
- `data.namespace` is logical and adapter-owned. A manifest cannot name a SQL table, ORM field path, filesystem path, or arbitrary JSON path.
- IDs and action codes are unique within the manifest and match `^[a-z][a-z0-9_]{1,63}$`.
- Unknown top-level properties are rejected in v1 so a future contract cannot be silently misread by an older runtime.

### Attribute declarations

An attribute declaration has this shape:

```json
{
  "id": "name",
  "type": "string",
  "label_key": "sheet.roll_drauf_light.name.label",
  "binding": {
    "kind": "core",
    "key": "name"
  },
  "read": ["owner", "campaign_operator"],
  "write": ["owner", "campaign_operator"],
  "required": true
}
```

Supported v1 `type` values are `string`, `integer`, `number`, `boolean`, `enum`, `string_list`, and `object`. `enum` requires a finite list of values declared by data, not code.

Supported v1 binding kinds are:

- `core`: a stable adapter key for an existing `Character` field;
- `system_namespace`: a stable key inside the manifest’s logical system namespace; and
- `derived`: reserved for a computed declaration and not writable.

`read` and `write` use the manifest’s capability vocabulary:

- `public`: visible without a character relationship, subject to the host surface’s normal access rules;
- `campaign_member`: visible to a member of the campaign when the host surface permits it;
- `owner`: the authenticated user owns the relevant character or token;
- `campaign_operator`: the existing DM/CO_DM campaign operator boundary; and
- `none`: the capability is unavailable.

These values describe intended surface behavior. They never grant permission. The permission service must independently verify the current user, campaign, session, token, and resource relationship before returning or mutating a value.

The manifest may declare `write: ["owner", "campaign_operator"]`, but it may not declare `write: ["platform_admin"]` as a shortcut around campaign ownership. Platform roles remain a separate policy input.

### Computed declarations

Computed values are references to a small server-side resolver allowlist:

```json
{
  "id": "strength_modifier",
  "type": "integer",
  "label_key": "sheet.roll_drauf_light.strength_modifier.label",
  "resolver_id": "ability_modifier",
  "arguments": {
    "ability": "strength"
  },
  "read": ["owner", "campaign_operator"]
}
```

`resolver_id` is data, not a function name that can be imported or evaluated. v1 permits `ability_modifier` only. A future resolver must be registered in application code and covered by its own contract tests before a manifest may reference it.

### Action references

An action declaration is a UI and validation description for an existing server action:

```json
{
  "code": "attack_basic",
  "label_key": "action.attack_basic.label",
  "description_key": "action.attack_basic.description",
  "category": "combat",
  "target": "required",
  "payload_schema": {
    "type": "object",
    "properties": {
      "advantage": { "type": "boolean" },
      "disadvantage": { "type": "boolean" }
    },
    "additionalProperties": false
  },
  "roll_preset": "basic_attack",
  "invoke": ["owner", "campaign_operator"]
}
```

The v1 action vocabulary is:

- `target`: `none`, `optional`, or `required`;
- `category`: `combat`, `movement`, `interaction`, or `other`;
- `roll_preset`: an optional identifier resolved by a server allowlist, never an arbitrary dice formula; and
- `invoke`: the intended capability scope, enforced by the existing action route.

The validator must reject an action whose `code` is not present in the server action registry. This preserves the current behavior boundary: adding JSON cannot add executable behavior. The current `requires_target` and `suggested_roll` values can be adapted into this shape without changing `execute_action` in the Apply phase.

### Localization

All user-facing manifest text is addressed by `*_key` values. The manifest’s `i18n.required_keys` must include every display, attribute, computed-value, and action label/description key it references.

Resolution rules:

1. The default locale must resolve every required key through the existing content system.
2. A requested locale may override individual keys.
3. Missing requested-locale keys fall back to the default locale.
4. Missing default-locale keys invalidate the manifest; raw keys are not an acceptable production fallback.
5. Placeholder names, if the content system supports them, must match across locales.

This keeps the manifest compatible with the current PageContent/content-defaults path and avoids creating a second translation authority.

### Compatibility and migration

`contract_version`, `module_version`, and `data.schema_version` have distinct meanings:

| Version | Owner | Change means |
| --- | --- | --- |
| `contract_version` | Sheet Manifest Module | The JSON interface or validation rules changed. Unsupported versions fail closed. |
| `module_version` | System module author | Sheet/action declarations or copy-key usage changed without necessarily changing stored meaning. |
| `data.schema_version` | System adapter | Stored character data meaning or binding compatibility changed. |

`compatibility.migration_ids` contains names of approved application migrations only. It cannot contain code, source text, or a dynamically evaluated transformation. If a data-schema change needs a migration, Deploy must provide the migration in application code, test it against exported/imported characters, and update the adapter version deliberately.

Unknown persisted attributes are preserved by the existing character-data layer but are not surfaced or mutated by a manifest until explicitly declared. A manifest update must not silently delete data.

## Reference manifest for the current VTT

This is a contract example, not an executable registration. It describes only the three actions that already exist in `vtt/play/actions.py` and a small set of current character values.

```json
{
  "contract_version": 1,
  "system_id": "roll-drauf-light",
  "module_version": "0.1.0",
  "display": {
    "name_key": "sheet.roll_drauf_light.name",
    "description_key": "sheet.roll_drauf_light.description"
  },
  "i18n": {
    "default_locale": "de",
    "namespace": "sheet.roll_drauf_light",
    "required_keys": [
      "sheet.roll_drauf_light.name",
      "sheet.roll_drauf_light.description",
      "sheet.roll_drauf_light.name.label",
      "sheet.roll_drauf_light.species.label",
      "sheet.roll_drauf_light.class.label",
      "sheet.roll_drauf_light.level.label",
      "sheet.roll_drauf_light.skills.label",
      "sheet.roll_drauf_light.strength_modifier.label",
      "action.attack_basic.label",
      "action.attack_basic.description",
      "action.dash_move.label",
      "action.dash_move.description",
      "action.interact_object.label",
      "action.interact_object.description"
    ]
  },
  "data": {
    "schema_version": 1,
    "namespace": "roll_drauf_light",
    "attributes": [
      {
        "id": "name",
        "type": "string",
        "label_key": "sheet.roll_drauf_light.name.label",
        "binding": { "kind": "core", "key": "name" },
        "read": ["owner", "campaign_operator"],
        "write": ["owner", "campaign_operator"],
        "required": true
      },
      {
        "id": "species",
        "type": "string",
        "label_key": "sheet.roll_drauf_light.species.label",
        "binding": { "kind": "core", "key": "race" },
        "read": ["owner", "campaign_operator"],
        "write": ["owner", "campaign_operator"],
        "required": false
      },
      {
        "id": "class",
        "type": "string",
        "label_key": "sheet.roll_drauf_light.class.label",
        "binding": { "kind": "core", "key": "class_name" },
        "read": ["owner", "campaign_operator"],
        "write": ["owner", "campaign_operator"],
        "required": false
      },
      {
        "id": "level",
        "type": "integer",
        "label_key": "sheet.roll_drauf_light.level.label",
        "binding": { "kind": "core", "key": "level" },
        "read": ["owner", "campaign_operator"],
        "write": ["campaign_operator"],
        "required": true
      },
      {
        "id": "skills",
        "type": "string_list",
        "label_key": "sheet.roll_drauf_light.skills.label",
        "binding": { "kind": "system_namespace", "key": "skills" },
        "read": ["owner", "campaign_operator"],
        "write": ["owner", "campaign_operator"],
        "required": false
      }
    ],
    "computed": [
      {
        "id": "strength_modifier",
        "type": "integer",
        "label_key": "sheet.roll_drauf_light.strength_modifier.label",
        "resolver_id": "ability_modifier",
        "arguments": { "ability": "strength" },
        "read": ["owner", "campaign_operator"]
      }
    ]
  },
  "actions": [
    {
      "code": "attack_basic",
      "label_key": "action.attack_basic.label",
      "description_key": "action.attack_basic.description",
      "category": "combat",
      "target": "required",
      "payload_schema": {
        "type": "object",
        "properties": {
          "advantage": { "type": "boolean" },
          "disadvantage": { "type": "boolean" }
        },
        "additionalProperties": false
      },
      "roll_preset": "basic_attack",
      "invoke": ["owner", "campaign_operator"]
    },
    {
      "code": "dash_move",
      "label_key": "action.dash_move.label",
      "description_key": "action.dash_move.description",
      "category": "movement",
      "target": "none",
      "payload_schema": {
        "type": "object",
        "properties": {
          "distance": { "type": "number", "minimum": 0 }
        },
        "additionalProperties": false
      },
      "invoke": ["owner", "campaign_operator"]
    },
    {
      "code": "interact_object",
      "label_key": "action.interact_object.label",
      "description_key": "action.interact_object.description",
      "category": "interaction",
      "target": "optional",
      "payload_schema": {
        "type": "object",
        "properties": {
          "object_id": { "type": "string" }
        },
        "additionalProperties": false
      },
      "invoke": ["owner", "campaign_operator"]
    }
  ],
  "compatibility": {
    "runtime_capabilities": ["sheet_surface.v1", "action_refs.v1"],
    "migration_ids": []
  }
}
```

The `skills` binding is intentionally logical. The existing character serializer can map it to the system namespace in `character_data`; the manifest must not know the current JSON storage layout. Likewise, `basic_attack` is a preset reference, not a new dice expression.

## Ownership and adapters

| Concern | Owning module | Manifest relationship |
| --- | --- | --- |
| Sheet shape and labels | Sheet Manifest Module / system module | Declares fields, keys, and categories. |
| Character storage mapping | System adapter around the character model | Resolves `core` and `system_namespace` bindings; owns migrations. |
| Action semantics | Server action registry and `execute_action` | Validates referenced codes and executes behavior. |
| Authorization | Existing permission service and play route | Enforces user, campaign, session, role, ownership, visibility, and lifecycle checks. |
| Copy and translations | PageContent/content defaults | Resolves required message keys and locale fallback. |
| Client rendering | Future sheet/action renderer | Reads a resolved manifest; never evaluates manifest content. |
| Realtime state | Existing state serializer/socket layer | Continues role-scoped snapshots and sequenced events. |

The principal adapter seam is between the logical manifest bindings and the current `Character` representation. This keeps the manifest stable if `character_data` is normalized later, and it prevents a sheet author from coupling to SQLAlchemy or the socket protocol.

## Validation and security rules

Registration or resolution must fail closed when any of these conditions occurs:

- unsupported `contract_version` or incompatible runtime capability;
- duplicate field, computed-value, or action IDs;
- unknown binding kind, core key, resolver ID, roll preset, or action code;
- malformed or over-broad payload schema;
- missing required default-locale content key;
- mismatched locale placeholders;
- an action declaration that tries to provide executable text, an import path, a URL, a macro, or an arbitrary formula;
- a migration entry that is not an approved migration ID; or
- a manifest that attempts to name a database, filesystem, user account, or platform-role bypass.

Manifests are repository-managed in the first Deploy slice. There is no user upload, marketplace, remote fetch, plugin VM, DOM access, or script execution in this design. The Roll20 repositories are used as architectural references only; their code, assets, sheet templates, and rules content are not copied.

## Tradeoffs

| Choice | Benefit | Cost accepted |
| --- | --- | --- |
| JSON declarations | Easy to inspect, validate, diff, and version | Less expressive than a scriptable sheet system |
| Allowlisted action references | Preserves current auth, determinism, and auditability | New actions require application code and review |
| Logical bindings | Decouples sheets from persistence layout | Requires a system adapter for each supported data shape |
| Content keys instead of inline copy | Reuses the existing editable German-first content path | A manifest is not self-contained without content registration |
| Explicit version separation | Makes contract, module, and data changes reviewable | Authors must update the correct version deliberately |
| No generic formula language in v1 | Avoids an unsafe and ambiguous execution surface | More advanced rules need dedicated server resolvers later |

## Acceptance criteria for Deploy

The following are the handoff criteria for a later implementation phase:

1. A schema/validator accepts the reference manifest and rejects malformed, unknown, executable, or incompatible declarations.
2. The registry exposes one read-only resolve seam and returns no partially validated manifest.
3. The Roll-Drauf Light adapter resolves the declared core fields and system-namespace fields without exposing raw persistence paths.
4. Every action reference is checked against the existing action registry; an unknown code cannot become executable through JSON.
5. Locale resolution uses the existing content system, requires complete default-locale keys, and falls back per key for a requested locale.
6. Authorization tests prove that manifest declarations do not allow a player to invoke an action on a foreign token or bypass read-only/session checks.
7. Existing action-bar, character export/import, playtable, realtime sequence, and public-surface tests remain green.
8. No database migration, character-data rewrite, socket-event change, custom script runtime, drag/drop system, macro engine, marketplace, or arbitrary user-uploaded manifest support is included in the first implementation.

## Planned Deploy artifacts

The next phase may create these artifacts, subject to explicit Deploy approval:

- `vtt/sheets/` module containing the registry, contract types, validator, and Roll-Drauf Light adapter;
- a repository-managed `roll-drauf-light` v1 JSON manifest;
- contract tests for validation, locale fallback, logical bindings, unknown action rejection, and fail-closed behavior; and
- an optional later bootstrap read path that exposes the resolved manifest to the client without changing action execution.

The first Deploy slice should register and validate the manifest before changing the UI. Rendering and bootstrap exposure are separate seams so a contract failure cannot silently alter the live playtable.

## Explicit handoff

Apply is complete when this document is accepted as the solution design. No runtime implementation is included here. Deploy must confirm the manifest field vocabulary, the exact content-key registration, and the adapter mapping before editing application code.
