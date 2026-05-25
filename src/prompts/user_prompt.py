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

    # Goal enforcement — mode-aware.
    # Mode 1: goal is the in-interview objective (e.g. "Show product instinct clearly").
    # Mode 2: goal is the career destination (e.g. "Land AI engineer role").
    if is_mode1:
        goal_rule = f"""- The user's stated goal is "{goal}". This is the outcome they want from this specific {role} interaction with {company}.
- Before using the goal, check its shape:
  • If it reads as a clear in-event objective (e.g. "Show product instinct clearly", "Land a strong tech screen"), use it verbatim in phase3 and phase5.
  • If it reads as a career-level destination (e.g. "Land a job", "Find a role that fits my skills") or is grammatically awkward when dropped into a sentence, do NOT insert it verbatim. Instead, faithfully reframe it as a session-level intention for this specific event — e.g. "land a job that fits your skills" becomes "show {company} exactly how your skills fit this {role}".
- The reframed or verbatim goal MUST appear in phase3 (as what they accomplish in the rehearsed scene) and phase5 (as what they are walking in to deliver).
- Never produce sentences that read as machine-inserted. If a verbatim goal phrase would sound clunky in spoken coaching language, reframe it."""
    else:
        goal_rule = f"""- phase3 MUST name the user's career goal "{goal}" as the destination they are moving toward. Use the actual goal phrase, not a generic substitute like "your next role".
- phase5 MUST reference "{goal}" as what they are still moving toward."""

    # Stage enforcement — phase3 rehearses stage-appropriate content,
    # phase4 anchors evidence relevant to that stage and goal.
    stage_rule = f"""- phase3 MUST be shaped by the user's stage "{stage}" — follow the Stage Guidance in the system prompt for what to rehearse.
- phase4 MUST anchor a past moment that is specifically relevant to "{stage}" and "{goal}" — not a generic "moment you felt capable". Pull the kind of evidence the Stage Guidance describes for this stage."""

    mode1_company_rule = f"""- phase3 MUST name "{company}" and "{role}" explicitly. Not "the company" or "the interview" — use the actual names.
- phase5 MUST name "{company}" and "{role}" explicitly.""" if is_mode1 else ''

    critical_rules = f"""
CRITICAL RULES FOR THIS SESSION:
{mode1_company_rule}
{goal_rule}
{stage_rule}
- Generic output is a product defect. Be specific to this user's goal, stage, and emotional state.
"""

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
{critical_rules}
Now write the session."""
