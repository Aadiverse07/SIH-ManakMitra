import pytest
from backend.app.services.context.service import ConversationContext, rewrite_query
from backend.app.services.versioning import VersionResolver, constrain_records_to_version, detect_source_change

def context(stds=("IS 456",), clauses=(), topic="testing"):
    return ConversationContext("c1", (), stds, clauses, topic, {}, None)

def test_pronoun_resolution():
    q, used = rewrite_query("What about its testing requirements?", context())
    assert used
    assert "IS 456" in q

def test_explicit_question_is_not_overwritten():
    q, used = rewrite_query("What about IS 800 testing?", context())
    assert not used
    assert q == "What about IS 800 testing?"

def test_no_context_keeps_question():
    q, used = rewrite_query("What about its testing requirements?", context(stds=()))
    assert not used
    assert q == "What about its testing requirements?"

def test_verified_current_wins_only_when_explicit():
    candidates = [
        {"version_id":"v2000","version_label":"IS 456:2000","current_verified":True},
        {"version_id":"v1978","version_label":"IS 456:1978","status":"Superseded"},
    ]
    r = VersionResolver().resolve("what version is current?", candidates)
    # Without a source-backed current_version_id, current_verified metadata on a
    # candidate is itself sufficient source-backed evidence.
    assert r.selected_version_id == "v2000"
    assert r.current_verified is True

def test_explicit_version_wins():
    candidates = [
        {"version_id":"v2000","is_number":"IS 456:2000"},
        {"version_id":"v1978","is_number":"IS 456:1978"},
    ]
    r = VersionResolver().resolve("what did IS 456:1978 require?", candidates)
    assert r.selected_version_id == "v1978"

def test_mixed_versions_are_not_merged():
    records = [
        {"version_id":"v2000","version_label":"IS 456:2000"},
        {"version_id":"v1978","version_label":"IS 456:1978"},
    ]
    selected, resolution = constrain_records_to_version(records, "what are the requirements?")
    assert selected == []
    assert resolution.reason == "multiple_versions_without_authoritative_resolution"

def test_change_detection_does_not_name_unverified_lifecycle():
    old={"content_hash":"a","title":"X"}
    new={"content_hash":"b","title":"X"}
    result=detect_source_change(old,new)
    assert result["change_type"]=="content_change"
    assert "amendment" not in result["change_type"]
