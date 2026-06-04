"""User prompt — this user's specific session context and inputs."""


def build_calibration_block(ec: dict) -> str:
    """Build the [SESSION CALIBRATION] block for the user prompt.

    Compact, ASCII-only format — the system prompt instructs Maya to treat
    this block as binding directives for the session.
    """
    arc = ec['tone_arc']
    tone_arc_line = (
        f"phase1: {arc['phase1']} | phase2: {arc['phase2']} | "
        f"phase3: {arc['phase3']} | phase4: {arc['phase4']} | phase5: {arc['phase5']}"
    )

    lines = [
        "[SESSION CALIBRATION]",
        f"Anxiety level: {ec['anxiety_level_before']}/10",
        f"Overall tone: {ec['tone']}",
        f"Tone arc: {tone_arc_line}",
    ]

    if ec['acknowledge_emotion']:
        lines += [
            "EMOTIONAL WITNESSING RULE ACTIVE:",
            "phase2 MUST open by acknowledging what this person is carrying.",
            "Do not begin coaching content before this acknowledgment.",
        ]

    lines.append(f"Primary need: {ec['primary_need']}")
    return "\n".join(lines)


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

_ROLE_CATEGORY_TEXT: dict[str, str] = {
    "product_design_ux": "a product design or UX role",
    "product_management": "a product management role",
    "software_engineering": "a software engineering role",
    "data_analytics": "a data or analytics role",
    "marketing": "a marketing role",
    "sales": "a sales role",
    "operations": "an operations role",
    "finance": "a finance role",
    "people_hr": "a people or HR role",
    "leadership_executive": "a leadership or executive role",
}

_TIMELINE_TEXT: dict[str, str] = {
    "asap": "They need to land something soon — the urgency is real.",
    "3m": "They're aiming to land something in the next few months.",
    "6m": "They have some runway — working toward a move in the next six months.",
    "12m": "They're not in a rush — exploring options over the next year or so.",
}


def _build_company_type_sentence(company_types: list[str] | None) -> str:
    """Describe the type of environment the user is targeting — only when there's a clear lean.

    Mixed preferences (e.g. startup + enterprise) produce no useful signal for Maya, so we
    return empty string in that case rather than forcing a vague observation.
    """
    if not company_types:
        return ""

    types = set(company_types) - {"any"}
    if not types:
        return ""

    small = types & {"startup", "scale_up"}
    large = types & {"large_tech", "enterprise"}

    if small and large:
        return ""  # No clear lean — don't say anything

    if small:
        return "They're primarily targeting startups and scale-ups."
    if large == {"large_tech"}:
        return "They're targeting large tech companies."
    if large == {"enterprise"}:
        return "They're targeting enterprise companies."
    return "They're targeting larger, established companies."


def _derive_pipeline_signal(ctx: dict | None) -> str | None:
    """Return one sentence describing the user's most actionable gap, or None.

    Checks in priority order — returns the first match. Treats missing/None
    fields as 0 so the logic never raises. Returns None when there's not enough
    data to point clearly to a gap.
    """
    if not ctx:
        return None

    apps = ctx.get("applications_sent_max") or 0
    contacts = ctx.get("recruiter_contacts") or 0
    first_rounds = ctx.get("first_round_interviews") or 0
    final_rounds = ctx.get("final_round_interviews") or 0

    if apps > 20 and contacts == 0:
        return "They've sent many applications but haven't connected with any recruiters yet."
    if apps > 10 and first_rounds == 0:
        return "They've been applying but haven't reached an interview yet."
    if contacts > 0 and first_rounds == 0:
        return "They've made recruiter contacts but haven't converted to interviews."
    if first_rounds > 0 and final_rounds == 0:
        return "They've had first-round interviews but haven't advanced further."
    if first_rounds > 0:
        return "They've had first-round interviews — they're getting in the door."
    return None


