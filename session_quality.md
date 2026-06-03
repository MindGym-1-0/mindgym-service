# Session Quality — How We Improve Maya

## TL;DR for any agent working on the session pipeline

We make Maya's scripts better through **prompt engineering, measured by an eval loop.**
Nothing else. We do **not** fine-tune the model, and we do **not** add libraries or
repos to "enhance" quality. The quality lives in the system prompt and the user prompt,
and we prove it improved by running the eval tool before and after every change.

If you are about to suggest fine-tuning, a new dependency, or a framework to make
sessions feel better — stop. That is not the approach. The approach is: change the
prompt, run the eval, compare scores, keep or revert.

---

## Why prompt engineering, not fine-tuning

- **We don't know the target well enough to fine-tune yet.** Fine-tuning locks in a
  fixed notion of "good." We're still discovering what "good" means for Maya. Prompting
  is reversible in seconds; fine-tuning is a commitment.
- **We don't have the data.** Fine-tuning would need hundreds of high-quality example
  scripts we don't have.
- **Iteration speed.** Prompt change → re-run eval → see the result in minutes. That
  loop is the whole point. Fine-tuning breaks it.
- **It's an MVP.** Fine-tuning is a later-stage tool we may never need. Don't reach for
  it now.

## Why not skills / repos / libraries

There is no package that makes a coaching script feel alive. That's craft, and it lives
in the prompt. Adding a dependency to chase "wow" adds surface area without adding
quality. Keep the system lean: prompt in, script out, eval scores it.

---

## What "alive" means (so the prompt can aim at it)

A generic script could be addressed to anyone. An alive script proves it heard *this*
user. Five levers, roughly in order of impact:

