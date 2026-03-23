from backend.services.postmortem import PostmortemInput, generate_postmortem


def _incident():
    return {
        "incident_id": "inc-42",
        "fingerprint": "abc1234567",
        "title": "payments-api:backend:error anomaly",
        "status": "open",
        "service": "payments-api",
        "environment": "prod",
        "category": "backend",
        "severity": "error",
        "opened_at": "2026-04-23T12:00:00+00:00",
        "acknowledged_at": None,
        "mitigated_at": None,
        "resolved_at": None,
        "root_cause_service": "postgres-writer",
        "root_cause_score": 0.87,
        "impact_score": 2.5,
        "burn_rate_1h": 42.0,
        "affected_services": 3,
        "context_json": '{"rca_breakdown": {"anomaly": 0.3, "earliness": 1.0, "fanout": 0.5, "criticality": 0.8}}',
    }


def test_minimal_input_produces_markdown():
    md = generate_postmortem(PostmortemInput(incident=_incident()))
    assert "# Postmortem" in md
    assert "payments-api" in md
    assert "postgres-writer" in md  # root cause


def test_rca_breakdown_rendered():
    md = generate_postmortem(PostmortemInput(incident=_incident()))
    assert "anomaly" in md
    assert "earliness" in md
    assert "0.300" in md or "0.30" in md  # breakdown value


def test_sections_present():
    md = generate_postmortem(PostmortemInput(incident=_incident()))
    for section in [
        "## 1. Summary",
        "## 2. Timing",
        "## 3. Root cause",
        "## 4. Evidence",
        "## 5. Timeline",
        "## 6. Похожие инциденты",
        "## 7. Action items",
        "## 8. Lessons learned",
    ]:
        assert section in md


def test_similar_incidents_rendered_as_table():
    inp = PostmortemInput(
        incident=_incident(),
        similar_incidents=[
            {
                "incident_id": "inc-1",
                "score": 0.9,
                "incident": {
                    "service": "payments-api",
                    "category": "backend",
                    "severity": "error",
                    "opened_at": "2026-04-20T10:00:00+00:00",
                },
            }
        ],
    )
    md = generate_postmortem(inp)
    # Table header
    assert "| # | Service" in md
    # Row
    assert "| 1 |" in md


def test_timeline_events_ordered():
    inp = PostmortemInput(
        incident=_incident(),
        timeline_events=[
            {"event_type": "opened", "event_time": "2026-04-23T12:00:00+00:00", "actor": "system", "payload": {}},
            {"event_type": "rca_recomputed", "event_time": "2026-04-23T12:05:00+00:00", "actor": "rca-worker", "payload": {"root_cause_service": "postgres-writer", "root_cause_score": 0.87}},
        ],
    )
    md = generate_postmortem(inp)
    opened_pos = md.find("Инцидент открыт")
    rca_pos = md.find("RCA пересчитан")
    assert opened_pos > 0 and rca_pos > opened_pos
