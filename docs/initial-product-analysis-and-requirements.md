# PythonDepot Next-Version Product Analysis and Software Requirements

**Source reviewed:** `ZipPrompt.md`, treated as a flattened ZIP/archive listing of the PythonDepot v0.6.0 application, including application code, routes, domain modules, UI rendering, tests, documentation, examples, deployment configuration, and changelog.

**Analysis method:** Static product, UX, workflow, requirements, and implementation-readiness review. No live application session, production telemetry, or user interviews were supplied. Statements marked **Inference** are therefore hypotheses to validate, not established facts.

**Review date:** 2026-08-01

---

## Executive summary

PythonDepot has evolved from a curated Python package catalog into a broad dependency decision and governance platform. It combines package discovery, vulnerability intelligence, package comparison, provenance, portfolio risk triage, Python upgrade planning, evidence-backed reviews, SBOM policy evaluation, and a separate command-line assistant for migrating projects to `uv`.

The strongest product idea is not any single feature. It is the potential to create one continuous workflow from **discover → evaluate → approve → adopt → monitor → remediate or migrate**. The current implementation does not yet deliver that continuous experience. It exposes multiple useful but weakly connected products: an older security dashboard, six governance workspaces, API-oriented catalog/review/report features, and a CLI migration assistant. Users must re-enter package or project context, interpret inconsistent trust and health signals, and bridge gaps manually.

The next version should therefore prioritize coherence and workflow completion rather than adding another isolated module. The first release theme should be **“From signal to action”**: a unified package/project workspace, persistent project import, actionable risk triage, trustworthy evidence and freshness labeling, and reliable end-to-end completion of currently partial actions. Authentication, authorization, tenant isolation, auditability, and production-grade persistence are release gates because the product already presents organization policy, moderation, decisions, waivers, and private catalogs.

---

# 1. Product understanding

## 1.1 What the application appears to do

PythonDepot is a Python dependency intelligence and governance product with four overlapping value propositions:

1. **Package discovery and assessment**
   - Search and inspect Python packages.
   - View metadata, popularity, trends, ratings, reviews, vulnerability status, and a composite health score.
   - Compare candidate packages and record a defensible decision.

2. **Dependency security and operational monitoring**
   - Scan packages using OSV.dev and a legacy Safety CLI path.
   - Calculate CVSS severity and aggregate package health.
   - Surface portfolio risk changes and vulnerability alerts.
   - Deliver webhooks and maintain scan/alert history.

3. **Engineering modernization and migration**
   - Detect package-manager compatibility.
   - Plan Python version upgrades and expose direct or transitive blockers.
   - Migrate pip, Poetry, pip-tools, or Pipenv projects to `uv` through a CLI that supports dry runs, lock conversion, CI/CD updates, batch mode, reports, and rollback guidance.

4. **Governance and organizational control**
   - Assess release provenance without claiming that provenance equals safety.
   - Evaluate SBOMs against license policy.
   - Manage expiring waivers and organization-scoped private catalogs.
   - Collect evidence-backed reviews and prevent conflicted moderation.
   - Create auditable package decisions with immutable evidence digests.

### Product maturity observation

The domain model is more advanced than the user journey. The application includes thoughtful concepts such as evidence age, immutable decision evidence, conflict-safe moderation, risk-delta deduplication, transitive blocker paths, and expiring waivers. However, several UI actions are rendered without demonstrated end-to-end handlers, some services return empty or placeholder results, and persistence is split between SQLAlchemy storage and separate SQLite files. The product is therefore best understood as a capable prototype or early MVP with strong domain experiments, not yet a unified production workflow.

## 1.2 Likely user segments

| Segment | Primary goal | Highest-value workflows | Main risk if unsupported |
|---|---|---|---|
| Application developer | Choose and adopt a dependency quickly and safely | Search, compare, package detail, install/migration guidance | Abandons the product for PyPI, GitHub, OSV, or manual research |
| Tech lead / architect | Standardize package and Python choices across projects | Decision workspace, upgrade planner, portfolio | Decisions remain undocumented and inconsistent |
| DevOps / platform engineer | Modernize dependency tooling and CI reproducibly | `uv` migration, CI/CD changes, batch operations, rollback | Avoids automation if changes are opaque or unsafe |
| Security engineer | Find, prioritize, assign, and verify dependency risk | Dashboard, risk inbox, scan details, alerts, remediation | Alert fatigue and duplicate manual triage |
| Compliance / policy administrator | Enforce license and supply-chain rules with evidence | SBOM policy console, waivers, provenance, audit history | Cannot safely use the product for approvals |
| Package maintainer | Understand package standing and respond to trust/review issues | Package page, provenance, reviews, moderation | Low trust in ratings or unfair moderation |
| Engineering manager | See portfolio exposure and modernization progress | Portfolio dashboards, reports, ownership, SLA status | Cannot turn data into accountable action |

**Inference:** The application currently serves expert technical users better than occasional users. Terms such as SBOM, CVSS, attestation, lock hash, build backend, and transitive blocker are presented with limited progressive guidance.

## 1.3 Main workflows and usage scenarios

### A. Package discovery and selection

1. Search for a package.
2. Open package metadata and health information.
3. Review vulnerability, trend, provenance, license, and community evidence.
4. Add two or more packages to a comparison workspace.
5. Record a selected package and rationale.

**Observed discontinuity:** Search, security dashboard, product comparison, trust, and review services exist, but no single package workspace demonstrably connects them or preserves selected candidates across screens.

### B. Dependency risk monitoring

1. Register or import packages/projects.
2. Trigger or schedule scans.
3. Review overview and trend charts.
4. Open alerts or changed portfolio risks.
5. Acknowledge, assign, snooze, resolve, or reopen an item.
6. Verify remediation with a fresh scan.

**Observed discontinuity:** State transitions exist, but ownership, due dates, notes, bulk actions, transition history, remediation guidance, and verification rules are incomplete or absent.

### C. Python upgrade planning

1. Choose a target Python version.
2. Supply dependency metadata.
3. Analyze compatibility.
4. Inspect direct and transitive blockers.
5. Follow an ordered plan.
6. Validate the upgraded project.

**Observed discontinuity:** The UI asks users to paste dependency JSON even though the product already understands lockfiles, project structures, and dependency formats elsewhere. This creates unnecessary expert-only work.

### D. Migration to `uv`

1. Scan one or more local projects.
2. Detect dependency formats and compatibility issues.
3. Preview lockfile and CI/CD changes.
4. Apply changes or generate a report only.
5. Run validation and use rollback guidance if needed.

**Observed discontinuity:** This is CLI-only and appears separate from the web product’s project, policy, security, and upgrade contexts. Migration outcomes do not visibly become monitored portfolios or auditable decisions.

### E. Policy evaluation and waiver handling

1. Define denied license rules.
2. Upload or supply an SBOM.
3. Run a dry-run evaluation.
4. Inspect violations and waived items.
5. Request, approve, expire, or revoke a waiver.
6. export evidence for audit or CI gating.

