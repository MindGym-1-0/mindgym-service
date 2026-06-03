# Plan: Personalise Maya's Session Scripts with Onboarding Context

## Goal

Maya currently only knows what the user tells her in the session setup flow (feeling, prep type, company, anxiety). She knows nothing about the person. This plan wires the user's onboarding data into the session prompt so Maya feels like a coach who actually knows them — their search situation, their emotional pattern, where they're stuck.

The "wow, this app actually gets me" feeling.

---

## What We Are NOT Changing

- `src/prompts/system_prompt.py` — untouched
- Frontend — no new screens, no new API fields
- `OnboardingRequest` / `SessionStartRequest` Pydantic models — untouched
- JSON output contract / `SessionScript` model — untouched

---

## The 5 Onboarding Fields to Use

All 5 confirmed in the DB (migration `20260529_onboarding_full_schema.sql` + `009_users_onboarding_expansion.sql`):

| Field | DB column | Values |
|---|---|---|
| Employment status | `employment_status` | `employed`, `unemployed`, `laid_off` |
| How long searching | `unemployed_duration` | `1m`, `2m`, `3m`, `6m`, `1y` (DB) / `1y+` (Pydantic) — handle both |
| Core emotional struggle | `emotional_challenge` | `rejection_silence`, `interview_anxiety`, `imposter_syndrome`, `burnout`, `uncertainty`, `financial_pressure` |
| Target role (free text) | `target_role_note` | e.g. "Senior PM in fintech" |
| Normal anxiety level | `baseline_anxiety` | 1–10 |

**Skipped:** `target_role_category` — session already has `company` + `role` as free text, which is more specific.

---

## Enum Translation Tables

These are computed in Python before the prompt is built. Gemini never sees the raw enum values.

### `emotional_challenge` → human sentence

| Enum | Sentence |
|---|---|
| `rejection_silence` | The hardest part of their search has been applying and hearing nothing back — the silence. |
| `interview_anxiety` | Their biggest challenge is the anxiety that builds before interviews. |
| `imposter_syndrome` | They carry a feeling of not belonging or not being qualified enough. |
| `burnout` | The search has worn them down — they're running on fumes. |
| `uncertainty` | They're unsure whether they're on the right path or making the right moves. |
| `financial_pressure` | The financial pressure of their situation adds real weight to every step. |

### `employment_status` + `unemployed_duration` → combined sentence

| Status | Duration | Sentence |
|---|---|---|
| `employed` | — | They're currently employed and exploring new opportunities. |
| `unemployed` | `3m` | They've been searching for about 3 months. |
| `laid_off` | `3m` | They were laid off about 3 months ago. |
| `laid_off` | `1y` or `1y+` | They were laid off over a year ago. |
| `unemployed`/`laid_off` | null | They're currently unemployed and actively searching. |

### `baseline_anxiety` vs today's `anxiety_level_before` delta

| Condition | Sentence |
|---|---|
| Today within ±2 of baseline | Today's anxiety is close to their normal level. |
| Today 3+ above baseline | They're significantly more anxious than usual today. |
| Today 3+ below baseline | They're calmer than usual today. |

---

## Where the Block Goes in the Prompt

Between the situation line and `--- SESSION INPUTS ---`:

**Before (no onboarding):**
```
This person has an interview tomorrow — Product Manager at Stripe.
Right now they feel overwhelmed, and they want to feel calm by the end.

--- SESSION INPUTS ---
```

**After (with onboarding):**
```
This person has an interview tomorrow — Product Manager at Stripe.
Right now they feel overwhelmed, and they want to feel calm by the end.

About this person: They were laid off about 3 months ago. The hardest
part of their search has been applying and hearing nothing back — the
silence. They're aiming for Senior PM in fintech. They're significantly
more anxious than usual today.
Use this to inform tone. Do not reference it directly in the script.

--- SESSION INPUTS ---
```

The guardrail line is required — without it Gemini tries to prove it read the context by shoving it into the script.

---

## Implementation Steps

### Step 1 — `src/prompts/user_prompt.py`

Add `_build_about_block(user_context: dict | None, anxiety_level_before: int) -> str`:
- Translates 5 onboarding fields into 3–4 prose sentences using the tables above
- Returns empty string if `user_context` is None or all fields are None
- Handle both `"1y"` and `"1y+"` in the duration map — don't fix DB/Pydantic mismatch, just handle both values gracefully
- Block ends with guardrail line

Add to `build_user_prompt()` signature:
- `user_context: dict | None = None`
- `anxiety_level_before: int = 5` (default keeps backward compatibility — 5 is neutral)

Insert `_build_about_block()` output between situation line and `--- SESSION INPUTS ---`.

### Step 2 — `src/lib/prompt_builder.py`

