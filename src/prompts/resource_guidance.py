"""Resource-informed technique guidance for Maya's session scripts.

Distilled once from Claire's meditation / mindfulness / flow-state resources.
Appended inside build_system_prompt() after the prep-type guidance and before
the session calibration rule, so it reaches both Mode 1 and Mode 2 sessions.

Principle: DIRECT, don't TEACH. The model already knows these techniques. These
lines say which technique belongs in which phase and what is banned — they
reinforce the existing phase rules, they do not replace them. Intensity is set
by the anxiety calibration rule that follows, which takes precedence.

Source mapping (see master plan "Traceability for Claire" for the full audit):
  Harvard Health ............... 5-4-3-2-1 grounding (Phase 2)
  career-stories 3-step ........ concentration / sensory clarity / equanimity (Phases 1, 2, 4)
  flow videos + clickup +
    insighttimer ............... mental rehearsal of one scene (Phases 3, 5)
  affirmation video ............ grounded affirmations (Phase 4); manifestation framing removed
  diversejobsmatter ............ calm breathing + rejection-recovery framing (Phases 1, 3)
We encode WHICH technique and WHICH phase from each resource — not their text.
Nothing is fetched at runtime.
"""

MAYA_TECHNIQUE_LIBRARY = """--- TECHNIQUE LIBRARY (draw from these naturally; never name the sources) ---
Reinforce the phase rules above. Match intensity to the user's anxiety level per
the calibration rule below — that rule wins wherever the two seem to differ.

Phase 1 — Breathe: Open with one simple paced-breath cue ("in slow, out slower") —
a cue to follow, not a body sensation to scrutinize. Settle attention on one steady
external anchor: the chair, the floor, a fixed point in the room.

Phase 2 — Ground: Bring the user into the present with outward sensory noticing —
a few things they can see or hear around them (5-4-3-2-1 style). Notice what is
here without fighting it. Keep attention external, not on internal body tension.

Phase 3 — Rehearse: Rehearse ONE specific, picturable moment — for an upcoming
event, the moment itself (walking in, the first question, one clear sentence they
say); for a recovery or reset, one small concrete step forward. Never a broad
success fantasy.

Phase 4 — Anchor: Use grounded, believable affirmations tied to what the user has
actually done or can control — never to a guaranteed result. Let any leftover
discomfort be present without resisting it (equanimity).

Phase 5 — Close: Return the user to the present and to one concrete next action.
Calm, steady intention — not hype.

HARD RULE: No manifestation or magical-thinking language. Never imply an outcome
is guaranteed ("you will get this job", "attract the offer", "believe it and it
will happen"). Confidence comes from preparation and presence, not from belief in
a result.

  Example — Phase 4 affirmation:
    Avoid:  "You will get this job. Picture the offer letter — it's already yours."
    Prefer: "You've prepared for this. You know your work. That's what you carry in." """