**Observed discontinuity:** The UI describes a waiver queue but the reviewed implementation shows evaluation more clearly than a complete request/approval lifecycle.

### F. Evidence-backed review and moderation

1. Submit package experience with a lock evidence hash.
2. Preview the review.
3. Publish as a verified user.
4. Moderate, while preventing self-promotion or package-owner conflicts.
5. Preserve append-only moderation events.

**Observed discontinuity:** Requiring users to manually know and enter a lock hash is high friction. The UI hides unsafe actions, which is good, but does not explain why an action is unavailable or expose an audit trail clearly.

### G. Reporting

1. Generate a monthly report.
2. View top-rated, healthiest, and most-reviewed packages.
3. Retrieve HTML or JSON.
4. List historical reports.

**Observed discontinuity:** Report generation exists, while `list_reports()` and `get_report()` are explicitly incomplete in the reviewed service, preventing a dependable report-library workflow.

---

# 2. UI/UX analysis

## 2.1 Strengths

1. **Task-oriented workspace names.** “Compare packages,” “Risk inbox,” and “Python upgrade planner” communicate user intent better than purely technical module labels.
2. **One primary task per screen.** The product UI deliberately centers each workspace on one main action.
3. **Explicit empty and recovery states.** Empty, success, warning, failure, and retry concepts are built into the UI rather than left for later.
4. **Accessibility foundations.** Skip links, landmarks, labels, keyboard-friendly forms, live regions, responsive layouts, escaped user content, and mobile-specific behavior are present.
5. **Responsible trust language.** The provenance screen explicitly distinguishes verified origin from software safety, reducing a dangerous interpretation error.
6. **Permission-aware action removal.** Review moderation suppresses conflicted actions and organization policy endpoints include tenant-oriented controls.
7. **Dry-run and rollback philosophy.** The migration assistant treats preview and recovery as core product behavior, which aligns strongly with user expectations for code-changing automation.
8. **Risk-delta approach.** Showing changed risk rather than repeatedly surfacing every known issue can reduce alert fatigue if carried consistently into the UI.

## 2.2 Weaknesses

1. **Fragmented information architecture.** A legacy security dashboard and six governance workspaces coexist, while catalog, ratings, reports, ecosystem, and migration capabilities remain separate. The product lacks a clear global hierarchy such as Projects, Packages, Risks, Decisions, Policies, and Administration.
2. **No durable working context.** Users likely need to remain within a project, portfolio, package, or organization context. Current screens often start with a blank form or generic workspace.
3. **Data re-entry across workflows.** Package names, project information, dependency data, SBOMs, targets, and evidence are supplied repeatedly instead of being reused.
4. **Action labels without demonstrated completion.** “Refresh portfolio,” “Try again,” “Hide review,” “New policy rule,” “Run dry-run,” and other controls appear in HTML, but the archive does not consistently demonstrate complete form actions, confirmation, persistence, and resulting states.
5. **Technical input burden.** Pasted dependency JSON, manual evidence hashes, and raw license identifiers expect domain expertise and invite errors.
6. **Weak prioritization guidance.** Scores and severities are shown, but the product does not consistently tell the user what to do next, why it matters, who owns it, or whether a fix is available.
7. **Inconsistent freshness semantics.** A static “Evidence freshness: current” label is not sufficient. Each source can have a different observation time and failure mode.
8. **Mixed terminology and scoring.** Health score, CVSS severity, provenance status, policy outcome, risk severity, and review verification coexist without a shared explanation hierarchy.
9. **Limited discoverability between related screens.** There is no clearly observed contextual jump from a risk to package evidence, from a package to comparison, from an upgrade blocker to migration, or from a policy violation to a waiver.
10. **Form error and progress design is under-specified.** Long-running scans, batch migrations, imports, and evaluations need granular progress, cancellation, retry, partial-success, and resumability.

## 2.3 Confusing elements

- “Evidence freshness: current” appears globally even though OSV, PyPI, repository, attestation, scan, and policy data may be observed at different times.
- “Scan queued” may be returned even when the legacy scanner is unavailable, making queued, running, unavailable, failed, and completed states ambiguous.
- A package can be “verified origin” but still vulnerable or policy-prohibited. The product explains this on one screen, but users need the distinction everywhere.
- A “clean” scan can be misread as “safe” unless source, version, timestamp, coverage, and scan limitations are visible.
- “Healthiest” reports can rank unscanned packages too favorably if a zero vulnerability count is not clearly distinguished from verified clean status.
- Review states such as `VERIFIED_USER`, `HIDDEN`, `RESTORED`, and `REJECTED` are implementation-oriented and may not be suitable user-facing language.
- The product name and description still emphasize curated discovery while the current scope is governance and engineering workflow automation.

## 2.4 Friction points

| Friction | User impact | Severity |
|---|---|---|
| Paste dependency JSON in upgrade planner | Blocks non-experts and creates format errors | Critical |
| Manually enter lock evidence hash for reviews | High abandonment risk and unclear trust mechanism | High |
| Re-enter package/project context | Repetition and loss of orientation | High |
| Separate dashboard, workspaces, and CLI | Context switching and duplicated investigation | Critical |
| No visible alert owner/due date/notes/history | Triage does not become accountable work | Critical |
| Static or ambiguous data freshness | Users may make decisions from stale evidence | Critical |
| Incomplete report retrieval/history | Generated artifacts are not operationally useful | Medium |
| Generic migration guidance when scan data is absent | Creates false confidence and low actionability | High |
| No clear partial-success treatment for batch work | Difficult recovery for large portfolios | High |
| Limited filters and bulk operations | Daily security work becomes repetitive | High |

## 2.5 Navigation and workflow observations

A better navigation model would organize the product around stable user objects:

- **Home:** assigned risks, recent changes, pending approvals, running jobs.
- **Projects:** dependencies, Python targets, migration status, SBOM, policy, scans.
- **Packages:** discovery, package detail, compare, provenance, reviews.
- **Risks:** unified inbox, vulnerabilities, policy violations, expiring waivers.
- **Decisions:** comparison workspaces and approval records.
- **Policies:** rules, evaluations, waivers, audit exports.
- **Reports:** generated and scheduled reports.
- **Administration:** organizations, roles, integrations, data sources.

This structure turns the current six workspaces into contextual views rather than six unrelated destinations.

---

# 3. User behavior analysis

## 3.1 Likely user habits

The following are **inferences to validate with analytics and interviews**:

