import uuid
from decimal import Decimal
from typing import Any, Final
from uuid import UUID

import orjson
from aiogram import Bot
from fastapi import Request
from httpx import AsyncClient, HTTPStatusError
from loguru import logger

from src.core.config import AppConfig
from src.core.enums import TransactionStatus
from src.infrastructure.database.models.dto import (
    PaymentGatewayDto,
    PaymentResult,
    PlategaGatewaySettingsDto,
)

from .base import BasePaymentGateway


class PlategaGateway(BasePaymentGateway):
    """
    Platega.io payment gateway implementation.

    Documentation: https://docs.platega.io/
    """

    _client: AsyncClient

    API_BASE: Final[str] = "https://app.platega.io"
    # Payment method: 2 = SBP QR (можно настроить через настройки в будущем)
    DEFAULT_PAYMENT_METHOD: Final[int] = 2

    def __init__(self, gateway: PaymentGatewayDto, bot: Bot, config: AppConfig) -> None:
        super().__init__(gateway, bot, config)

        if not isinstance(self.data.settings, PlategaGatewaySettingsDto):
            raise TypeError(
                f"Invalid settings type: expected {PlategaGatewaySettingsDto.__name__}, "
                f"got {type(self.data.settings).__name__}"
            )

        # Проверяем наличие обязательных настроек
        if not self.data.settings.merchant_id or not self.data.settings.api_secret:
            raise ValueError("Platega gateway requires merchant_id and api_secret to be configured")

        # Создаем HTTP клиент с базовыми заголовками авторизации
        self._client = self._make_client(
            base_url=self.API_BASE,
            headers={
                "X-MerchantId": self.data.settings.merchant_id,  # type: ignore[dict-item]
                "X-Secret": self.data.settings.api_secret.get_secret_value(),  # type: ignore[union-attr]
                "Content-Type": "application/json",
            },
        )

    async def handle_create_payment(self, amount: Decimal, details: str) -> PaymentResult:
        """
        Создает платежную транзакцию в Platega и возвращает ссылку на оплату.

        Args:
            amount: Сумма платежа
            details: Описание платежа

        Returns:
            PaymentResult с ID транзакции и URL для оплаты

        Raises:
            HTTPStatusError: При ошибке HTTP запроса
            KeyError: При отсутствии обязательных полей в ответе
        """
        # Генерируем уникальный ID для заказа (будет использован как externalId)
        order_id = str(uuid.uuid4())
        payload = await self._create_payment_payload(str(amount), order_id, details)

        try:
            response = await self._client.post("transaction/process", json=payload)
            response.raise_for_status()
            data = orjson.loads(response.content)
            return self._get_payment_data(data, order_id)

        except HTTPStatusError as exception:
            logger.error(
                f"HTTP error creating Platega payment. "
                f"Status: '{exception.response.status_code}', Body: {exception.response.text}"
            )
            raise
        except (KeyError, orjson.JSONDecodeError) as exception:
            logger.error(f"Failed to parse Platega response. Error: {exception}")
            raise
        except Exception as exception:
            logger.exception(f"An unexpected error occurred while creating Platega payment: {exception}")
            raise

    async def handle_webhook(self, request: Request) -> tuple[UUID, TransactionStatus]:
        """
        Обрабатывает webhook от Platega об изменении статуса транзакции.

        Platega отправляет POST запрос с заголовками X-MerchantId и X-Secret
        и JSON телом с данными транзакции.

        Args:
            request: FastAPI Request объект

        Returns:
            Кортеж (transaction_id, transaction_status)

        Raises:
            PermissionError: При неудачной верификации webhook
            ValueError: При отсутствии обязательных полей или неверном статусе
        """
        logger.debug("Received Platega webhook request")

        # Проверяем заголовки авторизации
        if not self._verify_webhook_headers(request):
            raise PermissionError("Platega webhook verification failed: invalid headers")

        webhook_data = await self._get_webhook_data(request)
        transaction_id_str = webhook_data.get("id")

        if not transaction_id_str:
            raise ValueError("Required field 'id' is missing in webhook payload")

        status = webhook_data.get("status")
        transaction_id = UUID(transaction_id_str)

        # Маппинг статусов Platega на внутренние статусы транзакций
        match status:
            case "CONFIRMED":
                transaction_status = TransactionStatus.COMPLETED
            case "CANCELED":
                transaction_status = TransactionStatus.CANCELED
            case "PENDING":
                # PENDING статус не обрабатываем через webhook, только CONFIRMED/CANCELED
                raise ValueError(f"Unexpected PENDING status in webhook. Transaction ID: {transaction_id_str}")
            case _:
                raise ValueError(f"Unsupported status: {status}")

        logger.info(
            f"Platega webhook processed successfully. "
            f"Transaction ID: {transaction_id_str}, Status: {status}"
        )

        return transaction_id, transaction_status

    async def _create_payment_payload(
        self, amount: str, order_id: str, description: str
    ) -> dict[str, Any]:
        """
        Создает payload для запроса создания транзакции.

        Args:
            amount: Сумма платежа
            order_id: Уникальный ID заказа
            description: Описание платежа

        Returns:
            Словарь с данными для запроса
        """
        return_url = await self._get_bot_redirect_url()

        return {
            "paymentMethod": self.DEFAULT_PAYMENT_METHOD,
            "paymentDetails": {
                "amount": float(amount),
                "currency": self.data.currency.value,
            },
            "description": description,
            "return": return_url,
            "failedUrl": return_url,  # Используем тот же URL для успеха и неудачи
            "payload": order_id,  # Сохраняем order_id в payload для отслеживания
        }

    def _get_payment_data(self, data: dict[str, Any], order_id: str) -> PaymentResult:
        """
        Извлекает данные платежа из ответа API.

        Args:
            data: Ответ от Platega API
            order_id: ID заказа, который был передан при создании (используется для логирования)

        Returns:
            PaymentResult с ID транзакции и URL для оплаты

        Raises:
            KeyError: При отсутствии обязательных полей в ответе
        """
        logger.debug(f"Processing Platega payment response. Order ID: {order_id}")
        transaction_id_str = data.get("transactionId")

        if not transaction_id_str:
            raise KeyError("Invalid response from Platega API: missing 'transactionId'")

        redirect_url = data.get("redirect")

        if not redirect_url:
            raise KeyError("Invalid response from Platega API: missing 'redirect'")

        # Используем transactionId от Platega как ID платежа
        return PaymentResult(id=UUID(transaction_id_str), url=str(redirect_url))

    def _verify_webhook_headers(self, request: Request) -> bool:
        """
        Проверяет заголовки авторизации webhook запроса.

        Platega отправляет заголовки X-MerchantId и X-Secret для верификации.

        Args:
            request: FastAPI Request объект

        Returns:
            True если заголовки валидны, False иначе
        """
        headers = request.headers
        received_merchant_id = headers.get("X-MerchantId")
        received_secret = headers.get("X-Secret")

        expected_merchant_id = self.data.settings.merchant_id  # type: ignore[union-attr]
        expected_secret = self.data.settings.api_secret.get_secret_value()  # type: ignore[union-attr]

        if not received_merchant_id or not received_secret:
            logger.warning("Platega webhook missing required headers")
            return False

        # Сравниваем значения заголовков с настройками
        merchant_id_valid = received_merchant_id == expected_merchant_id
        secret_valid = received_secret == expected_secret

        if not merchant_id_valid or not secret_valid:
            logger.critical(
                f"Platega webhook verification failed. "
                f"MerchantId match: {merchant_id_valid}, Secret match: {secret_valid}"
            )
            return False

        return True
