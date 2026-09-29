# Guided class, race and spell creation

## Discover

Status: completed. The user asked to continue Guided after deploying Advanced,
and clarified that the hosted VTT is the shared development environment.
The existing editor already supplies dependency-ordered questions, immutable
revisions, dirty/conflict/retry/access handling and three display modes. Its type
selector omits the three executable homebrew types; nested mechanics currently
need JSON rather than guided fields. The Advanced studio and private test API
already handle the complete author-to-execution path.

## Apply and implementation handoff

Extend the existing editor with the three registered mechanical profiles and a
schema-driven form component for their Guided and Structured modes. Reuse the
server's question schemas and A1 decisions; no new API, schema registration,
content defaults or mechanics. Preserve all existing item/manual/race controls.

Nested forms support objects, optional fields, bounded arrays, enum/boolean and
numeric/text values, and explicit one-of selections. Class levels, features,
grants, choices, resource costs, spell resolution/effects and scaling are editable
without JSON. Missing values remain missing; choosing no entries or no optional
modifiers is explicit. A selected variant may supply its constant discriminator
because that exact choice was made by the author. Branches retain local input
while switching; only the selected branch is submitted.

Guided progress shows required answers and offers review of prior ready answers;
the server selects the next unresolved question. Changes continue to invalidate
dependent answers. Plain-language previews display nested mechanics. Completed
executable revisions link to the Advanced private test bench, using the same
saved workspace and revisions. Advanced document editing remains available.

Medium risks: accidental inferred values are handled by explicit empty/variant
choices and exact typed reads; nested input loss by retained branch input and the
existing dirty/retry/conflict controls; schema drift by server-owned schemas and
authoritative validation; legacy regression by limiting the new component to the
three mechanical profiles. No dependency or backend architecture changes.

Acceptance: real browser creation of class/race/spell revisions through fields,
canonical equality with explicit authored fixtures, no JSON textareas in Guided,
nested add/remove and variant changes, unresolved-value validation, progress and
review, locale/mobile/keyboard checks, retained Advanced and existing editor
behavior. Retain implementation hashes, screenshots and test logs in the task
workspace's `guided-evidence/`. Human study and broader runtime rules remain open.

## Implementation and automated Monitor evidence

Guided and Structured now expose all three mechanical profiles. A shared nested
form renders server-owned object/array/enum/boolean/variant schemas, with explicit
empty lists and optional modifiers. The current question still saves through A1;
all dependent invalidation, draft versions, revision pins and ownership remain
server-controlled. No new backend API, migration or dependency was introduced.
Progress, review controls, readable nested previews and localized readiness
messages lead into the existing Advanced test bench.

The final five Guided browser cases pass on the final implementation: complete
class/race/spell creation and revision handoff, explicit missing values and locale
changes, full nested conflict restoration with exact lost-response retry,
array removal/empty lists, and access-loss clearing of input/progress. Their
documents equal the explicitly authored fixtures, including an empty description.
Desktop/mobile screenshots were inspected at 1280px and 390px.

The combined runner passed 59 checks before the final access-loss case was added;
the final five-case Guided run then passed. This establishes 60 focused cases and
53 additional existing editor/access/design/race regressions: **113 distinct
passing cases**. The first combined regression had six Advanced locator errors
because a new handoff link made its broad link selector ambiguous. The test now
selects the navigation link explicitly; all six Advanced browser journeys pass
in the combined runner. No application workaround was needed for those errors.
Node syntax and diff whitespace checks passed. SQLAlchemy's existing relationship
warnings remain visible in the retained logs.

Reproduce the complete focused set with:

```sh
venv/bin/python tools/ce_homebrew_check.py --guided
```

The runner owns an isolated PostgreSQL container and requires installed Playwright
Chromium. The final Guided checks used another owned disposable database. This
is Chromium automation evidence, not human acceptance or assistive-technology
coverage. The renderer is scoped to the currently registered mechanical schemas;
it is not a general JSON Schema form implementation for arbitrary external schemas.

## Shared development rollout

The user's deploy-and-continue instruction and shared-development clarification
authorize publishing this verified follow-up on the same hosted VTT. Use the
app-only, exact-image procedure from the Advanced release; retain the Advanced
image as `roll-drauf-vtt-app:rollback-guided-20260929` and take a fresh protected
database backup. Authoring/adapter remain enabled and runtime/shadow remain off.
No further live migration is needed. Repeat the default-command startup check,
operational image tests, source/asset identity checks and unchanged release gate.
The executed result is retained in the task workspace's
`guided-deployment-2026-09-29/release-result.json`.