1. Developers search several packages rapidly, open a few familiar candidates, and prefer a concise answer before expanding evidence.
2. Security users begin with changed or critical items, filter by project/owner/severity, perform bulk acknowledgements, and return later to unresolved work.
3. Platform engineers run migrations first in dry-run mode, review diffs, apply to a small pilot, then batch the same operation across repositories.
4. Policy users repeatedly evaluate similar SBOMs against stable rules and care most about new violations, expiring waivers, and audit evidence.
5. Tech leads compare the same package dimensions repeatedly: maintenance, compatibility, security, license, provenance, adoption, migration cost, and evidence age.
6. Users copy package names, issue IDs, commands, and remediation notes into GitHub, Jira, Azure DevOps, Slack, or Teams.
7. Users revisit the product when receiving an alert, not necessarily through the home page. Deep links and preserved filters are therefore important.

## 3.2 Repeated actions

- Searching the same package across catalog, trust, vulnerability, and review contexts.
- Selecting project and organization context.
- Filtering risk lists by severity and state.
- Refreshing package or portfolio evidence.
- Copying install/migration commands.
- Creating or updating tickets for findings.
- Assigning and resolving related alerts one by one.
- Importing dependency files and SBOMs after each change.
- Re-running scans or policy evaluations to prove remediation.
- Explaining why a package was chosen or why a waiver was approved.

## 3.3 Likely pain points

1. **“I have data, but not a decision.”** Multiple signals do not resolve into a recommended next action or defensible summary.
2. **“I fixed it, but the product still shows it.”** Without explicit verification and freshness rules, remediation status may lag.
3. **“The score changed and I do not know why.”** Composite scores need transparent factor and change explanations.
4. **“I cannot tell whether this is new.”** Daily users need delta-first views and baseline comparisons.
5. **“I cannot complete the workflow here.”** Missing assignment, approval, ticket, export, or apply actions force tool switching.
6. **“The automation might damage my project.”** Migration users need file-level diffs, backups, test execution, rollback, and clear partial-failure semantics.
7. **“Why is this action missing?”** Permission-aware hiding should be paired with an explanation and a legitimate escalation path.
8. **“Which data should I trust?”** Users need source, time, scope, and uncertainty for each evidence item.

## 3.4 Usage bottlenecks

- Sequential ecosystem batch scans will become slow for real portfolios.
- External services can fail or time out, but the UI lacks a consistent degraded-data model.
- SQLite and process-local assumptions limit concurrent organization use.
- Separate databases and persistence layers can produce inconsistent state.
- Long-running work appears request-oriented instead of job-oriented.
- Missing authentication and role context make review, organization, waiver, and decision identity unreliable.
- The migration scanner contains skipped RED-phase tests, reducing confidence in a flagship workflow.

## 3.5 Expected but missing interactions

- Import a repository, lockfile, requirements file, or SBOM through upload or connected source.
- Save and reopen a project with its dependencies and scan history.
- See “what changed since last scan/evaluation.”
- Open a risk and view evidence, affected paths, fix versions, owner, SLA, notes, and history.
- Select many risks and assign, acknowledge, snooze, or export them.
- Create a Jira/Azure DevOps/GitHub issue from a risk.
- Compare packages directly from search results or a project dependency list.
- Apply a migration through a controlled job with diff preview and test results.
- Subscribe to a package/project and configure notification thresholds.
- Request, approve, revoke, and audit a waiver.
- Export a decision or policy result in human-readable and machine-readable formats.
- Understand why data is unavailable and retry only the failed source.

---

# 4. What should be improved

## 4.1 Critical improvements

1. **Unify the product around persistent Projects and Packages.** Every risk, policy result, upgrade plan, migration, decision, and report should reuse these objects.
2. **Complete end-to-end interactions.** Every visible control must have a defined handler, validation, progress, persistence, success, failure, and recovery state.
3. **Replace raw technical entry with guided import.** Support repository, file upload, lockfile, requirements, `pyproject.toml`, and SBOM import with preview and validation.
4. **Make the risk inbox operational.** Add owner, due date, notes, history, related findings, fix guidance, verification, bulk actions, saved filters, and deep links.
5. **Provide evidence-level freshness and confidence.** Show source, observed time, scope/version, last success, failure status, and refresh behavior.
6. **Add identity, roles, and auditable tenant isolation.** This is mandatory for moderation, private catalogs, policy, waivers, decisions, and assignments.
7. **Productionize persistence and background jobs.** Consolidate storage, support transactional updates, and run scans/imports/migrations as observable jobs.
8. **Finish or clearly gate incomplete modules.** In particular, remove placeholder behavior, implement report retrieval, eliminate scanner RED-phase gaps, and distinguish unscanned from clean.
9. **Connect the `uv` migration assistant to the web project lifecycle.** Dry-run reports, diffs, apply status, validation, and rollback should be accessible as project history.
10. **Define a shared status and terminology system.** Safety, provenance, policy, compatibility, and freshness must not collapse into one misleading score.

## 4.2 Medium-priority improvements

- Global search and command palette.
- Saved views, table column preferences, and filter persistence.
- Scheduled and incremental scans.
- Notification center and configurable routing.
- Ticketing and source-control integrations.
- Decision templates and reusable organization criteria.
- Visual transitive dependency paths and impact scope.
- Explainable score changes with before/after factors.
- Report scheduling, history, sharing, and export.
- Full moderation and waiver audit timeline.
- Guided policy rule builder with test cases.
- Concurrent batch scanning with rate limiting and partial retry.

## 4.3 Nice-to-have improvements

- Dark mode and density controls if not already consistently available.
- Keyboard command palette for expert users.
- Custom dashboard widgets.
- Public read-only package decision links.
- Organization-wide package recommendation lists.
- Natural-language summaries as a supplement to, never a replacement for, source evidence.

---

# 5. Requirements

## Prioritization method

- **Must have:** Required for a coherent, safe, repeatable core workflow or production use.
- **Should have:** High-value improvement that materially increases daily efficiency or adoption.
- **Could have:** Valuable but not necessary for the next release’s core promise.
- **Won’t have for now:** Deliberately deferred because it adds scope without resolving current workflow gaps.

## 5.1 Business requirements

### BR-001: Unified dependency governance workflow
- **Type:** Business
- **Description:** PythonDepot shall support a continuous workflow from project/package import through assessment, decision, monitoring, remediation, and verification.
- **User value:** Users no longer assemble decisions manually across disconnected tools and screens.
- **Priority:** Must have
- **Rationale:** Existing capabilities cover each stage separately, but context and state do not flow between them.
- **Acceptance criteria:**
  1. A user can create/import a project and reach its packages, risks, policy status, upgrade plan, and migration history without re-entering identifiers.
  2. A package selected in search can be added to a comparison or monitored project in no more than two actions.
  3. A resolved risk can be verified by a fresh scan and retains its complete history.

### BR-002: Trustworthy organizational use
- **Type:** Business
- **Description:** PythonDepot shall provide authenticated, role-based, organization-scoped workflows for decisions, moderation, assignments, policies, waivers, and private packages.
- **User value:** Organizations can rely on records and approvals without identity ambiguity or cross-tenant exposure.
- **Priority:** Must have
- **Rationale:** Current domain concepts already depend on actor identity and organization context.
- **Acceptance criteria:**
  1. All protected actions are attributable to an authenticated user.
  2. Organization data cannot be read or modified outside authorized tenancy.
  3. Role and conflict restrictions are enforced server-side and recorded.
  4. Unauthorized attempts return a safe error and generate an audit event where appropriate.

