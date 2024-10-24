from abc import ABC, abstractmethod
from typing import Literal, NoReturn


class BillExtractorBase(ABC):
    """Abstract base class for bill data extraction.

    This class serves as a template for implementing bill data extractors
    for different receipt/bill formats. It defines the common interface that
    all bill extractors should follow.

    Attributes:
        bill_data: Raw bill data to be processed.
    """

    def __init__(  # noqa: D107
            self,
            data: str,
            bill_type: Literal["html"],
        ) -> None:
        self.bill_data = data
        self.bill_type = bill_type

    @abstractmethod
    def extract_bill(self) -> NoReturn:
        """Extract and process bill data from the raw input.

        This method must be implemented by subclasses to parse and extract
        relevant information from the bill data according to their specific format.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        msg = "Subclass must implement abstract method"
        raise NotImplementedError(msg)
