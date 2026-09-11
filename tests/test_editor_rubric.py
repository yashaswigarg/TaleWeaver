import pytest
from taleweaver.state import EditorCritique


def test_editor_rubric_schema_and_defaults():
    critique = EditorCritique(
        approved=True,
        score=9,
        pacing_score=8.5,
        lore_consistency_score=9.0,
        character_voice_score=9.5,
        composite_score=9.0,
        critique="Masterful tension and dialogue.",
        required_fixes=[],
    )
    assert critique.approved is True
    assert critique.pacing_score == 8.5
    assert critique.lore_consistency_score == 9.0
    assert critique.composite_score == 9.0


def test_editor_rejection_criteria():
    critique = EditorCritique(
        approved=False,
        score=5,
        pacing_score=5.0,
        lore_consistency_score=6.0,
        character_voice_score=5.5,
        composite_score=5.5,
        critique="The dialogue felt modern and out of character.",
        required_fixes=["Rewrite dialogue to match archaic fantasy tone"],
    )
    assert critique.approved is False
    assert critique.composite_score < 7.0
    assert len(critique.required_fixes) == 1
