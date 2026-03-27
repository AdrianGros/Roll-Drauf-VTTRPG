# DAD-M Programmplan: Multi-Tenant Scale, Asset Management, Owner Governance (20 Meilensteine)

```
artifact: planning-output
program: vtt-scale-multitenant
method: DAD-M
status: draft-ready
date: 2026-03-27
```

---

## Zielbild

- Viele DMs mit vielen Kampagnen und Sessions stabil betreiben.
- Skalierbares File-Management fuer Maps, Tokens, Handouts und Session-Artefakte.
- Klare Owner/Admin-Faehigkeiten fuer Account-/Profil-/Rollen-/Loeschprozesse.
- Tiefe Discovery je Meilenstein vor Implementierung.

---

## DAD-M Leitlinie pro Meilenstein

- Discover: Ist-Analyse, Risiken, offene Fragen, klare Scope-Grenzen.
- Apply: Architektur-/Daten-/API-Entscheidungen mit Akzeptanzkriterien.
- Deploy: inkrementelle Lieferung mit Migrationspfad und Rollout-Strategie.
- Monitor: Metriken, Betriebsnachweis, Regression, Go/No-Go.

---

## 20 Meilensteine (M17-M36)

### M17: Tenant and Ownership Domain Discovery
- Discover: Plattformrollen (`owner/admin/support`) vs. Kampagnenrollen (`dm/co_dm/player`) inventarisieren, Konflikte und Edge-Cases dokumentieren.
- Apply: finale Rollenmatrix inkl. Permissions/Denied-Paths und Eskalationsregeln.
- Deploy: zentrale Permission-Library + Basis-Guards in API.
- Monitor: Autorisierungs-Tests + Audit-Log-Abdeckung.

### M18: Account Lifecycle and Profile Governance
- Discover: Anforderungen fuer Deaktivieren, Soft-Delete, Hard-Delete, Ownership-Transfer.
- Apply: User-Lifecycle-State-Machine + Loesch-/Anonymisierungsrichtlinie.
- Deploy: Admin-Endpoints fuer Profilverwaltung, Sperre, Transfer, Loeschantrag.
- Monitor: Recovery-/Rollback-Nachweis bei Fehlbedienung.

### M19: Asset Domain Deep Discovery
- Discover: Asset-Typen, Ownership-Modelle, Kampagnenbindung, Referenzbeziehungen, Retention.
- Apply: Asset-Metadatenmodell inkl. Checksums, Version, Scope, Referenzgraph.
- Deploy: `assets` Kernmodell und Referenzpfade.
- Monitor: Integritaets- und Referential-Consistency-Checks.

### M20: Upload Security Pipeline
- Discover: Threat-Modell fuer Uploads (MIME-Spoofing, oversized files, abuse patterns).
- Apply: Validierungs- und Quarantaene-Strategie inkl. Limits und Content-Typen.
- Deploy: Upload-Guardrails (MIME-Whitelist, Size Caps, Filename Safety, optional AV Hook).
- Monitor: Security-Metriken, Rejection-Rate, Abuse-Detektion.

### M21: Storage Abstraction (Local -> Object Storage)
- Discover: Betriebsziele fuer S3-kompatiblen Storage, Portabilitaet, Lock-in-Risiko.
- Apply: Storage-Adapter-Interface (local, S3) + Konfigurationsmodell.
- Deploy: produktionsfaehiger Object-Storage-Adapter mit Fallback.
- Monitor: Latenz-/Fehler-/Retry-Metriken pro Provider.

### M22: Asset Serving and Access Control
- Discover: Downloadmuster, Caching, signed URL vs. gated content API.
- Apply: Zugriffskonzept je Asset-Scope und Rolle.
- Deploy: autorisierte Content-Delivery-Route + optional presigned flow.
- Monitor: Unauthorized-Access-Rate, Cache-Hit-Ratio.

### M23: Campaign Workspace UX (Maps/Tokens/Handouts)
- Discover: DM-Workflow-Mapping fuer Upload, Bibliothek, Zuweisung, Archiv.
- Apply: UX-Flows fuer Asset-Auswahl, Replace, Version-Hinweise.
- Deploy: Campaign-UI fuer Asset-Management.
- Monitor: Task-Completion-Time und Fehlklickrate.

### M24: Session Workspace UX (Live Runtime)
- Discover: Session-spezifische Asset-Bedarfe (aktiver Layer, Token-Skins, schnelle Wechsel).
- Apply: Operator-Cockpit-Interaktionen mit minimalem Klickpfad.
- Deploy: Play-UI Integration fuer live Asset-Wechsel.
- Monitor: Live-Session-Stabilitaet bei Asset-Wechsel unter Last.

### M25: Realtime Asset Sync Contracts
- Discover: Event-Sequencing fuer Asset-Aenderungen und Rejoin/ReSync.
- Apply: Socket-Contracts fuer asset-created/updated/deleted + Snapshot-Konsistenz.
- Deploy: Realtime-Propagation in Session-Raeumen.
- Monitor: Out-of-order- und Conflict-Rate.

