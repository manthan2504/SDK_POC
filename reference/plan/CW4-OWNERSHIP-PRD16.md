# CW-4 (claim–evidence verdict) ownership — per PRD v1.6 only

Source: `D:\SDKPOC\Caliber-PRD-v1.6.pdf` (20 pages, full text extracted with pdfplumber and read end to end).
Scope rule honoured: v1.7 (HTML or PDF), `reference/`, and `D:\Caliber\docs\` were **not** consulted.

---

## 1. The answer, in one sentence

**Neither — v1.6 never uses the term "CW-4" and never names an agent for the claim–evidence verdict at all; but the thing CW-4 describes (rating a claimed skill `none / mentioned / demonstrated / led`) is defined in v1.6 as part of the onboarding/capture stage and lives on the artifact the Profiler owns (the SkillProfile), so it is emphatically *not* the Role Analyst's.**

The PDF contains no occurrence of "CW-4", "CW-", "claim–evidence verdict", or any effort-level/model assignment per work item. "Opus" appears once, only as a candidate provider model (§9, p14). That vocabulary is not from this PRD.

---

## 2. The quotes that support it

**a. The ladder itself is defined inside §7.1 "Signup & onboarding — capture the full career" (p7):**

> "Cross-check mechanism: each claimed skill gets an evidence strength (none / mentioned / demonstrated / led). Claimed-but-weak → flagged probe area, targeted first — mirroring what a real interviewer attacks."

Note the passive voice: *"gets an evidence strength."* v1.6 never says **who** assigns it.

**b. Same section, same stage, the derived signals (§7.1, p7):**

> "Signals derived: depth score per skill (claimed vs evidenced), ownership level (contributor/owner/leader), recency, seniority signals (scope, ambiguity, cross-team, tradeoffs)."

**c. The functional requirement puts it in engine A, Context / ingestion (§8.A, FR-A5, p12):**

> "FR-A5: Output a normalized demonstrated-skills profile with per-skill evidence strength."

**d. The data model attaches evidence strength to the SkillProfile (§10, p14):**

> "SkillProfile (demonstrated skills, evidence strength, source artifacts)"

**e. The Profiler is the agent that produces/normalizes that SkillProfile (§10.1, p14):**

> "Profiler — understand the candidate's experience; normalize the SkillProfile."

**f. The Role Analyst is given no evidence responsibility whatsoever (§10.1, p15) — this is its complete definition in v1.6:**

> "Role analyst — understand the target role + analyze the JD; assemble/adapt the role-bar."

One line. Its inputs are the target role and the JD. The candidate's profile is not named as an input to it anywhere in §10.1.

**g. Downstream, evidence strength is *consumed*, not produced, by the gap stage (§7.3, p9):**

> "Inputs: the SkillProfile (with evidence strength), the Role-Bar for the target role, years of experience, and — if provided — the JD."

> "Gap computation (per sub-skill): pull evidence strength → compare to expected depth for their experience level (JD-adjusted) → gap size = required − demonstrated → priority = gap size × weight × recency."

"Pull evidence strength" is the decisive verb: by §7.3 the verdict already exists and is being read, not made.

Chain: §7.1 defines the ladder at capture → FR-A5 makes it the ingestion engine's output → §10 makes it a SkillProfile field → §10.1 makes the Profiler the SkillProfile's owner. The Role Analyst is nowhere on that chain.

---

## 3. What v1.6 says each of the two agents produces

**Profiler** (§10.1 p14, plus §8.A p12, §7.1 p7):
- Produces the **SkillProfile**: "normalized demonstrated-skills profile with per-skill evidence strength" (FR-A5).
- Backing capture (§7.1): per-company work-experience blocks and per-project blocks (role, responsibilities, processes, achievements/impact, stack, scale & constraints, hardest problem).
- Derived: depth score per skill (claimed vs evidenced), ownership level, recency, seniority signals; claimed-but-weak → probe-area flag.
- Gated by the completeness gate (§7.1, p8): "This confirmed profile is the single source of truth for every downstream stage."

**Role analyst** (§10.1 p15, plus §7.3 p9):
- Produces the **Role-Bar**: "a structured, versioned definition of what a specific role is actually tested on, calibrated by experience level. Not a syllabus — the real bar."
- Structure: competency areas → sub-skills, each with "expected depth per experience level (aware → can build → can design → can defend under load); weight (how heavily tested); how it's tested (MCQ / practical / open-ended)."
- "JD overlay — a supplied JD re-weights the bar toward what that role asks for (D7)."
- Versioned.

The Role-Bar carries **expected** depth for a role. The SkillProfile carries **evidenced** depth for a person. A claim–evidence verdict is a statement about a person's resume, so it can only ride on the SkillProfile — the Profiler's artifact. The Role-Bar has no per-candidate fields at all.

---

## 4. What in v1.6 could reasonably be read as putting evidence judging on the role side

This is the real finding, and it is not trivial. Four things in v1.6 point that way:

**(i) §7.2 "Role selection + honest leveling" (p8) — the strongest one.** The role-selection stage is explicitly given the job of re-reading the candidate's demonstrated depth and issuing a verdict on it:

> "Our honest read — from the real profile, Caliber recommends roles that genuinely fit, each with a fit label"

> "Principle — honesty over flattery. Caliber tells the truth: 'you present as Senior, but your demonstrated depth maps to Mid for this bar; here's what closes it.'"

That is a claimed-vs-demonstrated judgement, written into the *role* section, consuming the profile. Anyone mapping §7.2 onto the agent named "Role analyst" would conclude the Role Analyst re-judges evidence.

**(ii) §7.2's approved candidate-facing copy (p8)** describes an evidence/ownership verdict in so many words, again inside the role section:

> "We conduct a structured review of your entire career path — for each role, the specific projects you delivered, the tech/tools you used, and your exact contributions. The goal is not to test 100% mastery of a language or tool, but to validate that your practical knowledge matches your years of experience — to verify genuine ownership, benchmark you for the assessment, and align your profile with the best target roles."

"Verify genuine ownership" is exactly CW-4's job description, and it sits in the role-selection section, not the capture section.

**(iii) §7.3's title and framing (p9).** The section is called "**Gap analysis engine & the role-bar**" — it bundles the Role Analyst's artifact with a stage that takes "the SkillProfile (with evidence strength)" as input and computes `required − demonstrated`. A reader skimming for "where is evidence weighed against the bar" lands on the section whose title contains "role-bar."

**(iv) "Re-weighting" language attaches to the role side (§7.3, p9):** "JD overlay — a supplied JD re-weights the bar." That re-weighting is of the *bar's* weights, not of the candidate's evidence — but the verb is the same one someone would use for re-weighing evidence.

Conclusion on this point: v1.6 does contain a second, role-stage judgement about the candidate's demonstrated level (§7.2 honest leveling), distinct from the capture-time evidence ladder (§7.1). v1.6 never says which agent owns honest leveling. That silence is the most plausible origin of a belief that the Role Analyst owns the claim–evidence verdict.

---

## 5. Ambiguities in v1.6 — stated, not resolved

1. **No agent is ever named for the evidence ladder.** §7.1 says a claimed skill "gets an evidence strength"; it never says by the Profiler, by an agent, or by the resume parser. FR-A5 assigns it to *engine* A (Context / ingestion), and §10.1's agent list is a separate taxonomy that is never mapped onto the FR engines. The Profiler attribution is inferred from the SkillProfile chain, not stated.
2. **v1.6 contains two different "evidence" judgements and the phrase "claim–evidence verdict" could mean either.** (a) The capture-time ladder `none / mentioned / demonstrated / led` (§7.1) — matches CW-4's description. (b) The AI judge's answer grading, which returns "per-dimension score + specific gaps + **evidence quotes**" (§7.7 p11; §9 p14; FR-D3 p13). The word "verdict" in v1.6 appears *only* in grader contexts (p15 "verdict agreement"; Appendix C p19 "Verdict = pass if overall ≥ operational threshold"). So "verdict" is grader vocabulary in v1.6 while `mentioned/demonstrated/led` is capture vocabulary — the term "claim–evidence verdict" straddles the two and v1.6 does not join them.
3. **Honest leveling has no owner.** §7.2's "you present as Senior but demonstrate Mid" read, and §7.5's "Honesty moment: this is where 'you present as Senior but demonstrate Mid' gets evidence" (p10), describe a cross-stage judgement that v1.6 assigns to no agent in §10.1. It is neither clearly the Profiler's nor clearly the Role Analyst's.
4. **No appendix defines an evidence ladder.** Appendix B (glossary, p18–19) has Role-bar, completeness gate, assessment plan, probe set, gate, gap guidance, reassessment loop, grader/judge, beachhead role, provider abstraction, honest leveling — but **no entry for "evidence strength."** Appendix C is the 5-dimension grader rubric only. Appendix D's sample role-bar has a "Claimed-but-unproven" bucket ("anything asserted on the resume ... that the probe must actually verify", p19) but says nothing about who rated it.
5. **§10.1 gives no inputs/outputs per agent.** Each of the eight agents is one clause. There is no I/O table in v1.6, so "the Role Analyst's inputs" cannot be read off the document — it can only be inferred from §7.2/§7.3, which is where the confusion is seeded.

---

## Extraction quality

Text extraction was clean throughout all 20 pages; every quote above is verbatim. The only defects are `(cid:0)` placeholders where the source used emoji/icon glyphs (fit labels in §7.2 p8; the checkmarks in §12 p15–16). No quote above depends on those glyphs. v1.6 has no printed page numbers, so citations are PDF page indices.