### BR-003: Evidence-backed decisions
- **Type:** Business
- **Description:** Every decision, policy outcome, and risk status shall retain the evidence snapshot and freshness context used at the time.
- **User value:** Users can defend past decisions and understand changes later.
- **Priority:** Must have
- **Rationale:** Immutable decision digests and provenance concepts exist but are not consistently applied across workflows.
- **Acceptance criteria:**
  1. Decision records include evidence sources, timestamps, versions, criteria, rationale, actor, and digest.
  2. Re-evaluation never silently rewrites finalized historical records.
  3. Users can compare current evidence with the finalized snapshot.

### BR-004: Measurable workflow effectiveness
- **Type:** Business
- **Description:** The product shall measure task completion, time to triage, remediation verification, migration success, and workflow abandonment without collecting unnecessary sensitive data.
- **User value:** Product improvements can be based on real behavior rather than assumptions.
- **Priority:** Should have
- **Rationale:** Analytics exist, but current event logic is basic and may not correctly rank trends.
- **Acceptance criteria:**
  1. A documented event taxonomy exists for core workflows.
  2. Funnel and duration metrics can be computed for import, triage, decision, policy, and migration flows.
  3. Organization administrators can control telemetry consistent with privacy policy.

## 5.2 User requirements

### UR-001: Persistent project workspace
- **Type:** User
- **Description:** As a developer or team lead, I want to save a project once and reuse its dependency context across all analyses.
- **User value:** Eliminates repetitive uploads and inconsistent inputs.
- **Priority:** Must have
- **Rationale:** Upgrade, migration, policy, portfolio, and vulnerability workflows all consume overlapping project data.
- **Acceptance criteria:**
  1. Users can create, rename, archive, and reopen projects.
  2. A project stores imports, dependency graph, Python target, SBOM, scans, evaluations, migrations, and ownership metadata.
  3. Re-import shows a change preview before updating the active baseline.

### UR-002: Guided dependency import
- **Type:** User
- **Description:** As a user, I want to import supported project files instead of manually formatting dependency JSON.
- **User value:** Faster onboarding with fewer errors.
- **Priority:** Must have
- **Rationale:** The archive already contains parsers for multiple project formats, while the upgrade UI expects pasted JSON.
- **Acceptance criteria:**
  1. Support `pyproject.toml`, `requirements.txt`, `requirements.in`, `Pipfile`, `Pipfile.lock`, `poetry.lock`, `setup.py`, `setup.cfg`, and supported SBOM formats.
  2. The system validates files, previews detected dependencies, and identifies ignored or ambiguous entries.
  3. Users can correct mappings before committing the import.

### UR-003: Actionable risk detail
- **Type:** User
- **Description:** As a security user, I want each risk to explain impact, evidence, affected projects, available fixes, and the next recommended action.
- **User value:** Reduces investigation time and improves remediation quality.
- **Priority:** Must have
- **Rationale:** Current risk items contain project, package, severity, message, and state, which is insufficient for daily triage.
- **Acceptance criteria:**
  1. Risk detail includes source, affected version/path, severity rationale, fix version or workaround, evidence timestamp, owner, due date, notes, and history.
  2. If no fix exists, the UI states that explicitly and offers supported alternatives.
  3. Related duplicate findings can be grouped without losing source evidence.

### UR-004: Batch triage
- **Type:** User
- **Description:** As a security user, I want to perform safe bulk actions on filtered risk items.
- **User value:** Removes repetitive work from high-volume portfolios.
- **Priority:** Should have
- **Rationale:** The current inbox exposes state but no demonstrated bulk operations.
- **Acceptance criteria:**
  1. Users can select all visible or all matching items.
  2. Bulk assign, acknowledge, snooze, export, and add-note actions show scope and confirmation.
  3. Partial failures are reported per item and can be retried.

### UR-005: Safe migration control
- **Type:** User
- **Description:** As a platform engineer, I want to preview, apply, validate, and roll back migration changes with complete transparency.
- **User value:** Builds trust in automation that changes source code and CI configuration.
- **Priority:** Must have
- **Rationale:** The CLI has dry-run and rollback concepts, but the workflow is not integrated or fully observable through the product.
- **Acceptance criteria:**
  1. File-level diffs are shown before apply.
  2. A backup or version-control checkpoint is required before mutation.
  3. Validation commands and results are captured.
  4. Failed and partial migrations identify changed files and provide executable rollback steps.

### UR-006: Understand evidence quality
- **Type:** User
- **Description:** As any decision-maker, I want to know where each signal came from, when it was observed, and what it does not prove.
- **User value:** Prevents overconfidence in stale or incomplete data.
- **Priority:** Must have
- **Rationale:** Current global freshness and score labels can oversimplify heterogeneous evidence.
- **Acceptance criteria:**
  1. Every key signal has source, observed time, relevant package version, and status.
  2. Unavailable, stale, unscanned, clean, unknown, and failed are visually and semantically distinct.
  3. Users can refresh one source without rerunning unrelated analyses.

### UR-007: Complete waiver lifecycle
- **Type:** User
- **Description:** As a policy administrator, I want to request, review, approve, reject, revoke, and expire waivers with an audit history.
- **User value:** Enables controlled exceptions without weakening policy enforcement.
- **Priority:** Must have
- **Rationale:** Evaluation recognizes expiring waivers, but the lifecycle is not fully implemented in the UI.
- **Acceptance criteria:**
  1. Requests require scope, rule, justification, owner, approver, and expiration.
  2. Expired or revoked waivers never suppress violations.
  3. Upcoming expirations are visible and notifiable.
  4. All status changes are immutable audit events.

### UR-008: Explain unavailable actions
- **Type:** User
- **Description:** As a user, I want to know why an action is disabled or hidden and what legitimate next step is available.
- **User value:** Reduces confusion around permissions and conflicts.
- **Priority:** Should have
- **Rationale:** Current permission-aware removal improves safety but can reduce learnability.
- **Acceptance criteria:**
  1. Where disclosure is safe, the UI explains the applicable role or conflict rule.
  2. A permitted escalation or request-access path is offered.
  3. Explanations never reveal restricted tenant data.

## 5.3 Functional requirements

### FR-001: Canonical project and package context
- **Type:** Functional
- **Description:** The system shall maintain canonical project and normalized package records referenced by all workflows.
- **User value:** Consistent data across screens and jobs.
- **Priority:** Must have
- **Rationale:** Current modules use multiple persistence approaches and some placeholder package creation behavior.
- **Acceptance criteria:**
  1. Package names follow Python normalization rules and aliases resolve to one canonical identity.
  2. All analyses reference immutable input snapshots.
  3. Deleting or archiving a project does not destroy required audit records.

