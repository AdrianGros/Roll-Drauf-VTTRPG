# FV01 species labels: Deploy and Monitor

Status: implementation and targeted verification in progress; not yet delivered. Permanent. Contract: [completed Apply](DADM_APPLY_FV01_SPECIES_LABELS_2026-11-24.md). Canonical full version remains in progress, with independent FV15 implementation assigned to Claude.

## Implementation

Adds73 reviewed/source-pinned labels (41 trait slots,24 ancestry/lineage option names,2 sizes,1 creature type,5 damage types) to the existing overlay, for847 entity identities/147 terms. Compiler validates exact canonical coverage and genuine source quotes;64 source hashes and canonical creator data remain unchanged. Preserves the real parsed Fiendish Legacies anchor under Human and Halfling's Luck heading. Species helpers leave authored homebrew literal. Existing card, summary, trait and native selects display localized labels while values remain canonical. Darkvision's authored fragment is cataloged; the six existing German option descriptions remain German with truthful fallback notice/lang. No rules mechanics, schema, authorization, dependencies or artwork changes. No generative use of any image.

User journey: authenticated dashboard → Characters → Create character → guided steps → Origin/species; valid for DM and Player. Existing display settings select independent rules language. Labels/selections must survive language switch and reload without altering data/state/evaluation/draft version. Broader option descriptions, structured findings and sheet/editor language remain FV01 work.

## Verification and delivery evidence

22 targeted cases pass:7 source/compiler/API/new species/browser cases in182.66s and15 equipment/pending-input/source/overlay/dialog/subclass regressions in416.77s. Only existing mapper warnings were emitted. Both generators are fresh (847 identities/147 terms;3843 UI sources), changed JS/proof scripts parse, canonical model/64 pins remain unchanged and diff whitespace passes. No full-suite claim. Commit/push, image/source baseline checks, DB archive, protected rollback, app-only release, normal DM1440/Player390 mixed-language journeys and scoped QA cleanup remain pending.
