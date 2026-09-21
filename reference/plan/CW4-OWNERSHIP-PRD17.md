# CW-4 ownership per PRD v1.7

Source: `D:\SDKPOC\Caliber-PRD-v1.7.html` (read in full). No engineering docs consulted.

## 1. The answer in one sentence

PRD v1.7 never uses the term "CW-4" and never describes a per-quote claim–evidence adjudication step at all; the closest thing in its own model — assigning each claimed skill an evidence strength of `none / mentioned / demonstrated / led` — sits in the onboarding/capture stage (§7.1) and lands in the `SkillProfile`, which §10.1's agent-contract table makes the **[1] Profiler's** output, so the Profiler is the only agent that could carry it — but the PRD never says so in words, it leaves §7.1's "cross-check mechanism" in the passive voice with no agent named.

Short form: **Profiler, by output-schema inference only — not by explicit assignment. The Role Analyst is ruled out. The term "CW-4" and the Opus-5/high-effort routing are not in the PRD.**

## 2. Supporting quotes, with sections

**§7.1 — Signup & onboarding — capture the full career** (the evidence ladder itself; note the passive voice, no agent named):

> "Cross-check mechanism: each claimed skill gets an evidence strength (none / mentioned / demonstrated / led). Claimed-but-weak → flagged probe area, targeted first — mirroring what a real interviewer attacks."

**§7.1** (the derived-signals sentence, same stage, also agentless):

> "Signals derived: depth score per skill (claimed vs evidenced), ownership level (contributor/owner/leader), recency, seniority signals (scope, ambiguity, cross-team, tradeoffs)."

**§10.1, agent-contract table, row [1]** (the only place the PRD attaches those fields to an owner):

> "[1] Profiler — Understand the candidate's experience; normalize the SkillProfile; flag thin areas and claimed-but-weak skills. Input (from app): Parsed resume text and/or manual Q&A answers; previous draft profile (on re-run). Output (validated, saved): SkillProfile (skills, evidence strength, ownership, recency, seniority signals) + missing_fields[]"

**§10.1, agent-contract table, row [2]** (rules the Role Analyst out — it has no evidence field anywhere in its output):

> "[2] Role Analyst — Understand the target role + analyze the JD; assemble/adapt the role-bar; recommend fitting roles. Input (from app): Confirmed SkillProfile; target role or JD; base RoleBar (if one exists). Output (validated, saved): RoleBar (JD overlay applied, versioned) + role recommendations with fit labels"

**§7.3 — Gap analysis engine & the role-bar** (the Gap Analyst *consumes* evidence strength, confirming it is assigned upstream of [3]):

> "Inputs: the SkillProfile (with evidence strength), the Role-Bar for the target role, years of experience, and — if provided — the JD."
> "Gap computation (per sub-skill): pull evidence strength → compare to expected depth for their experience level (JD-adjusted) → gap size = required − demonstrated …"

**§8-A, FR-A5** (same placement, in the ingestion engine — the engine §12 maps to slice S1 / step [1]):

> "FR-A5: Output a normalized demonstrated-skills profile with per-skill evidence strength."

**§12, Phase 1 slice table** (ties the ingestion engine to the Profiler):

> "S1 — Onboarding + confirm (manual entry, then LLM resume-parse; completeness gate: 100% captured + confirmed). Pipeline steps added: [1] Profiler"

## 3. What each of the two agents produces, per the PRD

**[1] Profiler (§10.1 table; §7.1)**
- Inputs: parsed resume text and/or manual Q&A answers; previous draft profile on re-run.
- Outputs: `SkillProfile` — skills, **evidence strength**, ownership, recency, seniority signals — plus `missing_fields[]`.
- Responsibility line: "normalize the SkillProfile; flag thin areas and **claimed-but-weak skills**."
- §7.1 v1.7 pipeline note: "the Profiler returns the structured SkillProfile and a list of missing or thin fields. The app, not an agent, runs the completeness gate."
- Data model §10: "SkillProfile (demonstrated skills, evidence strength, source artifacts)."

**[2] Role Analyst (§10.1 table; §7.2)**
- Inputs: confirmed SkillProfile; target role or JD; base RoleBar if one exists.
- Outputs: `RoleBar` (JD overlay applied, versioned) + role recommendations with fit labels (Strong fit / Stretch / Not yet, §7.2).
- Nothing in its output object concerns the candidate's own claims or evidence. It reads the confirmed profile but writes only the target-side standard.

