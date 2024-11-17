# ruff: noqa: G004

from __future__ import annotations

import logging
from decimal import Decimal

from pydantic import BaseModel, model_validator

logger = logging.getLogger(__name__)


class TaxModel(BaseModel):
    """Data model representing tax and fee items in a receipt."""
    name: str
    rate: int | None
    total: Decimal

    @model_validator(mode="after")
    def validate_tax_fields(self) -> None:
        if self.rate is not None and not 0 <= self.rate <= 100:  # noqa: PLR2004
            logger.warning(
                f"Tax '{self.name}' has invalid rate: {self.rate}. "
                "Rate should be between 0 and 1"
            )

        if self.total < Decimal(0):
            logger.warning(f"Tax '{self.name}' has negative amount: {self.amount}")

        return self
