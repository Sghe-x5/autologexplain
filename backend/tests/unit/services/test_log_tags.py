from backend.services.log_tags import (
    ALLOWED_SEVERITIES,
    build_origin,
    detect_category,
    enrich_log_record,
    normalize_severity,
)


def test_meta_category_has_priority():
    row = {"metadata": {"category": "database"}, "service": "api", "message": "something"}
    category, reason = detect_category(row)
    assert category == "database"
    assert reason.startswith("from_metadata")


def test_keyword_classification_database():
    row = {"service": "postgres-writer", "message": "slow query", "metadata": {}}
    category, reason = detect_category(row)
    assert category == "database"
    assert "keyword" in reason


def test_keyword_classification_network():
    row = {"service": "proxy", "message": "Connection refused by upstream"}
    category, reason = detect_category(row)
    assert category == "network"
    assert "keyword" in reason


def test_normalize_severity_from_level_and_status():
    assert normalize_severity("WARN") == "warning"
    assert normalize_severity(None, status_code=502) == "critical"
    assert normalize_severity(None, status_code=404) == "error"


def test_enrich_log_record_builds_tags_and_origin():
    row = {
        "product": "maps",
        "service": "frontend",
        "environment": "prod",
        "level": "INFO",
        "message": "ui loaded",
    }

    enriched = enrich_log_record(row)

    assert enriched["category"] == "frontend"
    assert enriched["category_reason"].startswith("keyword")
    assert enriched["severity"] == "info"
    assert enriched["origin"] == "maps/frontend@prod"
    assert set(enriched["tags"]) == {"frontend", "info"}


def test_build_origin_handles_missing_parts():
    assert build_origin({"product": "", "service": "", "environment": "prod"}) == "prod"
    assert build_origin({"product": "app", "service": None, "environment": ""}) == "app"


def test_allowed_severities_sorted_unique():
    assert list(ALLOWED_SEVERITIES) == sorted(set(ALLOWED_SEVERITIES))