Conclusion from the schemas alone: an evidence verdict can only ride in `SkillProfile.evidence_strength`, and `SkillProfile` is written by [1] and read by [2], [3], [4], [5]. The Role Analyst has no field to put it in.

## 4. Ambiguities and contradictions — stated, not resolved

1. **Nowhere is the judging act assigned to an agent in prose.** §7.1 says "each claimed skill *gets* an evidence strength" — passive, no actor. The PRD never says "the Profiler decides whether the evidence supports the claim." §7.1's body text appears unrewritten from earlier versions (only a "v1.7 Pipeline note" was appended); the Profiler attribution rests entirely on §10.1's output schema. This is inference from a field list, not a stated requirement.
2. **No per-quote / per-claim granularity anywhere.** The PRD's unit is "each claimed skill," not "this quoted sentence from the resume." There is no artifact in the data model (§10) that pairs a resume quote with a skill and a verdict. The Evaluator's "evidence quotes" (§10.1 row [6]) are quotes from the candidate's *assessment answer*, not from the resume — a different object at a different pipeline stage.
3. **"Claimed-but-unproven" is tagged in two places.** §10.1 [1] says the Profiler flags "claimed-but-weak skills"; §7.3 says "Claimed-but-unproven skills are tagged probe-first regardless of score" (Gap Analyst), and FR-B4 makes "claimed-but-unproven" a Gap Analyst bucket. The PRD does not say whether the Profiler's flag and the Gap Analyst's bucket are the same tag re-emitted or two separate judgments.
4. **"Claimed vs demonstrated" appears at three levels with no reconciliation.** Per-skill evidence strength (§7.1, Profiler output); the "leveling read (claimed vs demonstrated level)" produced by **[3] Gap Analyst** (§10.1 row [3]); and §7.5's "Honesty moment: this is where 'you present as Senior but demonstrate Mid' gets evidence" — placed inside the *assessment*, i.e. steps [5]/[6]. So "does the evidence support the claim" is answered once cheaply at capture and again expensively at assessment, and the PRD does not label either as authoritative.
5. **Two different ladders, easy to confuse.** The evidence ladder is `none / mentioned / demonstrated / led` (§7.1). The role-bar depth ladder is "aware → can build → can design → can defend under load" (§7.3), which is *expected* depth per experience level, not evidence. The gap computation in §7.3 compares one against the other without stating a mapping between the two scales.
6. **Four levels, not three.** The question's "mentioned / demonstrated / led" omits `none`, which §7.1 includes.
7. **No model or effort routing is specified per agent.** §9 says only: "Models (provider-abstracted, D10): best model per task — strong reasoning model for grading, cheaper models for MCQ generation. Candidates: Claude (Opus/Sonnet), OpenAI models/agents, founder's Azure LLM." §10.1 lists "Model routing per agent (provider abstraction, D10)" under "What the app (not an agent) owns." "Opus 5," a named effort level, and any per-agent model table are **absent from PRD v1.7**.
8. **Open question §Appendix F touches [2]'s scope** without touching evidence: "Role Analyst for the beachhead: while the Senior AI Engineer bar is founder-authored, [2] only applies the JD overlay and role recommendations. Confirm whether to skip it when there is no JD." This narrows the Role Analyst further; nothing suggests it ever judges candidate evidence.

## 5. Where the evidence ladder / skill evidence levels appear

Exactly once, in **§7.1** ("Signup & onboarding — capture the full career"), under the heading **"Cross-check mechanism"**, inside the onboarding/capture stage. §7.0's journey table assigns that stage to **[1] Profiler**; §10.1's contract table carries "evidence strength" as a field of the Profiler's `SkillProfile` output; §10's data model repeats it ("SkillProfile (demonstrated skills, evidence strength, source artifacts)"); FR-A5 (§8-A) restates it as an ingestion-engine requirement. It is referenced again only as an **input** in §7.3 (Gap Analyst) and §10.1 row [3].

The string "CW-4" (and "CW", and "workload") does not occur anywhere in PRD v1.7.

## 6. Bottom line for a reader deciding implementation

- If you need a claim–evidence verdict in a v1.7-faithful build, the PRD's model puts the field in the Profiler's output and nowhere else.
- But the PRD does **not** specify it as a distinct, expensive judging *step*, does not give it a per-quote unit of work, does not name an agent as the judge in prose, and does not assign it a model or effort. Treating it as a separately-routed high-effort workload is an engineering elaboration on top of PRD v1.7, not something v1.7 states.
- The Role Analyst is not a candidate: its contract (§10.1 row [2]) produces only a JD-adjusted RoleBar and fit-labelled role recommendations.
