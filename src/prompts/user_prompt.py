"""User prompt — this user's specific session context and inputs."""


def build_user_prompt(
    preparation_for: str,
    current_feeling: str,
    desired_feeling: str,
    time_available: str,
    company: str | None,
    role: str | None,
    user_context: dict,
) -> str:
    """Build the user prompt — everything specific to this user and this session."""
    first_name = user_context.get('first_name', '')
    goal = user_context.get('goal', '')
    stage = user_context.get('stage', '')
    anxiety_level = user_context.get('anxiety_level', '')

    is_mode1 = bool(company and role)

    name_line = f"User's first name: {first_name}" if first_name else ''

    mode1_context = f"""Company: {company}
Role: {role}""" if is_mode1 else ''

    mode1_rules = f"""
CRITICAL RULES FOR THIS SESSION:
- phase3 MUST name "{company}" and "{role}" explicitly. Not "the company" or "the interview" — use the actual names.
- phase5 MUST name "{company}" and "{role}" explicitly.
- Generic output is a product defect. Be specific.
""" if is_mode1 else ''

    return f"""--- USER CONTEXT ---
{name_line}
Career goal: {goal}
Job search stage: {stage}
Baseline anxiety level: {anxiety_level}/10
{mode1_context}
--- SESSION INPUTS ---
Preparing for: {preparation_for}
Currently feeling: {current_feeling}
Wants to feel by the end: {desired_feeling}
Time available: {time_available} — pace the session to roughly fit this duration
{mode1_rules}
Now write the session."""
