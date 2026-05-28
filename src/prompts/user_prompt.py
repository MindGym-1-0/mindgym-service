"""User prompt — this user's specific session context and inputs."""


def build_user_prompt(
    preparation_for: str,
    current_feeling: str,
    desired_feeling: str,
    time_available: str,
    company: str | None,
    role: str | None,
    feeling_note: str | None = None,
) -> str:
    """Build the user prompt — everything specific to this session."""
    is_mode1 = bool(company and role)

    mode1_context = f"Company: {company}\nRole: {role}" if is_mode1 else ''

    mode1_company_rule = (
        f'- phase3 MUST name "{company}" and "{role}" explicitly. '
        f'Not "the company" or "the interview" — use the actual names.\n'
        f'- phase5 MUST name "{company}" and "{role}" explicitly.'
    ) if is_mode1 else ''

    critical_rules = f"""
CRITICAL RULES FOR THIS SESSION:
{mode1_company_rule}
- Generic output is a product defect. Be specific to this user's emotional state and session type.
"""

    feeling_detail = f'\nIn their own words: "{feeling_note}"' if feeling_note else ''

    return f"""--- SESSION INPUTS ---
Preparing for: {preparation_for}
Currently feeling: {current_feeling}{feeling_detail}
Wants to feel by the end: {desired_feeling}
Time available: {time_available} — pace the session to roughly fit this duration
{mode1_context}
{critical_rules}
Now write the session."""
