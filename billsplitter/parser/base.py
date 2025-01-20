from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from billsplitter.data_model.receipt import ReceiptModel


class BillParserBase(ABC):
    """Abstract base class for bill data extraction.

    This class serves as a template for implementing bill data extractors
    for different receipt/bill formats. It defines the common interface that
    all bill extractors should follow.

    Attributes:
        bill_data: Raw bill data to be processed.
    """

    @abstractmethod
    def extract_bill(self) -> ReceiptModel:
        """Extract and process bill data from the raw input.

        This method must be implemented by subclasses to parse and extract
        relevant information from the bill data according to their specific format.

        The returned dictionary should contain the following keys:
            - items: A

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        msg = "Subclass must implement abstract method"
        raise NotImplementedError(msg)
