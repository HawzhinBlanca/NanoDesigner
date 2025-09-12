Perfect — here’s how this plays out:

⸻

Two-Week Delivery Board (Execution Plan)

Week 1 — P0 Foundations

Day 1–2
	•	✅ Update Backend Blueprint.md
	•	Lock OpenRouter image contract: add exact model slug, headers, payload schema, recordable client test.
	•	Rewrite SynthID AC: change to verified_by: declared|external|none.
	•	Add per-org isolation rules (Qdrant collections per org, R2 prefixes, Postgres row filters).

Day 3–4
	•	✅ Update Frontend Blueprint.md
	•	Reflect new /render schema (with verified_by).
	•	Add per-org dashboards & budget UI (cost cap progress bars, alerts).
	•	Document upload security pipeline (quarantine → AV/MIME → promote).

Day 5
	•	Build /render end-to-end: planner → guardrails → OR → R2 save → signed URL → Langfuse trace.
	•	Integration test with fake OR client cassette.

⸻

Week 2 — Hardening + Demo Slice

Day 6–7
	•	Implement upload pipeline: AV scan (ClamAV container), MIME allowlist, EXIF scrub, quarantine R2 path.
	•	Update acceptance criteria in Backend Blueprint to require “AV+MIME pass” before ingest promotion.

Day 8
	•	Add per-org budget caps:
	•	Kong plugin to enforce daily caps.
	•	Server logic for usage tracking, 50/80/100% alerts.
	•	Frontend cost panel shows live usage.

Day 9–10
	•	Build frontend thin slice:
	•	Auth → Assets (upload w/ AV+MIME) → Composer (prompt + refs) → Preview grid (WebSocket) → History (signed URL + SynthID “declared”).
	•	CI gates: Lighthouse budgets, Chromatic visual diffs, Playwright E2E hitting /render.

⸻

Blueprint Updates Required
	•	Backend Blueprint.md
	•	Add OpenRouter contract tests for gemini-2.5-flash-image-preview.
	•	Rewrite SynthID ACs → no hard verification; add verified_by field.
	•	Add Org isolation section (Qdrant collections per org, Postgres row filters, R2 prefixing).
	•	Add Cost Control section: Kong budget plugin, per-org daily caps, alerts.
	•	Add Upload Security section: AV scan, MIME allowlist, EXIF strip, quarantine promotion flow.
	•	Update Acceptance Criteria AC1–AC10 accordingly.
	•	Frontend Blueprint.md
	•	Update RenderResponse schema → verified_by flag.
	•	Add Cost Panel in dashboard (budget bar + alerts).
	•	Add Upload Security UI: “scanning…” status, retry flow, blocked file error states.
	•	Add Org dashboard: usage, errors, per-org traces.
	•	Update Acceptance Criteria to include AV scan required, cost panel visible, budget alerts visible.

⸻

Ship Gate (Demo Safe)

Release v0.1 only if:
	1.	/render E2E passes contract tests with OR cassette.
	2.	SynthID logged as declared, not claimed verified.
	3.	Tenant isolation enforced in Qdrant/Postgres/R2.
	4.	Upload promotion gated by AV+MIME+EXIF checks.
	5.	Per-org budget caps functional; frontend shows usage bar + 429 UX.
	6.	Thin slice (Auth → Assets → Composer → Preview → History) works in Playwright E2E.
	7.	Lighthouse mobile perf ≥90, bundle ≤200KB, visual diffs approved.

⸻

Do you want me to apply these blueprint updates directly into your Backend and Frontend docs now so your spec stays authoritative, or keep them as a delta list you apply manually?