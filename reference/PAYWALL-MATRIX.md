# Paywall matrix — the D3 boundary, surface by surface

**Status: LOCKED.** §5.1 of the PRD, decided 2026-08-30. Moving a row across the
line is a change to a locked decision and needs an ADR, not a commit.

> *Free through the aha, charge for the assessment.* Value lands before the ask;
> the paywall sits right before they find out if they can actually pass.

`ARC-14` implements this. `GRD-22` will test it as a table — that suite should
read this file, not re-derive the boundary from the code.

---

## The rule that makes the rest legible

**The absence of a grant is the free tier.** There is no tier column, no
`is_premium` flag and no plan name anywhere in the schema. A user with no rows in
`user_entitlement` is a free user. This is why the free surfaces below have no
entitlement to name: nothing gates them, so nothing can accidentally gate them.

Consequently the only way to move the wall is to add a member to `PaidFeature`
(`api/src/caliber/enums.py`) and a dependency to a route. Both show up in a diff
as exactly that.

---

## Free — through the aha

| Surface | Route | PRD | Built |
|---|---|---|---|
| Signup, onboarding, capture, confirm | `/api/v1/auth/*`, `/api/v1/profile*` | §7.1 | ✅ |
| Gap map | `GET /api/v1/profile/gap-map` | §7.3 | ✅ arithmetic only |
| Honest leveling read | — | §7.2, §6 | ❌ **not built (S5)** |
| Assessment-plan preview | `GET /api/v1/profile/assessment-plan` | §7.4 | ✅ arithmetic only |
| The upgrade wall itself | `GET /api/v1/upgrade` | §5.1 | ✅ |
| Notify-me capture | `POST/DELETE /api/v1/upgrade/interest` | GRD-23 | ✅ |

### The honest leveling read is a real hole, not an oversight

`WORKLOG` COM-2 records it: §5.1 sells the leveling read as part of the free
tier, but it is scheduled in **S5** while the wall goes up at the end of **S2**.
So the wall currently stands on a free tier missing a quarter of what it names,
and any activation funnel measured now is measuring an incomplete offer.

The chosen handling is to **say so**. `GET /api/v1/upgrade` returns
`available: false` on that item and the page renders it as still coming. The
alternative — listing it as though it shipped — would put a false claim on the
one screen whose entire job is to be believed about what you get for money.

---

## Paid — the assessment and everything the loop needs

| Surface | `PaidFeature` | PRD | Built |
|---|---|---|---|
| Topic-by-topic assessment | `assessment` | §7.5–7.6 | ❌ S3 |
| Gap guidance | `guidance` | §7.7 | ❌ S4 |
| Reassessment loop | `reassessment` | §7.7 | ❌ S4 |
| Progress dashboard | `progress_dashboard` | §7.8 | ❌ S5 |

Only one paid route exists today — `GET /api/v1/assessment` — and it serves no
content. It exists so the gate is real and tested before S3 has anything to hang
on it: a free caller gets **402**, an entitled caller gets **204 No Content**.
That is the honest pair of answers while §7.5 is unbuilt.

---

## Status codes

| Code | Meaning here |
|---|---|
| **401** | Not signed in. Checked **before** entitlement — a 402 to an anonymous caller would confirm the endpoint exists to someone who has not earned that answer. |
| **402** | Signed in, no grant. Chosen over 403 deliberately: 403 says *you may never*, 402 says *you may, once you have paid*. The UI needs to tell those apart to know whether to offer the upgrade path. |
| **409** | Profile not confirmed. Unrelated to payment — §7.1's gate, and it fires on free surfaces too. |

---

## Granting access without a payment provider

Billing is Phase 3. Until then the only writer is an operator script — never an
API route, because a self-service entitlement endpoint "for local dev" is one
misconfigured environment away from being the product.

```bash
uv run python scripts/grant_entitlement.py list   someone@example.com
uv run python scripts/grant_entitlement.py grant  someone@example.com assessment
uv run python scripts/grant_entitlement.py grant  someone@example.com --all --days 30
uv run python scripts/grant_entitlement.py revoke someone@example.com assessment
```

Grants are idempotent and carry a `source` and optional `note`, so "why does this
account have access?" always has an answer.

---

## What the wall deliberately does not do

- **No price.** §5.1 puts the pricing model in Phase 3 and locks only the
  boundary. A number on the page would be inventing a commercial decision.
- **No checkout.** There is no payment provider. A live-looking pay button on a
  screen about honesty would be the one dishonest element on it.
- **No second copy of anyone's PII.** Notify-me stores a user id, a timestamp and
  which surface the click came from. The candidate's email is already on
  `app_user`; duplicating it would add a deletion obligation (ARC-18) and no
  information.
- **No irreversible signup.** `DELETE /api/v1/upgrade/interest` removes the row.
  A list you cannot leave is a dark pattern.
