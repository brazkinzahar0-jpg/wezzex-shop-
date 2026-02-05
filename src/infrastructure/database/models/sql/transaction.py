from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User

from uuid import UUID

from sqlalchemy import JSON, BigInteger, Boolean, Enum, ForeignKey, Integer
from sqlalchemy import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.enums import Currency, PaymentGatewayType, PurchaseType, TransactionStatus
from src.infrastructure.database.models.dto import PlanSnapshotDto, PriceDetailsDto

from .base import BaseSql
from .timestamp import TimestampMixin


class Transaction(BaseSql, TimestampMixin):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, unique=True)

    user_telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id"),
        nullable=False,
    )

    status: Mapped[TransactionStatus] = mapped_column(
        Enum(
            TransactionStatus,
            name="transaction_status",
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False)

    purchase_type: Mapped[PurchaseType] = mapped_column(Enum(PurchaseType), nullable=False)
    gateway_type: Mapped[PaymentGatewayType] = mapped_column(
        Enum(
            PaymentGatewayType,
            name="payment_gateway_type",
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )

    pricing: Mapped[PriceDetailsDto] = mapped_column(JSON, nullable=False)
    currency: Mapped[Currency] = mapped_column(
        Enum(
            Currency,
            name="currency",
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    plan: Mapped[PlanSnapshotDto] = mapped_column(JSON, nullable=False)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_telegram_id], lazy="selectin")
