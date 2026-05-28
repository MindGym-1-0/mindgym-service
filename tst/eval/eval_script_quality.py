"""Interactive script quality evaluator — run this manually to inspect Gemini output.

Usage:
    python tst/eval/eval_script_quality.py

To test a different Gemini model:
    GEMINI_MODEL=gemini-2.0-flash python tst/eval/eval_script_quality.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from repo root or from tst/eval/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

import google.generativeai as genai  # noqa: E402

from src.lib.config import settings  # noqa: E402
from src.lib.gemini_service import is_hype_in_phase1  # noqa: E402
from src.lib.prompt_builder import build_prompt  # noqa: E402
from src.types.session import SessionScript  # noqa: E402


PREPARATION_FOR_OPTIONS = [
    'interview_tomorrow',
    'recruiter_call',
    'networking',
    'salary_negotiation',
    'rejection_recovery',
    'restarting_search',
    'general_reset',
]

CURRENT_FEELING_OPTIONS = [
    'overwhelmed',
    'discouraged',
    'exhausted',
    'unsure',
    'anxious but hopeful',
]

DESIRED_FEELING_OPTIONS = [
    'calm',
    'grounded',
    'confident',
    'focused',
    'clear_minded',
    'composed',
]

TIME_OPTIONS = ['5 min', '10 min', '15 min']

MODE1_TYPES = {'interview_tomorrow', 'recruiter_call'}


def _divider(char: str = '=', width: int = 60) -> str:
    return char * width


def _prompt_choice(question: str, options: list[str]) -> str:
    print(f"\n{question}")
    for i, opt in enumerate(options, start=1):
        print(f"  {i}. {opt}")
    while True:
        raw = input("Enter number or value: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        if raw in options:
            return raw
        print(f"  Invalid — enter a number 1-{len(options)} or the exact value.")


def _prompt_optional(question: str) -> str | None:
    raw = input(f"\n{question} (press Enter to skip): ").strip()
    return raw if raw else None


def collect_inputs() -> dict:
    preparation_for = _prompt_choice(
        "preparation_for:", PREPARATION_FOR_OPTIONS
    )
    current_feeling = _prompt_choice(
        "current_feeling:", CURRENT_FEELING_OPTIONS
    )
    desired_feeling = _prompt_choice(
        "desired_feeling:", DESIRED_FEELING_OPTIONS
    )
    time_available = _prompt_choice(
        "time_available:", TIME_OPTIONS
    )

    if preparation_for in MODE1_TYPES:
        print("\n  (company and role are required for this mode)")
        company = input("\ncompany: ").strip() or None
        role = input("role: ").strip() or None
    else:
        company = _prompt_optional("company")
        role = _prompt_optional("role")

    while True:
        raw = input("\nanxiety_level_before (1=calm … 10=extremely anxious): ").strip()
        if raw.isdigit() and 1 <= int(raw) <= 10:
            anxiety_level_before = int(raw)
            break
        print("  Invalid — enter a number from 1 to 10.")

    feeling_note = _prompt_optional("feeling_note (user's own words, optional)")

    return {
        "preparation_for": preparation_for,
        "current_feeling": current_feeling,
        "desired_feeling": desired_feeling,
        "time_available": time_available,
        "anxiety_level_before": anxiety_level_before,
        "company": company,
        "role": role,
        "feeling_note": feeling_note,
    }


def _check_mode1_validation(script: SessionScript, company: str, role: str) -> list[str]:
    """Return a list of validation failure reasons, empty if all pass."""
    p3 = script.phase3.lower()
    p5 = script.phase5.lower()
    failures = []
    if company.lower() not in p3:
        failures.append(f'company "{company}" missing from phase3')
    if role.lower() not in p3:
        failures.append(f'role "{role}" missing from phase3')
    if company.lower() not in p5:
        failures.append(f'company "{company}" missing from phase5')
    if role.lower() not in p5:
        failures.append(f'role "{role}" missing from phase5')
    return failures


def run_scenario(inputs: dict) -> None:
    print(f"\n{_divider('-')}")
    print("  Generating script...")
    print(_divider('-'))

    company = inputs.get("company")
    role = inputs.get("role")
    anxiety_level_before = inputs["anxiety_level_before"]

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)

        prompt = build_prompt(
            preparation_for=inputs["preparation_for"],
            current_feeling=inputs["current_feeling"],
            desired_feeling=inputs["desired_feeling"],
            time_available=inputs["time_available"],
            anxiety_level_before=anxiety_level_before,
            company=company,
            role=role,
            feeling_note=inputs.get("feeling_note"),
        )

        response = model.generate_content(prompt)
        raw_text = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()

        print(f"\n  Raw Gemini response:\n  {raw_text}\n")

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            print(f"  !! JSON parse failed: {e}")
            print("  !! Fallback would be used in production.")
            return

        try:
            script = SessionScript(**data)
        except Exception as e:
            print(f"  !! SessionScript construction failed: {e}")
            print("  !! Fallback would be used in production.")
            return

        if company and role:
            failures = _check_mode1_validation(script, company, role)
            if failures:
                print("  !! Mode 1 validation FAILED:")
                for f in failures:
                    print(f"       - {f}")
                print("\n  Script phases (raw, before rejection):")
                print(f"\n  Phase 3: {script.phase3}")
                print(f"\n  Phase 5: {script.phase5}")
                print("\n  !! Fallback would be used in production.")
                return

        if anxiety_level_before >= 7 and is_hype_in_phase1(script.phase1):
            print("  !! High-anxiety hype guard FAILED:")
            print("     phase1 contains energizing/hype language for a high-anxiety session.")
            print(f"\n  Phase 1: {script.phase1}")
            print("\n  !! Fallback would be used in production.")
            return

        print(f"\n  [OK] Script passed all checks  (anxiety_level_before={anxiety_level_before})")
        print(f"\n  Phase 1: {script.phase1}")
        print(f"\n  Phase 2: {script.phase2}")
        print(f"\n  Phase 3: {script.phase3}")
        print(f"\n  Phase 4: {script.phase4}")
        print(f"\n  Phase 5: {script.phase5}")

    except Exception as e:
        print(f"\n  !! Gemini call failed: {type(e).__name__}: {e}")
        print("  !! Fallback would be used in production.")


def main() -> None:
    print(f"\n{_divider()}")
    print("  MindGym Script Quality Evaluator")
    print(f"  Model: {settings.gemini_model} (Gemini)")
    print(_divider())

    while True:
        inputs = collect_inputs()
        run_scenario(inputs)

        print(f"\n{_divider('-')}")
        again = input("  Run another scenario? (y/n): ").strip().lower()
        if again != 'y':
            break

    print(f"\n{_divider()}")
    print("  Done.")
    print(_divider())


if __name__ == "__main__":
    main()
