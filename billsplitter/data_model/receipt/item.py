# ruff: noqa: G004

from __future__ import annotations

import logging
from decimal import Decimal

from pydantic import BaseModel, model_validator

logger = logging.getLogger(__name__)


class ItemModel(BaseModel):
    """Data model representing an individual item in a receipt."""
    name: str
    quantity: int | Decimal | None
    unit_price: Decimal | None = None
    subtotal: Decimal

    metadata: dict | None = None

    @model_validator(mode="after")
    def validate_item_fields(self) -> None:
        if self.quantity is not None and self.quantity <= 0:
            logger.warning(f"Item '{self.name}' has invalid quantity: {self.quantity}")

        if self.unit_price is not None and self.unit_price <= Decimal(0):
            logger.warning(f"Item '{self.name}' has invalid unit price: {self.unit_price}")

        if self.subtotal <= Decimal(0):
            logger.warning(f"Item '{self.name}' has invalid subtotal: {self.subtotal}")

        return self