### FR-002: Background job orchestration
- **Type:** Functional
- **Description:** Scans, imports, policy evaluations, migrations, and report generation shall execute as background jobs with observable state.
- **User value:** Users can monitor long operations and recover from failures.
- **Priority:** Must have
- **Rationale:** External calls and batch operations are not suitable for opaque request/response execution.
- **Acceptance criteria:**
  1. Job states include queued, running, partially completed, succeeded, failed, cancelled, and unavailable where applicable.
  2. Jobs expose timestamps, progress, item-level errors, retryability, and result links.
  3. Retries are idempotent and do not duplicate alerts or audit events.

### FR-003: Scan-state correctness
- **Type:** Functional
- **Description:** The system shall accurately distinguish scan status from vulnerability outcome.
- **User value:** Prevents false assurance.
- **Priority:** Must have
- **Rationale:** Legacy behavior can report queued or zero vulnerabilities when the scanner is unavailable.
- **Acceptance criteria:**
  1. Scanner unavailable cannot produce a clean outcome.
  2. Unscanned packages are excluded from “clean” counts and health rankings unless explicitly segmented.
  3. Scan responses identify engine, database/source, package version, and completion time.

### FR-004: Risk workflow model
- **Type:** Functional
- **Description:** Risk items shall support assignment, SLA, notes, state transitions, verification, and immutable history.
- **User value:** Converts alerts into managed work.
- **Priority:** Must have
- **Rationale:** The current state model is too shallow for team operations.
- **Acceptance criteria:**
  1. Allowed transitions are configurable and validated server-side.
  2. Resolve requires a resolution reason.
  3. Verified resolution requires fresh evidence showing that the finding no longer applies, or an approved active waiver.
  4. Reopen records the cause and preserves prior resolution history.

### FR-005: Dependency graph and blocker paths
- **Type:** Functional
- **Description:** The system shall build and display dependency graphs that distinguish direct and transitive packages and show all relevant blocker paths.
- **User value:** Users can identify the actual dependency to upgrade or replace.
- **Priority:** Must have
- **Rationale:** The planner currently uses a simplified incoming-parent path that may not capture complete graph relationships.
- **Acceptance criteria:**
  1. Cycles are detected without infinite traversal.
  2. Multiple paths to a blocker can be expanded and collapsed.
  3. Graph results state which input snapshot and environment markers were evaluated.

### FR-006: Integrated comparison and decision records
- **Type:** Functional
- **Description:** Users shall create comparisons from search, project dependencies, or recommendations and finalize a decision only when required evidence is present.
- **User value:** Makes evaluation faster and auditable.
- **Priority:** Should have
- **Rationale:** Decision storage exists but the current UI shows “Evidence pending” without a complete evidence acquisition flow.
- **Acceptance criteria:**
  1. Criteria can include security, compatibility, license, provenance, maintenance, adoption, migration effort, and custom organization criteria.
  2. Missing or stale evidence is clearly identified before finalization.
  3. Finalized decisions are immutable; superseding decisions link to predecessors.

### FR-007: Report repository
- **Type:** Functional
- **Description:** The system shall persist, list, retrieve, filter, and export generated reports.
- **User value:** Reports become reusable operational artifacts.
- **Priority:** Must have
- **Rationale:** Report generation exists, while listing and retrieval are explicitly incomplete.
- **Acceptance criteria:**
  1. Reports are filterable by type, period, project, organization, creator, and status.
  2. HTML and JSON outputs are retrievable from the same report version.
  3. Regeneration creates a new version rather than silently overwriting historical output.

### FR-008: Migration validation pipeline
- **Type:** Functional
- **Description:** Applied migrations shall run configured targeted and full validation commands and store results.
- **User value:** Confirms that automation did not break the project.
- **Priority:** Must have
- **Rationale:** The current assistant updates dependency and CI files, so tests and validation are essential to completion.
- **Acceptance criteria:**
  1. Users can configure lint, targeted tests, full regression tests, lock verification, and build commands.
  2. Apply is marked successful only after required validations pass.
  3. Timeout, skipped, failed, and unavailable validation states are distinct.
  4. Reports include commands, exit codes, durations, and relevant output excerpts.

### FR-009: Notification and subscription rules
- **Type:** Functional
- **Description:** Users shall subscribe to projects, packages, policy events, waiver expirations, and job outcomes with threshold and channel controls.
- **User value:** Relevant changes reach the right person without alert overload.
- **Priority:** Should have
- **Rationale:** Webhooks exist, but user-centered notification preference and routing are not visible.
- **Acceptance criteria:**
  1. Rules support event type, severity, project, package, owner, and digest frequency.
  2. Delivery status and retries are visible.
  3. Duplicate events within a configured window are consolidated.

### FR-010: Review evidence capture
- **Type:** Functional
- **Description:** The product shall derive review evidence from an imported project or guided file selection rather than requiring manual hash entry by default.
- **User value:** Makes trusted reviews understandable and usable.
- **Priority:** Should have
- **Rationale:** Manual lock-hash entry is technically oriented and error-prone.
- **Acceptance criteria:**
  1. Users can select an eligible project snapshot or upload a supported lockfile.
  2. The product computes the digest locally or server-side according to documented privacy behavior.
  3. The preview explains what evidence will be published and what remains private.

### FR-011: Full moderation timeline
- **Type:** Functional
- **Description:** Review moderation shall expose append-only events, reasons, actor role, conflict checks, and appeal status to authorized users.
- **User value:** Improves fairness and accountability.
- **Priority:** Should have
- **Rationale:** Append-only moderation concepts exist but are not fully surfaced.
- **Acceptance criteria:**
  1. Moderation actions require a reason where policy specifies.
  2. Conflicted actors cannot act, even through direct API calls.
  3. Authorized users can see the complete timeline and current state.

### FR-012: Partial-failure batch behavior
- **Type:** Functional
- **Description:** All batch workflows shall return item-level outcomes and support retrying only failed items.
- **User value:** Prevents rework and supports large portfolios.
- **Priority:** Must have
- **Rationale:** Batch migration and scanning can encounter mixed results.
- **Acceptance criteria:**
  1. The batch summary includes succeeded, skipped, warned, and failed counts.
  2. Each failure includes a stable code, user-readable explanation, and retry guidance.
  3. Successful items are not rerun unless explicitly requested.

## 5.4 Non-functional requirements

### NFR-001: Accessibility
- **Type:** Non-functional
- **Description:** All core workflows shall conform to WCAG 2.2 AA.
- **User value:** Usable by keyboard, assistive technology, and users with visual or cognitive accessibility needs.
- **Priority:** Must have
- **Rationale:** Strong foundations exist and should become a measurable release criterion.
- **Acceptance criteria:**
  1. Automated accessibility checks pass on all core states.
  2. Keyboard-only completion is verified for import, triage, comparison, migration, review, and policy workflows.
  3. Focus, errors, progress, tables, charts, dialogs, and live updates have accessible semantics.

