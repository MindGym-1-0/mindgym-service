"""User prompt — this user's specific session context and inputs."""

_EMOTIONAL_CHALLENGE_TEXT: dict[str, str] = {
    "rejection_silence": "The hardest part of their search has been applying and hearing nothing back — the silence.",
    "interview_anxiety": "Their biggest challenge is the anxiety that builds before interviews.",
    "imposter_syndrome": "They carry a feeling of not belonging or not being qualified enough.",
    "burnout": "The search has worn them down — they're running on fumes.",
    "uncertainty": "They're unsure whether they're on the right path or making the right moves.",
    "financial_pressure": "The financial pressure of their situation adds real weight to every step.",
}

_DURATION_TEXT: dict[str, str] = {
    "1m": "about a month",
    "2m": "about 2 months",
    "3m": "about 3 months",
    "6m": "about 6 months",
    "1y": "over a year",
    "1y+": "over a year",
}


def _build_about_block(user_context: dict | None, anxiety_level_before: int) -> str:
    """Translate onboarding fields into a short prose paragraph Maya can use.

    Returns empty string when user_context is None or has no useful fields —
    the prompt behaves exactly as before when there is no onboarding data.
    The block ends with a guardrail so Gemini uses the context to inform tone
    without reciting the facts back to the user.
    """
    if not user_context:
        return ""

    status = user_context.get("employment_status")
    duration = user_context.get("unemployed_duration")
    challenge = user_context.get("emotional_challenge")
    role_note = user_context.get("target_role_note")
    baseline = user_context.get("baseline_anxiety")

    if not any([status, challenge, role_note]):
        return ""

    sentences: list[str] = []

    if status == "employed":
        sentences.append("They're currently employed and exploring new opportunities.")
    elif status in ("unemployed", "laid_off") and duration:
        dur = _DURATION_TEXT.get(duration, duration)
        prefix = "They were laid off" if status == "laid_off" else "They've been searching for"
        sentences.append(f"{prefix} {dur}.")
    elif status in ("unemployed", "laid_off"):
        sentences.append("They're currently unemployed and actively searching.")

    if challenge:
        text = _EMOTIONAL_CHALLENGE_TEXT.get(challenge, "")
        if text:
            sentences.append(text)

    if role_note:
        sentences.append(f"They're aiming for {role_note}.")

    if baseline is not None:
        delta = anxiety_level_before - baseline
        if delta >= 3:
            sentences.append("They're significantly more anxious than usual today.")
        elif delta <= -3:
            sentences.append("They're calmer than usual today.")
        else:
            sentences.append("Today's anxiety is close to their normal level.")

    if not sentences:
        return ""

    return (
        "About this person: " + " ".join(sentences) + "\n"
        "Let this context naturally inform your tone and acknowledgment — especially in phase 2, "
        "which should open by naming what this person has been carrying (not the label, but what it "
        "feels like in human terms). Do not recite onboarding facts. Let them shape how you speak "
        "to this person."
    )


def _build_situation_line(
    first_name: str | None,
    preparation_for: str,
    current_feeling: str,
    desired_feeling: str,
    company: str | None,
    role: str | None,
) -> str:
    """Stitch the key facts into one natural sentence Gemini can anchor on.

    Why: Gemini writes more naturally from a human sentence than from a bare
    list of labels. Every piece is optional-safe so missing fields (no name,
    Mode 2 with no company/role) never leave a grammar gap.
    """
    who = first_name.strip() if first_name and first_name.strip() else "This person"

    # Map the prep type to a short natural phrase. Falls back to the raw value
    # so a newly-added prep type still produces a readable (if plain) sentence.
    prep_phrases = {
        "interview_tomorrow": "has an interview tomorrow",
        "recruiter_call": "has a recruiter call coming up",
        "networking": "is preparing for a networking conversation",
        "salary_negotiation": "is heading into a salary negotiation",
        "rejection_recovery": "is recovering from a rejection",
        "restarting_search": "is restarting their job search",
        "general_reset": "wants a general reset",
    }
    prep = prep_phrases.get(preparation_for, f"is preparing for: {preparation_for}")

    # Add company/role only when present (Mode 1).
    if company and role:
        prep += f" \u2014 {role} at {company}"

    return (
        f"{who} {prep}. Right now they feel {current_feeling}, "
        f"and they want to feel {desired_feeling} by the end."
    )


def build_user_prompt(
    preparation_for: str,
    current_feeling: str,
    desired_feeling: str,
    time_available: str,
    company: str | None,
    role: str | None,
    feeling_note: str | None = None,
    first_name: str | None = None,
    user_context: dict | None = None,
    anxiety_level_before: int = 5,
) -> str:
    """Build the user prompt — everything specific to this session.

    user_context holds onboarding fields fetched from the users table.
    Defaults to None — prompt is identical to today when not provided.
    anxiety_level_before is needed here to compute the baseline delta.
    """
    is_mode1 = bool(company and role)

    situation_line = _build_situation_line(
        first_name, preparation_for, current_feeling, desired_feeling, company, role
    )
    about_block = _build_about_block(user_context, anxiety_level_before)
    about_section = f"\n{about_block}\n" if about_block else ""

    mode1_context = f"Company: {company}\nRole: {role}" if is_mode1 else ''

    mode1_company_rule = (
        f'- phase3 MUST name "{company}" and "{role}" explicitly. '
        f'Not "the company" or "the interview" — use the actual names.\n'
        f'- phase5 MUST name "{company}" and "{role}" explicitly.'
    ) if is_mode1 else ''

    # NOTE: max_output_tokens caps all sessions at the same budget, so
    # time_available cannot meaningfully change script LENGTH. We nudge density
    # instead (terser vs slightly more spacious). Real per-duration scaling
    # needs the token cap raised for longer sessions — out of scope here.
    pacing = {
        "5 min": "Keep it tight and economical — every line earns its place.",
        "10 min": "A measured pace — room to settle without wandering.",
        "15 min": "A slightly more spacious pace — let key moments land.",
    }.get(time_available, "A measured pace.")

    critical_rules = f"""
CRITICAL RULES FOR THIS SESSION:
{mode1_company_rule}
- Generic output is a product defect. Be specific to this user's emotional state and session type.
"""

    feeling_detail = f'\nIn their own words: "{feeling_note}"' if feeling_note else ''

    return f"""{situation_line}
{about_section}
--- SESSION INPUTS ---
Preparing for: {preparation_for}
Currently feeling: {current_feeling}{feeling_detail}
Wants to feel by the end: {desired_feeling}
Time available: {time_available} — {pacing}
{mode1_context}
{critical_rules}
Now write the session."""