from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from bs4 import BeautifulSoup

from splitmybill.data_model.receipt import ItemModel, ReceiptModel, TaxModel
from splitmybill.parser import BillParserBase


class InstacartHTMLConstants:
    """Constants for parsing Instacart HTML receipt tables.

    This class contains the HTML class names used to identify and extract
    information from Instacart receipt tables.

    Attributes:
        adjusted_items_table_class: HTML class for the adjustments items table.
        found_items_table_class: HTML class for the delivered items table.
    """
    adjusted_items_table_class = "items adjustments"
    found_items_table_class = "items delivered"

    items_block_class = ".item-block"
    items_wanted_class = ".item-wanted .item-name"
    items_delivered_class = ".item-delivered .item-name"
    items_delivered_price_class = ".item-delivered .total"

    items_name_class = ".item-name"
    item_quantity_class = ".item-name .muted"
    items_price_class = ".item-price .total"

    charges_table_class = "charges"
    charge_type_class = ".charge-type"
    charge_amount_class = ".amount"
    charge_final_name = "Total CAD"

    ignore_keys: ClassVar[list[str]] = ["Instacart+ Member Free Delivery!"]


class InstacartParser(BillParserBase):
    """Extractor for parsing Instacart HTML receipts.

    This class implements the bill extraction logic specifically for Instacart
    receipts in HTML format. It parses the HTML structure to extract items,
    prices, and other relevant billing information.

    Args:
        bill_data: Raw HTML content of the Instacart receipt.
        bill_type: Format of the bill, defaults to "html".
    """
    def __init__(
            self,
            bill_data: str,
            *args,
            **kwargs
    ) -> None:
        """Initialize the Instacart receipt extractor.

        Args:
            bill_data: Raw HTML content of the Instacart receipt to be parsed.
        """
        self.bill_data = bill_data
        self._make_soup()

    def extract_bill(self)  -> ReceiptModel:
        """Extract all relevant information from the Instacart receipt.

        Processes the HTML receipt to extract adjusted items, found items, and order totals.

        Returns:
            A dictionary containing:
                - 'adjusted_items': List of items that were adjusted (refunded/modified)
                - 'found_items': List of items that were actually delivered
                - 'order_totals': Dictionary of various total amounts in the order

            Each item in the lists is a dictionary containing item details like
            name, price, and quantity.
        """
        adjusted_items = self._extract_adjusted_items()
        found_items = self._extract_found_items()
        taxes_and_fess, subtotal, total = self._extract_order_totals()

        return ReceiptModel(
            items=adjusted_items + found_items,
            taxes_and_fees=taxes_and_fess,
            subtotal=subtotal,
            total=total
        )

    @classmethod
    def is_valid_html(cls, bill_data: str) -> bool:
        """Check if the given HTML content is parseable by InstacartParser.

        Args:
            bill_data (str): The HTML content of the receipt to check

        Returns:
            bool: True if the content appears to be a parseable Instacart receipt
        """
        key_markers = [
            InstacartHTMLConstants.adjusted_items_table_class,
            InstacartHTMLConstants.found_items_table_class,
            InstacartHTMLConstants.charges_table_class
        ]

        matches = sum(1 for marker in key_markers if marker in bill_data)
        return matches >= 2  # noqa: PLR2004

    def _make_soup(self) -> None:
        self.soup = BeautifulSoup(self.bill_data, "html.parser")

    def _extract_adjusted_items(self) -> list[ItemModel]:
        adjusted_table = \
            self.soup.find("table",
                           {"class": InstacartHTMLConstants.adjusted_items_table_class})
        items = []

        if adjusted_table is None:
            return items

        for item in adjusted_table.select(InstacartHTMLConstants.items_block_class):
            metadata = {}
            if "weight adjustment" in item.text:
                info = \
                    item.select_one(InstacartHTMLConstants.items_name_class).text.strip().splitlines()
                wanted = info[0]
                delivered = info[0]
                for data in info:
                    if "Adjustment" in data:
                        parsed_data = data.split(" ")
                        original_quantity = parsed_data[1]
                        adjusted_quantity = parsed_data[4]
                        metadata["weight_unit"] = "kg"
                wanted += f" ({original_quantity})"
                delivered += f" ({adjusted_quantity})"
                quantity = Decimal(adjusted_quantity)
                item_name = f"REPLACED:{wanted}->{delivered}"
                delivered_prices = item.select(InstacartHTMLConstants.items_delivered_price_class)
                for price in delivered_prices:
                    if "strike" in price["class"]:
                        continue
                    delivered_price = Decimal(price.text.strip()[1:])
            elif "Refunded amount" in item.text:
                continue
            else:
                wanted = \
                    item.select_one(InstacartHTMLConstants.items_wanted_class).text.strip().splitlines()[0]
                delivered = \
                    item.select_one(InstacartHTMLConstants.items_delivered_class).text.strip().splitlines()[0]
                quantity = \
                    item.select_one(InstacartHTMLConstants.item_quantity_class).text.split("x")[0].strip()
                item_name = f"REPLACED:{wanted}->{delivered}"
                delivered_price = \
                    item.select_one(InstacartHTMLConstants.items_delivered_price_class).text.strip()[1:]
            items.append(
                ItemModel(
                    name=str(item_name),
                    quantity=Decimal(quantity),
                    subtotal=Decimal(delivered_price),
                    metadata=metadata
                )
            )
        return items

    def _extract_found_items(self) -> list[ItemModel]:
        found_table = \
            self.soup.find("table",
                           {"class": InstacartHTMLConstants.found_items_table_class})
        items = []
        for item in found_table.select(InstacartHTMLConstants.items_block_class):
            metadata = {}
            delivered = \
                item.select_one(InstacartHTMLConstants.items_name_class).text.strip().splitlines()[0]
            prices = item.select(InstacartHTMLConstants.items_price_class)
            for price_soup in prices:
                if "strike" in price_soup["class"]:
                    continue
                price = Decimal(price_soup.text.strip()[1:])
            quantity = \
                item.select_one(InstacartHTMLConstants.item_quantity_class).text.split("x")[0].strip().split()
            if len(quantity) > 1:
                metadata["weight_unit"] = quantity[1]
                quantity = quantity[0]
            else:
                quantity = Decimal(quantity[0])
            items.append(
                ItemModel(
                    name=str(delivered),
                    quantity=Decimal(quantity),
                    subtotal=Decimal(price),
                    metadata=metadata
                )
            )
        return items

    def _extract_order_totals(self) -> tuple[list[TaxModel], Decimal]:
        order_totals = []
        subtotal = None
        total = None
        charges_table = \
            self.soup.find("table", {"class": InstacartHTMLConstants.charges_table_class})
        for item in charges_table.find_all("tr"):
            charge_type = item.select_one(InstacartHTMLConstants.charge_type_class).text.strip()

            if charge_type in InstacartHTMLConstants.ignore_keys:
                continue

            raw_amount = item.select_one(InstacartHTMLConstants.charge_amount_class).text.strip()
            raw_amount = raw_amount.replace("$", "")
            charge_amount = Decimal(raw_amount)
            tax_model_item = TaxModel(
                name=str(charge_type),
                total=Decimal(charge_amount)
            )
            if str(charge_type) == "Items Subtotal":
                subtotal = Decimal(charge_amount)
                continue
            if str(charge_type) == "Total CAD":
                total = Decimal(charge_amount)
                continue
            order_totals.append(tax_model_item)

        return order_totals, subtotal, total