### NFR-002: Performance and responsiveness
- **Type:** Non-functional
- **Description:** Interactive pages shall remain responsive for realistic portfolio sizes, while long operations run asynchronously.
- **User value:** Daily work is not blocked by large datasets.
- **Priority:** Must have
- **Rationale:** Sequential scans and table-heavy screens will not scale.
- **Acceptance criteria:**
  1. P95 server response time for non-job UI/API reads is under 500 ms at the agreed reference load.
  2. Local filtering/sorting feedback appears within 100 ms for loaded data.
  3. Lists use server-side pagination or virtualization for large result sets.
  4. Batch scanning uses bounded concurrency and external-service rate limits.

### NFR-003: Reliability and idempotency
- **Type:** Non-functional
- **Description:** Repeated requests and retries shall not corrupt state or duplicate decisions, alerts, waivers, or migration actions.
- **User value:** Users can safely recover from network and service failures.
- **Priority:** Must have
- **Rationale:** The product integrates multiple external services and long-running operations.
- **Acceptance criteria:**
  1. Mutating operations support idempotency keys where appropriate.
  2. Job and webhook retry policies are documented and tested.
  3. Backups and restore procedures meet defined recovery objectives.

### NFR-004: Security and privacy
- **Type:** Non-functional
- **Description:** The system shall protect tenants, credentials, uploaded project data, webhooks, and generated artifacts.
- **User value:** Users can connect real projects without exposing sensitive dependency or repository data.
- **Priority:** Must have
- **Rationale:** SSRF protections exist, but broader organizational security is required.
- **Acceptance criteria:**
  1. Authorization is enforced on every organization-scoped object.
  2. Secrets are never written to logs, diffs, reports, or UI payloads.
  3. Uploads are size-limited, type-validated, malware-scanned where required, and securely deleted according to retention policy.
  4. Outbound requests use allowlists or validated destinations and block private address ranges after DNS resolution.

### NFR-005: Observability
- **Type:** Non-functional
- **Description:** The system shall provide structured logs, metrics, traces, job diagnostics, and external-source health indicators.
- **User value:** Failures can be diagnosed without opaque “try again” loops.
- **Priority:** Must have
- **Rationale:** OSV, PyPI, webhook, scanner, and CI interactions introduce distributed failure modes.
- **Acceptance criteria:**
  1. Every request and job has a correlation identifier.
  2. External source latency, error rate, and last successful retrieval are monitored.
  3. User-facing error IDs map to diagnostic records without exposing sensitive details.

### NFR-006: Data integrity and migration safety
- **Type:** Non-functional
- **Description:** The product shall use transactional, versioned persistence suitable for concurrent multi-user deployment.
- **User value:** Records remain consistent under collaboration and upgrade.
- **Priority:** Must have
- **Rationale:** The reviewed implementation uses SQLAlchemy plus separate SQLite repositories and notes single-process limitations.
- **Acceptance criteria:**
  1. Production uses a supported transactional database with schema migrations.
  2. Cross-object updates execute atomically or use a documented outbox/saga pattern.
  3. Concurrency conflicts are detected and surfaced rather than silently overwriting changes.

### NFR-007: Compatibility and extensibility
- **Type:** Non-functional
- **Description:** Evidence sources, scanners, package managers, notification channels, and ticketing integrations shall use versioned adapter contracts.
- **User value:** New sources can be added without destabilizing core workflows.
- **Priority:** Should have
- **Rationale:** The product already has parallel OSV/Safety paths and multiple migration formats.
- **Acceptance criteria:**
  1. Adapter failures are isolated and reported per source.
  2. Contract tests validate schemas and error behavior.
  3. API changes follow a documented versioning and deprecation policy.

## 5.5 UX/UI requirements

### UX-001: Contextual global navigation
- **Type:** UX/UI
- **Description:** Navigation shall be organized around Home, Projects, Packages, Risks, Decisions, Policies, Reports, and Administration, with visible organization and project context.
- **User value:** Users know where they are and can move between related tasks without losing state.
- **Priority:** Must have
- **Rationale:** Current workspace navigation is feature-oriented and fragmented.
- **Acceptance criteria:**
  1. Current location is indicated visually and programmatically.
  2. Breadcrumbs and context selectors preserve authorized state.
  3. Deep links restore relevant filters and selected objects.

### UX-002: Progressive disclosure of technical detail
- **Type:** UX/UI
- **Description:** Screens shall lead with outcome, impact, and next action, with technical evidence available on demand.
- **User value:** Supports both occasional developers and expert reviewers.
- **Priority:** Must have
- **Rationale:** Current workflows expose raw JSON, hashes, status codes, and specialist terminology early.
- **Acceptance criteria:**
  1. Primary summaries use plain language without removing technical precision.
  2. Raw evidence, vectors, digests, and source payloads are expandable and copyable.
  3. Terminology help is accessible by keyboard and screen reader.

### UX-003: Unified status language
- **Type:** UX/UI
- **Description:** The UI shall use a documented status system that separates evidence availability, security outcome, provenance, policy, compatibility, and workflow state.
- **User value:** Prevents conflating “verified,” “clean,” “approved,” and “safe.”
- **Priority:** Must have
- **Rationale:** The product currently presents many status vocabularies.
- **Acceptance criteria:**
  1. Color is never the only status indicator.
  2. Each status has a short definition and scope.
  3. “Unknown,” “unavailable,” “stale,” and “not evaluated” are distinct.

### UX-004: Consistent asynchronous feedback
- **Type:** UX/UI
- **Description:** Long-running actions shall provide progress, safe navigation away, cancellation when feasible, and a return path to results.
- **User value:** Reduces uncertainty and duplicate submissions.
- **Priority:** Must have
- **Rationale:** Scans and migrations can take much longer than routine page requests.
- **Acceptance criteria:**
  1. Submission immediately shows a job identifier and state.
  2. Refreshing or leaving the page does not lose the job.
  3. Completion and failure messages link directly to results or recovery.

### UX-005: Efficient risk tables
- **Type:** UX/UI
- **Description:** Risk lists shall support search, multi-filtering, sorting, grouping, saved views, column customization, bulk selection, and keyboard operation.
- **User value:** Optimizes the product’s most frequent operational workflow.
- **Priority:** Must have
- **Rationale:** The current basic state filter and search are insufficient for portfolio triage.
- **Acceptance criteria:**
  1. Filters are reflected in the URL and restorable.
  2. Active filters and result count are always visible.
  3. Empty results explain whether no risks exist or filters excluded them.