1. **Specificity over abstraction** — name the actual moment ("the pause before the
   first question at the Stripe final round"), not the category ("your interview").
2. **Sensory anchoring** — give the user something to do with body or attention. The
   body is the only thing fully present during the script.
3. **Naming the resistance** — meet the user's `current_feeling` before moving them
   toward `desired_feeling`. Acknowledge the weight first.
4. **Asymmetric rhythm** — vary sentence length. Long sentences open space; short ones
   land. Uniform cadence is the #1 tell of generic AI writing.
5. **Restraint** — trust silence. Don't pile on metaphors or stack affirmations. One
   quiet line that doesn't ask anything of the reader.

Note: we stream **text** word-by-word (typewriter animation in
`sessions/active/page.tsx`). The user is *reading*, not listening. So **whitespace and
line breaks are part of Maya's rhythm** — a break where she'd pause, a short line
standing alone. Audio narration is post-MVP; if it ever ships, the TTS reads these same
scripts, so script quality is the source of audio quality either way. We tune the same
thing regardless.

---

## Maya's voice (what the prompt enforces)

**Who she is:** a sports psychologist who's worked with performers for years. Direct
without sweetness. Plainspoken because she's earned it. Not impressed by stakes, not
performing care.

**Rhythm:** mostly short sentences, occasional long ones to carry a visualization.
Deliberate fragments. Present tense, second person ("you"), rarely "we."

**Never says:**
- "amazing / incredible / powerful"
- "journey / path forward"
- "you've got this / crush it"
- "take a moment to"
- "it's important to remember that"
- decorative three-item lists
- questions she doesn't want answered

The highest-leverage way to teach voice in the prompt is **contrast examples** —
"Maya does not say X, she says Y" — not adjectives describing her tone.

---

## The 5-phase emotional arc

Phases are not five equal blocks. Each has a distinct job, energy, and grammar.
The arc is: **decelerate → locate → embody → consolidate → release** — a wave that
builds in phase 3, peaks in 4, releases in 5. NOT a steadily rising hype curve.

| Phase | Name | Feels like | Job |
|-------|------|------------|-----|
| 1 | Breathe | Decelerate | Slow the body down. No event name, no future tense, no hype. Longest in feel, shortest in word count. |
| 2 | Ground | Locate | Acknowledge `current_feeling`, give it permission. Anchor to what's real and already done. |
| 3 | Rehearse | Inhabit | The heart. Name company + role (Mode 1). Most vivid, most sensory, puts the user in the room. |
| 4 | Anchor | Claim | Lock one thing (a sensation, a phrase) the user can return to tomorrow. |
| 5 | Close | Release | Quiet forward motion. Name company + role one last time (Mode 1). Let go. Not "go crush it." |

---

## Prompt structure

**System prompt** (`src/prompts/system_prompt.py`):
1. Maya — who she is (3–4 sentences)
2. Maya's voice — what she does (rhythm, register)
3. Maya's voice — what she never does (the explicit avoid list)
4. The 5-phase arc (one line per phase)
5. Per-phase instructions (job, energy, include, avoid — each phase shaped differently)
6. **Two contrast examples** (generic phase 3 vs Maya phase 3, same inputs) — biggest unlock
7. Hard rules (Mode 1 names company + role in phases 3 and 5, etc.)

**User prompt** (`src/prompts/user_prompt.py`):
1. The user's situation as a short **prose paragraph** — NOT key-value pairs. Gemini writes
   far better from "They have a final round at Stripe tomorrow for a Senior PM role,
   sitting at anxiety 8/10, chose 'overwhelmed', wants to feel grounded" than from a
   field dump.
2. What they're carrying (`current_feeling`, `anxiety_level_before`, `feeling_note`)
3. What they're moving toward (`desired_feeling`, the event)
4. Per-phase tone calibration from `emotional_calibration.py` — injected as **voice
   modifiers** ("speak slower, shorter sentences"), not content instructions.
5. Final reminder of hard constraints

**Principles:**
- Show don't tell — examples beat adjectives
- Constrain by negation — avoid-lists work better than do-lists
- Per-phase instructions, not global
- Calibration is a voice modifier, not content
- Inputs are raw material to build from, not slots to fill

---

## The eval loop (how we measure "wow")

Build the eval to catch failures, not to certify winners.

**Layer 1 — automated / deterministic** (runs on every generation, lives in `tst/eval/eval_script_quality.py`):
- Mode 1: company AND role each appear in phase 3 and phase 5
- No banned phrases (built from the "never says" list above)
- Sentence-length variance per phase (flag if too uniform)
- Phase-1 hype detection (already exists — extend the word list as failures appear)
- Avg sentence length per phase (phase 1 should skew slower/longer than phase 3)
- Pronoun density ("you" frequent, "we" rare)

**Layer 2 — LLM-judge / semantic** (separate Claude or Gemini call, strict short rubric,
score each phase 1–5 + one-line rationale):
- Specificity, Embodiment, Voice, Restraint, Arc-fit
- Track the rationales — they show what's drifting.

**Layer 3 — human (ground truth):** read 10 scripts/week, rate 1–7 on "would I send this
to a friend the night before their interview." This is the only metric that truly matters;
everything else is a proxy for it.

**Layer 4 — production signal:** anxiety delta
(`anxiety_level_after − anxiety_level_before`), segmented by `current_feeling` chip and
`preparation_for` type. Flat or negative deltas on a segment tell you exactly where to tune.

---

## Workflow — one change at a time

1. Keep ~30 golden inputs fixed (all 7 prep types, anxiety ranges, both modes).
2. Run Layer 1 + Layer 2 automatically → score.
3. Human spot-check bottom 5 and top 5 (Layer 3).
4. Identify the **single most common failure mode**.
5. Make **ONE** targeted prompt change for it.
6. Re-run the same 30 inputs, compare, keep or revert.

Never change two things at once against different inputs — you lose the ability to tell
what helped.

---

## First concrete move

Write two Maya contrast examples (generic vs her voice) for **phase 3** — highest leverage,
easiest to feel the difference — drop them into the system prompt, run the eval, watch the
score lift. Then carry that feel into the other phases.