### M26: Quotas, Billing Signals, Fair Use
- Discover: sinnvolle Quotas pro User, DM, Kampagne, Tenant.
- Apply: Quota-Policy + Eskalationspfade (Warnung, Block, Grace).
- Deploy: Enforcement + Usage-Endpoints.
- Monitor: Quota-Verletzungen, Top-Consumers, Storage-Wachstum.

### M27: Background Jobs and Async Processing
- Discover: asynchrone Aufgaben (thumbnailing, transcoding, cleanup, scan).
- Apply: Job-Architektur (queue, retries, idempotency, dead-letter).
- Deploy: Worker-Subsystem + initiale Job-Typen.
- Monitor: Queue-Lag, Retry-Rate, Erfolgsquote.

### M28: Data Retention and Legal Boundaries
- Discover: Datenaufbewahrung, Loeschfristen, Moderations- und Audit-Daten.
- Apply: Retention-Policies pro Datentyp mit Human-Decision-Punkten.
- Deploy: automatische Retention-Jobs + Policy-Config.
- Monitor: Retention-Compliance-Reports.

### M29: Backup, Restore, Tenant-Selective Recovery
- Discover: Recovery-Szenarien (global vs. tenant-scoped).
- Apply: RPO/RTO-Ziele und Wiederherstellungsprozeduren.
- Deploy: Tenant-Selective-Restore fuer Assets + Metadaten.
- Monitor: regelmaessige Restore-Drills mit Evidenz.

### M30: Admin Console v1
- Discover: Operator/Support-Bedarfe fuer Nutzer, Rollen, Kampagnen, Assets.
- Apply: Admin-Informationsarchitektur + kritische Aktionen mit Guardrails.
- Deploy: Admin-Konsole fuer Suche, Filter, Sperren, Transfers.
- Monitor: Admin-Action-Audit und Vier-Augen-Logs bei High-Risk-Aktionen.

### M31: Observability for Multi-Tenant Operations
- Discover: fehlende SLOs und tenantbezogene Telemetrie-Luecken.
- Apply: Metrikmodell (per tenant/campaign/session) + Alerting-Design.
- Deploy: Dashboards + Alerts + strukturierte Korrelation.
- Monitor: SLO-Compliance und Alarmqualitaet.

### M32: Performance and Cost Optimization
- Discover: Hot Paths in Upload, Asset-Serve, Session-Bootstrap.
- Apply: Caching-, Compression-, CDN- und DB-Index-Strategie.
- Deploy: Optimierungen mit kontrolliertem Rollout.
- Monitor: p95/p99, Egress-Kosten, DB-Last.

### M33: Multi-Region Readiness (Optionality)
- Discover: Bedarf und Risiken fuer geo-verteilte Nutzung.
- Apply: Architekturpfad fuer region-aware storage/session routing.
- Deploy: vorbereitende Entkopplungen (stateless services, region tags).
- Monitor: Latenzvergleich und Failover-Simulation.

### M34: Compliance, Security Hardening, and Audit Readiness
- Discover: Security-Gaps, Policy-Luecken, Audit-Anforderungen.
- Apply: Hardening-Plan (secrets, encryption, key rotation, least privilege).
- Deploy: Security Controls + Pen-Test Remediation.
- Monitor: Security-Gate Evidence + periodische Reviews.

### M35: Migration and Backward Compatibility Closure
- Discover: verbleibende Legacy-Pfade (`background_url`, `token_url`, alte APIs).
- Apply: Migrationsstrategie mit klarer Sunset-Timeline.
- Deploy: Dual-Read/Single-Write Cutover + Sunset-Flags.
- Monitor: Legacy-Usage-Drop, Error-Budget vor Abschaltung.

### M36: Release Certification and Operating Playbook v2
- Discover: finale Go-Live Risiken, offene Betriebsluecken.
- Apply: Zertifizierungs-Checkliste fuer Scale-Readiness.
- Deploy: finaler Rollout + Playbook v2 + Incident-Routinen.
- Monitor: End-to-End Rehearsal, Go/No-Go Nachweis, Post-Launch Review.

---

## Programmweite Discovery-Schwerpunkte (tief)

- Domaenen-Grenzen: Nutzer, Kampagne, Session, Asset, Moderation, Audit.
- Permission-Ebenen: Plattform vs. Kampagne.
- Datenfluesse: Upload -> Persistenz -> Referenzierung -> Serving -> Retention.
- Failure-Szenarien: Konflikte, Rollback, Restore, Ownership-Verlust.
- Betriebsrealitaet: Kosten, Lastspitzen, Abuse, Support-Prozesse.

---

## Exit-Kriterien fuer das 20-Meilenstein-Programm

- Rollen- und Owner-Modell vollstaendig durchgaengig in API, UI, Ops und Audit.
- Asset-Management vollstaendig tenant-sicher und skalierbar.
- Session-Workspace unterstuetzt produktiv viele parallele DMs/Kampagnen.
- Wiederherstellung, Loeschung und Governance sind reproduzierbar nachweisbar.
- Release-Gates bestehen unter realistischen Last- und Failover-Bedingungen.