### UX-006: Source-specific freshness display
- **Type:** UX/UI
- **Description:** Freshness shall be shown per evidence source and summarized without masking stale or failed sources.
- **User value:** Makes decisions time-aware.
- **Priority:** Must have
- **Rationale:** A single page-level “current” label is potentially misleading.
- **Acceptance criteria:**
  1. Summary shows oldest critical evidence and any failed source.
  2. Exact timestamps and relative age are available.
  3. Refresh controls identify cost, scope, and expected duration.

### UX-007: Prevention before confirmation
- **Type:** UX/UI
- **Description:** Destructive or consequential actions shall use previews, validation, and scope summaries before requiring confirmation.
- **User value:** Prevents mistakes without relying on repeated modal dialogs.
- **Priority:** Must have
- **Rationale:** Migration, policy, moderation, and bulk triage actions can have major effects.
- **Acceptance criteria:**
  1. Users see affected objects and predicted changes before execution.
  2. Irreversible actions require explicit acknowledgement.
  3. Reversible actions provide an undo or rollback path where technically feasible.

### UX-008: Helpful empty, error, and degraded states
- **Type:** UX/UI
- **Description:** Every screen shall distinguish no data, no matching data, not configured, permission denied, source unavailable, and processing states.
- **User value:** Users understand what to do next.
- **Priority:** Must have
- **Rationale:** Existing empty/recovery states are a strong foundation but too generic.
- **Acceptance criteria:**
  1. Each state provides a specific cause and relevant action.
  2. “Try again” retries the failed operation rather than reloading unrelated state.
  3. Stable prior data remains visible and is labeled stale when refresh fails.

## 5.6 Data and integration requirements

### DI-001: Evidence provenance model
- **Type:** Data/Integration
- **Description:** All externally sourced facts shall use a common evidence record containing source, retrieval time, subject, version/scope, status, payload digest, and retention policy.
- **User value:** Consistent trust and audit semantics.
- **Priority:** Must have
- **Rationale:** PyPI, OSV, attestations, analytics, lockfiles, and SBOMs have different freshness and failure characteristics.
- **Acceptance criteria:**
  1. Evidence records are queryable by subject and snapshot.
  2. UI and exports can show provenance without exposing secrets or oversized raw payloads.
  3. Superseded evidence remains linked to historical decisions.

### DI-002: Repository and CI integration
- **Type:** Data/Integration
- **Description:** The product should integrate with supported Git providers to import projects, create branches or pull requests, and report validation status.
- **User value:** Makes migration and remediation part of the development workflow.
- **Priority:** Should have
- **Rationale:** CLI migration already changes CI/CD files, and users likely work in source control.
- **Acceptance criteria:**
  1. Integrations request least-privilege scopes.
  2. Users preview changed files before creating a branch or pull request.
  3. Commit, branch, PR, and validation links are attached to the project job history.

### DI-003: Ticketing integration
- **Type:** Data/Integration
- **Description:** Authorized users should create and synchronize remediation tickets with GitHub Issues, Jira, or Azure DevOps.
- **User value:** Avoids manually copying risk context.
- **Priority:** Should have
- **Rationale:** Risk ownership and due dates usually live in established work-management tools.
- **Acceptance criteria:**
  1. Ticket templates include package, project, evidence, impact, fix guidance, and deep link.
  2. External ticket ID and status are visible in the risk.
  3. Synchronization failures do not change the risk state silently.

### DI-004: SBOM standards support
- **Type:** Data/Integration
- **Description:** The product shall validate and process documented versions of CycloneDX and SPDX, including schema and component identity errors.
- **User value:** Supports common compliance inputs without custom transformation.
- **Priority:** Must have
- **Rationale:** The policy gate currently accepts a generic component structure but production use requires explicit standards.
- **Acceptance criteria:**
  1. Supported versions and fields are documented.
  2. Invalid documents produce line/item-level feedback where possible.
  3. Normalization preserves original identifiers and source file digest.

### DI-005: Data export and API consistency
- **Type:** Data/Integration
- **Description:** Core objects and results shall be exportable through versioned APIs and downloadable formats.
- **User value:** Enables automation, audits, and integration without screen scraping.
- **Priority:** Should have
- **Rationale:** The product already exposes many APIs, but persistence and result consistency vary by module.
- **Acceptance criteria:**
  1. Exports include schema version, generated time, organization/project scope, and evidence references.
  2. Pagination, filtering, sorting, and errors follow common conventions.
  3. API contracts match UI-visible status terminology.

## 5.7 Could-have requirements

### CR-001: Expert command palette
- **Type:** UX/UI
- **Description:** Provide keyboard-accessible global actions for search, navigation, refresh, compare, assign, and start a scan.
- **User value:** Speeds frequent expert workflows.
- **Priority:** Could have
- **Rationale:** The product targets technical repeat users, but core flows must be unified first.
- **Acceptance criteria:** Common commands are searchable, permission-aware, and keyboard operable.

### CR-002: Decision templates
- **Type:** Functional
- **Description:** Allow organizations to save reusable comparison criteria and weights without hiding raw evidence.
- **User value:** Standardizes package selection.
- **Priority:** Could have
- **Rationale:** Repeated architectural decision patterns are likely, but weighting can create false precision if introduced too early.
- **Acceptance criteria:** Templates are versioned, editable by authorized roles, and recorded in finalized decisions.

### CR-003: Natural-language evidence summary
- **Type:** Functional
- **Description:** Generate a concise explanation of package or project posture grounded only in displayed evidence.
- **User value:** Reduces synthesis effort.
- **Priority:** Could have
- **Rationale:** Users face many signals, but correctness, source linkage, and core actionability must come first.
- **Acceptance criteria:** Every material statement links to evidence; uncertainty and stale data are explicit; generated text cannot approve policy or close risk automatically.

## 5.8 Won’t have for now

### WH-001: General-purpose Python package hosting registry
- **Type:** Business
- **Description:** PythonDepot will not become a replacement package hosting service in the next version.
- **User value:** Keeps focus on decision, governance, security, and migration workflows.
- **Priority:** Won’t have for now
- **Rationale:** No observed user-flow gap requires hosting packages, and it would add major security and operational scope.
- **Acceptance criteria:** Roadmap and messaging distinguish catalog intelligence from package artifact hosting.

### WH-002: Fully autonomous dependency changes without review
- **Type:** Functional
- **Description:** The product will not apply migration or remediation changes directly to protected branches without human review and validation.
- **User value:** Preserves user control and trust.
- **Priority:** Won’t have for now
- **Rationale:** Current dry-run, rollback, evidence, and governance design favors controlled automation.
- **Acceptance criteria:** Protected mutations require preview, authorization, and validation workflow.

### WH-003: Universal multi-language dependency management
- **Type:** Business
- **Description:** The next version will remain focused on Python rather than adding JavaScript, Java, .NET, or other ecosystems.
- **User value:** Allows the team to complete current Python workflows before broadening scope.
- **Priority:** Won’t have for now
- **Rationale:** The current product has significant Python-specific depth and unfinished core integration.
- **Acceptance criteria:** New architecture remains extensible but release scope is Python-only.

---

