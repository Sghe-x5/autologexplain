"""
Unit tests for backend.services.log_clustering

Tests cover:
- _preprocess(): variable token replacement
- _token_similarity(): matching logic including wildcards
- _merge_template(): template update on merge
- DrainParser.add_log(): routing to existing or new groups
- extract_templates(): end-to-end clustering
"""

from backend.services.log_clustering import (
    DrainParser,
    LogGroup,
    _merge_template,
    _preprocess,
    _token_similarity,
    extract_templates,
)


# ─── _preprocess ─────────────────────────────────────────────────────────────────

def test_preprocess_strips_ip():
    assert "10.0.0.1" not in _preprocess("Connected to 10.0.0.1:5432")
    assert "<*>" in _preprocess("Connected to 10.0.0.1:5432")


def test_preprocess_strips_uuid():
    msg = "Request 550e8400-e29b-41d4-a716-446655440000 failed"
    assert "550e8400" not in _preprocess(msg)
    assert "<*>" in _preprocess(msg)


def test_preprocess_strips_numbers():
    assert "<*>" in _preprocess("Retried 42 times")


def test_preprocess_strips_quoted_string():
    assert "<*>" in _preprocess('Table "users" not found')


def test_preprocess_lowercases():
    assert _preprocess("ERROR: Disk Full") == _preprocess("error: disk full")


def test_preprocess_strips_hex():
    assert "<*>" in _preprocess("address 0xDEADBEEF")


# ─── Unit-suffix normalisation ──────────────────────────────────────────────────
# Regression guard: numbers glued to common unit suffixes (ms / s / MB / %)
# must collapse to "<*>" just like bare integers, otherwise Drain produces
# duplicate clusters (e.g. "timeout after 100ms ..." and "timeout after <*> ...")
# for the same template.

def test_preprocess_strips_time_unit_ms():
    assert _preprocess("took 100ms") == "took <*>"


def test_preprocess_strips_time_unit_seconds():
    assert _preprocess("retry after 30s") == "retry after <*>"


def test_preprocess_strips_size_unit_mb():
    assert _preprocess("allocated 500MB") == "allocated <*>"


def test_preprocess_strips_percent():
    assert _preprocess("disk 75% full") == "disk <*> full"


def test_preprocess_strips_microseconds():
    assert _preprocess("latency 250us") == "latency <*>"


def test_unit_and_bare_numbers_produce_same_template():
    """'100ms' and '5000' in the same slot must end up in one cluster."""
    logs = [
        {"message": "db timeout after 100ms on pool"},
        {"message": "db timeout after 5000 on pool"},
        {"message": "db timeout after 30s on pool"},
        {"message": "db timeout after 2m on pool"},
    ]
    result = extract_templates(logs)
    assert result["unique_templates"] == 1
    assert result["templates"][0]["count"] == 4


# ─── _token_similarity ────────────────────────────────────────────────────────────

def test_similarity_identical_tokens():
    t = ["connection", "refused"]
    assert _token_similarity(t, t) == 1.0


def test_similarity_different_length_is_zero():
    assert _token_similarity(["a", "b"], ["a"]) == 0.0


def test_similarity_partial_match():
    template = ["connection", "to", "<*>", "refused"]
    tokens   = ["connection", "to", "db", "refused"]
    # 3 out of 4 positions match (wildcard counts as match)
    assert _token_similarity(template, tokens) == 1.0


def test_similarity_no_match():
    t1 = ["foo", "bar"]
    t2 = ["baz", "qux"]
    assert _token_similarity(t1, t2) == 0.0


def test_similarity_wildcard_always_matches():
    template = ["<*>", "<*>"]
    tokens   = ["anything", "here"]
    assert _token_similarity(template, tokens) == 1.0


# ─── _merge_template ─────────────────────────────────────────────────────────────

def test_merge_same_tokens_unchanged():
    result = _merge_template(["connection", "refused"], ["connection", "refused"])
    assert result == ["connection", "refused"]


def test_merge_different_tokens_become_wildcard():
    result = _merge_template(["connection", "refused"], ["connection", "timeout"])
    assert result == ["connection", "<*>"]


def test_merge_existing_wildcard_preserved():
    result = _merge_template(["<*>", "failed"], ["db", "failed"])
    assert result == ["<*>", "failed"]


# ─── DrainParser ─────────────────────────────────────────────────────────────────

def test_identical_messages_same_group():
    parser = DrainParser()
    g1 = parser.add_log("connection refused")
    g2 = parser.add_log("connection refused")
    assert g1.id == g2.id
    assert g1.log_count == 2


def test_structurally_similar_messages_same_group():
    parser = DrainParser()
    g1 = parser.add_log("connection to 10.0.0.1 refused")
    g2 = parser.add_log("connection to 10.0.0.2 refused")
    assert g1.id == g2.id
    assert "<*>" in g1.template


def test_structurally_different_messages_different_groups():
    parser = DrainParser()
    g1 = parser.add_log("disk is full")
    g2 = parser.add_log("connection refused by server")
    assert g1.id != g2.id


def test_different_length_messages_different_groups():
    parser = DrainParser()
    g1 = parser.add_log("error")
    g2 = parser.add_log("connection timeout error")
    assert g1.id != g2.id


def test_get_templates_sorted_by_count():
    parser = DrainParser()
    for _ in range(5):
        parser.add_log("database connection failed")
    parser.add_log("disk write error")
    parser.add_log("disk write error")

    templates = parser.get_templates()
    assert templates[0].log_count >= templates[1].log_count


def test_template_generalises_variable_parts():
    parser = DrainParser()
    parser.add_log("query timeout after 3 seconds")
    parser.add_log("query timeout after 10 seconds")
    templates = parser.get_templates()
    assert len(templates) == 1
    # The number should be replaced with <*>
    assert "<*>" in templates[0].template


def test_log_group_to_dict():
    g = LogGroup(id=0, template_tokens=["foo", "<*>"], log_count=3)
    d = g.to_dict()
    assert d["id"]    == 0
    assert d["count"] == 3
    assert "<*>" in d["template"]


# ─── extract_templates ────────────────────────────────────────────────────────────

def test_extract_templates_empty():
    result = extract_templates([])
    assert result["total_logs"] == 0
    assert result["templates"]  == []


def test_extract_templates_returns_required_keys():
    logs = [{"message": "connection refused"} for _ in range(3)]
    result = extract_templates(logs)
    assert "templates"        in result
    assert "clustered_logs"   in result
    assert "total_logs"       in result
    assert "unique_templates" in result


def test_extract_templates_clusters_similar_messages():
    logs = [
        {"message": "connection to 10.0.0.1 refused"},
        {"message": "connection to 10.0.0.2 refused"},
        {"message": "connection to 10.0.0.3 refused"},
        {"message": "disk is full on /dev/sda1"},
    ]
    result = extract_templates(logs)
    # 4 messages → at most 2 clusters (3 connection + 1 disk)
    assert result["unique_templates"] <= 2
    assert result["total_logs"] == 4


def test_extract_templates_clustered_logs_count_matches_input():
    logs = [{"message": f"error {i}"} for i in range(10)]
    result = extract_templates(logs)
    assert len(result["clustered_logs"]) == 10


def test_extract_templates_respects_top_n():
    logs = [{"message": f"unique error message variant number {i} here"} for i in range(30)]
    result = extract_templates(logs, top_n=5)
    assert len(result["templates"]) <= 5
