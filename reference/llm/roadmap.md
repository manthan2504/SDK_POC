> **POC copy — edited 2026-09-18.** Snapshot of `D:\Caliber\docs\llm\roadmap.md` with the provider-gateway
> material removed (the dev-cycle banner, build-order step 1's gateway provider, build-order step 7, and open
> decisions D1/D2/D4). Everything else is verbatim.

# §9 — AI-Layer Roadmap, Gates & Open Decisions

> **Development cycle (2026-09-02, ADR-0011):** Claude-only fleet (Opus 5 / Sonnet 5 / Haiku 4.5 + local
> embeddings). The critical path: credentials/credits → harness → human gold set → Phase 0A gate.

How the registry becomes reality: the build order, the mapping onto `docs/BACKLOG.md`
(which stays the master sequence — this file adds the AI-layer view, it never overrides the
backlog), the dated obligations, and every open decision with its owner. **Nothing here is
built ahead of its slice.**

## 9.1 The standing gate

A workload is DONE when: built behind the provider seam · its named gating eval has run on
the pinned model with the results file committed · mandatory slices reported · its Status
in workloads.md §2 updated in the same change. `built, eval owed` is not done (FR-I4).

## 9.2 Build order (locked, FR-I4-shaped: harness before agents)

| Step | What | Backlog anchor | Gate |
|---|---|---|---|
| 0 | **`ant auth login`** — human-only, blocks every real call | Part 10 item 1 | `ant auth status` shows active profile |
| 1 | Provider spine completion: `cw` task tags (§2.8) + trace fields (§8.2) | AGT-02 | Conformance tests green offline |
| 2 | **Eval harness + S3 cheap-tier gauntlet** (≥100 runs/model, real schemas, real transport; Inspect-AI-vs-build decided by ADR) | AGT-09, GRD2-03 | Gauntlet = OPS-1's eval-of-record |
| 3 | **Gold set 45 → ~200** — human-authored, five strata, IRR-gated (§5.3). The project's largest human-time item; cannot be delegated to AI | GRD2-01, Phase 0A | Admission κ ≥ 0.6; ≥90–100 fail items near the cut |
| 4 | **Judge re-baseline** — Opus vs Sonnet-workhorse bake-off + aggregation & schema arms (§5.5) + prompt registry (AGT-06) | GRD2-04 | **Phase 0A HARD GATE: ≥85% agreement AND zero false-pass AND zero rank inversions, reproduced on pinned model.** Below it: no-go recorded, S3 slice does not start |
| 5 | Effort sweeps (before any >medium default locks) + calibration layer defaulting to identity | GRD2-06 (0B) | Sweep records committed |
| 6 | **S3 class-D migration bake-off — BEFORE OCT 15** | new: registry class-D | Owner + rehearsed fallback config as registry fields |

## 9.3 Slice activation (which product slice turns which workloads on)

| Slice | Workloads activated | Notes |
|---|---|---|
| S1 (done) | CW-1 (built, eval owed) · clarify seam of CW-3 | Ran on `LLM_PROVIDER=fake`; eval debt recorded |
| Phase 0A/0B | CW-20 (as the human gold-set program) · CW-13 baseline · harness | Gates everything downstream |
| S2 | CW-3 (full) · CW-4 · CW-5 · CW-6 · CW-7 · CW-17 · CW-19 · EMB-1 · whole-bar ADR-0011 | CW-17 needs the D5 dual-authoring reviewer (human dependency, long lead) |
| S3 | CW-8 · CW-9 · CW-10 · CW-11 · CW-12 · CW-18 | Only if Phase 0A passed |
| S4 | CW-14 · CW-15 · S4-auditor standing duty (needs D5) | Guidance behind D8 checker |
| S5 | Readiness surfaces consume everything; no new workloads | Numeric display still gated by 0B (GRD-32 flag) |
| Phase 2 | CW-16 · CW-22 · Adaptation agent (deferred, menu-only) | Do not build ahead |

## 9.4 Dated obligations

Single source: models.md §3.7 calendar. The two that bite first: **Oct 15** S3 bake-off;
**~Sep 29** Sonnet 4.5 retirement (veto only — nothing depends on it today).

## 9.5 Open decisions & ratification queue (nothing self-executes)

| # | Decision | Options on the table | Owner | Blocks |
|---|---|---|---|---|
| D5 | Cross-vendor data gate | Vendor retention/ZDR attestations + credential entries before S4/dormants touch real content | user | S4 standing audits; Sol/Terra activation |
| R1 | CW-20 Terra offline exception | Ratify vs use S4 Gemini (familiarity risk) | user | Fake generation at scale |
| R2 | MiniCheck local verifier (local model #2) | Ratify (eval + owner already named) vs strike | user | CW-4 veto lane |
| R3 | Sol/Terra dormant alternates | Activate (needs D5) vs strike (S1 failures = retry/defer only) | user | Availability posture |
| R4 | CW-21 unsourced row | Accept as-is vs commission research | user | CW-21 build |
| R5 | Whole-bar-in-context fork | Whole bar for single-role assessment vs retrieval fragments → **ADR-0011** | user + architect pass | CW-8/9/13 context design |
| R6 | Eval harness base | Inspect AI vs hand-rolled → ADR | build-time | AGT-09 |
| — | Prior-standing product holds | 0.4 numeric-score scoping (CON-2) | user | S3/S4 demo copy |

## 9.6 Change log

- 2026-09-01 — Suite created (v1): Registry v2 + Mapping v2 transcribed from their locks;
  ADRs 0001–0010 backfilled; evidence dispositions from `research/p3_*.md` recorded in §5.5.
  Suite changes follow §2.7 change control + the §5.7 eval rule; this log records each.