def _build_pipeline_sentence(user_context: dict) -> str:
    """Translate funnel stats into one sentence about where they are in the search.

    Reads bottom-up: finals → first rounds → apps. Returns empty string when
    there's not enough data to say anything meaningful.
    """
    apps = user_context.get("applications_sent_max") or user_context.get("applications_sent_min")
    first_rounds = user_context.get("first_round_interviews") or 0
    final_rounds = user_context.get("final_round_interviews") or 0

    if apps is None:
        return ""

    if final_rounds >= 2:
        return "They've made it to final rounds — they're clearly competitive, but not landing offers yet."
    if final_rounds == 1:
        return "They've had a final-round interview — getting close, but not there yet."
    if first_rounds >= 3:
        return "They're getting first-round interviews but not breaking through to finals yet."
    if first_rounds >= 1:
        return "They've had some first-round interviews — early traction, still building momentum."
    if apps >= 30:
        return "They've sent a high volume of applications with almost no response — the silence has been heavy."
    if apps >= 10:
        return "They've been applying steadily but haven't gotten interviews yet — the lack of traction is wearing."
    return "They're early in their search, just starting to put themselves out there."


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
    timeline = user_context.get("job_timeline")
    challenge = user_context.get("emotional_challenge")
    role_category = user_context.get("target_role_category")
    role_note = user_context.get("target_role_note")
    company_types = user_context.get("company_types")
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

    if timeline:
        text = _TIMELINE_TEXT.get(timeline, "")
        if text:
            sentences.append(text)

    if challenge:
        text = _EMOTIONAL_CHALLENGE_TEXT.get(challenge, "")
        if text:
            sentences.append(text)

    pipeline = _build_pipeline_sentence(user_context)
    if pipeline:
        sentences.append(pipeline)

    if role_category == "not_sure":
        sentences.append("They haven't settled on a direction yet — that uncertainty is part of what they're carrying.")
    elif role_note:
        sentences.append(f"They're aiming for {role_note}.")
    elif role_category:
        category_phrase = _ROLE_CATEGORY_TEXT.get(role_category, "")
        if category_phrase:
            sentences.append(f"They're targeting {category_phrase}.")

    company_type_sentence = _build_company_type_sentence(company_types)
    if company_type_sentence:
        sentences.append(company_type_sentence)

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
        "Use this as emotional context. Do not recite these facts. "
        "Translate them into what this person is carrying, especially in phase2."
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
        f"{who} {prep}. They feel {current_feeling} and want to leave {desired_feeling}."
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
    emotional_calibration: dict | None = None,
) -> str:
    """Build the user prompt — everything specific to this session.

    user_context holds onboarding fields fetched from the users table.
    Defaults to None — prompt is identical to today when not provided.
    anxiety_level_before is needed here to compute the baseline delta.
    emotional_calibration is rendered here (not in system prompt) so the
    system prompt stays static for Vellum and prompt caching.
    """
    is_event_linked = bool(company and role)

    situation_line = _build_situation_line(
        first_name, preparation_for, current_feeling, desired_feeling, company, role
    )
    about_block = _build_about_block(user_context, anxiety_level_before)

    mode1_context = f"Company: {company}\nRole: {role}" if is_event_linked else ""

    mode1_company_rule = (
        f'- phase3 MUST name "{company}" and "{role}" explicitly. '
        f'Not "the company" or "the interview" — use the actual names.\n'
        f'- phase5 MUST name "{company}" and "{role}" explicitly.'
    ) if is_event_linked else ""

    # NOTE: max_output_tokens caps all sessions at the same budget, so
    # time_available cannot meaningfully change script LENGTH. We nudge density
    # instead (terser vs slightly more spacious). Real per-duration scaling
    # needs the token cap raised for longer sessions — out of scope here.
    pacing = {
        "5 min": "Keep it tight and economical — every line earns its place.",
        "10 min": "A measured pace — room to settle without wandering.",
        "15 min": "A slightly more spacious pace — let key moments land.",
    }.get(time_available, "A measured pace.")

    feeling_detail = f'\nIn their own words: "{feeling_note}"' if feeling_note else ""

    critical_rules = (
        f"CRITICAL RULES FOR THIS SESSION:\n"
        f"{mode1_company_rule}\n"
        f"- Generic output is a product defect. Be specific to this user's emotional state and session type."
    )

    session_inputs = (
        f"--- SESSION INPUTS ---\n"
        f"Preparing for: {preparation_for}\n"
        f"Currently feeling: {current_feeling}{feeling_detail}\n"
        f"Wants to feel by the end: {desired_feeling}\n"
        f"Time available: {time_available} — {pacing}\n"
        f"{mode1_context}"
    )

    sections = []
    if emotional_calibration:
        sections.append(build_calibration_block(emotional_calibration))
    sections.append(situation_line)
    if about_block:
        sections.append(about_block)
    sections.append(session_inputs)
    sections.append(critical_rules)
    sections.append("Now write the session.")

    return "\n\n".join(s.strip() for s in sections if s.strip())
