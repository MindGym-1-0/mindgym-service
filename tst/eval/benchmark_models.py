"""Multi-model script quality benchmark.

Generates 5-phase session scripts from 3 models on 4 fixed scenarios,
scores them on the existing quality rubric, and produces a comparison doc.

Usage:
    python tst/eval/benchmark_models.py

Outputs:
    tst/eval/benchmark_results/<scenario>_<model>.json  — raw scripts
    tst/eval/benchmark_results/comparison.md            — comparison table
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

import os
import re

import anthropic as anthropic_sdk
import google.generativeai as genai
from openai import OpenAI

from src.lib.config import settings
from src.lib.emotional_calibration import build_emotional_calibration
from src.prompts.system_prompt import build_system_prompt
from src.prompts.user_prompt import build_user_prompt
from src.types.session import SessionScript

RESULTS_DIR = Path(__file__).parent / "benchmark_results"
RESULTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

MODELS = {
    "gemini-2.5-flash": {
        "provider": "gemini",
        "model_id": "gemini-2.5-flash",
        "tier": "fast",
        "input_cost_per_1k": 0.000075,
        "output_cost_per_1k": 0.0003,
    },
    "claude-haiku-4-5": {
        "provider": "anthropic",
        "model_id": "claude-haiku-4-5-20251001",
        "tier": "fast",
        "input_cost_per_1k": 0.0008,
        "output_cost_per_1k": 0.004,
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "model_id": "gpt-4o-mini",
        "tier": "fast",
        "input_cost_per_1k": 0.00015,
        "output_cost_per_1k": 0.0006,
    },
}

JUDGE_MODEL = "claude-opus-4-8"

# ---------------------------------------------------------------------------
# Fixed scenarios (non-negotiable — same inputs to every model)
# ---------------------------------------------------------------------------

SCENARIOS = [
    {
        "id": "high_anxiety_mode1",
        "label": "High-anxiety Mode 1 (interview)",
        "inputs": {
            "preparation_for": "interview_tomorrow",
            "company": "Google",
            "role": "Product Manager",
            "current_feeling": "overwhelmed",
            "anxiety_level_before": 8,
            "desired_feeling": "calm",
            "time_available": "10 min",
            "feeling_note": None,
        },
    },
    {
        "id": "low_anxiety_mode1",
        "label": "Low-anxiety Mode 1 (recruiter call)",
        "inputs": {
            "preparation_for": "recruiter_call",
            "company": "Stripe",
            "role": "Software Engineer",
            "current_feeling": "anxious but hopeful",
            "anxiety_level_before": 3,
            "desired_feeling": "confident",
            "time_available": "10 min",
            "feeling_note": None,
        },
    },
    {
        "id": "heavy_mode2",
        "label": "Heavy Mode 2 (rejection recovery)",
        "inputs": {
            "preparation_for": "rejection_recovery",
            "company": None,
            "role": None,
            "current_feeling": "discouraged",
            "anxiety_level_before": 6,
            "desired_feeling": "grounded",
            "time_available": "10 min",
            "feeling_note": None,
        },
    },
    {
        "id": "open_mode2",
        "label": "Open Mode 2 (general reset)",
        "inputs": {
            "preparation_for": "general_reset",
            "company": None,
            "role": None,
            "current_feeling": "unsure",
            "anxiety_level_before": 4,
            "desired_feeling": "clear_minded",
            "time_available": "10 min",
            "feeling_note": None,
        },
    },
]

# ---------------------------------------------------------------------------
# API key validation
# ---------------------------------------------------------------------------

def check_api_keys() -> None:
    missing = []
    if not settings.gemini_api_key:
        missing.append("GEMINI_API_KEY")
    if not os.getenv("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if not os.getenv("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if missing:
        sys.exit(f"ERROR: Missing API keys: {', '.join(missing)}. Add them to .env and retry.")

# ---------------------------------------------------------------------------
# Prompt builder (shared across all models)
# ---------------------------------------------------------------------------

def build_prompt_parts(inputs: dict) -> tuple[str, str]:
    is_mode1 = bool(inputs.get("company") and inputs.get("role"))
    ec = build_emotional_calibration(
        current_feeling=inputs["current_feeling"],
        desired_feeling=inputs["desired_feeling"],
        anxiety_level_before=inputs["anxiety_level_before"],
    )
    system = build_system_prompt(emotional_calibration=ec, is_mode1=is_mode1)
    user = build_user_prompt(
        preparation_for=inputs["preparation_for"],
        current_feeling=inputs["current_feeling"],
        desired_feeling=inputs["desired_feeling"],
        time_available=inputs["time_available"],
        company=inputs.get("company"),
        role=inputs.get("role"),
        feeling_note=inputs.get("feeling_note"),
    )
    return system, user

# ---------------------------------------------------------------------------
# Model callers
# ---------------------------------------------------------------------------

def _parse_json(raw: str) -> dict | None:
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def call_gemini(model_id: str, system: str, user: str) -> dict:
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(model_id)
    prompt = f"{system}\n\n{user}"
    t0 = time.monotonic()
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(max_output_tokens=8192),
    )
    latency = time.monotonic() - t0
    raw = response.text or ""
    finish_reason = str(response.candidates[0].finish_reason) if response.candidates else "unknown"
    data = _parse_json(raw)
    input_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
    output_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
    return {
        "raw": raw,
        "data": data,
        "json_valid": data is not None,
        "latency": round(latency, 2),
        "finish_reason": finish_reason,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def call_anthropic(model_id: str, system: str, user: str) -> dict:
    client = anthropic_sdk.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    t0 = time.monotonic()
    response = client.messages.create(
        model=model_id,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    latency = time.monotonic() - t0
    raw = response.content[0].text if response.content else ""
    finish_reason = response.stop_reason or "unknown"
    data = _parse_json(raw)
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    return {
        "raw": raw,
        "data": data,
        "json_valid": data is not None,
        "latency": round(latency, 2),
        "finish_reason": finish_reason,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def call_openai(model_id: str, system: str, user: str) -> dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    t0 = time.monotonic()
    response = client.chat.completions.create(
        model=model_id,
        max_tokens=2048,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    latency = time.monotonic() - t0
    raw = response.choices[0].message.content or ""
    finish_reason = response.choices[0].finish_reason or "unknown"
    data = _parse_json(raw)
    input_tokens = response.usage.prompt_tokens if response.usage else 0
    output_tokens = response.usage.completion_tokens if response.usage else 0
    return {
        "raw": raw,
        "data": data,
        "json_valid": data is not None,
        "latency": round(latency, 2),
        "finish_reason": finish_reason,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def call_model(model_key: str, system: str, user: str) -> dict:
    cfg = MODELS[model_key]
    if cfg["provider"] == "gemini":
        result = call_gemini(cfg["model_id"], system, user)
    elif cfg["provider"] == "anthropic":
        result = call_anthropic(cfg["model_id"], system, user)
    else:
        result = call_openai(cfg["model_id"], system, user)

    input_cost = (result["input_tokens"] / 1000) * cfg["input_cost_per_1k"]
    output_cost = (result["output_tokens"] / 1000) * cfg["output_cost_per_1k"]
    result["cost_usd"] = round(input_cost + output_cost, 6)
    return result

# ---------------------------------------------------------------------------
# Deterministic checks
# ---------------------------------------------------------------------------

_BANNED_PHASE5 = {
    "shine", "make your mark", "unique strengths", "align perfectly with their vision",
    "show them what you're made of", "go get it", "you've got this",
}

_HIGH_ANXIETY_HYPE_WORDS = {
    "pump", "pumped", "energy", "energized", "excited", "hyped",
    "let's go", "crush it", "fired up", "unstoppable",
}


def run_deterministic_checks(scenario: dict, data: dict | None) -> dict:
    if data is None:
        return {"pass": False, "failures": ["JSON invalid — no script to check"]}

    failures = []
    inputs = scenario["inputs"]
    company = inputs.get("company")
    role = inputs.get("role")
    anxiety = inputs["anxiety_level_before"]

    for phase in ["phase1", "phase2", "phase3", "phase4", "phase5"]:
        text = data.get(phase, "")
        if len(text) < 20:
            failures.append(f"{phase} too short ({len(text)} chars)")

    if company and role:
        p3 = data.get("phase3", "").lower()
        p5 = data.get("phase5", "").lower()
        if company.lower() not in p3:
            failures.append(f'company "{company}" missing from phase3')
        if role.lower() not in p3:
            failures.append(f'role "{role}" missing from phase3')
        if company.lower() not in p5:
            failures.append(f'company "{company}" missing from phase5')
        if role.lower() not in p5:
            failures.append(f'role "{role}" missing from phase5')

    p5_text = data.get("phase5", "").lower()
    for phrase in _BANNED_PHASE5:
        if phrase in p5_text:
            failures.append(f'banned phrase in phase5: "{phrase}"')

    if anxiety >= 7:
        p1_text = data.get("phase1", "").lower()
        for word in _HIGH_ANXIETY_HYPE_WORDS:
            if word in p1_text:
                failures.append(f'hype word in phase1 at anxiety {anxiety}: "{word}"')

    return {"pass": len(failures) == 0, "failures": failures}

# ---------------------------------------------------------------------------
# Opus judge (single call for all 12 scripts)
# ---------------------------------------------------------------------------

def run_judge(all_results: list[dict]) -> dict[str, dict]:
    scripts_text = ""
    for r in all_results:
        scripts_text += f"\n\n=== SCRIPT ID: {r['id']} ===\n"
        scripts_text += f"Scenario: {r['scenario_label']}\nModel: {r['model_key']}\n\n"
        if r["data"]:
            for phase in ["phase1", "phase2", "phase3", "phase4", "phase5"]:
                scripts_text += f"[{phase.upper()}]\n{r['data'].get(phase, '')}\n\n"
        else:
            scripts_text += "(JSON parse failed — no script)\n"

    prompt = f"""You are judging AI coaching scripts written by different language models.
