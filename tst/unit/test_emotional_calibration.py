"""Unit tests for emotional calibration."""
import pytest

from src.lib.emotional_calibration import build_emotional_calibration


# --- anxiety_level_before → stress/energy/confidence bands ---

@pytest.mark.unit
@pytest.mark.parametrize('anxiety_level_before,expected', [
    (1, ('high', 'low', 'low')),
    (2, ('high', 'low', 'low')),
    (3, ('high', 'low', 'low')),
    (4, ('moderate', 'moderate', 'moderate')),
    (5, ('moderate', 'moderate', 'moderate')),
    (6, ('moderate', 'moderate', 'moderate')),
    (7, ('low', 'high', 'high')),
    (8, ('low', 'high', 'high')),
    (9, ('low', 'high', 'high')),
    (10, ('low', 'high', 'high')),
])
def test_intensity_bands_from_anxiety_level_before(
    anxiety_level_before: int, expected: tuple[str, str, str]
) -> None:
    """anxiety_level_before must map to correct stress/energy/confidence levels."""
    result = build_emotional_calibration(
        current_feeling='unsure',
        desired_feeling='confident',
        anxiety_level_before=anxiety_level_before,
        baseline_anxiety_level=5,
    )
    assert result['stress_level'] == expected[0]
    assert result['energy_level'] == expected[1]
    assert result['confidence_level'] == expected[2]


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
        baseline_anxiety_level=5,
    )
    assert result['primary_need'] == expected_primary_need


@pytest.mark.unit
def test_tone_arc_overwhelmed() -> None:
    """overwhelmed tone arc must be slow, body-first, no hype."""
    result = build_emotional_calibration(
        current_feeling='overwhelmed',
        desired_feeling='confident',
        anxiety_level_before=2,
        baseline_anxiety_level=5,
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
        baseline_anxiety_level=5,
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
        baseline_anxiety_level=5,
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
        baseline_anxiety_level=7,
    )
    assert result['current_feeling'] == 'overwhelmed'
    assert result['desired_feeling'] == 'confident'
    assert result['anxiety_level_before'] == 2
    assert result['baseline_anxiety_level'] == 7
    assert result['tone'] == 'slow and calming'


@pytest.mark.unit
def test_unknown_current_feeling_raises() -> None:
    """An unrecognised current_feeling must raise ValueError."""
    with pytest.raises(ValueError, match='Unknown current_feeling'):
        build_emotional_calibration(
            current_feeling='totally_fine',
            desired_feeling='confident',
            anxiety_level_before=5,
            baseline_anxiety_level=5,
        )
