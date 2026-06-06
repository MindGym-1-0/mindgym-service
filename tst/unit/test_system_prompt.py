from __future__ import annotations

import pytest

from src.prompts.resource_guidance import MAYA_TECHNIQUE_LIBRARY
from src.prompts.system_prompt import build_system_prompt


@pytest.mark.unit
def test_system_prompt_contains_technique_library():
    # Arrange
    prompt = build_system_prompt(is_event_linked=False)

    # Act / Assert
    assert "TECHNIQUE LIBRARY" in prompt


@pytest.mark.unit
def test_system_prompt_mentions_grounding_before_visualization():
    # Arrange
    prompt = build_system_prompt(is_event_linked=False)

    # Act — use the canonical phase headers, not bare "Phase N" which also
    # appears inside the technique library in a different order
    ground_pos = prompt.index("Phase 2 — Ground")
    rehearse_pos = prompt.index("Phase 3 — Rehearse")

    # Assert — grounding phase must precede the rehearsal/visualization phase
    assert ground_pos < rehearse_pos


@pytest.mark.unit
def test_system_prompt_forbids_manifestation_language():
    # Arrange
    prompt = build_system_prompt(is_event_linked=False)

    # Act / Assert
    assert "HARD RULE" in prompt
    assert "manifestation" in prompt


@pytest.mark.unit
def test_build_system_prompt_includes_resource_guidance_both_variants():
    # Arrange
    event_linked_prompt = build_system_prompt(is_event_linked=True)
    open_context_prompt = build_system_prompt(is_event_linked=False)

    # Act / Assert — the technique library block reaches both Mode 1 and Mode 2
    assert MAYA_TECHNIQUE_LIBRARY in event_linked_prompt
    assert MAYA_TECHNIQUE_LIBRARY in open_context_prompt
