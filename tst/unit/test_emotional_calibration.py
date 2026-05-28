"""Unit tests for emotional calibration."""
import pytest

from src.lib.emotional_calibration import build_emotional_calibration


# --- anxiety_level_before → stress band ---
# Scale: 1 = calm, 10 = extremely anxious. High anxiety → high stress.

@pytest.mark.unit
@pytest.mark.parametrize('anxiety_level_before,expected_stress', [
    (1, 'low'),
    (2, 'low'),
    (3, 'low'),
    (4, 'moderate'),
    (5, 'moderate'),
    (6, 'moderate'),
    (7, 'high'),
    (8, 'high'),
    (9, 'high'),
    (10, 'high'),
])
def test_stress_band_from_anxiety_level_before(
    anxiety_level_before: int, expected_stress: str
) -> None:
    """anxiety_level_before must map to the correct stress band."""
    result = build_emotional_calibration(
        current_feeling='unsure',
        desired_feeling='confident',
        anxiety_level_before=anxiety_level_before,
    )
    assert result['stress_level'] == expected_stress


@pytest.mark.unit
def test_energy_and_confidence_not_in_result() -> None:
    """energy_level and confidence_level must not be present — they are not derived."""
    result = build_emotional_calibration(
        current_feeling='unsure',
        desired_feeling='confident',
        anxiety_level_before=5,
    )
    assert 'energy_level' not in result
    assert 'confidence_level' not in result


# --- acknowledge_emotion ---
# Fires when anxiety >= 7 AND feeling is overwhelmed/discouraged/exhausted.
# The negative emotion is the real trigger; anxiety is just the gate.

@pytest.mark.unit
@pytest.mark.parametrize('current_feeling', ['overwhelmed', 'discouraged', 'exhausted'])
def test_acknowledge_emotion_fires_on_high_anxiety_and_negative_feeling(
    current_feeling: str,
) -> None:
    """acknowledge_emotion must be True when anxiety >= 7 and feeling is negative."""
    result = build_emotional_calibration(
        current_feeling=current_feeling,
        desired_feeling='confident',
        anxiety_level_before=7,
    )
    assert result['acknowledge_emotion'] is True


@pytest.mark.unit
@pytest.mark.parametrize('current_feeling', ['overwhelmed', 'discouraged', 'exhausted'])
def test_acknowledge_emotion_does_not_fire_on_low_anxiety(current_feeling: str) -> None:
    """acknowledge_emotion must be False when anxiety < 7, even with a negative feeling."""
    result = build_emotional_calibration(
        current_feeling=current_feeling,
        desired_feeling='confident',
        anxiety_level_before=6,
    )
    assert result['acknowledge_emotion'] is False


@pytest.mark.unit
@pytest.mark.parametrize('current_feeling', ['unsure', 'anxious but hopeful'])
def test_acknowledge_emotion_does_not_fire_on_non_negative_feelings(
    current_feeling: str,
) -> None:
    """acknowledge_emotion must be False for non-negative feelings even at high anxiety."""
    result = build_emotional_calibration(
        current_feeling=current_feeling,
        desired_feeling='confident',
        anxiety_level_before=9,
    )
    assert result['acknowledge_emotion'] is False


# --- current_feeling → primary_need and tone_arc ---

@pytest.mark.unit
@pytest.mark.parametrize('current_feeling,expected_primary_need', [
    ('overwhelmed', 'grounding before confidence'),
    ('discouraged', 'restore belief and self-worth'),
    ('exhausted', 'low-effort recovery and gentle readiness'),
    ('unsure', 'clarity and steady direction'),
    ('anxious but hopeful', 'channel nervous energy into confidence'),
])
def test_primary_need_from_current_feeling(
    current_feeling: str, expected_primary_need: str
) -> None:
    """current_feeling must drive the correct primary_need."""
    result = build_emotional_calibration(
        current_feeling=current_feeling,
        desired_feeling='confident',
        anxiety_level_before=3,
    )
    assert result['primary_need'] == expected_primary_need


@pytest.mark.unit
def test_tone_arc_overwhelmed() -> None:
    """overwhelmed tone arc must be slow, body-first, no hype."""
    result = build_emotional_calibration(
        current_feeling='overwhelmed',
        desired_feeling='confident',
        anxiety_level_before=2,
    )
    arc = result['tone_arc']
    assert arc['phase1'] == 'very slow, calming, body-first'
    assert arc['phase2'] == 'stabilizing and reassuring'
    assert arc['phase3'] == 'steady visualization, no hype'
    assert arc['phase4'] == 'warm evidence-based confidence'


@pytest.mark.unit
def test_tone_arc_anxious_but_hopeful() -> None:
    """anxious but hopeful arc must channel energy, not suppress it."""
    result = build_emotional_calibration(
        current_feeling='anxious but hopeful',
        desired_feeling='confident',
        anxiety_level_before=6,
    )
    arc = result['tone_arc']
    assert arc['phase1'] == 'steady breath, not too slow'
    assert arc['phase3'] == 'confident, vivid rehearsal'


# --- desired_feeling → phase5 landing ---

@pytest.mark.unit
@pytest.mark.parametrize('desired_feeling,expected_phase5', [
    ('calm', 'softer ending'),
    ('grounded', 'steady ending'),
    ('confident', 'stronger send-off'),
    ('focused', 'clear next-step ending'),
    ('clear_minded', 'uncluttered, simple ending'),
    ('composed', 'poised, controlled ending'),
])
def test_desired_feeling_shapes_phase5_landing(
    desired_feeling: str, expected_phase5: str
) -> None:
    """desired_feeling must refine the phase5 landing tone."""
    result = build_emotional_calibration(
        current_feeling='unsure',
        desired_feeling=desired_feeling,
        anxiety_level_before=4,
    )
    assert result['tone_arc']['phase5'] == expected_phase5


# --- passthrough fields ---

@pytest.mark.unit
def test_passthrough_fields_are_present() -> None:
    """Result must include all input fields for prompt rendering."""
    result = build_emotional_calibration(
        current_feeling='overwhelmed',
        desired_feeling='confident',
        anxiety_level_before=2,
    )
    assert result['current_feeling'] == 'overwhelmed'
    assert result['desired_feeling'] == 'confident'
    assert result['anxiety_level_before'] == 2
    assert result['tone'] == 'affirming, peak-performance priming'
    assert 'baseline_anxiety_level' not in result
    assert 'energy_level' not in result
    assert 'confidence_level' not in result


