"""Hardcoded fallback scripts and actions served when OpenAI fails or times out."""
from src.types.session import RecommendedAction, SessionScript

_COMPANY_DEFAULT = 'this company'
_ROLE_DEFAULT = 'this role'


def get_fallback_script(
    preparation_for: str,
    company: str | None,
    role: str | None,
) -> SessionScript:
    """Return a hardcoded 5-phase SessionScript for the given preparation_for value.

    Called by session_service when Gemini times out or returns an invalid response.
    Injects company and role for event-specific templates.
    Raises ValueError for unrecognised preparation_for values.
    """
    c = company or _COMPANY_DEFAULT
    r = role or _ROLE_DEFAULT
    has_event_context = bool(company and role)

    templates = {
        'general_reset': SessionScript(
            phase1=(
                "Close your eyes. Breathe in for four counts, hold for two, out for six. "
                "Let everything from the day fall away with that exhale. "
                "One more — in for four, out for six. You are here now. Nothing else matters right now."
            ),
            phase2=(
                "Feel the weight of your body — grounded, present, real. "
                "Scan slowly from your feet upward — legs, back, shoulders, hands. "
                "Let each part of your body soften. You are safe. You are reset."
            ),
            phase3=(
                "Bring to mind where you are headed. "
                "Not the noise, not the doubt — just the direction. "
                "Picture yourself making steady progress, one day at a time. "
                "You do not need to have it all figured out. You just need to keep moving forward. "
                "That is exactly what you are doing."
            ),
            phase4=(
                "Think of one thing you have done recently that you are quietly proud of — "
                "however small it seems. That is evidence. That is momentum. "
                "You are more capable than you give yourself credit for."
            ),
            phase5=(
                "You are reset. You are clear. You are still moving forward. "
                "Take that with you into the rest of your day."
            ),
        ),
        'restarting_search': SessionScript(
            phase1=(
                "Close your eyes. Breathe in for four counts, hold for two, out for six. "
                "Feel your body settle with each breath. "
                "Again — in for four, out for six. Starting over takes courage. You have it."
            ),
            phase2=(
                "Feel your feet on the ground. You are here, you are present, you are ready to begin again. "
                "Starting fresh is not a step back — it is a deliberate step forward. "
                "Everything you have learned so far comes with you."
            ),
            phase3=(
                "Picture yourself actively back in the search, moving confidently toward your next role. "
                "Your applications are going out. Your conversations are happening. "
                "You are showing up consistently, one step at a time. "
                "Each action you take brings you closer to what is ahead. "
                "You are not behind. You are exactly where you need to be right now."
            ),
            phase4=(
                "Think of a time you started something from scratch and made it work. "
                "You have built things before. You know how to begin. "
                "That same capability is here with you now — ready to go."
            ),
            phase5=(
                "You are restarting with clarity and purpose. "
                "One action today. Then another tomorrow. You are already on your way."
            ),
        ),
        'rejection_recovery': SessionScript(
            phase1=(
                "Close your eyes. Breathe in slowly for four counts, hold for two, out for six. "
                "Let that breath carry some of the weight out with it. "
                "Again — in for four, out for six. You are allowed to feel this. And you are going to be okay."
            ),
            phase2=(
                "Feel the ground beneath your feet. Solid, steady, still there. "
                "Notice your body — it carried you through today and it is still here. "
                "You are safe. This moment is hard, but it is not the end of your story."
            ),
            phase3=(
                (
                    f"This rejection from the {r} opportunity at {c} is one closed door on a path that has many more ahead. "
                    if has_event_context
                    else "This rejection is one closed door on a path that has many more ahead. "
                )
                + "Think about what you learned from this process — the conversations, the preparation, the growth. "
                + "None of that disappears with a no. You are more ready now than you were before you started. "
                + "The right opportunity is still out there, and you are still moving toward it."
            ),
            phase4=(
                "Think of something you have overcome before — a setback that felt final but wasn't. "
                "You got through that. You will get through this too. "
                "Rejection is not a reflection of your worth. It is just part of the process."
            ),
            phase5=(
                "You are still in it. You are still moving forward. "
                "Rest today. Come back stronger tomorrow."
            ),
        ),

        'salary_negotiation': SessionScript(
            phase1=(
                "Close your eyes. Breathe in for four counts, hold for two, out for six. "
                "Feel the tension leave your body with each exhale. "
                "Do that once more. You are grounded, you are steady, you are ready."
            ),
            phase2=(
                "Feel your feet firmly on the floor. Your body is calm and strong. "
                "You are not asking for a favour — you are having a professional conversation about your value. "
                "That is completely normal. That is what confident professionals do."
            ),
            phase3=(
                f"Picture yourself in the conversation with {c} about your {r} compensation. "
                "You state your number clearly and calmly — no apology, no hesitation. "
                "There is a pause. You sit with it comfortably — you do not fill the silence. "
                f"You know your worth in this {r} role and {c} knows it too. "
                "The conversation ends with mutual respect, whatever the outcome."
            ),
            phase4=(
                "Think of a moment you stood your ground professionally and it paid off. "
                "You have done hard conversations before and come out the other side. "
                "Your value does not change based on how this conversation goes — it is already real."
            ),
            phase5=(
                f"You are walking into this negotiation with {c} knowing exactly what you bring as a {r}. "
                "State your number. Hold your ground. You've earned this."
            ),
        ),
        'networking': SessionScript(
            phase1=(
                "Take a slow breath in for four counts, hold for two, and out for six. "
                "Let your jaw unclench and your shoulders drop. "
                "One more time — in for four, out for six. You are relaxed and ready."
            ),
            phase2=(
                "Feel where you are right now — your feet on the ground, your hands at rest. "
                "You are present. You are not performing, you are just connecting. "
                "People respond to warmth and genuine interest — and you have both."
            ),
            phase3=(
                f"Picture yourself at the networking event with people from {c}, meeting someone in a {r} capacity. "
                "You introduce yourself naturally — no script, just genuine conversation. "
                "You ask good questions and you listen. The other person lights up. "
                f"By the end of the conversation, they remember you as someone worth knowing at {c}. "
                "You leave having made a real connection, not just exchanged pleasantries."
            ),
            phase4=(
                "Think of a time you clicked with someone new — a conversation that flowed easily and felt good. "
                "You have that ability. It is already inside you. "
                "Tonight you are not selling yourself — you are just being yourself."
            ),
            phase5=(
                f"You are walking into {c} ready to connect as a {r}. "
                "Be curious, be genuine, and enjoy it. You've got this."
            ),
        ),
        'recruiter_call': SessionScript(
            phase1=(
                "Close your eyes. Breathe in slowly for four counts — hold for two — and out for six. "
                "Feel your body settle. Do that one more time. "
                "You are calm, you are clear, and you are ready for this conversation."
            ),
            phase2=(
                "Feel the chair beneath you and your feet on the floor. "
                "Take a moment to arrive fully in this moment — not in the call yet, just here, grounded. "
                "Your voice is steady. Your thoughts are clear. You know your story."
            ),
            phase3=(
                f"Picture yourself on the call with the recruiter from {c} about the {r} role. "
                "Your tone is warm and confident. You speak about your background clearly and with purpose. "
                f"When they ask why you're interested in {c}, your answer is honest and compelling. "
                f"You ask smart questions about the {r} role and they are impressed. "
                "The call ends on a high note — they want to move you forward."
            ),
            phase4=(
                "Think of a time you communicated really well — a conversation where you felt heard and respected. "
                "That same ease is available to you right now. "
                "You speak well. You listen well. That is enough."
            ),
            phase5=(
                f"You are ready for this call with {c}. "
                f"You are the right person for the {r} role — go show them that."
            ),
        ),
        'interview_tomorrow': SessionScript(
            phase1=(
                "Close your eyes and take a slow breath in through your nose for four counts. "
                "Hold it gently for two. Now breathe out through your mouth for six counts. "
                "Let your shoulders drop. Do that twice more — in for four, out for six. "
                "You are settling in. There is nowhere else you need to be right now."
            ),
            phase2=(
                "Bring your attention to your feet. Feel the ground beneath them — solid, steady, real. "
                "Move your awareness slowly up through your legs, your back, your hands resting in your lap. "
                "You are here. Your body is calm. Your mind is clear. "
                "Whatever happened today before this moment — set it aside. Right now, only this."
            ),
            phase3=(
                f"Picture yourself arriving at {c} tomorrow for your {r} interview. "
                "You walk in with a steady pace — not rushed, not nervous, just present. "
                f"You shake hands, you smile, and you take your seat. The conversation begins and you are ready. "
                f"You speak clearly about your experience. You listen well. You are exactly the person {c} needs for this {r} role. "
                "See yourself finishing the interview, standing up, and walking out knowing you gave everything you had."
            ),
            phase4=(
                "Think of a moment in your life when you were completely in your element — "
                "a time you solved something hard, impressed someone, or simply knew you were good at what you do. "
                "Hold that memory for a moment. Feel what you felt then. "
                "That version of you is the one walking into that interview tomorrow."
            ),
            phase5=(
                f"You are ready for {c}. You have prepared, you have shown up, and you have everything it takes. "
                f"Walk in tomorrow as the {r} you already are. Let's go."
            ),
        ),
    }

    if preparation_for not in templates:
        raise ValueError(f'Unknown preparation_for: {preparation_for!r}')

    return templates[preparation_for]