Score each script on 5 dimensions (1–5 each) and provide a one-line rationale per dimension.

Dimensions:
- specificity: Does it name concrete moments, not abstractions?
- embodiment: Does it give the user something physical/sensory to hold?
- voice: Does it sound like a real coach, not a chatbot? Varied rhythm, no filler phrases?
- restraint: Does it resist over-explaining, stacking affirmations, or fake positivity?
- arc_fit: Does each phase do its distinct job (decelerate→locate→embody→consolidate→release)?

For each script, output a JSON object with this exact structure:
{{
  "script_id": "<id>",
  "scores": {{
    "specificity": {{"score": <1-5>, "rationale": "<one line>"}},
    "embodiment": {{"score": <1-5>, "rationale": "<one line>"}},
    "voice": {{"score": <1-5>, "rationale": "<one line>"}},
    "restraint": {{"score": <1-5>, "rationale": "<one line>"}},
    "arc_fit": {{"score": <1-5>, "rationale": "<one line>"}}
  }},
  "avg": <average of 5 scores, 1 decimal>
}}

Output a JSON array containing one object per script. Nothing else — no markdown, no explanation.

Scripts to judge:
{scripts_text}"""

    client = anthropic_sdk.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text if response.content else "[]"
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        judgments = json.loads(cleaned)
        return {j["script_id"]: j for j in judgments}
    except Exception as e:
        print(f"  WARNING: Judge response failed to parse: {e}")
        return {}

# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def write_report(all_results: list[dict], judgments: dict[str, dict]) -> Path:
    lines = ["# Model Benchmark — Session Script Quality\n"]
    lines.append(f"**Models tested:** {', '.join(MODELS.keys())}  ")
    lines.append(f"**Judge:** {JUDGE_MODEL}  ")
    lines.append(f"**Scenarios:** {len(SCENARIOS)}  \n")

    lines.append("## Results\n")
    header = "| Scenario | Model | JSON valid | Latency (s) | Cost ($) | Det. checks | Specificity | Embodiment | Voice | Restraint | Arc-fit | Judge avg | Human (1–7) |"
    sep    = "|---|---|---|---|---|---|---|---|---|---|---|---|---|"
    lines.append(header)
    lines.append(sep)

    for r in all_results:
        j = judgments.get(r["id"], {})
        scores = j.get("scores", {})

        def s(dim: str) -> str:
            return str(scores[dim]["score"]) if dim in scores else "—"

        det = "✅" if r["det_checks"]["pass"] else f"❌ {len(r['det_checks']['failures'])} fail"
        avg = str(j.get("avg", "—"))

        lines.append(
            f"| {r['scenario_label']} | {r['model_key']} "
            f"| {'✅' if r['json_valid'] else '❌'} "
            f"| {r['latency']} "
            f"| {r['cost_usd']} "
            f"| {det} "
            f"| {s('specificity')} | {s('embodiment')} | {s('voice')} | {s('restraint')} | {s('arc_fit')} "
            f"| {avg} | |"
        )

    lines.append("\n## Per-model summary\n")
    for model_key in MODELS:
        model_results = [r for r in all_results if r["model_key"] == model_key]
        avg_latency = round(sum(r["latency"] for r in model_results) / len(model_results), 1)
        total_cost = round(sum(r["cost_usd"] for r in model_results), 5)
        det_passes = sum(1 for r in model_results if r["det_checks"]["pass"])
        json_passes = sum(1 for r in model_results if r["json_valid"])

        judge_avgs = [judgments[r["id"]]["avg"] for r in model_results if r["id"] in judgments]
        quality_avg = round(sum(judge_avgs) / len(judge_avgs), 1) if judge_avgs else "—"

        lines.append(f"### {model_key}")
        lines.append(f"- Avg latency: {avg_latency}s")
        lines.append(f"- Total cost (4 scenarios): ${total_cost}")
        lines.append(f"- JSON valid: {json_passes}/4")
        lines.append(f"- Det. checks passed: {det_passes}/4")
        lines.append(f"- Judge avg quality: {quality_avg}/5")
        lines.append(f"- **Ship/no-ship:** _(fill in after reading scripts)_\n")

    lines.append("## Rationales (from judge)\n")
    for r in all_results:
        j = judgments.get(r["id"], {})
        if not j:
            continue
        lines.append(f"### {r['scenario_label']} — {r['model_key']}")
        for dim, val in j.get("scores", {}).items():
            lines.append(f"- **{dim}** ({val['score']}/5): {val['rationale']}")
        lines.append("")

    out = RESULTS_DIR / "comparison.md"
    out.write_text("\n".join(lines))
    return out

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  MindGym Model Benchmark")
    print("=" * 60)

    check_api_keys()
    print("  API keys: OK\n")

    all_results: list[dict] = []

    for scenario in SCENARIOS:
        print(f"  Scenario: {scenario['label']}")
        system, user = build_prompt_parts(scenario["inputs"])

        for model_key in MODELS:
            print(f"    → {model_key} ... ", end="", flush=True)
            try:
                result = call_model(model_key, system, user)
                det = run_deterministic_checks(scenario, result["data"])
                script_id = f"{scenario['id']}__{model_key.replace('-', '_')}"

                raw_file = RESULTS_DIR / f"{script_id}.json"
                raw_file.write_text(json.dumps({
                    "scenario": scenario,
                    "model": model_key,
                    "result": result,
                    "det_checks": det,
                }, indent=2))

                all_results.append({
                    "id": script_id,
                    "scenario_id": scenario["id"],
                    "scenario_label": scenario["label"],
                    "model_key": model_key,
                    **result,
                    "det_checks": det,
                })
                status = f"✅ {result['latency']}s" if result["json_valid"] else f"❌ JSON invalid"
                print(status)

            except Exception as e:
                print(f"❌ ERROR: {e}")
                all_results.append({
                    "id": f"{scenario['id']}__{model_key.replace('-', '_')}",
                    "scenario_id": scenario["id"],
                    "scenario_label": scenario["label"],
                    "model_key": model_key,
                    "raw": "",
                    "data": None,
                    "json_valid": False,
                    "latency": 0,
                    "cost_usd": 0,
                    "finish_reason": "error",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "det_checks": {"pass": False, "failures": [str(e)]},
                })

        print()

    print("  Running Opus judge (single call for all scripts)...")
    judgments = run_judge(all_results)
    print(f"  Judge returned scores for {len(judgments)} scripts.\n")

    report_path = write_report(all_results, judgments)
    print(f"  Report written to: {report_path}")
    print(f"  Raw scripts saved to: {RESULTS_DIR}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
