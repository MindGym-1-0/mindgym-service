"""User prompt — this user's specific session context and inputs."""


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
) -> str:
    """Build the user prompt — everything specific to this session.

    first_name is optional and currently not passed by the caller (the session
    path has no first_name fetch yet — see prompt_builder.py). The prompt works
    identically with or without it; wire the DB read in a follow-up.
    """
    is_mode1 = bool(company and role)

    situation_line = _build_situation_line(
        first_name, preparation_for, current_feeling, desired_feeling, company, role
    )

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

--- SESSION INPUTS ---
Preparing for: {preparation_for}
Currently feeling: {current_feeling}{feeling_detail}
Wants to feel by the end: {desired_feeling}
Time available: {time_available} — {pacing}
{mode1_context}
{critical_rules}
Now write the session."""