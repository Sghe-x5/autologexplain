import allure


@allure.feature("Logs Service")
@allure.story("/tree endpoint")
def test_get_products_services_tree(client, mock_logs_services_tree):
    with allure.step("GET /logs/tree"):
        resp = client.get("/logs/tree")

    with allure.step("Проверить статус 200"):
        assert resp.status_code == 200

    with allure.step("Проверить корректность структуры JSON"):
        data = resp.json()
        assert isinstance(data, list)
        assert "product" in data[0]
        assert "services" in data[0]


@allure.feature("Logs Service")
@allure.story("/health endpoint")
def test_health_check(client, mock_health_response):
    with allure.step("GET /logs/health"):
        resp = client.get("/logs/health")

    with allure.step("Проверить статус 200"):
        assert resp.status_code == 200

    with allure.step("Проверить поля status, clickhouse, redis"):
        data = resp.json()
        assert "status" in data
        assert "clickhouse" in data
        assert "redis" in data