# 6. New opportunities

## 6.1 Project health cockpit

**Opportunity:** A single project home combining dependency changes, vulnerability posture, policy outcome, Python compatibility, migration state, and ownership.

**Why users may want it:** Most users manage applications and repositories, not isolated package facts. A project cockpit would reduce repeated input and show the most relevant next actions.

**Evidence/reasoning:** The application already has portfolio snapshots, vulnerability scans, policy evaluation, upgrade planning, and migration analysis. Their shared project context is the clearest missing connective layer.

## 6.2 Change-impact feed

**Opportunity:** A delta-first feed showing new vulnerabilities, publisher identity changes, dependency changes, newly failed policy rules, waiver expirations, and Python compatibility regressions.

**Why users may want it:** Returning users want to know what changed since their last trusted baseline, not reread the entire current state.

**Evidence/reasoning:** Risk-delta deduplication and snapshot digests already exist. Extending that concept across evidence types is a logical product consolidation, not a random new feature.

## 6.3 Remediation and migration pull-request workflow

**Opportunity:** Convert a verified fix or `uv` migration plan into a reviewable branch or pull request with generated diffs and test evidence.

**Why users may want it:** It closes the loop from insight to engineering action while retaining human control.

**Evidence/reasoning:** The migration assistant already updates lock and CI/CD files and provides rollback guidance. The missing user-centered step is safe delivery through normal source-control review.

## 6.4 Organization dependency standards

**Opportunity:** Approved, discouraged, and prohibited package lists backed by documented decisions and policy evidence.

**Why users may want it:** Teams repeatedly evaluate the same packages. Reusing approved decisions avoids duplicated research and drives standardization.

**Evidence/reasoning:** Decision workspaces, private catalogs, policy gates, and package comparison already supply the required foundations.

## 6.5 Evidence freshness service-level rules

**Opportunity:** Let organizations define acceptable evidence ages, such as vulnerability data under 24 hours for critical projects or provenance checks on every new release.

**Why users may want it:** “Current” is context-dependent. Regulated or high-risk projects need explicit freshness guarantees.

**Evidence/reasoning:** Freshness is already surfaced as a UI concept but is not source-specific or policy-driven.

## 6.6 Pilot-to-fleet migration campaigns

**Opportunity:** Group projects into a migration campaign, pilot on selected repositories, track blockers, apply a standard playbook, and monitor completion.

**Why users may want it:** Platform teams rarely migrate only one project. They need controlled rollout, comparable status, and exception management.

**Evidence/reasoning:** Batch migration, effort estimates, project scanning, reports, and portfolio concepts already exist, making campaign management a natural extension.

## 6.7 Market validation needed before commitment

The following assumptions should be tested before expanding scope:

- Whether customers primarily buy package discovery, security operations, policy governance, or migration automation.
- Whether web-based migration or CLI/CI integration is preferred by platform teams.
- Which evidence dimensions actually influence package choice.
- Whether trusted reviews add decision value beyond verified project usage and maintainer signals.
- Which external systems are essential for workflow completion: GitHub, GitLab, Azure DevOps, Jira, Slack, or Teams.
- What portfolio size and scan frequency define the first production scaling target.

Recommended discovery methods:

1. Interview 5 to 8 users from each primary segment.
2. Run task-based usability tests on import, risk triage, comparison, migration dry-run, and waiver approval.
3. Instrument current flows to measure blank-state exits, repeated searches, filter usage, and action completion.
4. Conduct a concierge pilot with 3 to 5 real repositories per organization.
5. Validate willingness to pay for the consolidated workflow rather than individual point features.

---

# 7. Final recommendation

## 7.1 What should be built first and why

Build the next version around a **persistent Project Workspace and Unified Risk Workflow**. This provides the highest leverage because it connects the product’s existing strengths rather than adding another isolated capability.

### Phase 0: Release safety and truthfulness

1. Complete authentication, role-based access, organization isolation, and audit identity.
2. Consolidate production persistence and introduce schema migrations.
3. Correct scan state semantics and remove any path where unavailable or unscanned can appear clean.
4. Complete the OSV dependency scanner work and eliminate RED-phase test gaps for release scope.
5. Implement report listing/retrieval and remove or feature-flag placeholder interactions.
6. Define shared status, evidence, freshness, and error models.

### Phase 1: Core workflow

1. Persistent project creation and guided import.
2. Project cockpit with dependencies, latest changes, risks, policy status, and jobs.
3. Operational risk inbox with assignment, due date, notes, history, bulk actions, saved filters, and verification.
4. Evidence-level freshness, source detail, and partial-source retry.
5. Background jobs with progress, partial failure, cancellation, and result history.

### Phase 2: Decision and change delivery

1. Contextual package comparison from search and projects.
2. Integrated Python upgrade and `uv` migration workflow.
3. File diff, backup/checkpoint, targeted and full regression validation, rollback.
4. Repository pull-request integration.
5. Complete policy waiver lifecycle and audit exports.

### Phase 3: Adoption and scale

1. Notification subscriptions and ticketing integrations.
2. Migration campaigns across project fleets.
3. Organization package standards and decision templates.
4. Scheduled reports and leadership views.
5. Selected AI summaries only after evidence linkage and core correctness are proven.

## 7.2 UI and workflow improvements to prioritize immediately

- Replace the six-workspace-first navigation with object-based navigation.
- Add an always-visible organization/project context.
- Replace pasted JSON and manual hashes with guided file/project selection.
- Make every visible action complete and testable end to end.
- Redesign risk lists for filtering, bulk action, ownership, and deep-link restoration.
- Show source-specific freshness and preserve stale prior results when a refresh fails.
- Use a shared visual vocabulary that separates security, provenance, policy, compatibility, and workflow statuses.
- Provide next-action guidance rather than showing scores alone.
- Treat jobs, partial success, and retry as first-class UI states.

## 7.3 Requirements most likely to improve adoption and efficiency

1. **UR-001 Persistent project workspace**
2. **UR-002 Guided dependency import**
3. **UR-003 Actionable risk detail**
4. **FR-002 Background job orchestration**
5. **FR-003 Scan-state correctness**
6. **FR-004 Risk workflow model**
7. **UX-001 Contextual global navigation**
8. **UX-005 Efficient risk tables**
9. **UX-006 Source-specific freshness display**
10. **FR-008 Migration validation pipeline**
11. **BR-002 Trustworthy organizational use**
12. **DI-001 Evidence provenance model**

## Closing assessment

PythonDepot already contains many of the domain primitives expected in a serious Python dependency intelligence product. The primary next-version challenge is not ideation. It is integration, workflow completion, trustworthy state semantics, and production readiness. If the team focuses on persistent project context and closing the loop from evidence to accountable action, the product can become materially more useful than a collection of dashboards and utilities. If it continues to add separate modules without consolidating navigation, data, status, and ownership, cognitive load and maintenance complexity will grow faster than user value.
