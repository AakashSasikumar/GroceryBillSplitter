from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from billsplitter.data_model.receipt import ReceiptModel


class BaseSplitter(ABC):
    def __init__(
            self,
            receipt: ReceiptModel,
            participants: list[str],
        ):
        self.receipt = receipt

        if not participants:
            msg = "Participants list cannot be empty"
            raise ValueError(msg)

        self.participants = participants

    @abstractmethod
    def split_bill(self):
        """Splits the Receipt."""
        pass
