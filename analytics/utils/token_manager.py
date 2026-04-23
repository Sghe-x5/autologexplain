import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import jwt
import yandexcloud
from dotenv import load_dotenv
from yandex.cloud.iam.v1.iam_token_service_pb2 import CreateIamTokenRequest
from yandex.cloud.iam.v1.iam_token_service_pb2_grpc import IamTokenServiceStub

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_ANALYTICS_ENV = Path(__file__).resolve().parents[1] / ".env"


class YandexCloudTokenManager:
    def __init__(self) -> None:
        """
        Инициализация менеджера токенов с загрузкой ключа из переменных окружения
        """
        self.iam_token: str | None = None
        self.expires_at: datetime | None = None
        self.token_lock = False
        self.service_account_key = self._load_config_from_env()

    def _load_config_from_env(self) -> dict:
        """
        Загружает конфигурацию сервисного аккаунта из переменных окружения

        :return: Словарь с данными сервисного аккаунта
        :raises: ValueError если переменные не заданы
        """
        load_dotenv(_ANALYTICS_ENV)
        config = {
            "id": os.getenv("YC_KEY_ID"),
            "service_account_id": os.getenv("YC_SERVICE_ACCOUNT_ID"),
            "private_key": os.getenv("YC_PRIVATE_KEY"),
        }

        if not all(config.values()):
            missing = [k for k, v in config.items() if not v]
            raise ValueError(f"Missing required env variables: {missing}")

        private_key = config["private_key"]
        if private_key is not None and "\\n" in private_key:
            config["private_key"] = private_key.replace("\\n", "\n")

        return config

    def _create_jwt(self) -> str:
        """
        Создает JWT токен для аутентификации

        :return: Закодированный JWT токен
        """
        now = int(time.time())
        payload = {
            "aud": "https://iam.api.cloud.yandex.net/iam/v1/tokens",
            "iss": self.service_account_key["service_account_id"],
            "iat": now,
            "exp": now + 3600,  # Токен действителен 1 час
        }

        return jwt.encode(
            payload,
            self.service_account_key["private_key"],
            algorithm="PS256",
            headers={"kid": self.service_account_key["id"]},
        )

    def _request_iam_token(self) -> str:
        """
        Запрашивает новый IAM токен у Yandex Cloud

        :return: IAM токен
        :raises: Exception при ошибке запроса
        """
        try:
            jwt_token = self._create_jwt()

            sdk = yandexcloud.SDK(service_account_key=self.service_account_key)
            iam_service = sdk.client(IamTokenServiceStub)
            response = iam_service.Create(CreateIamTokenRequest(jwt=jwt_token))

            return response.iam_token

        except Exception as e:
            logger.error(f"Failed to get IAM token: {str(e)}")
            raise

    def _is_token_expired(self) -> bool:
        """
        Проверяет, истек ли срок действия токена

        :return: True если токен истек или отсутствует
        """
        if not self.iam_token or not self.expires_at:
            return True

        return datetime.now() + timedelta(minutes=5) >= self.expires_at

    def get_token(self) -> str:
        """
        Возвращает текущий валидный IAM токен,
        при необходимости запрашивает новый

        :return: Актуальный IAM токен
        """
        if not self._is_token_expired() and self.iam_token is not None:
            return self.iam_token

        try:
            self.token_lock = True
            logger.info("Requesting new IAM token...")

            self.iam_token = self._request_iam_token()
            self.expires_at = datetime.now() + timedelta(hours=11)

            logger.info("Successfully updated IAM token")
            return self.iam_token

        finally:
            self.token_lock = False