_FALLBACK_ACTIONS: dict[str, list[dict]] = {
    'rejection_recovery': [
        {'title': 'Name the narrative', 'body': 'Write one sentence about what this rejection taught you — not what it says about you.', 'timing': 'Today'},
        {'title': 'Return to your evidence', 'body': "Re-read your last 3 wins — applications, interviews, kind feedback. They're still true.", 'timing': 'Ongoing'},
        {'title': 'Reach out to one person', 'body': "Send a message to someone in your network — not to ask for a job, just to stay warm.", 'timing': 'Tomorrow'},
    ],
    'interview_tomorrow': [
        {'title': 'Rehearse your opener', 'body': "Say your 'tell me about yourself' answer aloud, once, with confidence.", 'timing': 'Today'},
        {'title': 'Prepare two questions', 'body': 'Write two thoughtful questions to ask the interviewer — it signals genuine interest.', 'timing': 'Today'},
        {'title': 'Protect your sleep', 'body': 'Your brain consolidates preparation during sleep. Be in bed by 10pm.', 'timing': 'Tonight'},
    ],
    'recruiter_call': [
        {'title': 'Confirm your narrative', 'body': "Know in one sentence why you're looking and what you're moving toward.", 'timing': 'Today'},
        {'title': "Research the recruiter's firm", 'body': 'Five minutes on their recent placements signals you take the relationship seriously.', 'timing': 'Today'},
        {'title': 'Follow up within 24 hours', 'body': 'Send a short thank-you and one specific detail from the call.', 'timing': 'Tomorrow'},
    ],
    'networking': [
        {'title': 'Draft your opening line', 'body': "Write a two-sentence intro that explains what you're working on and what you're looking for.", 'timing': 'Today'},
        {'title': 'Identify three people to reach', 'body': "Pick contacts you've been meaning to reconnect with. Send one message today.", 'timing': 'Ongoing'},
        {'title': 'Follow up on warm leads', 'body': 'Reply to any unanswered messages from the last two weeks.', 'timing': 'Tomorrow'},
    ],
    'salary_negotiation': [
        {'title': 'Anchor your number', 'body': "Write down the number you'll say first. Practice saying it aloud without flinching.", 'timing': 'Today'},
        {'title': 'Know your walk-away', 'body': "Define the minimum you'd accept before you get in the room — not during.", 'timing': 'Today'},
        {'title': 'Practice the pause', 'body': 'After you name your number, stop talking. Silence is your strongest tool.', 'timing': 'Ongoing'},
    ],
    'restarting_search': [
        {'title': 'Clear the backlog', 'body': 'Archive applications more than 3 weeks old with no response. Start fresh.', 'timing': 'Today'},
        {'title': 'Update one thing', 'body': 'Refresh your LinkedIn headline or resume summary — just one paragraph.', 'timing': 'Today'},
        {'title': 'Set a daily minimum', 'body': 'One meaningful outreach per day is more powerful than a weekly sprint.', 'timing': 'Ongoing'},
    ],
    'general_reset': [
        {'title': "Name what's weighing on you", 'body': "Write it down in one sentence. Getting it out of your head makes it manageable.", 'timing': 'Today'},
        {'title': 'Pick one thing to move', 'body': 'Choose the single smallest action in your job search you can take today.', 'timing': 'Today'},
        {'title': 'Build a recovery ritual', 'body': 'A 10-minute daily reset — walk, journal, breathe — compounds over weeks.', 'timing': 'Ongoing'},
    ],
}


def get_fallback_actions(preparation_for: str) -> list[RecommendedAction]:
    """Return hardcoded recommended actions when OpenAI fails or times out."""
    rows = _FALLBACK_ACTIONS.get(preparation_for, _FALLBACK_ACTIONS['general_reset'])
    return [RecommendedAction(**r) for r in rows]
