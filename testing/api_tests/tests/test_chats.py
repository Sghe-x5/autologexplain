import allure


@allure.feature("Chats")
@allure.story("/new endpoint")
def test_create_chat_anonymous(client):
    with allure.step("Отправить POST /chats/new без параметров"):
        resp = client.post("/chats/new")
    with allure.step("Проверить, что статус 200"):
        assert resp.status_code == 200
    with allure.step("Проверить наличие chat_id и token в ответе"):
        data = resp.json()
        assert "chat_id" in data
        assert "token" in data


@allure.feature("Chats")
@allure.story("/renew endpoint")
def test_renew_chat_token_success(client):
    with allure.step("Создать чат POST /chats/new"):
        create_resp = client.post("/chats/new")
        chat_id = create_resp.json()["chat_id"]

    with allure.step("Использовать chat_id для POST /chats/renew"):
        resp = client.post("/chats/renew", params={"chat_id": chat_id})

    with allure.step("Проверить, что вернулся новый токен"):
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["chat_id"] == chat_id


@allure.feature("Chats")
@allure.story("/renew endpoint")
def test_renew_chat_token_not_found(client):
    with allure.step("Отправить POST /chats/renew с несуществующим chat_id"):
        resp = client.post("/chats/renew", params={"chat_id": "non_existing_chat"})

    with allure.step("Проверить статус 404 и деталь ошибки"):
        assert resp.status_code == 404
        data = resp.json()
        assert data["detail"] == "chat_not_found"