Add to `build_prompt()` signature:
- `user_context: dict | None = None`

Pass both `user_context` and `anxiety_level_before` through to `build_user_prompt()`. No logic — pure pass-through.

### Step 3 — `tst/eval/eval_script_quality.py`

Add optional `user_context` support to `run_scenario()`. Prompt at the start of each run:
```
Include onboarding context? (y/n):
```
If yes → pass hardcoded test dict. If no → pass None.

Hardcoded test dict:
```python
{
    "employment_status": "laid_off",
    "unemployed_duration": "3m",
    "emotional_challenge": "rejection_silence",
    "target_role_note": "Senior PM in fintech",
    "baseline_anxiety": 7,
}
```

### Quality Gate (between step 3 and step 4)

Run **two scenarios**, each twice (with and without context):

**Scenario A** — High-anxiety Google PM interview (anxiety 8, overwhelmed, interview_tomorrow)
**Scenario B** — Rejection recovery (no company/role, discouraged, rejection_recovery) — this is the critical one. `emotional_challenge: rejection_silence` should make the biggest difference here. If "the hardest part has been the silence" doesn't noticeably shift how Maya handles a rejection recovery session, the feature isn't earning its keep.

Read phase1 and phase2 side by side for each scenario.

**Pass:**
- Phase 1/2 feel noticeably different between the with/without runs in both scenarios
- Maya's tone shifts — heavier, more specific acknowledgment — without explicitly referencing the onboarding facts
- No recitation ("I know you were laid off...")

**Fail:**
- No visible difference in either scenario
- Maya explicitly references the onboarding data

Both scenarios must pass. If either fails → tweak `_build_about_block()` and re-run.

### Step 4 — `src/lib/session_service.py` *(only after quality gate passes)*

In `start_session()`, before calling `build_prompt()`, add one DB read:
```python
SELECT employment_status, unemployed_duration, emotional_challenge,
       target_role_note, baseline_anxiety
FROM users WHERE id = user_id
```
Pass result as `user_context` dict to `build_prompt()`.
If fetch fails or returns nothing → pass `None` → session works exactly as today.

Note: `_ensure_user_profile()` cannot be reused — `ignore_duplicates=True` means it returns nothing on conflict. Separate query is correct.

---

## Quality Gate Results (2026-06-01)

### Status: Steps 1–3 built and tested. Step 4 pending.

### Scenario A — High-anxiety interview (Google, AI Engineer, anxiety 9, overwhelmed)
- Phase 2 difference: "asked a lot of you" → "asked **so much** of you" — subtle but present
- `rejection_silence` and `laid_off` context not visibly shaping the interview scenario — expected, interview is the dominant signal
- **Verdict: marginal pass**

### Scenario B — Rejection recovery (no company, discouraged, anxiety 6)
- Phase 3 clearly personalised: *"moving forward, knowing you are still a **Senior PM, ready to contribute in fintech.** You're just recalibrating your aim."* — `target_role_note` coming through
- Phase 5 improved: more specific ("your specific skills") vs generic
- Phase 2 marginally worse with context — more abstract, `rejection_silence` not clearly shaping it
- **Verdict: partial pass — target_role_note working, emotional_challenge not yet visible in phase 2**

### Outstanding tweak before step 4
Phase 2 is where `emotional_challenge` should land most strongly (per the plan), but it's not showing up clearly. Options:
1. Strengthen the guardrail to explicitly direct phase 2: *"especially let the emotional_challenge inform how phase 2 opens"*
2. Or accept current state and wire step 4 — real user data may produce stronger results

Confirm approach with Opus before proceeding to step 4.

### Hype guard fix (done)
Removed `"energy"` from `_HIGH_ANXIETY_HYPE_WORDS` — was causing false positive on `"nervous energy"`. `"energized"` still covers the real hype case.

---

## Backward Compatibility

Every new param defaults to `None`. If a user hasn't onboarded or fields are missing, `_build_about_block()` returns empty string and the prompt is identical to today. Zero risk to existing users.

---

## Test Example

User profile:
```
employment_status: laid_off
unemployed_duration: 3m
emotional_challenge: rejection_silence
target_role_note: Senior PM in fintech
baseline_anxiety: 7
```

Session today:
```
preparation_for: interview_tomorrow
company: Stripe
role: Product Manager
current_feeling: overwhelmed
anxiety_level_before: 8
desired_feeling: calm
time_available: 10 min
```

Expected about block:
```
About this person: They were laid off about 3 months ago. The hardest part
of their search has been applying and hearing nothing back — the silence.
They're aiming for Senior PM in fintech. They're significantly more anxious
than usual today.
Use this to inform tone. Do not reference it directly in the script.
```
