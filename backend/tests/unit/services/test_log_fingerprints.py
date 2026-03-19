from backend.services.log_fingerprints import (
    build_fingerprint_observation,
    enrich_log_record_with_fingerprint,
    make_fingerprint,
    normalize_message_template,
)


def test_normalize_message_template_masks_dynamic_tokens():
    raw = "Timeout 500 for req 123e4567-e89b-12d3-a456-426614174000 from 10.0.0.1"

    template = normalize_message_template(raw)

    assert "<num>" in template
    assert "<uuid>" in template
    assert "<ip>" in template


def test_normalize_message_template_masks_hex_ip_and_numeric_tokens():
    raw = "Read failed at 0xDEADBEEF from 192.168.1.5 after 3 retries"

    template = normalize_message_template(raw)

    assert template == "read failed at <hex> from <ip> after <num> retries"


def test_normalize_message_template_handles_none_and_empty_message():
    assert normalize_message_template(None) == ""
    assert normalize_message_template("") == ""
    assert normalize_message_template("   ") == ""


def test_make_fingerprint_is_stable():
    template = "db timeout for order <num>"

    fp1 = make_fingerprint(template, "orders", "database")
    fp2 = make_fingerprint(template, "orders", "database")

    assert fp1 == fp2


def test_same_message_with_different_uuids_has_same_fingerprint():
    msg1 = "Request 123e4567-e89b-12d3-a456-426614174000 failed in 42 ms"
    msg2 = "Request 123e4567-e89b-12d3-a456-426614174999 failed in 7 ms"

    fp1 = make_fingerprint(normalize_message_template(msg1), "orders", "backend")
    fp2 = make_fingerprint(normalize_message_template(msg2), "orders", "backend")

    assert fp1 == fp2


def test_same_message_with_different_service_has_different_fingerprint():
    template = normalize_message_template("Timeout after 42 ms")

    fp_orders = make_fingerprint(template, "orders", "backend")
    fp_payments = make_fingerprint(template, "payments", "backend")

    assert fp_orders != fp_payments


def test_same_message_with_different_category_has_different_fingerprint():
    template = normalize_message_template("Timeout after 42 ms")

    fp_backend = make_fingerprint(template, "orders", "backend")
    fp_network = make_fingerprint(template, "orders", "network")

    assert fp_backend != fp_network


def test_enrich_log_record_with_fingerprint_reuses_category_enrichment():
    row = {
        "product": "maps",
        "service": "postgres-writer",
        "environment": "prod",
        "level": "ERROR",
        "message": "Query timeout for shard 42",
        "metadata": {},
    }

    enriched = enrich_log_record_with_fingerprint(row)

    assert enriched["category"] == "database"
    assert enriched["message_template"] == "query timeout for shard <num>"
    assert enriched["fingerprint"]


def test_enrich_log_record_with_fingerprint_handles_missing_message():
    row = {
        "product": "maps",
        "service": "api",
        "environment": "prod",
        "level": "INFO",
        "message": None,
        "metadata": {"category": "backend"},
    }

    enriched = enrich_log_record_with_fingerprint(row)

    assert enriched["message_template"] == ""
    assert enriched["category"] == "backend"
    assert enriched["fingerprint"]


def test_build_fingerprint_observation_uses_timestamp_and_example_message():
    row = {
        "timestamp": "2024-12-01T10:00:00Z",
        "product": "maps",
        "service": "postgres-writer",
        "environment": "prod",
        "level": "ERROR",
        "message": "Query timeout for shard 42",
        "metadata": {},
    }

    observation = build_fingerprint_observation(row)

    assert observation["service"] == "postgres-writer"
    assert observation["category"] == "database"
    assert observation["message_template"] == "query timeout for shard <num>"
    assert observation["example_message"] == "Query timeout for shard 42"
    assert observation["occurrence_count"] == 1
