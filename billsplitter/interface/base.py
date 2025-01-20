from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from billsplitter.data_model.receipt import ReceiptModel
    from billsplitter.data_model.split import BillSplitModel


class BaseInterface(ABC):
    @abstractmethod
    def collect_split(self, receipt_data: ReceiptModel) -> BillSplitModel:
        pass

    @abstractmethod
    def display_split(self, split_data: BillSplitModel) -> None:
        pass
